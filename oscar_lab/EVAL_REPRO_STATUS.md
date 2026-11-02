# OSCAR Evaluation ↔ 复现对照状态

> 状态日期：2026-11-01。证据分层：**【原论文】** / **【复现】**（官方 `oscar-cc` ns-3）/ **【扩展】**（`oscar_lab` 简化模型）。  
> 主来源：`EVALUATION_COVERAGE.md`、`official_repro/{SUMMARY,PROVENANCE}.md`、官方 `config/oscar-nsdi26/` figure 列表（上游 NASA-NJU/OSCAR）。  
> **诚实边界**：Fig.1/2/3/8a/b/9a/b **已重跑**；大规模 Evaluation（Fig.10–12 / `run_all.sh`）**未做**；本仓不声称全量 Evaluation。

---

## 1. Evaluation 是什么

在 OSCAR（NSDI’26）里，**Evaluation** 指论文 **§6 Evaluations**：用测试床 + ns-3 仿真，验证端到端可部署的 O(1) 收敛 CC 是否：

1. 在真实噪声下仍能快速、公平收敛（测试床）；
2. 微基准上证实 O(1)、参考状态与 BLS 机制有效（ns-3 microbench）；
3. 大规模 fat-tree workload 上改善 FCT / 训练集合通信完成时间（ns-3 large-scale）。

**§5 Implementation**（DPDK/RNIC 开销，Table 2）常与 Evaluation 一并讨论部署性，但章节上独立于 §6。

本对照表关注：已复现的实验结果、覆盖的 **Evaluation 指标类**，以及至少一种**非最优**场景——不等于复刻整节 §6。

---

## 2. 论文有几个 Evaluation / 几个实验

### 2.1 章节结构（§6）

| 小节 | 内容 | 主要平台 |
|---|---|---|
| **§6 Evaluations**（1 个总章） | 总评估章 | — |
| **§6.1 Setup** | 对比算法、参数、测试床/仿真设定 | — |
| **§6.2 Testbed Evaluation** | 真实噪声收敛、公平、BLS、all-to-all | 7×40 Gb/s 测试床 |
| **§6.3 Micro Benchmarks** | O(1) 收敛、参考状态/BLS 消融、信号精度 | ns-3 微基准 |
| **§6.4 Large-scale Simulations** | 长尾/微突发/Hadoop/incast/训练流量 FCT | 320-host fat-tree ns-3 |

**计数口径**：1 个 Evaluation 总章（§6）+ **3 个实验小节**（6.2–6.4；6.1 为 setup）+ 相关 **§5 开销**。

概念层亦对应三类：测试床 / 微基准 / 大规模仿真。

### 2.2 官方 artifact 图（`config/oscar-nsdi26/figures/`）

可复现脚本侧的核心图：**Fig.1, 2a/2b, 3a/3b, 8a/8b, 9a/9b, 10a/10b/10c, 11, 12**（共 **12** 组主图；另有 legend PDF）。  
动机/机制说明图 Fig.1–3 实验细节在 §6.3；Fig.8–9 为消融；Fig.10–12 为大规模。论文正文另有测试床 Fig.6–7 等（无完整对应 artifact 配置于本仓对照表）。

`experiments/run_all.sh` 会扫目录下约 **58** 个 JSON 配置；全套约 **4 h**——**本轮未跑**。

---

## 3. 完整对照表

| 图 / 实验 | 指标 | 我们的状态 | 证据 | 备注 |
|---|---|---|---|---|
| **Fig. 1** 收敛阶分类（DCQCN/Poseidon/HPCC） | 归一化 rate/window；扰动后 settle-to-~1 时间 | **【复现】已重跑** | 本仓：`fig1_metrics.json`；`fig1_{dcqcn,hpcc,poseidon}_summary.json`；`summaries/fig1_*_overallStatistics.json`；`compare_fig1.png`（prior overlay）。全量 `fig1_*_rerun.json`（>50 MB）与 `figures/fig1.pdf` **未随本仓发布**（上游可 regen） | settle≈9872 / 7928 / 5076 μs（DCQCN/Poseidon/HPCC）；thr **75.52 / 84.38 / 86.29** Gbps；~15.6 / 18.3 / 23.0 s；`overallStatistics` 与仓库 **bit-identical** |
| **Fig. 2** HPCC 旧参考状态过度反应 | goodput/吞吐、fair share、INT \(U\)、微基准 FCT | **【复现】已重跑**（短 stopTime） | `fig2_rerun.json` / `fig2_rerun_compare.json`；与仓库 `overallStatistics` **bit-identical** | 吞吐 **84.3694 Gbps**；\(u_{\max}=9.83462\)；avg/p99 FCT **1.162 / 2.512 ms**；~5.2 s |
| **Fig. 3** 延迟/梯度可观测性 | oracle vs estimator；估计误差 / MSE | **【复现】harness 已重跑**；MSE **未复现 / 不宣称** | `fig3_rerun.json`；`fig3_metrics.json`（offline MSE exploratory only）。官方 `fig3a/b.pdf` 仅在上游 | ~4.8 s，与仓库一致。论文 MSE 0.0058 vs 0.079；离线重算未对齐且方向亦未恢复 → 不宣称 MSE |
| **测试床 §6.2**（Fig.6–7 等） | 收敛时间、fair share、BLS 噪声鲁棒、all-to-all 完成时间 | **未复现** | 仅【原论文】§6.1/§6.2 | 无 7 机 40 Gb/s 硬件。论文：~12 μs RTT 场景约 **25 μs** vs HPCC **~80 μs** |
| **Fig. 8** 参考状态机制消融 | 两流速率轨迹 | **【复现】已重跑** | `fig8a/b_rerun.json`；`fig8a/b_summary.json`。官方 PDF 仅在上游 | thr **79.13 / 85.79 Gbps**；~1.8 / 1.4 s。8a 与仓库 identical；8b 无 prior warehouse |
| **Fig. 9** BLS/控制消融 | 吞吐、队列长度 | **【复现】已重跑** | `fig9a/b_rerun.json`；`fig9a/b_summary.json`。官方 PDF 仅在上游 | thr **87.91 / 92.54 Gbps**；~2.3 / 2.1 s。9a 与仓库 identical；9b 无 prior warehouse |
| **Fig. 10** 大规模真实 workload | 平均/尾 FCT slowdown（CacheFollower 等） | **未复现** | 上游 `figures/fig10*` / `experiments/fig10*`（不在本仓） | 全套 fat-tree ~4 h 未跑。**【原论文】非最优**：小流 vs HPCC **−7.6%** 等 |
| **Fig. 11** HPCC vs HPCC* | 按流大小 avg/p99 FCT slowdown | **未复现** | 上游 `figures/fig11.pdf`（不在本仓） | 【原论文】**Hadoop**：相对 HPCC **−23.3%**、HPCC* **−15.9%** |
| **Fig. 12** 训练/集合通信 | 归一化平均完成时间（ring/a2a±spray） | **未复现**（上游有脚本/notebook/PDF） | 上游 `figures/fig12.pdf`；`experiments/fig12/` | 未本轮重跑 |
| **Table 2 / §5** 端侧开销 | cycles/ACK、每流状态字节 | **未复现** | 仅【原论文】 | ~34/52 cycles/ACK；额外 ~36 B/流。无 DPDK/RNIC 基准 |
| **【扩展】E3/E5/F1 等**（非论文图） | 利用率、份额/Jain、队列 KB | **扩展探针，非官方复现** | `results/e*.csv`、`f1_*.csv`；`figs/` | E5 coupled：份额 ≈16.3/83.7，Jain **0.688**（非最优侧证） |

### 3.1 本轮已覆盖的 Evaluation 指标（≥2 类）

| 指标类 | 对应图 | 数值摘要 |
|---|---|---|
| 收敛 / 速率轨迹 | Fig. 1 | settle 时间 DCQCN/Poseidon/HPCC ≈ 9872/7928/5076 μs |
| 吞吐 / goodput | Fig. 2 | 84.3694 Gbps（重跑） |
| INT 利用率 \(U\) | Fig. 2 | \(u_{\max}=9.83462\)（重跑） |
| 微基准 FCT | Fig. 2 | avg 1.162 ms / p99 2.512 ms（重跑） |
| 延迟/梯度可观测性 | Fig. 3 | harness 验证；MSE 不宣称 |

### 3.2 非最优场景

| 来源 | 场景 | 要点 |
|---|---|---|
| 【原论文】 | Hadoop / 小流（Fig.10–11 讨论） | vs HPCC **−23.3%**；vs HPCC* **−15.9%**；&lt;1 BDP 小流 vs HPCC **−7.6%** |
| 【扩展】 | E5 coupled \(k_0=0.25\) | 份额 16.3/83.7，Jain 0.688（`results/e5_twoflow.csv`） |

详见 `official_repro/nonoptimal_scenario.json`。

---

## 4. 复现覆盖小结

| 检查项 | 状态 | 依据 |
|---|---|---|
| 官方微基准重跑 | **已完成（最小标准）** | 官方 ns-3 **重跑 Fig.1/2/3/8/9**；有 prior 时 `overallStatistics` bit-identical |
| 多类 Evaluation 指标 | **已覆盖** | ≥2 类：Fig.1 收敛轨迹 + Fig.2 吞吐/\(U\)/FCT（另有 Fig.3 harness、Fig.8/9 消融吞吐） |
| 非最优场景 | **有** | 原论文 Hadoop/小流 + 扩展 E5 |
| 全量 Evaluation / fat-tree / 测试床 / DPDK | **未做** | 明确缺口，不声称 |

不声称：全量 Evaluation、`run_all.sh`、Fig.10–12 重跑、测试床、DPDK、Fig.3 MSE 标量。

---

## 5. Artifact 索引

| 路径 | 用途 |
|---|---|
| `official_repro/SUMMARY.md` / `PROVENANCE.md` | 最小复现条结论与 provenance |
| `official_repro/fig{1,2,3}_metrics.json`、`fig{1_*,2,3,8a,8b,9a,9b}_rerun*.json`、`summaries/` | 指标与重跑产物 |
| `official_repro/compare_fig*.png` | Fig.1/2 对照图（**prior warehouse overlays**，非本轮新渲） |
| `EVALUATION_COVERAGE.md` | Evaluation 覆盖表 |
| `<OSCAR_NS3_ROOT>/config/oscar-nsdi26/figures/` | 官方 PDF 图（仅上游；本仓不发布） |
| `<OSCAR_NS3_ROOT>/config/oscar-nsdi26/experiments/` | 官方实验 JSON + `run_all.sh` |
