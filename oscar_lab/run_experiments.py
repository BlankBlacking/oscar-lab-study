#!/usr/bin/env python3
"""
Experiment runner for the OSCAR "conditional O(1)" study.

Scenarios
---------
e1  phase sweep      : N flows reach steady state, N-1 depart at t0,
                       sweep the survivor's batch phase offset.
e2  target-queue sweep: same departure, sweep Q_target / BDP (the paper uses 0.5).
e3  RTT misconfig     : single flow, config RTT = k * true RTT, sweep k.
e4  AI normalization  : N long flows, U_AI vs U_AI/n_hat.

Output: results/<name>.csv
Usage:
    python run_experiments.py e1
    python run_experiments.py all --seeds 3
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import asdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from oscar_sim import Config, Sim

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def run_one(**kw) -> dict:
    cfg = Config(**kw)
    s = Sim(cfg)
    r = s.run()
    # queue at t0
    q0 = float("nan")
    if s.t0 is not None and s.queue_samples:
        q0 = min(s.queue_samples, key=lambda x: abs(x[0] - s.t0))[1] / 1e3
    r["q_at_t0_kb"] = q0
    r.update({f"cfg_{k}": v for k, v in kw.items()})
    return r


def _write(name: str, rows: list[dict]) -> None:
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{name}.csv")
    keys = sorted({k for row in rows for k in row})
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for row in rows:
            w.writerow(row)
    print(f"wrote {path} ({len(rows)} rows)")


def e1(seeds: int = 3) -> None:
    rows = []
    for ph in [i / 8 for i in range(8)]:
        for sd in range(seeds):
            rows.append(run_one(
                n_flows=10, short_bytes=0.0, depart_at=5e-3,
                duration=12e-3, phase_frac=ph, seed=sd,
                q_target_frac=0.5,
            ))
    _write("e1_phase", rows)


def e2(seeds: int = 3) -> None:
    rows = []
    for q in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0]:
        for sd in range(seeds):
            rows.append(run_one(
                n_flows=10, short_bytes=0.0, depart_at=5e-3,
                duration=12e-3, seed=sd, q_target_frac=q,
                reset_batch_on_depart=True,
            ))
    _write("e2_qtarget", rows)


def e3(seeds: int = 1) -> None:
    """Coupled vs decoupled RTT misconfiguration, fine grid."""
    rows = []
    grid = [0.50, 0.60, 0.62, 0.64, 0.655, 0.6667, 0.68, 0.70, 0.85, 1.00]
    for mode in ["coupled", "decoupled"]:
        for k in grid:
            for sd in range(seeds):
                if mode == "coupled":
                    kw = dict(rtt_scale=k, est_scale=k)
                else:
                    kw = dict(rtt_scale=1.0, est_scale=k)
                r = run_one(
                    n_flows=1, short_bytes=0.0, duration=8e-3,
                    bdp_floor=1.0, seed=sd, **kw,
                )
                r["mode"] = mode
                r["k"] = k
                rows.append(r)
    _write("e3_rtt", rows)


def e5(seeds: int = 1) -> None:
    """Two-flow competition: one misconfigured flow vs one correct flow.

    coupled   : the misconfigured flow scales both D_target/BDP and tau/eps
    decoupled : it scales only tau/eps; D_target/BDP stay in true units
    """
    rows = []
    for mode in ["coupled", "decoupled"]:
        for k in [0.25, 0.30, 0.40, 0.50, 1.00]:
            if mode == "coupled":
                scales = ((k, k), (1.0, 1.0))
            else:
                scales = ((1.0, k), (1.0, 1.0))
            for sd in range(seeds):
                r = run_one(
                    n_flows=2, short_bytes=0.0, duration=20e-3,
                    bdp_floor=1.0, flow_scales=scales, seed=sd,
                )
                r["mode"] = mode
                r["k0"] = k
                rows.append(r)
    _write("e5_twoflow", rows)


def e6(seeds: int = 1) -> None:
    """2x2 attribution: {D_target/BDP true vs scaled} x {floor true vs scaled}."""
    rows = []
    for rs in [0.5, 1.0]:
        for ft in [False, True]:
            for es in [1.0, 0.5]:
                for sd in range(seeds):
                    r = run_one(
                        n_flows=1, short_bytes=0.0, duration=8e-3,
                        rtt_scale=rs, floor_true_rtt=ft, est_scale=es,
                        bdp_floor=1.0, seed=sd,
                    )
                    r["rtt_scale"] = rs
                    r["floor_true"] = ft
                    r["est_scale"] = es
                    rows.append(r)
    _write("e6_attribution", rows)


def e7(seeds: int = 1) -> None:
    """Two-flow 2x2 attribution, swept over k = the mis-scaled RTT factor.

    Cells (flow0 misconfigured, flow1 correct):
      coupled      (rtt_scale=k, est_scale=1, floor_scale=k)
      d_target_only(rtt_scale=k, est_scale=1, floor_scale=1)
      floor_only   (rtt_scale=1, est_scale=1, floor_scale=k)
      baseline     (1, 1, 1)
    """
    rows = []
    for k in [0.25, 0.40, 0.50, 0.60]:
        cells = {
            "coupled":       (k,   1.0, k),
            "d_target_only": (k,   1.0, 1.0),
            "floor_only":    (1.0, 1.0, k),
            "baseline":      (1.0, 1.0, 1.0),
        }
        for name, f0 in cells.items():
            scales = (f0, (1.0, 1.0, 1.0))
            for sd in range(seeds):
                r = run_one(
                    n_flows=2, short_bytes=0.0, duration=20e-3,
                    bdp_floor=1.0, flow_scales=scales, seed=sd,
                )
                r["k"] = k
                r["cell"] = name
                rows.append(r)
    _write("e7_twoway", rows)


def _thr_shares(r: dict) -> tuple[float, float, float]:
    """Return (share0%, share1%, thr_jain) from per_flow_thr."""
    thr = r["per_flow_thr"]
    s0, s1 = float(thr[0]), float(thr[1])
    tot = s0 + s1
    if tot <= 0:
        return float("nan"), float("nan"), float("nan")
    p0, p1 = 100.0 * s0 / tot, 100.0 * s1 / tot
    jain = (s0 + s1) ** 2 / (2.0 * (s0 * s0 + s1 * s1))
    return p0, p1, jain


def f1(seeds: int = 1) -> None:
    """F1 autocal matrix: E3 k=0.5, E5 coupled/decoupled, E6 worst cell × off/on."""
    rows = []
    matrix = [
        # (tag, kwargs for Config, needs two-flow metrics)
        ("e3_coupled_k0.5", dict(
            n_flows=1, short_bytes=0.0, duration=8e-3, bdp_floor=1.0,
            rtt_scale=0.5, est_scale=0.5,
        ), False),
        ("e5_coupled_k0.25", dict(
            n_flows=2, short_bytes=0.0, duration=20e-3, bdp_floor=1.0,
            flow_scales=((0.25, 0.25), (1.0, 1.0)),
        ), True),
        ("e5_decoupled_k0.5", dict(
            n_flows=2, short_bytes=0.0, duration=20e-3, bdp_floor=1.0,
            flow_scales=((1.0, 0.5), (1.0, 1.0)),
        ), True),
        ("e6_worst", dict(
            n_flows=1, short_bytes=0.0, duration=8e-3, bdp_floor=1.0,
            rtt_scale=0.5, floor_true_rtt=False, est_scale=1.0,
        ), False),
    ]
    for tag, base, two in matrix:
        for on in [False, True]:
            for sd in range(seeds):
                kw = dict(base)
                kw["rtt_autocal"] = on
                kw["seed"] = sd
                r = run_one(**kw)
                r["scenario"] = tag
                r["autocal"] = on
                if two:
                    p0, p1, tj = _thr_shares(r)
                    r["share0"] = p0
                    r["share1"] = p1
                    r["thr_jain"] = tj
                rows.append(r)
    _write("f1_autocal", rows)


def f1_ablation(seeds: int = 1) -> None:
    """D5 orthogonal ablation on the worst E3/E6 cell.

    Keep estimator recalibration off in the single-component rows so that
    ``floor_only`` and ``d_only`` mean exactly what their labels claim.
    """
    rows = []
    modes = [
        # name, master, D_target, floor, estimator tau/eps
        ("off",         False, False, False, False),
        ("floor_only",  True,  False, True,  False),
        ("d_only",      True,  True,  False, False),
        ("full",        True,  True,  True,  True),
    ]
    for name, ac, ad, af, ae in modes:
        for sd in range(seeds):
            r = run_one(
                n_flows=1, short_bytes=0.0, duration=8e-3, bdp_floor=1.0,
                rtt_scale=0.5, est_scale=0.5, seed=sd,
                rtt_autocal=ac, autocal_d=ad, autocal_floor=af,
                autocal_est=ae,
            )
            r["ablation"] = name
            rows.append(r)
    _write("f1_ablation", rows)


def e8(seeds: int = 1) -> None:
    """F2: physical hetero RTT. flow0 base, flow1 = alpha * base.

    calib:
      own — each flow uses its true RTT (oracle upper bound)
      min — both use the shorter (min) RTT
    Optionally +autocal.
    """
    rows = []
    rtt = 12e-6
    for alpha in [1.0, 1.5, 2.0, 3.0]:
        for calib in ["min", "own"]:
            for ac in [False, True]:
                for sd in range(seeds):
                    # flow0: prop_extra=0; flow1: (alpha-1)*rtt
                    extras = (0.0, (alpha - 1.0) * rtt)
                    r = run_one(
                        n_flows=2, short_bytes=0.0, duration=20e-3,
                        bdp_floor=1.0, seed=sd,
                        flow_prop_extra=extras,
                        hetero_calib=calib,
                        rtt_autocal=ac,
                    )
                    p0, p1, tj = _thr_shares(r)
                    r["alpha"] = alpha
                    r["calib"] = calib
                    r["autocal"] = ac
                    r["share0"] = p0
                    r["share1"] = p1
                    r["thr_jain"] = tj
                    r["share_ratio"] = (p1 / p0) if p0 > 1e-9 else float("nan")
                    rows.append(r)
    _write("e8_hetero", rows)


def f3(seeds: int = 1) -> None:
    """Optional smoke: mu_scale in {0.5, 1.0, 1.5}, single flow."""
    rows = []
    for m in [0.5, 1.0, 1.5]:
        for sd in range(seeds):
            r = run_one(
                n_flows=1, short_bytes=0.0, duration=8e-3,
                bdp_floor=1.0, mu_scale=m, seed=sd,
            )
            r["mu_scale"] = m
            rows.append(r)
    _write("f3_mu_scale", rows)


def e4(seeds: int = 2) -> None:
    rows = []
    for n in [10, 50, 100]:
        for norm in [False, True]:
            for sd in range(seeds):
                rows.append(run_one(
                    n_flows=n, short_bytes=0.0, duration=12e-3,
                    ai_norm=norm, seed=sd,
                ))
    _write("e4_ainorm", rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "which",
        choices=["e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8",
                 "f1", "f1_ablation", "f3", "all"],
    )
    ap.add_argument("--seeds", type=int, default=3)
    args = ap.parse_args()
    if args.which in ("e1", "all"):
        e1(args.seeds)
    if args.which in ("e2", "all"):
        e2(args.seeds)
    if args.which in ("e3", "all"):
        e3(args.seeds)
    if args.which in ("e5", "all"):
        e5(args.seeds)
    if args.which in ("e6", "all"):
        e6(args.seeds)
    if args.which in ("e7", "all"):
        e7(args.seeds)
    if args.which in ("f1", "all"):
        f1(args.seeds)
    if args.which in ("f1_ablation", "all"):
        f1_ablation(args.seeds)
    if args.which in ("e8", "all"):
        e8(args.seeds)
    if args.which in ("f3", "all"):
        f3(args.seeds)


if __name__ == "__main__":
    main()
