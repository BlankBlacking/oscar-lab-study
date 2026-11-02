# OSCAR Evaluation 证据覆盖表

> 状态日期：2026-11-01（官方 Fig.1/2/3/8/9 重跑后更新）。标签：**【原论文】**论文结果；**【复现】**官方 `oscar-cc` ns-3；**【扩展】**`oscar_lab` 简化仿真。  
> 重要边界：官方仓库是 ns-3.40 派生实现；`oscar_lab` 是单瓶颈教学模型，不能冒充论文全量复现。  
> 本轮复现包：`official_repro/`（见 `SUMMARY.md` / `PROVENANCE.md`）。

## 1. 原论文 Evaluation → 本地证据

| 论文问题 / 图 | 环境与指标 | 【原论文】结论 | 本地证据 | 覆盖判断 |
|---|---|---|---|---|
| Fig. 1：不同 CC 的加速/减速收敛阶 | ns-3 微基准；归一化 rate/window 随时间 | DCQCN 为加性慢收敛，Poseidon/HPCC 的部分路径更快 | **本轮重跑**；本仓证据 `fig1_metrics.json` + `fig1_*_summary.json` + `compare_fig1.png`（prior overlay）。全量 `fig1_*_rerun.json` 与上游 `figures/fig1.pdf` **未随本仓发布**。settle≈9872/7928/5076 μs；`overallStatistics` **bit-identical** | **【复现】已重跑验证** |
| Fig. 2：HPCC 旧参考状态导致过度反应 | ns-3；goodput、fair share、INT 利用率 \(U\) | 参考状态与拥塞信号不同步会重复乘性调整、停发和慢恢复 | **本轮重跑** `official_repro/fig2_rerun.json`（~5.2 s；**短 stopTime**）与仓库 `fig2.json` 的 `overallStatistics` **bit-identical**：吞吐 84.3694 Gbps，\(u_{\max}=9.83462\)，avg/p99 FCT 1.162/2.512 ms | **【复现】已重跑验证** |
| Fig. 3：延迟/梯度可观测性与估计精度 | ns-3 oracle/estimator；估计误差 | 延迟与延迟梯度在各自有效工况可近似精确状态；BLS 比逐包梯度稳定；论文 MSE 0.0058 vs 0.079 | **本轮重跑** `fig3_rerun.json`（~4.8 s；**短 stopTime**）与仓库 `overallStatistics` 一致。离线 MSE 未对齐论文标量，且 offline 方向亦未恢复 → **不宣称 MSE**（harness only） | **【复现】harness only**；MSE **not** reproduced |
| Fig. 8：公平与参考状态机制 | ns-3；两流速率轨迹 | 同步参考状态减轻暂态停发/过冲 | **本轮重跑** `fig8a/b_rerun.json`（~1.8/1.4 s）；thr 79.13/85.79 Gbps；8a 与仓库 identical；8b 无 prior warehouse。官方 PDF 仅上游 | **【复现】已重跑** |
| Fig. 9：BLS/控制消融 | ns-3；吞吐与队列长度 | 设计组件减少波动和欠载 | **本轮重跑** `fig9a/b_rerun.json`（~2.3/2.1 s）；thr 87.91/92.54 Gbps；9a 与仓库 identical；9b 无 prior warehouse。官方 PDF 仅上游 | **【复现】已重跑** |
| Fig. 10：大规模真实 workload | 320-host fat-tree ns-3；平均/尾 FCT slowdown | OSCAR 在多数长尾/微突发 workload 上改善 FCT | 上游官方图/配置；本仓无产物 | **未复现**（全套约 4 h） |
| Fig. 11：HPCC 与同目标 HPCC* | ns-3；按流大小的平均/p99 FCT slowdown | 区分控制律与目标状态影响；优势小于只对 HPCC 的比较 | 上游官方图；本仓无产物 | **未复现** |
| Fig. 12：训练/集合通信 | ns-3；归一化平均完成时间 | OSCAR 在 ring/all-to-all（含 spraying）上具有竞争力 | 上游 notebook/PDF；本仓无产物 | **未复现** |
| 测试床收敛与噪声 | 7 台 40 Gb/s 服务器；收敛时间、fair share | 12 μs RTT 场景约 25 μs 收敛，快于 HPCC 的约 80 μs | 论文 §6.1/§6.3 | **未复现**：无对应硬件 |
| 端侧开销 | DPDK/RNIC；cycles/ACK、每流状态 | 约 34/52 cycles/ACK，额外约 36 B/流 | 论文 Table 2 / §5 | **未复现**：无 DPDK/RNIC 基准 |

## 2. `oscar_lab` 的多指标证据（全部为【扩展】）

| 指标 | 证据 | 可报告结果 | 边界 |
|---|---|---|---|
| 吞吐/利用率 | `results/e3_rtt.csv`, `e6_attribution.csv`, `f1_autocal.csv` | coupled \(k=0.5\) 47.58%；autocal 99.81% | 单瓶颈、确定性、单 seed |
| 公平/份额/Jain | `results/e5_twoflow.csv`, `f1_autocal.csv`, `e7_twoway.csv`, `e8_hetero.csv` | 16.29/83.71、Jain 0.688；【扩展】autocal 后 44.83/55.17、Jain 0.989 | Jain 高不等于 50/50；非饿死 |
| 收敛时间 | `results/e1_phase.csv`, `e2_qtarget.csv` | 既有机制探针为 0.52–0.86 ms 量级 | `bdp_floor=0` 的旧探针，只作局限/假设，不作论文复现 |
| 队列/延迟代理 | 各 CSV 的 `q_steady_kb`, `q_target_kb` | F1 单流：off 0.57 KB；on 73.23 KB；真目标 75 KB | 记录的是稳态队列 KB；排队时延可按 \(q/\mu\) 换算，但本报告不伪造误差棒 |
| FCT | 无 | — | 简化模型未记录短流 FCT，不补造 |

## 3. 本轮官方运行判定

- **已解决**：先前审计称“无 build / Python 3.14 失败”。实际上 `oscar-cc/build/` 已有 release 产物；用 `PATH=oscar-cc/.venv/bin:$PATH`（Python 3.11）后 `./ns3` 可用。
- **已重跑**：Fig. 1（DCQCN/HPCC/Poseidon）、Fig. 2、Fig. 3、Fig. 8a/b、Fig. 9a/b（Python 3.11；seed 8259）。Fig.2/3 缩短 stop；Fig.1/8/9 用官方 runtime。有 prior 的配置 `overallStatistics` 与仓库 **bit-identical**。
- **未跑**：`run_all.sh` 全套、Fig. 10–12、测试床。
- PDF 复现条款（最小标准）：**满足** — ≥2 Evaluation 指标（Fig.1 收敛 + Fig.2 吞吐/\(U\)/FCT；另含 Fig.8/9 消融吞吐）+ 非最优场景（Hadoop【原论文】+ E5【扩展】）。

## 4. 结论

OSCAR 单篇现有证据覆盖了**收敛轨迹、吞吐/利用率、INT \(U\)、微基准 FCT、Fig.8/9 消融吞吐**，并以官方重跑验证 Fig. 1–3/8–9 仓库产物可信（8b/9b 为首次本地产出）。`oscar_lab` 仍是 RTT 标定脆弱性的独立扩展。测试床、完整 fat-tree workload、真实 FCT 套件与端侧开销仍是明确缺口——这些**不是** PDF 复现硬门槛所要求的全量 Evaluation。
