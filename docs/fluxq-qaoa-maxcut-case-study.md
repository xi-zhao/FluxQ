# FluxQ 实战案例：把一个 QAOA MaxCut 参数扫描，变成可复现、可对比、可导出的量子工作流

## 一句话版本

FluxQ 不只是生成一个量子脚本，而是把一次量子运行固化成一个带 revision、baseline、report、export 和 benchmark 的工作流单元，适合 AI Agent、CI 和量子开发团队长期协作。

这个案例展示的是一个真实可运行的场景：我们让 FluxQ 执行一个 4 比特、2 层的 QAOA MaxCut 参数扫描任务，自动完成本地精确评估、选择代表参数点、固化 baseline、对比当前状态、导出 OpenQASM 3，并输出结构化 benchmark 和环境诊断结果。

## 适合拿去宣传的受众

- 想把量子代码生成接入 AI Agent 的团队
- 需要可追溯、可复盘量子实验流程的研发组织
- 想把量子工作流接进 CI/CD 的平台团队
- 需要向客户证明“结果可信、流程可审计”的基础设施产品团队

## 背景问题

很多量子开发流程已经能“生成电路”，但还做不到“可信交付”。

常见问题包括：

- 一次运行结束后，只剩下一个脚本，后续很难知道它对应哪个参数点
- 导出的 QASM、Qiskit Python 和图形产物，经常和真正评估过的参数点不完全一致
- 后续改动发生后，很难快速判断是工作负载真的变了，还是只是报告和产物漂移了
- 团队很难把量子运行结果稳定地交给 AI Agent、CI 或审查流程消费

FluxQ 的思路不是多加几种导出格式，而是把一次量子任务组织成一个 workspace-native 的决策单元：

1. 执行 workload
2. 固化 baseline
3. 对比当前状态
4. 导出可复用产物
5. 输出 benchmark 和环境诊断

## 案例目标

本案例使用仓库内置的示例文件：

- [examples/intent-qaoa-maxcut-sweep.md](/Users/xizhao/Nutstore%20Files/my_projects/Fluxq/Qcli/examples/intent-qaoa-maxcut-sweep.md)

目标是构建一个：

- 4-qubit
- 2-layer
- ring graph MaxCut
- 本地参数扫描
- 本地精确期望值评估
- 可导出 OpenQASM 3 和 Qiskit 代码
- 可保存 baseline 并做 compare

的完整工作流。

## 输入任务

示例 intent 的核心内容如下：

```yaml
---
title: QAOA MaxCut Sweep
exports:
  - qiskit
  - qasm3
backend_preferences:
  - qiskit-local
constraints:
  max_width: 4
  max_depth: 128
  basis_gates:
    - h
    - cx
    - rz
    - rx
  optimization_level: 2
  qaoa_layers: 2
  maxcut_edges:
    - [0, 1]
    - [1, 2]
    - [2, 3]
    - [3, 0]
  parameter_sweep:
    gamma_0: [0.2, 0.4]
    beta_0: [0.1, 0.3]
    gamma_1: [0.45]
    beta_1: [0.35]
shots: 512
---
```

自然语言目标是：

> Build a 4-qubit MaxCut QAOA ansatz with 2 layers on a ring graph.

## 完整演示命令

下面这组命令就是一条完整、可复现、适合公开演示的 FluxQ 工作流：

```bash
qrun init --workspace .quantum --json
qrun exec --workspace .quantum --intent-file examples/intent-qaoa-maxcut-sweep.md --json
qrun baseline set --workspace .quantum --revision rev_000001 --json
qrun compare --workspace .quantum --baseline --json
qrun export --workspace .quantum --format qasm3 --json
qrun bench --workspace .quantum --json
qrun doctor --workspace .quantum --json
```

这条链路背后的逻辑是：

- `init` 创建稳定 workspace
- `exec` 执行量子 workload，写入 report、artifacts、diagnostics
- `baseline set` 把这次运行固化为团队认可的参考版本
- `compare --baseline` 判断当前 workspace 是否仍和 baseline 一致
- `export` 导出与本次运行一致的产物
- `bench` 输出结构 benchmark，并说明结果是否可比较
- `doctor` 检查环境依赖是否满足工作流需求

## 真实运行结果

以下结果来自一次真实本地运行。

### 1. Workspace 初始化

```json
{
  "status": "ok",
  "workspace": "/private/tmp/fluxq-promo-case/.quantum",
  "workspace_version": "0.1",
  "project_id": "proj_2cc19830",
  "current_revision": "rev_000000",
  "created": true
}
```

这说明 FluxQ 已经把运行上下文组织成一个正式 workspace，而不是把结果散落在临时脚本里。

### 2. 执行 QAOA MaxCut Sweep

真实执行得到的核心结果如下：

- revision：`rev_000001`
- execution status：`ok`
- simulation status：`ok`
- parameter mode：`sweep`
- representative point：`sweep_002`
- best objective observable：`maxcut_cost`
- best objective value：`1.7687784005`

FluxQ 选出的代表参数点绑定如下：

```json
{
  "gamma_0": 0.4,
  "beta_0": 0.1,
  "gamma_1": 0.45,
  "beta_1": 0.35
}
```

对应的 `best_point` 结果摘要如下：

```json
{
  "label": "sweep_002",
  "source": "sweep",
  "workflow_mode": "sweep",
  "objective_observable": "maxcut_cost",
  "objective": "maximize",
  "objective_value": 1.7687784005
}
```

这一步的关键宣传点在于：

- FluxQ 不只是“知道你在 sweep”
- 它会把被实际采用的代表点记进 report
- 后续导出和比较都可以严格对齐这个点，而不是随便回退到默认参数

### 3. 结构资源结果

这次运行得到的结构资源如下：

```json
{
  "width": 4,
  "depth": 28,
  "size": 40,
  "two_qubit_gates": 16,
  "measure_count": 4,
  "parameter_count": 4,
  "parameter_names": [
    "gamma_0",
    "beta_0",
    "gamma_1",
    "beta_1"
  ]
}
```

换句话说，这不是一句空泛的“QAOA 已生成”，而是一份能直接给工程团队使用的量化结果：

- 4 个量子比特
- 深度 28
- 16 个两比特门
- 4 个参数

### 4. 产物落盘

本次运行写入了以下关键产物：

- `.quantum/specs/history/rev_000001.json`
- `.quantum/artifacts/history/rev_000001/qiskit/main.py`
- `.quantum/artifacts/history/rev_000001/qasm/main.qasm`
- `.quantum/artifacts/history/rev_000001/figures/circuit.txt`
- `.quantum/artifacts/history/rev_000001/figures/circuit.png`
- `.quantum/reports/history/rev_000001.json`

这意味着团队可以把一次运行作为 revision-safe 工件直接保留下来，而不是只保留一个最新版本脚本。

### 5. Baseline 固化与对比

将 `rev_000001` 设为 baseline 后，再执行 compare，返回结果是：

```json
{
  "status": "same_subject",
  "same_subject": true,
  "same_qspec": true,
  "same_report": true,
  "highlight": "Same workload identity (qaoa_ansatz) across both inputs."
}
```

这一步的价值非常适合宣传：

- 团队不再只会“重新跑一次”
- 团队可以明确回答“当前状态是否仍与批准版本一致”
- 对 AI Agent 和 CI 来说，这是一个天然的 gate

### 6. 导出 OpenQASM 3

导出命令成功返回：

```json
{
  "status": "ok",
  "format": "qasm3",
  "source_kind": "workspace_current",
  "source_revision": "rev_000001"
}
```

导出的 OpenQASM 3 片段如下：

```qasm
OPENQASM 3.0;
include "stdgates.inc";
bit[4] c;
qubit[4] q;
h q[0];
h q[1];
h q[2];
h q[3];
cx q[0], q[1];
rz(0.8) q[1];
cx q[0], q[1];
cx q[1], q[2];
rz(0.8) q[2];
cx q[1], q[2];
```

最重要的是：导出的产物和本次运行报告记录的代表参数点保持一致。

这对宣传尤其重要，因为它说明 FluxQ 不是“重新生成一个看起来类似的导出物”，而是在做可追溯的 runtime export。

### 7. 结构 Benchmark

`qrun bench --json` 为 `qiskit-local` 返回了如下结构 benchmark：

```json
{
  "backend": "qiskit-local",
  "status": "ok",
  "width": 4,
  "depth": 28,
  "transpiled_depth": 28,
  "two_qubit_gates": 16,
  "transpiled_two_qubit_gates": 16,
  "measure_count": 4,
  "details": {
    "benchmark_mode": "target_aware",
    "comparable": true,
    "comparability_reason": "target_aware_transpile",
    "transpile_status": "ok"
  }
}
```

这部分可以直接拿去做产品宣传里的差异化表达：

- FluxQ 不只是输出 benchmark 数字
- FluxQ 会告诉你这些 benchmark 是否真的可比较
- 它把 `target_aware`、`structural_only`、`synthesis_backed` 这种语义显式暴露出来

### 8. 环境诊断

`qrun doctor --json` 返回：

```json
{
  "status": "ok",
  "issues": [],
  "advisories": [
    "classiq unavailable: No module named 'classiq'"
  ]
}
```

这个结果说明：

- 当前工作流本身是可运行的
- 可选后端缺失只会被标成 advisory
- 不会因为一个没被当前 workload 依赖的可选后端，错误地把整条链路判成失败

## 为什么这个案例值得宣传

这个案例适合用作官网、发布说明、Demo 视频和社交媒体宣传，因为它同时具备三个特征。

### 第一，它不是玩具例子

这不是一个只生成 GHZ 的入门示例，而是一个真实的参数化 QAOA 任务：

- 有目标函数
- 有参数扫描
- 有代表点选择
- 有结构资源结果
- 有可复现的导出和 compare

### 第二，它能解释 FluxQ 的核心差异

很多工具能做到以下其中一件事：

- 生成量子代码
- 跑本地模拟
- 导出 QASM
- 存一份 JSON 报告

但 FluxQ 在这个案例里展示的是一条完整链路：

- 一个 workload 如何被执行
- 如何被固化为 baseline
- 如何被比较
- 如何被导出
- 如何被 benchmark
- 如何被 doctor 校验

这比“我们支持 QAOA”更有说服力。

### 第三，它特别适合 Agent 和 CI 叙事

如果你的宣传对象是：

- AI Agent 框架
- 自动化研发团队
- 企业级量子平台
- 需要可审计实验流程的客户

那么这个案例很好讲，因为它天然回答了三个关键问题：

1. 结果是不是可复现的
2. 导出物是不是和实际评估过的参数点一致
3. 后续改动是不是能和 baseline 做机器可读比较

## Agent/CI continuation

这条 QAOA 工作流在本地跑通以后，不应该停在“看一眼报告”这一步，而应该继续走标准 runtime gate：

```bash
qrun compare --workspace .quantum --baseline --fail-on subject_drift --json
qrun doctor --workspace .quantum --json --ci
```

这里的重点不是让 agent 或 CI 自己理解量子线路细节，而是直接消费结构化信号：

- `reason_codes` 说明为什么 compare 或 doctor 通过、降级或失败
- `next_actions` 告诉 host 下一步是复跑、修环境，还是继续交付
- `gate` 明确表达当前 revision 是否允许继续推进

机器消费者应当读取 `reason_codes`、`next_actions`、`gate`，而不是猜测状态或直接手改生成代码来绕过 runtime contract。

## Delivery handoff

当 `compare` 与 `doctor --ci` 都通过后，再把这个 QAOA revision 交给下游环境：

```bash
qrun pack --workspace .quantum --revision rev_000001 --json
qrun pack-inspect --pack-root .quantum/packs/rev_000001 --json
qrun pack-import --pack-root .quantum/packs/rev_000001 --workspace downstream/.quantum --json
```

这个顺序必须保持不变：先 `pack-inspect`，再 `pack-import`。这样下游 workspace 接收的是一个已经被 bundle-local 证据验证过的交付包，而不是一个未经检查就直接导入的目录快照。

## 官网案例页可直接复用的版本

### 标题

把一个 QAOA 参数扫描，从“一次运行”升级成“一个可复现工作流”

### 副标题

FluxQ 用 revisioned workspace、baseline compare、trust-aware export 和 target-aware benchmark，把量子工作流变成 AI Agent 和 CI 可以长期消费的工程资产。

### 正文

在这个案例中，我们用 FluxQ 执行了一个 4 比特、2 层的 QAOA MaxCut 参数扫描任务。FluxQ 不仅生成了 Qiskit 和 OpenQASM 3 产物，还通过本地精确期望值评估选出了代表参数点 `sweep_002`，得到目标值 `1.7687784005`，并把这次运行固化为 `rev_000001`。

随后，我们将该 revision 保存为 baseline，并立即验证当前 workspace 与 baseline 完全一致。FluxQ 还为同一 workload 生成了结构 benchmark，明确标注该结果属于 `target_aware`，并通过 `doctor` 输出当前环境健康状态与可选后端 advisory。

这意味着团队拿到的不再是“一个脚本”，而是一整套可追溯、可导出、可比较、可审计的量子工作流记录。

## 社交媒体短版文案

### 版本 A

我们用 FluxQ 跑了一个 4-qubit、2-layer 的 QAOA MaxCut 参数扫描。  
结果不只是生成了电路，而是生成了一个完整的 revisioned workspace：

- 自动选出代表参数点 `sweep_002`
- 目标值 `1.7687784005`
- 电路深度 `28`
- 两比特门数 `16`
- baseline / compare / export / bench / doctor 全链路可用

这就是 FluxQ 的核心价值：把量子生成从“一次性脚本”升级成“可复现工作流”。

### 版本 B

大多数量子工具能生成代码。  
FluxQ 解决的是生成之后的问题：

- 这次运行对应哪个参数点？
- 导出的 QASM 和评估过的结果是不是同一个版本？
- 当前 workspace 和批准 baseline 相比，有没有 drift？

在一个真实 QAOA MaxCut sweep 案例里，FluxQ 把这些都做成了机器可读输出。

## 1 分钟 Demo 讲稿

“这里我们不是在演示一个量子脚本生成器，而是在演示一个完整的量子工作流 runtime。我们给 FluxQ 一个 QAOA MaxCut sweep intent，它会把这次运行保存成 revision `rev_000001`，本地评估多个参数点，自动选出代表点 `sweep_002`，并把目标值、资源指标、导出物、报告和 benchmark 全部落盘到同一个 workspace。接着我们可以一键把它设成 baseline，再 compare 当前状态是否仍然一致。这样无论是 AI Agent、CI 还是团队代码审查，都拿到的是可复现、可追溯、可审计的量子运行结果。” 

## 结论

如果你想宣传 FluxQ，最值得强调的不是“支持 QAOA”“支持 QASM 导出”或者“支持 benchmark”，而是下面这句话：

> FluxQ 把一次量子运行，提升成一个 AI Agent 和 CI 都能信任的工作流单元。

这个 QAOA MaxCut sweep 案例就是最直接的证明。
