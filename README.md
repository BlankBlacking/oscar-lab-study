# OSCAR Lab

Lightweight Python lab and reproduction evidence for **OSCAR** (*O(1)-Step Convergence and Readily-deployable Congestion Control*, NSDI’26).

This repository contains:

1. **`oscar_lab/`** — a single-bottleneck event-driven simulator (~560-line kernel; ~1.1k LOC with runner/plot, no third-party deps except matplotlib for plots) that studies how OSCAR’s RTT-base calibration affects utilization and fairness, plus a simple running min-RTT autocalibration **【扩展】** mitigation / probe (not an official OSCAR patch).
2. **`oscar_lab/official_repro/`** — configs, metrics summaries, and comparison artifacts from re-running official ns-3 microbenchmarks (Fig. 1 / 2 / 3 / 8 / 9) against [NASA-NJU/OSCAR](https://github.com/NASA-NJU/OSCAR).

For the full ns-3 / `oscar-cc` tree, clone and build the upstream project: **https://github.com/NASA-NJU/OSCAR**.

---

## Quick start (`oscar_lab`)

```bash
cd oscar_lab
python3 oscar_sim.py --selftest
python3 run_experiments.py e3 --seeds 1
python3 run_experiments.py e5 --seeds 1
python3 run_experiments.py f1 --seeds 1
python3 plot_results.py   # needs matplotlib
```

More experiment flags and mechanism notes: [`oscar_lab/README.md`](oscar_lab/README.md).

---

## Layout

| Path | Contents |
|---|---|
| `oscar_lab/oscar_sim.py` | Event-driven single-bottleneck kernel |
| `oscar_lab/run_experiments.py` | Batch runner (E1–E8, F1, ablation, F3) |
| `oscar_lab/plot_results.py` | Plotting |
| `oscar_lab/results/` | CSV outputs |
| `oscar_lab/figs/` | PNG figures |
| `oscar_lab/official_repro/` | Official ns-3 rerun evidence (see `SUMMARY.md`, `PROVENANCE.md`) |
| `oscar_lab/EVAL_REPRO_STATUS.md` | Evaluation / reproduction status |
| `oscar_lab/EVALUATION_COVERAGE.md` | Coverage map vs paper Evaluation |

---

## Official ns-3 evidence

Reruns used the upstream [NASA-NJU/OSCAR](https://github.com/NASA-NJU/OSCAR) tree (ns-3.40–derived) with a **Python 3.11** environment (newer Pythons can break `./ns3` argparse). Where warehouse baselines existed, **`overallStatistics` matched bit-identically** (Fig.8b/9b had no prior warehouse; Fig.1 full trajectory JSONs are omitted from this pack as >50 MB). Fig.2/3 used a **shortened** `stopTime` relative to the official JSON (bit-identical still holds for `overallStatistics`); Fig.1/8/9 used official runtime. `compare_fig*.png` are **prior warehouse overlays** (copied), not newly rendered from this-pass traces.

Configs and compact metrics live under `oscar_lab/official_repro/`. Regenerate large Fig.1 traces from the corresponding `*_rerun_config.json` files against the upstream repo. Details: `oscar_lab/official_repro/SUMMARY.md` and `PROVENANCE.md`. This pack does **not** claim a full Evaluation / fat-tree / testbed reproduction.

---

## High-level findings

- **Official microbench:** Fig. 1–3 and Fig. 8–9 reruns align with warehouse baselines where comparable (`overallStatistics` bit-identical when a prior existed).
- **RTT-base mismatch (lab):** When a single (possibly wrong) `RTT_base` scales \(D_{\mathrm{target}}\), BDP floor, and \(\tau/\varepsilon\) together, single-flow utilization can fall to ~47.6% (\(k=0.5\)), and a mismatched flow in two-flow competition can be held to ~16/84 share (≈1:5, unfair share — not starvation).
- **Estimator alone is not the bottleneck:** Scaling only \(\tau/\varepsilon\) (decoupled) keeps single-flow utilization ~100%; loss comes from mis-calibrated targets/floors.
- **【扩展】Autocalibration probe:** End-host running min-RTT calibration (with \(\tau/\varepsilon\)) improves single-flow utilization to ~99.8% and two-flow share to ~45/55 (Jain ≈ 0.99) — directionally better, not equal split.

Scope note: the Python lab is a mechanistic single-bottleneck model, not a substitute for full ns-3 / fat-tree / testbed claims.
