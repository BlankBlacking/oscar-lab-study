# Official reproduction summary (minimum bar)

## Status
**PDF reproduction clause for OSCAR: MET (minimum)** — re-ran official Fig.1 (DCQCN/HPCC/Poseidon), Fig.2, Fig.3, Fig.8a/b, Fig.9a/b microbenches with Python 3.11 venv; Fig.1/2/3/8a/9a `overallStatistics` **bit-identical** to warehouse baselines where prior outputs existed; Fig.8b/9b are first local runs (no prior warehouse JSON). Extracted ≥2 Evaluation metrics; documented non-optimal scenario.

Not claimed: full Evaluation, fat-tree Fig.10–12, testbed, DPDK overhead, or Fig.3 MSE scalar match.

## Commands (Python 3.11 venv required)

```bash
cd <OSCAR_NS3_ROOT>
export PATH="$(pwd)/.venv/bin:$PATH"   # NOT system python3.14
./ns3 show profile                      # release

# Fig.2 / Fig.3 (earlier pass; shortened stop)
./ns3 run "rdma-simulator .../official_repro/fig2_rerun_config.json"   # ~5.2 s
./ns3 run "rdma-simulator .../official_repro/fig3_rerun_config.json"   # ~4.8 s

# Fig.1 / Fig.8 / Fig.9 (2026-11-01 pass; official runtime seed=8259)
./ns3 run "rdma-simulator .../official_repro/fig8a_rerun_config.json"
./ns3 run "rdma-simulator .../official_repro/fig8b_rerun_config.json"
./ns3 run "rdma-simulator .../official_repro/fig9a_rerun_config.json"
./ns3 run "rdma-simulator .../official_repro/fig9b_rerun_config.json"
./ns3 run "rdma-simulator .../official_repro/fig1_dcqcn_rerun_config.json"
./ns3 run "rdma-simulator .../official_repro/fig1_hpcc_rerun_config.json"
./ns3 run "rdma-simulator .../official_repro/fig1_poseidon_rerun_config.json"
```

## This-pass Fig.1 / 8 / 9 run table

| Config | Wall (s) | Exit | Key metric | Output | vs warehouse `overallStatistics` |
|---|---:|---:|---|---|---|
| fig8a | 1.77 | 0 | thr **79.1305 Gbps**; avgFct 0.311 ms | `fig8a_rerun.json` | **identical** |
| fig8b | 1.38 | 0 | thr **85.786 Gbps**; avgFct 0.312 ms | `fig8b_rerun.json` | no prior warehouse |
| fig9a | 2.25 | 0 | thr **87.9112 Gbps**; avgFct 0.445 ms | `fig9a_rerun.json` | **identical** |
| fig9b | 2.13 | 0 | thr **92.5383 Gbps**; avgFct 0.449 ms | `fig9b_rerun.json` | no prior warehouse |
| fig1 dcqcn | 15.57 | 0 | thr **75.5165 Gbps**; settle≈**9872 μs** | `fig1_dcqcn_rerun.json` | **identical** |
| fig1 hpcc | 23.01 | 0 | thr **86.2873 Gbps**; settle≈**5076 μs** | `fig1_hpcc_rerun.json` | **identical** |
| fig1 poseidon | 18.29 | 0 | thr **84.3781 Gbps**; settle≈**7928 μs** | `fig1_poseidon_rerun.json` | **identical** |

Total wall ≈ **64.4 s** for Fig.1+8+9. Timing logs: `logs/*_time.txt`. Compact stats: `*_summary.json` → `summaries/`.

## Metric coverage (≥2)

| Metric | Paper figure | Our evidence | Value |
|---|---|---|---|
| Convergence / rate trajectory (norm. rate windows, settle-to-~1) | Fig. 1 | **re-run** + `fig1_metrics.json` + `compare_fig1.png` | DCQCN settle_to_1 after 4 ms ≈ 9872 μs; HPCC ≈ 5076 μs; Poseidon ≈ 7928 μs (unchanged vs prior extract) |
| Throughput / goodput | Fig. 2 | **re-run identical** `fig2_rerun_compare.json` | totalThroughput **84.3694 Gbps**; long-flow overallFlowRate **51.93 Gbps** |
| INT utilization U (overshoot) | Fig. 2 | same re-run | **u_max = 9.83462** |
| FCT (microbench) | Fig. 2 overallStatistics | same re-run | avgFct **1.162 ms**; p99 **2.512 ms** |
| Delay/gradient observability | Fig. 3 | re-run identical + `fig3a/b.pdf` | harness verified; MSE scalars **not** claimed |
| Ref-state ablation (two-flow) | Fig. 8a/b | **re-run** `fig8a/b_rerun.json` | thr 79.13 / 85.79 Gbps |
| BLS/control ablation | Fig. 9a/b | **re-run** `fig9a/b_rerun.json` | thr 87.91 / 92.54 Gbps |

## Non-optimal scenario
See `nonoptimal_scenario.json`.
- 【原论文】Hadoop: OSCAR worse than HPCC 23.3% / HPCC* 15.9%; <1 BDP small flows −7.6% vs HPCC.
- 【扩展】E5 coupled k0=0.25: shares ≈16.3/83.7, Jain 0.688 (`../results/e5_twoflow.csv`).

## Artifact index
- `PROVENANCE.md`, `summaries/fig189_rerun_table.json`, `logs/fig189_rerun_batch.log`, `logs/*_time.txt`
- `fig{1_* ,8a,8b,9a,9b}_rerun.json` + `*_rerun_config.json` + `*_summary.json`
- `fig1_metrics.json`, `fig2_metrics.json`, `fig2_rerun_compare.json`, `fig3_metrics.json`
- `fig2_rerun*.json/log`, `fig3_rerun*.json/log`
- `compare_fig1.png`, `compare_fig2a.png`, `compare_fig2b.png`
- Official PDFs: `<OSCAR_NS3_ROOT>/config/oscar-nsdi26/figures/` (not shipped here)
