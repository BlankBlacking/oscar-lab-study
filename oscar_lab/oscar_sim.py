#!/usr/bin/env python3
"""
Single-bottleneck packet-level simulator for OSCAR (NSDI'26).

Purpose
-------
A minimal, dependency-free testbed to study ONE question:

    Is OSCAR's O(1)-step convergence conditional on the estimator
    sampling the drain/build transient?

It is deliberately NOT a reproduction of the paper's ns-3 setup.  It models:
  * one FIFO bottleneck port at rate mu, fixed-size packets, finite buffer
  * N sender-driven flows, each with (window w, rate r, inflight)
  * per-packet send timestamp + inflight echo (like OSCAR's header fields)
  * OSCAR's Batched Least Squares estimator (5 sufficient statistics)
  * OSCAR's control law: u_w, u_r, max/min, U_AI, U_HAI, unified u
  * a "stale reference" baseline that mimics HPCC's per-ACK repeated multiply

Everything is in bytes and seconds.

Quick start
-----------
    python oscar_sim.py --selftest
    python run_experiments.py e1
"""

from __future__ import annotations

import argparse
import heapq
import math
import random
from dataclasses import dataclass, field
from typing import List, Optional

INF = float("inf")


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
@dataclass
class Config:
    # network
    mu_true: float = 12.5e9          # bottleneck rate, bytes/s (100 Gbps)
    rtt_true: float = 12e-6          # true base RTT, seconds
    mtu: int = 4096                  # bytes
    buffer: float = 32e6             # bytes (32 MB, no drops by default)

    # OSCAR parameters
    tau_frac: float = 0.5            # tau = tau_frac * RTT_config
    q_target_frac: float = 0.5       # Q_target = q_target_frac * BDP
    u_ai: float = 0.001
    u_hai: float = 0.01
    bdp_floor: float = 0.0          # window floor as a fraction of BDP (0 = off)
    floor_true_rtt: bool = False     # legacy: if True, floor uses true-RTT BDP
    floor_scale: float = -1.0         # if >=0, floor BDP = mu * rtt_true * floor_scale

    # "misconfiguration" knobs (config / true)
    rtt_scale: float = 1.0           # D_target/BDP use rtt_true * rtt_scale
    est_scale: float = 1.0           # tau/eps use rtt_true * est_scale (decoupled knob)
    mu_scale: float = 1.0            # mu_config  = mu_scale  * mu_true
    flow_scales: tuple = ()          # optional per-flow ((rtt_scale, est_scale, [floor_scale]), ...)

    # F1: online RTT self-calibration from batch d_min
    rtt_autocal: bool = False        # master switch
    autocal_d: bool = True           # D_target <- (1+q_target_frac)*d_min
    autocal_floor: bool = True       # BDP floor <- mu * d_min
    autocal_est: bool = True         # also recalibrate tau/eps <- rtt_hat

    # F2: physical per-flow propagation asymmetry (true RTT differs)
    flow_prop_extra: tuple = ()      # per-flow added prop delay (seconds)
    hetero_calib: str = "own"        # "own" | "min" — how D_target/BDP are set initially

    # scenario
    n_flows: int = 10
    duration: float = 12e-3
    short_bytes: float = 2.5e6       # bytes each short flow sends (0 => all long)
    short_start: float = 1e-3        # when short flows start
    phase_frac: float = 0.0          # phase offset of flow 0's first batch
    depart_at: float = 0.0           # if >0: all flows except 0 stop at this time
    reset_batch_on_depart: bool = False  # align the survivor's next batch to t0
    seed: int = 1

    # variants
    ai_norm: bool = False            # U_AI / n_hat, n_hat = d*mu/inflight
    baseline: str = "oscar"          # "oscar" | "stale"
    short_unresponsive: bool = False # shorts blast at line rate, ignore CC

    # sampling / metrics
    sample_dt: float = 1e-5
    warmup_frac: float = 0.6
    conv_tol: float = 0.05           # +-5% of target
    conv_hold: float = 100e-6        # must stay in band this long


@dataclass
class Flow:
    fid: int
    remaining: float                 # bytes left (INF for long flow)
    phase: float = 0.0

    # per-flow control configuration (allows heterogeneous RTT misconfig)
    mu_c: float = 0.0
    rtt_c: float = 0.0
    tau: float = 0.0
    bdp_c: float = 0.0
    d_target: float = 0.0
    eps: float = 0.0
    floor_scale: float = -1.0
    floor_rtt_cfg: float = 0.0       # configured floor RTT (immune to D-only autocal)
    prop_extra: float = 0.0          # physical extra propagation (F2)
    rtt_true_flow: float = 0.0       # base RTT + prop_extra

    u: float = 1.0
    w: float = 0.0
    r: float = 0.0
    inflight: float = 0.0
    next_send: float = 0.0
    send_scheduled: bool = False

    # BLS batch accumulators
    batch_start: Optional[float] = None
    n: int = 0
    sx: float = 0.0
    sy: float = 0.0
    sxx: float = 0.0
    sxy: float = 0.0
    ssize: float = 0.0
    s_infl: float = 0.0
    d_min_batch: float = INF         # min delay in current batch (autocal)
    rtt_hat: float = INF             # running min-RTT estimate (online baseline)

    acked: float = 0.0
    sent: float = 0.0
    dropped: float = 0.0

    # stale-reference baseline
    d_ref: float = 0.0
    last_ref: float = 0.0


# --------------------------------------------------------------------------
# Simulator
# --------------------------------------------------------------------------
class Sim:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.rng = random.Random(cfg.seed)

        # true network
        self.mu = cfg.mu_true
        self.rtt = cfg.rtt_true

        # global configured values (mu is shared; RTT params are per-flow)
        self.mu_c = cfg.mu_true * cfg.mu_scale

        # flows
        self.flows: List[Flow] = []
        prop_extras = list(cfg.flow_prop_extra) if cfg.flow_prop_extra else [0.0] * cfg.n_flows
        while len(prop_extras) < cfg.n_flows:
            prop_extras.append(0.0)
        true_rtts = [cfg.rtt_true + pe for pe in prop_extras]
        min_true_rtt = min(true_rtts) if true_rtts else cfg.rtt_true

        for i in range(cfg.n_flows):
            is_long = (i == 0) or (cfg.short_bytes <= 0)
            remaining = INF if is_long else cfg.short_bytes
            if i < len(cfg.flow_scales):
                fc = cfg.flow_scales[i]
                rs, es = fc[0], fc[1]
                fs = fc[2] if len(fc) >= 3 else cfg.floor_scale
            else:
                rs, es, fs = cfg.rtt_scale, cfg.est_scale, cfg.floor_scale
            f = Flow(fid=i, remaining=remaining)
            f.mu_c = self.mu_c
            f.prop_extra = prop_extras[i]
            f.rtt_true_flow = true_rtts[i]
            # calibration base: physical hetero (F2) chooses own vs network-min RTT
            if cfg.hetero_calib == "min":
                calib_rtt = min_true_rtt
            else:
                calib_rtt = f.rtt_true_flow
            f.rtt_c = calib_rtt * rs
            f.tau = cfg.tau_frac * calib_rtt * es
            f.bdp_c = f.mu_c * f.rtt_c
            f.d_target = f.rtt_c * (1.0 + cfg.q_target_frac)
            f.eps = max(0.02 * calib_rtt * es, 0.05 * f.tau)
            f.phase = cfg.phase_frac * f.tau if i == 0 else 0.0
            f.floor_scale = fs
            f.u = 1.0
            floor_rtt = calib_rtt * (fs if fs >= 0 else (1.0 if cfg.floor_true_rtt else rs))
            f.floor_rtt_cfg = floor_rtt
            floor_bdp = f.mu_c * floor_rtt
            f.w = max(f.u * f.d_target * f.mu_c, max(cfg.bdp_floor * floor_bdp, cfg.mtu))
            f.r = f.u * f.mu_c
            if not is_long:
                f.next_send = cfg.short_start
                if cfg.short_unresponsive:
                    f.w = 1e18
                    f.r = cfg.mu_true
            self.flows.append(f)

        # queue / event loop
        self.server_free = 0.0
        self.heap: list = []
        self.seq = 0
        self.now = 0.0

        # metrics
        self.t0: Optional[float] = 0.0 if (cfg.short_bytes <= 0 and cfg.depart_at <= 0) else None
        self.u_at_t0: Optional[float] = (self.flows[0].u if self.t0 == 0.0 else None)
        self.acked_at_t0: float = 0.0
        self.acked_snapshot: list = [0.0] * cfg.n_flows
        self.conv_start: Optional[float] = None
        self.conv_time: Optional[float] = None
        self.trace: list = []          # (t, q_bytes, flow0.r, flow0.u, flow0.w)
        self.queue_samples: list = []  # (t, q_bytes)
        self.dropped = 0.0
        self.packets = 0
        self.acked_packets = 0
        self.ctrl_log: list = []

        self._init_events()

    # -- event helpers -----------------------------------------------------
    def _push(self, t: float, kind: str, fid: int, payload=None) -> None:
        self.seq += 1
        heapq.heappush(self.heap, (t, self.seq, kind, fid, payload))

    def _init_events(self) -> None:
        for f in self.flows:
            if f.remaining > 0:
                t = max(self.now, f.next_send)
                self._push(t, "send", f.fid)
                f.send_scheduled = True
        self._push(self.cfg.sample_dt, "sample", -1)
        if self.cfg.depart_at > 0:
            self._push(self.cfg.depart_at, "depart", -1)

    # -- main loop ---------------------------------------------------------
    def run(self) -> dict:
        end = self.cfg.duration
        while self.heap:
            t, _, kind, fid, payload = heapq.heappop(self.heap)
            if t > end:
                break
            self.now = t
            if kind == "send":
                self._on_send(fid)
            elif kind == "ack":
                self._on_ack(fid, payload)
            elif kind == "sample":
                self._on_sample()
                self._push(t + self.cfg.sample_dt, "sample", -1)
            elif kind == "depart":
                self._on_depart()
            self._maybe_set_t0()
        return self._result()

    # -- queue -------------------------------------------------------------
    def _backlog(self) -> float:
        return max(0.0, self.server_free - self.now) * self.mu

    # -- send --------------------------------------------------------------
    def _on_send(self, fid: int) -> None:
        f = self.flows[fid]
        f.send_scheduled = False
        if f.remaining <= 0:
            return
        if self.now + 1e-15 < f.next_send:
            self._push(f.next_send, "send", fid)
            f.send_scheduled = True
            return

        size = min(self.cfg.mtu, f.remaining)
        if f.inflight + size > f.w + 1e-9:
            # window is full: wait for an ACK to reschedule
            return

        f.remaining -= size
        f.sent += size
        f.inflight += size
        f.next_send = self.now + size / max(f.r, 1e3)

        backlog = self._backlog()
        if backlog + size > self.cfg.buffer:
            f.dropped += size
            f.inflight -= size
            self.dropped += size
        else:
            start = max(self.now, self.server_free)
            finish = start + size / self.mu
            self.server_free = finish
            qdelay = start - self.now
            delay = f.rtt_true_flow + qdelay
            pkt = (self.now, f.inflight, size, delay)
            self._push(self.now + delay, "ack", fid, pkt)
            self.packets += 1

        if f.remaining > 0 and f.inflight + self.cfg.mtu <= f.w:
            t = max(self.now, f.next_send)
            self._push(t, "send", fid)
            f.send_scheduled = True

    # -- ack ---------------------------------------------------------------
    def _on_ack(self, fid: int, pkt) -> None:
        f = self.flows[fid]
        send_ts, pkt_infl, size, delay = pkt
        f.inflight -= size
        f.acked += size
        self.acked_packets += 1

        if self.cfg.short_unresponsive and f.fid != 0:
            pass  # unresponsive shorts: no estimator, no control
        elif self.cfg.baseline == "stale":
            self._stale_update(f, delay)
        else:
            self._accumulate(f, send_ts, delay, size, pkt_infl)

        if f.remaining > 0 and not f.send_scheduled and f.inflight + self.cfg.mtu <= f.w:
            t = max(self.now, f.next_send)
            self._push(t, "send", fid)
            f.send_scheduled = True

    def _accumulate(self, f: Flow, send_ts: float, delay: float, size: float, pkt_infl: float) -> None:
        if f.batch_start is None:
            f.batch_start = send_ts - f.phase
        if f.n == 0:
            f.d_min_batch = delay
        else:
            f.d_min_batch = min(f.d_min_batch, delay)
        f.n += 1
        f.sx += send_ts
        f.sy += delay
        f.sxx += send_ts * send_ts
        f.sxy += send_ts * delay
        f.ssize += size
        f.s_infl += pkt_infl

        if send_ts - f.batch_start >= f.tau and f.n >= 3:
            self._control(f, send_ts)
            f.batch_start = send_ts
            f.n = 0
            f.sx = f.sy = f.sxx = f.sxy = f.ssize = f.s_infl = 0.0
            f.d_min_batch = INF

    # -- control -----------------------------------------------------------
    def _apply_autocal(self, f: Flow) -> Optional[float]:
        """Update D_target / floor from online min-RTT (batch d_min + running hat).

        Empty/unset batch: keep prior targets. Running hat only decreases so a
        standing queue cannot ratchet D_target upward (threat otherwise).
        """
        if not self.cfg.rtt_autocal:
            return None
        if f.n <= 0 or f.d_min_batch >= INF or f.d_min_batch <= 0.0:
            return None
        f.rtt_hat = min(f.rtt_hat, f.d_min_batch)
        d_min = f.rtt_hat
        if d_min >= INF or d_min <= 0.0:
            return None
        if self.cfg.autocal_d:
            f.d_target = d_min * (1.0 + self.cfg.q_target_frac)
            f.rtt_c = d_min
            f.bdp_c = f.mu_c * d_min
        if self.cfg.autocal_est:
            f.tau = self.cfg.tau_frac * d_min
            f.eps = max(0.02 * d_min, 0.05 * f.tau)
        return d_min

    def _control(self, f: Flow, send_ts: float) -> None:
        n = f.n
        delay = f.sy / n
        den = n * f.sxx - f.sx * f.sx
        if abs(den) < 1e-12:
            grad = 0.0
        else:
            grad = (n * f.sxy - f.sx * f.sy) / den
        infl = f.s_infl / n
        span = max(send_ts - f.batch_start, 1e-12)
        rate = f.ssize / span

        d_min = self._apply_autocal(f)

        if abs(delay - f.rtt_c) <= f.eps:
            f.u += self.cfg.u_hai
        else:
            u_w = infl / max(delay * f.mu_c, 1e-9)
            denom = 1.0 + grad
            if denom < 0.05:
                denom = 0.05
            u_r = rate / (denom * f.mu_c)
            u = max(u_w, u_r) if delay < f.d_target else min(u_w, u_r)
            if self.cfg.ai_norm:
                n_hat = max(1.0, delay * f.mu_c / max(infl, 1.0))
                u += self.cfg.u_ai / n_hat
            else:
                u += self.cfg.u_ai
            f.u = min(max(u, 1e-6), 50.0)

        if self.cfg.rtt_autocal and self.cfg.autocal_floor and d_min is not None:
            floor_rtt = d_min
        else:
            floor_rtt = f.floor_rtt_cfg
        floor_bdp = f.mu_c * floor_rtt
        f.w = max(f.u * f.d_target * f.mu_c, max(self.cfg.bdp_floor * floor_bdp, self.cfg.mtu))
        f.r = min(f.u * f.mu_c, 4.0 * self.mu)
        if f.fid == 0:
            self.ctrl_log.append((self.now, delay, grad, infl, rate, f.u, f.r, f.w, f.inflight, max(0.0, self.server_free-self.now)))

    def _stale_update(self, f: Flow, delay: float) -> None:
        """HPCC-like: w_r updated once per RTT and reused; the next RTT multiplies
        the already-reduced reference again, producing 1/2 -> 1/4 overreaction."""
        if f.d_ref == 0.0 or self.now - f.last_ref >= self.rtt:
            f.d_ref = max(delay, 1e-9)
            factor = f.d_target / f.d_ref
            f.w = min(max(f.w * factor, 0.01 * f.bdp_c), 4.0 * f.bdp_c)
            f.last_ref = self.now
        f.r = f.w / f.rtt_c

    # -- metrics -----------------------------------------------------------
    def _on_depart(self) -> None:
        for f in self.flows[1:]:
            f.remaining = 0.0
        self.t0 = self.now
        self.u_at_t0 = self.flows[0].u
        self.acked_at_t0 = self.flows[0].acked
        self.acked_snapshot = [f.acked for f in self.flows]
        if self.cfg.reset_batch_on_depart:
            f0 = self.flows[0]
            f0.batch_start = self.now
            f0.n = 0
            f0.sx = f0.sy = f0.sxx = f0.sxy = f0.ssize = f0.s_infl = 0.0
            f0.d_min_batch = INF

    def _maybe_set_t0(self) -> None:
        if self.t0 is not None or self.cfg.depart_at > 0:
            return
        # t0 = the moment the last competing flow stops *sending* (burst end),
        # not when the queue has drained.  The queue may still be large here.
        if all(f.remaining <= 0 for f in self.flows[1:]):
            self.t0 = self.now
            self.u_at_t0 = self.flows[0].u
            self.acked_at_t0 = self.flows[0].acked
            self.acked_snapshot = [f.acked for f in self.flows]

    def _on_sample(self) -> None:
        q = self._backlog()
        f0 = self.flows[0]
        self.queue_samples.append((self.now, q))
        self.trace.append((self.now, q, f0.r, f0.u, f0.w))

        if self.t0 is None:
            return
        target = self.mu  # one long flow left after shorts depart
        ok = abs(f0.r - target) / target < self.cfg.conv_tol
        if ok:
            if self.conv_start is None:
                self.conv_start = self.now
            if self.conv_time is None and self.now - self.conv_start >= self.cfg.conv_hold:
                self.conv_time = max(0.0, self.conv_start - self.t0)
        else:
            self.conv_start = None

    def _result(self) -> dict:
        f0 = self.flows[0]
        valid = self.t0 is not None and self.cfg.duration > self.t0
        t0 = self.t0 if self.t0 is not None else float("nan")
        dt = (self.cfg.duration - self.t0) if valid else float("nan")
        warm = max(self.t0, self.cfg.duration * self.cfg.warmup_frac) if valid else self.cfg.duration
        qs = [q for (t, q) in self.queue_samples if t >= warm]
        q_steady = sum(qs) / len(qs) if qs else float("nan")
        thr = (max(0.0, f0.acked - self.acked_at_t0) / dt) if valid else float("nan")
        # Jain index over u (long flows only; shorts are gone)
        us = [f.u for f in self.flows if f.remaining > 0]
        jain = (sum(us) ** 2) / (len(us) * sum(x * x for x in us)) if us else float("nan")
        first_g = float("nan")
        first_u = float("nan")
        if self.t0 is not None:
            for entry in self.ctrl_log:
                if entry[0] >= self.t0:
                    first_g = entry[2]
                    first_u = entry[5]
                    break
        return {
            "conv_time_us": (self.conv_time * 1e6) if self.conv_time is not None else float("nan"),
            "first_g": first_g,
            "first_u": first_u,
            "t0_us": t0 * 1e6,
            "u_at_t0": self.u_at_t0 if self.u_at_t0 is not None else float("nan"),
            "u_final": f0.u,
            "w_final_bdp": f0.w / f0.bdp_c,
            "q_steady_kb": q_steady / 1e3,
            "q_target_kb": (self.cfg.q_target_frac * f0.bdp_c) / 1e3,
            "q_target_true_kb": (self.cfg.q_target_frac * self.cfg.mu_true * self.cfg.rtt_true) / 1e3,
            "throughput_gbps": thr * 8 / 1e9,
            "thr_frac": thr / self.mu,
            "jain": jain,
            "per_flow_thr": [((f.acked - self.acked_snapshot[i]) / dt) if valid else float("nan") for i, f in enumerate(self.flows)],
            "per_flow_u": [f.u for f in self.flows],
            "per_flow_w_bdp": [f.w / f.bdp_c for f in self.flows],
            "drops_kb": self.dropped / 1e3,
            "packets": self.packets,
            "acked": self.acked_packets,
        }


# --------------------------------------------------------------------------
# Self-test
# --------------------------------------------------------------------------
def selftest() -> None:
    print("== S1: single flow, 100G, 12us RTT, D_target=1.5 RTT ==")
    cfg = Config(n_flows=1, short_bytes=0, duration=6e-3)
    r = Sim(cfg).run()
    print(r)
    assert 0.9 < r["thr_frac"] < 1.1, "single flow should fill the link"
    assert 60 < r["q_steady_kb"] < 95, "steady queue should be near 0.5 BDP (75 KB)"
    print("   OK: throughput and queue near target")

    print("\n== S2: two long flows, fairness ==")
    cfg = Config(n_flows=2, short_bytes=0, duration=8e-3)
    r = Sim(cfg).run()
    print(r)
    assert 0.85 < r["jain"] < 1.01, "two flows should be roughly fair"
    print("   OK: Jain ~ 1")

    print("\n== S3: stale-reference baseline should oscillate/overreact ==")
    cfg = Config(n_flows=2, short_bytes=0, duration=8e-3, baseline="stale")
    r = Sim(cfg).run()
    print(r)
    print("   (no hard assert: the point is qualitative overreaction)")

    print("\n== S4: microburst, long flow should recover ==")
    cfg = Config(n_flows=10, short_bytes=2.5e6, duration=12e-3)
    r = Sim(cfg).run()
    print(r)
    assert not math.isnan(r["conv_time_us"]), "long flow should converge"
    print("   OK: convergence time measured")

    print("\n== S5: rtt_autocal recovers coupled k=0.5 single-flow ==")
    cfg = Config(n_flows=1, short_bytes=0, duration=8e-3, bdp_floor=1.0,
                 rtt_scale=0.5, est_scale=0.5, rtt_autocal=True)
    r = Sim(cfg).run()
    print(r)
    assert r["thr_frac"] >= 0.85, f"autocal should pull thr back, got {r['thr_frac']}"
    print("   OK: autocal restores throughput")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
    else:
        print("use --selftest, or run run_experiments.py")


if __name__ == "__main__":
    main()
