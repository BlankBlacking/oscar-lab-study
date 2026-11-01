# Official OSCAR reproduction provenance (2026-11-01)

## Environment
- Repo: `<OSCAR_NS3_ROOT>` (clone of https://github.com/NASA-NJU/OSCAR)
- Python: `<OSCAR_NS3_ROOT>/.venv` → CPython **3.11.16** (system python3 is 3.14 and breaks ns3 argparse)
- Build: existing `release` profile at `build/`; `PATH=.venv/bin:$PATH ./ns3 show profile` → release
- Binary: `build/scratch/ns3.40-rdma-simulator`
- Self-check before Fig.1/8/9 runs: `python --version` → 3.11.16

## What was re-run

### Pass A — Fig.2 / Fig.3 (earlier same day)
| Experiment | Config | Wall time | Result | Match warehouse? |
|---|---|---|---|---|
| Fig.2 (HPCC stale reference / goodput+U) | `fig2_rerun_config.json` (seed 8259; runningTime 0.15s stopTime 0.2s) | ~5.2 s | `fig2_rerun.json` | **Yes** — overallStatistics and key series lengths identical |
| Fig.3 (delay/gradient observability) | `fig3_rerun_config.json` (same timing shorten) | ~4.8 s | `fig3_rerun.json` | **Yes** — overallStatistics identical |

### Pass B — Fig.1 / Fig.8 / Fig.9 (this pass; official runtime)
Official configs under `config/oscar-nsdi26/experiments/` with `outputFile.resultFile` redirected into `official_repro/*_rerun.json`. Runtime **unchanged**: seed **8259**, `runningTime=1s`, `stopTime=10s`.

| Experiment | Config | Wall (s) | Exit | Result | Match warehouse `overallStatistics`? |
|---|---|---:|---:|---|---|
| Fig.8a | `fig8a_rerun_config.json` | 1.77 | 0 | `fig8a_rerun.json` | **Yes** |
| Fig.8b | `fig8b_rerun_config.json` | 1.38 | 0 | `fig8b_rerun.json` | **N/A** — no prior warehouse JSON |
| Fig.9a | `fig9a_rerun_config.json` | 2.25 | 0 | `fig9a_rerun.json` | **Yes** |
| Fig.9b | `fig9b_rerun_config.json` | 2.13 | 0 | `fig9b_rerun.json` | **N/A** — no prior warehouse JSON |
| Fig.1 DCQCN | `fig1_dcqcn_rerun_config.json` | 15.57 | 0 | `fig1_dcqcn_rerun.json` | **Yes** |
| Fig.1 HPCC | `fig1_hpcc_rerun_config.json` | 23.01 | 0 | `fig1_hpcc_rerun.json` | **Yes** |
| Fig.1 Poseidon | `fig1_poseidon_rerun_config.json` | 18.29 | 0 | `fig1_poseidon_rerun.json` | **Yes** |

Baseline snapshot before this pass: `summaries/warehouse_baseline_before_rerun.json`.  
Per-config timing: `logs/*_time.txt`. Aggregate table: `summaries/fig189_rerun_table.json`.

Settle metrics re-extracted from Fig.1 reruns → `fig1_metrics.json` (settle DCQCN/Poseidon/HPCC ≈ 9872 / 7928 / 5076 μs; identical to prior extract).

## What was reused (not re-run)
- Official PDFs `config/oscar-nsdi26/figures/fig{1,2a,2b,3a,3b,8a,8b,9a,9b}.pdf`
- Compare PNGs from `oscar-cc/reproduction_compare/` (copied earlier): `compare_fig1.png`, `compare_fig2a.png`, `compare_fig2b.png`
- Fig.10–12 / testbed / DPDK — **not** re-run

## Metrics covered (≥2 Evaluation metrics)
1. **Convergence / rate trajectory (Fig.1)** — re-run + settle-to-1 times
2. **Throughput / goodput + INT utilization U (Fig.2)** — totalThroughput 84.37 Gbps; u_max ≈ 9.83
3. **Signal estimation harness (Fig.3)** — re-run identical; MSE scalars not claimed
4. **Ablation microbenches (Fig.8–9)** — re-run thr/FCT overallStatistics

## Non-optimal scenario
See `nonoptimal_scenario.json` — paper Hadoop/small-flow + lab E5 coupled miscalibration.

## Honesty
- Not a full Evaluation / fat-tree / 4-hour `run_all.sh` reproduction
- `oscar_lab` E3/E5/F1 remain **【扩展】**, not official reproduction
- Fig.10–12 FCT / testbed / DPDK overhead not re-run
- Fig.8b/9b had no prior warehouse outputs to bit-compare


## Upload-pack note (large traces omitted)
The following full ns-3 result traces are **>50 MB** and are **not** shipped in this GitHub upload pack (summaries/metrics/configs/logs remain):
- `fig1_dcqcn_rerun.json` (~124 MB)
- `fig1_hpcc_rerun.json` (~212 MB)
- `fig1_poseidon_rerun.json` (~138 MB)

Settle metrics extracted from those runs are in `fig1_metrics.json` / `summaries/fig1_*_overallStatistics.json`.
To regenerate full traces: clone [NASA-NJU/OSCAR](https://github.com/NASA-NJU/OSCAR), use **Python 3.11** venv, build `release`, then `./ns3 run "rdma-simulator …/fig1_*_rerun_config.json"` with configs in this directory.
