#!/usr/bin/env python3
"""Plot the three core experiments from results/*.csv."""

import csv
import os
import statistics
import collections

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
OUT = os.path.join(HERE, "figs")
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 180, "savefig.bbox": "tight",
})


def read(name):
    with open(os.path.join(RES, f"{name}.csv"), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fnum(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def group_mean(rows, key, val):
    g = collections.defaultdict(list)
    for r in rows:
        k = fnum(r.get(key))
        v = fnum(r.get(val))
        if k is not None and v is not None:
            g[k].append(v)
    return {k: statistics.mean(v) for k, v in sorted(g.items())}


# ---- E1: phase ----------------------------------------------------------
rows = read("e1_phase")
d = group_mean(rows, "cfg_phase_frac", "conv_time_us")
fig, ax = plt.subplots(figsize=(5.4, 3.2))
ax.plot(list(d.keys()), list(d.values()), "o-", color="#c0392b", lw=1.4, ms=5)
ax.set_xlabel("Batch phase offset  (fraction of tau)")
ax.set_ylabel("Convergence time (us)")
ax.set_title("E1: recovery after N-1 flows depart (N=10, Q=0.5 BDP)")
ax.grid(True, ls=":", lw=0.5, color="0.85")
ax.text(0.02, 0.95, "all points 520-860 us = 43-72 RTT\n(paper reports ~25 us for a deep-queue microburst)",
        transform=ax.transAxes, fontsize=7.5, va="top", color="0.3")
fig.savefig(os.path.join(OUT, "e1_phase.png"))
plt.close(fig)

# ---- E2: target queue ---------------------------------------------------
rows = read("e2_qtarget")
dd = group_mean(rows, "cfg_q_target_frac", "conv_time_us")
fig, ax = plt.subplots(figsize=(5.6, 3.3))
ax.plot(list(dd.keys()), list(dd.values()), "o-", lw=1.4, ms=5, color="#2c3e50",
        label="simulated (batch aligned to t0)")
ax.axvline(0.5, color="#27ae60", ls="--", lw=1.1, label="OSCAR target (0.5 BDP)")
ax.axvline(1.0, color="0.5", ls=":", lw=1.1, label="1 BDP")
ax.set_xlabel("Target queue  (fraction of BDP)")
ax.set_ylabel("Convergence time (us)")
ax.set_title("E2: deeper target queue -> full-batch capture -> faster recovery")
ax.legend(fontsize=7.5, frameon=False)
ax.grid(True, ls=":", lw=0.5, color="0.85")
fig.savefig(os.path.join(OUT, "e2_qtarget.png"))
plt.close(fig)

# ---- E3: coupled vs decoupled -----------------------------------------
rows = read("e3_rtt")
fig, ax = plt.subplots(figsize=(5.8, 3.5))
for mode, color, marker in [("coupled", "#c0392b", "o"), ("decoupled", "#2c3e50", "s")]:
    sub = [r for r in rows if r.get("mode") == mode]
    d = group_mean(sub, "k", "thr_frac")
    if d:
        ax.semilogy(list(d.keys()), [v * 100 for v in d.values()],
                    marker + "-", color=color, lw=1.4, ms=5, label=mode)
ax.axvline(2 / 3, color="#27ae60", ls=":", lw=1.2, label="k = 2/3")
ax.set_xlabel("Configured RTT / true RTT  (k)")
ax.set_ylabel("Throughput (% of line rate)")
ax.set_title("E3: only coupled D_target/BDP scaling costs throughput")
ax.legend(fontsize=8, frameon=False)
ax.grid(True, which="both", ls=":", lw=0.5, color="0.85")
fig.savefig(os.path.join(OUT, "e3_rtt.png"))
plt.close(fig)

# ---- E5: two-flow competition ------------------------------------------
import ast
rows = read("e5_twoflow")
ks = [0.25, 0.30, 0.40, 0.50]
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), sharey=True)
for ax, mode in zip(axes, ["coupled", "decoupled"]):
    sub = {float(r["k0"]): r for r in rows if r.get("mode") == mode}
    thr0 = [ast.literal_eval(sub[k]["per_flow_thr"])[0] / 12.5e9 * 100 for k in ks]
    thr1 = [ast.literal_eval(sub[k]["per_flow_thr"])[1] / 12.5e9 * 100 for k in ks]
    x = range(len(ks))
    ax.bar([i - 0.18 for i in x], thr0, width=0.34, color="#c0392b", label="misconfigured")
    ax.bar([i + 0.18 for i in x], thr1, width=0.34, color="#2c3e50", label="correct")
    ax.axhline(50, color="#27ae60", ls="--", lw=1.0, label="fair share")
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{k:g}" for k in ks])
    ax.set_xlabel("misconfigured flow's k")
    ax.set_title(mode)
    ax.grid(True, axis="y", ls=":", lw=0.5, color="0.85")
axes[0].set_ylabel("Throughput (% of line rate)")
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=3, fontsize=7.5,
           frameon=False, bbox_to_anchor=(0.5, -0.04))
fig.suptitle("E5: a coupled RTT misconfiguration starves the flow", fontsize=10, y=1.04)
fig.savefig(os.path.join(OUT, "e5_twoflow.png"))
plt.close(fig)

# ---- F1: autocal off/on matrix -----------------------------------------
def _maybe(name):
    path = os.path.join(RES, f"{name}.csv")
    return read(name) if os.path.exists(path) else None

rows = _maybe("f1_autocal")
if rows:
    # left: single-flow thr (e3/e6); right: e5 shares at k0=0.25
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.3))
    ax = axes[0]
    tags = ["e3_coupled_k0.5", "e6_worst"]
    labels = ["E3 k=0.5", "E6 worst"]
    off = [next(float(r["thr_frac"]) * 100 for r in rows
                if r["scenario"] == t and r["autocal"] == "False") for t in tags]
    on = [next(float(r["thr_frac"]) * 100 for r in rows
               if r["scenario"] == t and r["autocal"] == "True") for t in tags]
    x = range(len(tags))
    ax.bar([i - 0.18 for i in x], off, width=0.34, color="#7f8c8d", label="autocal off")
    ax.bar([i + 0.18 for i in x], on, width=0.34, color="#27ae60", label="autocal on")
    ax.axhline(90, color="#c0392b", ls="--", lw=1.0, label="90% target")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Throughput (% of line rate)")
    ax.set_title("Single-flow recovery")
    ax.set_ylim(0, 110)
    ax.grid(True, axis="y", ls=":", lw=0.5, color="0.85")
    ax.legend(fontsize=7, frameon=False)

    ax = axes[1]
    r_off = next(r for r in rows if r["scenario"] == "e5_coupled_k0.25" and r["autocal"] == "False")
    r_on = next(r for r in rows if r["scenario"] == "e5_coupled_k0.25" and r["autocal"] == "True")
    shares = [
        [float(r_off["share0"]), float(r_off["share1"])],
        [float(r_on["share0"]), float(r_on["share1"])],
    ]
    x = [0, 1]
    ax.bar([i - 0.18 for i in x], [s[0] for s in shares], width=0.34,
           color="#c0392b", label="misconfigured")
    ax.bar([i + 0.18 for i in x], [s[1] for s in shares], width=0.34,
           color="#2c3e50", label="correct")
    ax.axhline(50, color="#27ae60", ls="--", lw=1.0)
    ax.set_xticks(x)
    ax.set_xticklabels([
        f"off\nJain={float(r_off['thr_jain']):.2f}",
        f"on\nJain={float(r_on['thr_jain']):.2f}",
    ])
    ax.set_ylabel("Share (%)")
    ax.set_title("E5 coupled k0=0.25")
    ax.set_ylim(0, 100)
    ax.grid(True, axis="y", ls=":", lw=0.5, color="0.85")
    ax.legend(fontsize=7, frameon=False)
    fig.suptitle("F1: rtt_autocal repair", fontsize=10, y=1.02)
    fig.savefig(os.path.join(OUT, "f1_autocal.png"))
    plt.close(fig)

# ---- F1 ablation -------------------------------------------------------
rows = _maybe("f1_ablation")
if rows:
    order = ["off", "floor_only", "d_only", "full"]
    vals = [next(float(r["thr_frac"]) * 100 for r in rows if r["ablation"] == m) for m in order]
    fig, ax = plt.subplots(figsize=(5.4, 3.2))
    colors = ["#7f8c8d", "#e67e22", "#2980b9", "#27ae60"]
    ax.bar(order, vals, color=colors, width=0.6)
    ax.axhline(90, color="#c0392b", ls="--", lw=1.0, label="90% target")
    for i, v in enumerate(vals):
        ax.text(i, v + 1.5, f"{v:.1f}", ha="center", fontsize=8)
    ax.set_ylabel("Throughput (% of line rate)")
    ax.set_title("F1 ablation on E3/E6 worst cell (k=0.5 coupled)")
    ax.set_ylim(0, 115)
    ax.legend(fontsize=7.5, frameon=False)
    ax.grid(True, axis="y", ls=":", lw=0.5, color="0.85")
    fig.savefig(os.path.join(OUT, "f1_ablation.png"))
    plt.close(fig)

# ---- E8: physical hetero RTT -------------------------------------------
rows = _maybe("e8_hetero")
if rows:
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.3), sharey=True)
    for ax, calib in zip(axes, ["min", "own"]):
        for ac, color, marker, lab in [
            (False, "#c0392b", "o", "autocal off"),
            (True, "#27ae60", "s", "autocal on"),
        ]:
            sub = [r for r in rows
                   if r["calib"] == calib and r["autocal"] == str(ac)]
            sub = sorted(sub, key=lambda r: float(r["alpha"]))
            xs = [float(r["alpha"]) for r in sub]
            ys = [float(r["share_ratio"]) for r in sub]
            ax.plot(xs, ys, marker + "-", color=color, lw=1.4, ms=5, label=lab)
        ax.axhline(1.0, color="0.5", ls=":", lw=1.0)
        ax.set_xlabel("alpha = RTT_long / RTT_short")
        ax.set_title(f"calib={calib}")
        ax.grid(True, ls=":", lw=0.5, color="0.85")
    axes[0].set_ylabel("share_long / share_short")
    axes[0].legend(fontsize=7.5, frameon=False)
    fig.suptitle("F2/E8: physical hetero RTT", fontsize=10, y=1.02)
    fig.savefig(os.path.join(OUT, "e8_hetero.png"))
    plt.close(fig)

print("figures written to", OUT)
