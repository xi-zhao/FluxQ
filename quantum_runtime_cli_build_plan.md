# Quantum Runtime CLI 完整构建方案（可直接交给 Codex 执行）

## 0. 项目定位

### 产品名（占位）
- Python package: `quantum-runtime`
- CLI binary: `qrun`

### 一句话定义
做一个**独立于任何 coding agent 平台**的量子代码运行时 CLI：
- 输入：agent 生成的自然语言意图文件 / 结构化 intent / QSpec
- 核心：自有 QSpec / Workspace / 编译与验证闭环
- 输出：Qiskit 代码、OpenQASM 3、Classiq Python SDK 代码、仿真/转译/benchmark 报告

### 架构原则
1. **CLI 不是聊天机器人**，而是 agent 可调用的确定性 runtime。
2. **自有 IR（QSpec）是唯一真相**；Qiskit / Classiq 都是 backend 或 export target。
3. **状态不在 prompt 里，在 workspace 里**。
4. **先适配 aionrs，用 Bash + 文件方式接入，不做 aionrs 深耦合插件**。
5. **v1 不做内置 LLM planner**，由宿主 agent 负责把用户自然语言整理成 `intent.md`；CLI 负责解析、编译、验证、导出。
6. **先做确定性能力，再做智能能力**。

### v0.1 目标
- 支持 `intent.md -> QSpec -> Qiskit / QASM3 / 报告`
- 可选支持 `QSpec -> Classiq Python SDK`
- 支持本地仿真、Target 约束校验、资源统计、图输出
- 可被 aionrs / Codex / Claude Code 风格宿主通过 Bash 直接调用

### v0.1 非目标
- 不复刻 Classiq 的完整 synthesis engine
- 不实现完整 native QMOD parser
- 不做 Web Studio
- 不做硬件实际提交为默认路径
- 不把量子语义直接做成 aionrs 的 tool surface

---

## 1. 为什么这么做

### 1.1 先做独立 CLI，而不是深改 aionrs
- 宿主平台会变，但你的壁垒不应该绑在单个平台 API 上。
- aionrs 初期适合验证，因为它已经有文件读写、Bash、hooks、`CLAUDE.md` 注入、MCP 和 session；但你不应该把量子能力设计成 aionrs 内部专属协议。
- 真实产品边界应该是：**稳定 CLI ABI + 自有 Workspace + 自有 IR + 自有验证闭环**。

### 1.2 为什么不用“十几个 quantum tools”
- tool surface 会带来上下文税。
- 量子任务天然是“多阶段流水线”，不是“单步工具调用”。
- CLI 最好的 agent 接口应该是：
  1. 写 intent 文件
  2. 执行一条命令
  3. 读取一个 JSON 摘要和若干产物路径

### 1.3 为什么用 Python 做 runtime
- Qiskit、Classiq 的一线 SDK 都在 Python 生态里。
- Rust 可以后面做 launcher / thin wrapper，但核心 runtime、backend driver、导出器、验证器先放 Python 更现实。

---

## 2. 技术路线总览

## 2.1 总体组件

```text
┌─────────────────────────────────────────────┐
│ Agent Host                                 │
│ aionrs / Codex / Claude Code / IDE agent   │
└─────────────────────────────────────────────┘
                    │
                    │ 写 intent.md / 调用 qrun exec
                    ▼
┌─────────────────────────────────────────────┐
│ qrun CLI                                    │
│ - command parser                            │
│ - workspace loader                          │
│ - intent parser                             │
│ - pipeline orchestrator                     │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│ Core Runtime                                │
│ - QSpec models                              │
│ - normalization                             │
│ - lowering                                  │
│ - diagnostics                               │
│ - reporting                                 │
└─────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Qiskit backend  │  │ Classiq backend │  │ OpenQASM export │
│ emit/sim/target │  │ emit/synthesize │  │ dump/dumps      │
└─────────────────┘  └─────────────────┘  └─────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│ Workspace (.quantum/)                       │
│ spec / artifacts / reports / figures / trace│
└─────────────────────────────────────────────┘
```

## 2.2 运行流水线

```text
intent.md or qspec.json
    ↓
parse_intent()
    ↓
plan_to_qspec()
    ↓
normalize_qspec()
    ↓
emit artifacts (qiskit / qasm3 / classiq)
    ↓
simulate / transpile_validate / estimate / diagram
    ↓
write reports + manifest
    ↓
return compact JSON summary
```

---

## 3. 仓库结构

```text
quantum-runtime/
├─ pyproject.toml
├─ README.md
├─ LICENSE
├─ .gitignore
├─ src/
│  └─ quantum_runtime/
│     ├─ __init__.py
│     ├─ cli.py
│     ├─ logging.py
│     ├─ config.py
│     ├─ errors.py
│     ├─ api/
│     │  ├─ models.py
│     │  ├─ exec_result.py
│     │  └─ schemas.py
│     ├─ workspace/
│     │  ├─ manager.py
│     │  ├─ manifest.py
│     │  ├─ trace.py
│     │  └─ paths.py
│     ├─ intent/
│     │  ├─ parser.py
│     │  ├─ markdown.py
│     │  ├─ structured.py
│     │  └─ planner.py
│     ├─ qspec/
│     │  ├─ model.py
│     │  ├─ nodes.py
│     │  ├─ constraints.py
│     │  ├─ normalize.py
│     │  ├─ validate.py
│     │  └─ diff.py
│     ├─ lowering/
│     │  ├─ qiskit_emitter.py
│     │  ├─ qasm3_emitter.py
│     │  ├─ classiq_emitter.py
│     │  └─ helpers.py
│     ├─ importers/
│     │  ├─ qasm_import.py
│     │  └─ qiskit_import.py
│     ├─ backends/
│     │  ├─ base.py
│     │  ├─ qiskit_local.py
│     │  ├─ qiskit_target.py
│     │  ├─ classiq_backend.py
│     │  └─ registry.py
│     ├─ diagnostics/
│     │  ├─ simulate.py
│     │  ├─ transpile_validate.py
│     │  ├─ resources.py
│     │  ├─ diagrams.py
│     │  └─ benchmark.py
│     ├─ reporters/
│     │  ├─ writer.py
│     │  ├─ summary.py
│     │  └─ suggestions.py
│     └─ integrations/
│        └─ aionrs/
│           ├─ CLAUDE.md.example
│           ├─ hooks.example.toml
│           └─ run_quantum_task.sh
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  ├─ golden/
│  └─ fixtures/
├─ examples/
│  ├─ intent-ghz.md
│  ├─ intent-maxcut-qaoa.md
│  ├─ qspec-ghz.json
│  └─ qspec-maxcut-qaoa.json
└─ docs/
   ├─ architecture.md
   ├─ qspec.md
   ├─ cli.md
   ├─ aionrs-integration.md
   └─ classiq-compatibility.md
```

---

## 4. 依赖和环境

## 4.1 环境基线
- Python: **3.11**
- 包管理：`uv`（首选）或 `pip`
- 测试：`pytest`
- 数据模型：`pydantic v2`
- CLI：`typer`
- JSON：标准库 `json` + 可选 `orjson`

## 4.2 依赖分组

### 核心依赖
- `pydantic>=2`
- `typer>=0.12`
- `pyyaml>=6`
- `rich>=13`
- `networkx>=3`

### qiskit extra
- `qiskit`
- `qiskit-aer`
- 可选 `qiskit-ibm-runtime`

### classiq extra
- `classiq`

### dev extra
- `pytest`
- `pytest-cov`
- `ruff`
- `mypy`
- `types-PyYAML`

## 4.3 pyproject 建议

```toml
[project]
name = "quantum-runtime"
version = "0.1.0"
description = "Agent-facing quantum runtime CLI"
requires-python = ">=3.11,<3.12"
dependencies = [
  "pydantic>=2.8",
  "typer>=0.12",
  "pyyaml>=6.0",
  "rich>=13.7",
  "networkx>=3.3",
]

[project.optional-dependencies]
qiskit = [
  "qiskit>=2,<3",
  "qiskit-aer>=0.17",
]
ibm = [
  "qiskit-ibm-runtime>=0.40",
]
classiq = [
  "classiq>=1,<2",
]
dev = [
  "pytest>=8",
  "pytest-cov>=5",
  "ruff>=0.5",
  "mypy>=1.10",
]

[project.scripts]
qrun = "quantum_runtime.cli:app"
```

说明：
- `requires-python` 固定到 3.11.x 是为了减少跨 Qiskit / Classiq / matplotlib 的轮子兼容噪音。
- Qiskit major 先 pin 到 `<3`。
- Classiq 不锁死小版本，但 lockfile 必须锁定 tested minor。

---

## 5. CLI 设计

## 5.1 命令面

```bash
qrun init
qrun exec
qrun inspect
qrun export
qrun bench
qrun doctor
qrun backend list
qrun version
```

## 5.2 设计原则
- **agent-facing 主要命令只有一个：`exec`**
- 其余命令服务于人类调试、CI、排障

## 5.3 `qrun init`

初始化工作区：

```bash
qrun init --workspace .quantum
```

行为：
- 创建 `.quantum/`
- 写入 `workspace.json`
- 写入默认 `qrun.toml`
- 建立目录骨架

## 5.4 `qrun exec`

### 输入方式
```bash
qrun exec --workspace .quantum --intent-file .quantum/intents/task.md --json
qrun exec --workspace .quantum --qspec-file .quantum/specs/current.json --json
qrun exec --workspace .quantum --intent-text "生成4比特GHZ并测量" --json
```

### 核心行为
1. 加载 workspace
2. 读取 intent 或 qspec
3. 生成/更新 `QSpec`
4. 输出目标 artifacts
5. 执行诊断
6. 写入报告
7. 返回机器可读 JSON

### 标准 JSON 返回

```json
{
  "status": "ok",
  "workspace": ".quantum",
  "revision": "rev_000012",
  "summary": "Generated a 4-qubit GHZ circuit, exported Qiskit and OpenQASM 3, and validated successfully on local simulation.",
  "warnings": [],
  "errors": [],
  "artifacts": {
    "qspec": ".quantum/specs/current.json",
    "qiskit_code": ".quantum/artifacts/qiskit/main.py",
    "qasm3": ".quantum/artifacts/qasm/main.qasm",
    "diagram_png": ".quantum/figures/circuit.png",
    "report": ".quantum/reports/latest.json"
  },
  "diagnostics": {
    "simulation": {
      "status": "ok",
      "shots": 1024
    },
    "transpile": {
      "status": "ok",
      "backend": "local_target"
    },
    "resources": {
      "qubits": 4,
      "depth": 4,
      "two_qubit_gates": 3
    }
  },
  "next_actions": [
    "read .quantum/reports/latest.json",
    "inspect .quantum/artifacts/qiskit/main.py"
  ]
}
```

### Exit code 约定
- `0`: 完全成功
- `2`: 成功但有告警 / 部分降级
- `3`: 输入非法
- `4`: backend 不支持
- `5`: 编译失败
- `6`: 仿真/转译失败
- `7`: 外部依赖缺失（如未安装 classiq）

## 5.5 `qrun inspect`

```bash
qrun inspect --workspace .quantum
qrun inspect --workspace .quantum --json
```

输出：
- 当前 revision
- 当前 QSpec 摘要
- 最近 artifacts
- 最近诊断
- backend 能力

## 5.6 `qrun export`

```bash
qrun export --workspace .quantum --format qiskit
qrun export --workspace .quantum --format qasm3
qrun export --workspace .quantum --format classiq-python
```

## 5.7 `qrun bench`

```bash
qrun bench --workspace .quantum --backends qiskit-local,classiq --json
```

输出对比：
- 原始 depth
- transpiled depth
- 2Q gate 数量
- width
- backend capability notes
- 失败原因（如果某 backend 不支持）

## 5.8 `qrun doctor`

```bash
qrun doctor --workspace .quantum
qrun doctor --workspace .quantum --fix
```

功能：
- 检查依赖安装
- 检查 Qiskit / Aer / Classiq 是否可导入
- 检查 workspace 是否损坏
- 可选修复缺目录 / manifest 丢失

---

## 6. Workspace 设计

## 6.1 目录结构

```text
.quantum/
├─ workspace.json
├─ qrun.toml
├─ intents/
│  ├─ latest.md
│  └─ history/
├─ specs/
│  ├─ current.json
│  └─ history/
├─ artifacts/
│  ├─ qiskit/
│  │  └─ main.py
│  ├─ classiq/
│  │  └─ main.py
│  └─ qasm/
│     └─ main.qasm
├─ figures/
│  ├─ circuit.png
│  └─ circuit.txt
├─ reports/
│  ├─ latest.json
│  └─ history/
├─ trace/
│  └─ events.ndjson
└─ cache/
```

## 6.2 `workspace.json`

```json
{
  "workspace_version": "0.1",
  "project_id": "proj_xxx",
  "created_at": "2026-04-02T10:00:00Z",
  "current_revision": "rev_000012",
  "active_spec": "specs/current.json",
  "active_report": "reports/latest.json",
  "default_exports": ["qiskit", "qasm3"],
  "history_limit": 50
}
```

## 6.3 trace 设计
- 每次 exec 都往 `trace/events.ndjson` 追加事件
- 事件类型：
  - `intent_loaded`
  - `qspec_created`
  - `artifact_written`
  - `simulation_done`
  - `transpile_done`
  - `backend_failed`
  - `summary_emitted`

trace 是未来训练数据资产来源。

---

## 7. Intent 文件规范

## 7.1 规范目标
intent 文件由宿主 agent 生成，格式允许半结构化，但必须稳定。

## 7.2 推荐格式：Markdown + YAML front matter

```md
---
title: GHZ circuit
exports:
  - qiskit
  - qasm3
backend_preferences:
  - qiskit-local
constraints:
  max_width: 4
  max_depth: 64
shots: 1024
---

# Goal
Generate a 4-qubit GHZ circuit and measure all qubits.

# Inputs
None

# Outputs
Measurement counts

# Notes
Prefer simple educational code.
```

## 7.3 解析策略
`intent/parser.py` 负责：
1. 读 front matter
2. 读 section blocks
3. 生成 `IntentModel`
4. 缺失字段使用默认值填充

## 7.4 `IntentModel`

```python
class IntentModel(BaseModel):
    title: str | None = None
    goal: str
    exports: list[str] = ["qiskit", "qasm3"]
    backend_preferences: list[str] = ["qiskit-local"]
    constraints: dict[str, Any] = {}
    shots: int = 1024
    notes: str | None = None
```

说明：
- v1 不做复杂 NLP 解析器。
- 宿主 agent 负责把用户自然语言整理成这个格式。

---

## 8. QSpec（自有 IR）设计

## 8.1 设计原则
- **比 QASM 高一层**，保留语义块和约束
- **比完整 Classiq/Qmod 低一层**，便于快速落地
- 允许一部分高层 pattern node，而不是只允许 gate list

## 8.2 核心对象

```python
class QSpec(BaseModel):
    version: str = "0.1"
    program_id: str
    title: str | None = None
    goal: str
    entrypoint: str = "main"
    registers: list[Register]
    parameters: list[Parameter] = []
    body: list[Node]
    observables: list[Observable] = []
    constraints: Constraints = Constraints()
    backend_preferences: list[str] = ["qiskit-local"]
    metadata: dict[str, Any] = {}
```

### Register
```python
class Register(BaseModel):
    kind: Literal["qubit", "cbit"]
    name: str
    size: int
```

### Parameter
```python
class Parameter(BaseModel):
    name: str
    type: Literal["float", "int", "angle"] = "float"
    default: float | int | None = None
    bounds: tuple[float, float] | None = None
```

## 8.3 Node 类型（v1）

### 底层节点
- `AllocateNode`
- `GateNode`
- `MeasureNode`
- `ResetNode`
- `BarrierNode`
- `ForNode`
- `IfMeasureNode`
- `BlockNode`

### 语义节点
- `PatternNode`：`ghz`, `bell`, `qft`, `hardware_efficient_ansatz`, `qaoa_ansatz`
- `WithinApplyNode`：语义化 uncompute 块
- `ObservableNode`：Z / ZZ / Hamiltonian term

## 8.4 Node 示例

```python
class PatternNode(BaseModel):
    kind: Literal["pattern"] = "pattern"
    pattern: Literal[
        "ghz",
        "bell",
        "qft",
        "hardware_efficient_ansatz",
        "qaoa_ansatz",
    ]
    args: dict[str, Any] = {}
```

```python
class GateNode(BaseModel):
    kind: Literal["gate"] = "gate"
    op: str
    targets: list[str]
    controls: list[str] = []
    params: list[str | float | int] = []
```

## 8.5 Constraints

```python
class Constraints(BaseModel):
    max_width: int | None = None
    max_depth: int | None = None
    basis_gates: list[str] | None = None
    connectivity_map: list[tuple[int, int]] | None = None
    backend_provider: str | None = None
    backend_name: str | None = None
    shots: int = 1024
    optimization_level: int = 2
```

## 8.6 GHZ 的 QSpec 示例

```json
{
  "version": "0.1",
  "program_id": "prog_ghz_4",
  "title": "4-qubit GHZ",
  "goal": "Generate a 4-qubit GHZ circuit and measure all qubits.",
  "entrypoint": "main",
  "registers": [
    {"kind": "qubit", "name": "q", "size": 4},
    {"kind": "cbit", "name": "c", "size": 4}
  ],
  "parameters": [],
  "body": [
    {"kind": "pattern", "pattern": "ghz", "args": {"register": "q", "size": 4}},
    {"kind": "measure", "qubits": ["q[0]", "q[1]", "q[2]", "q[3]"], "cbits": ["c[0]", "c[1]", "c[2]", "c[3]"]}
  ],
  "constraints": {"max_width": 4, "shots": 1024},
  "backend_preferences": ["qiskit-local"],
  "metadata": {"source": "intent"}
}
```

## 8.7 QAOA 的 QSpec 示例
- `PatternNode(pattern="qaoa_ansatz")`
- `args` 包含：
  - graph
  - p
  - mixer
  - cost_hamiltonian
  - parameter_names

注意：
- v1 不做通用任意优化问题 parser。
- 只支持 MaxCut / Ising 风格最小可用建模。

---

## 9. Planner 设计（无内置 LLM）

## 9.1 原则
- 宿主 agent 写 `intent.md`
- CLI 只做**规则化解析 + 模板规划**

## 9.2 `planner.py` 的职责
把 `IntentModel` 映射到 `QSpec`：
- 如果 goal 命中固定模式：
  - “GHZ” -> `PatternNode(ghz)`
  - “Bell” -> `PatternNode(bell)`
  - “QFT” -> `PatternNode(qft)`
  - “QAOA” + MaxCut -> `PatternNode(qaoa_ansatz)`
- 否则：
  - 若输入已经是 `qspec-file`，直接通过
  - 若无法确定，返回结构化错误：`manual_qspec_required`

## 9.3 重要范围控制
v1 不接受“任意自然语言都自动规划成高质量量子算法”这种目标。

v1 的目标是：
- 把**常见、明确、模式化**的量子任务做稳
- 给 agent 一个**可预测的编译运行时**

---

## 10. Lowering / Emitter 设计

## 10.1 后端接口

```python
class BackendDriver(Protocol):
    name: str

    def supports(self, qspec: QSpec) -> CapabilityReport: ...
    def emit(self, qspec: QSpec, workspace: Path) -> EmitResult: ...
    def validate(self, qspec: QSpec, workspace: Path) -> ValidationReport: ...
    def simulate(self, qspec: QSpec, workspace: Path) -> SimulationReport | None: ...
    def benchmark(self, qspec: QSpec, workspace: Path) -> BenchmarkReport | None: ...
```

## 10.2 `QiskitEmitter`
职责：
- QSpec -> Python 源码
- 生成 `QuantumCircuit`
- 可选参数对象
- 可选观测量对象
- 输出为可运行脚本

### 代码模板要求
- 代码必须可直接运行
- 使用函数式入口：`def build_circuit(...) -> QuantumCircuit:`
- 如果有仿真入口，写在 `if __name__ == "__main__":`
- 自动包含 measurement counts 打印

### 生成模板示意
```python
from qiskit import QuantumCircuit


def build_circuit() -> QuantumCircuit:
    qc = QuantumCircuit(4, 4)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.cx(2, 3)
    qc.measure(range(4), range(4))
    return qc


if __name__ == "__main__":
    from qiskit_aer import AerSimulator
    qc = build_circuit()
    sim = AerSimulator()
    result = sim.run(qc, shots=1024).result()
    print(result.get_counts())
```

## 10.3 `Qasm3Emitter`
- 优先从 Qiskit circuit 导出
- 写入 `artifacts/qasm/main.qasm`
- 对于 Qiskit 不支持的高级节点，先 lower 到 circuit 再导出

## 10.4 `ClassiqEmitter`
职责：
- QSpec -> Classiq Python SDK 代码
- 尽量用高层模式表达，不降成纯 gate list

### v1 支持范围
- `ghz`
- `bell`
- `qft`
- `hardware_efficient_ansatz`
- 部分 `qaoa_ansatz`
- `within_apply`

### 不支持的情况
返回结构化能力错误：
```json
{
  "status": "unsupported",
  "reason": "pattern_not_supported_by_classiq_emitter",
  "details": {"pattern": "custom_oracle"}
}
```

## 10.5 `within_apply` 语义映射
- QSpec 内部保留 `WithinApplyNode`
- 对 Qiskit lowering：展开成 `U` / `V` / `U†` 结构
- 对 Classiq lowering：优先映射成接近 `within-apply` 语义的代码结构

---

## 11. Backend 实现

## 11.1 `QiskitLocalBackend`
能力：
- 本地模拟
- 统计资源
- 生成图
- 生成 QASM 3

### 主要实现
- `build_circuit_from_qspec(qspec)`
- `run_local_simulation(circuit, shots)`
- `draw_diagram(circuit)`
- `estimate_resources(circuit)`

## 11.2 `QiskitTargetBackend`
能力：
- 使用 `Target` 或 backend constraints 做转译校验
- 检查：
  - basis gates
  - coupling map
  - angle bounds（后续）
  - optimization result

### 输入来源
- 显式 `constraints.basis_gates/connectivity_map`
- 或远端 provider 获取的 backend（v1 可不做）

### 输出报告
```json
{
  "status": "ok",
  "transpiled_depth": 27,
  "transpiled_two_qubit_gates": 9,
  "warnings": []
}
```

## 11.3 `ClassiqBackend`
能力：
- 生成 Classiq Python SDK 文件
- 如果安装并配置 Classiq，则尝试 synthesize
- 输出 Classiq 相关资源和导出产物

### 配置开关
默认关闭，需要：
- 安装 `classiq`
- 显式 `backend_preferences` 包含 `classiq`
- 配置环境变量/API 信息

### v1 不做
- 不强依赖 Classiq 平台登录流程自动化
- 不实现 Studio 集成

---

## 12. Diagnostics 设计

## 12.1 simulation
- 默认只对 Qiskit local 路径执行
- 记录：
  - shots
  - counts
  - error
  - elapsed_ms

## 12.2 transpile validation
- 对有 constraints 的程序执行
- 记录：
  - success/fail
  - original depth / transpiled depth
  - original 2Q / transpiled 2Q
  - coupling insertions
  - warnings

## 12.3 resources
统一指标：
- width
- depth
- size
- gate_histogram
- two_qubit_gates
- measure_count
- parameter_count

## 12.4 diagrams
至少产出两个文件：
- `circuit.txt`
- `circuit.png`

## 12.5 benchmark
v1 benchmark 只做“结构性 benchmark”，不做真实硬件性能宣称：
- 比较不同 backend lowering 产物的 width/depth/2Q gates
- 如果某 backend 无法支持，记录原因

---

## 13. Reporter 设计

## 13.1 `reports/latest.json` 结构

```json
{
  "revision": "rev_000012",
  "input": {
    "mode": "intent",
    "path": ".quantum/intents/latest.md"
  },
  "qspec": {
    "path": ".quantum/specs/current.json",
    "hash": "sha256:..."
  },
  "artifacts": {...},
  "diagnostics": {...},
  "backend_reports": {...},
  "warnings": [],
  "errors": [],
  "suggestions": [
    "Try adding connectivity constraints for realistic transpilation.",
    "Add benchmark against Classiq backend if installed."
  ]
}
```

## 13.2 `summary.py`
把大报告压成一段适合 agent 读取的摘要。

规则：
- <= 1200 chars
- 包含 status / 核心产物 / 核心错误 / 下一步建议

---

## 14. Aionrs 集成方案（首发宿主）

## 14.1 首发集成原则
**不用自定义 aionrs tool，不改 aionrs core。**

只使用：
- Read
- Write
- Bash
- CLAUDE.md
- hooks（可选）

## 14.2 工作流

```text
用户自然语言
  ↓
aionrs 读取 CLAUDE.md 规则
  ↓
aionrs 写 .quantum/intents/latest.md
  ↓
aionrs 执行: qrun exec --workspace .quantum --intent-file .quantum/intents/latest.md --json
  ↓
aionrs 读取 reports/latest.json 和 artifacts
  ↓
aionrs 向用户总结并展示代码路径
```

## 14.3 `CLAUDE.md` 示例

```md
# Quantum Project Rules

When the user asks for quantum-computing code, do not handwrite large quantum programs first.

Workflow:
1. Write the task into `.quantum/intents/latest.md` using the intent template.
2. Run:
   `qrun exec --workspace .quantum --intent-file .quantum/intents/latest.md --json`
3. Read `.quantum/reports/latest.json`.
4. If artifacts were generated successfully, inspect the generated code before proposing edits.
5. Prefer updating the intent and re-running `qrun` over manually rewriting generated quantum code.
```

## 14.4 hooks 示例（可选）

```toml
[hooks.post_tool_use]
command = "bash -lc 'if [ -f .quantum/specs/current.json ]; then qrun doctor --workspace .quantum >/dev/null 2>&1 || true; fi'"
```

## 14.5 为什么这样接
- 保持平台无关
- 利用 aionrs 现有 Bash / 文件能力
- 不被 aionrs 当前 sub-agent / tool registry 行为绑定

---

## 15. Classiq 兼容策略

## 15.1 定位
Classiq 是**backend / exporter / optional synthesis engine**，不是源语义。

## 15.2 v1 兼容能力
1. `QSpec -> Classiq Python SDK`
2. 若已安装 Classiq，可尝试 synthesize
3. 支持输出对比报告
4. 支持从 OpenQASM 侧做互操作（后续）

## 15.3 v1 不做的兼容能力
- 不直接支持 native `.qmod` parser
- 不做完整 `qasm_to_qmod -> 再回到 QSpec` 的 round-trip
- 不保证所有高层语义节点都能映射到 Classiq

## 15.4 后续路线
v0.2 / v0.3 可加：
- `import --format qasm`
- `import --format qiskit`
- 如果需要，再做 `import --format classiq-qmod`（排到后面）

---

## 16. 版本与兼容策略

## 16.1 版本策略
- `0.1.x`: 稳定 CLI JSON 输出、稳定 workspace 布局、稳定 QSpec 基础字段
- `0.2.x`: 扩展 pattern node、Classiq synthesize 增强、import 能力
- `0.3.x`: 可选 remote hardware submit / richer benchmarking

## 16.2 兼容原则
- `qrun exec --json` 输出一旦发布，字段新增只能追加，不能删除/重命名
- `QSpec.version` 必须带 schema version
- workspace 中保留 revision 历史

---

## 17. 测试策略

## 17.1 Unit tests
覆盖：
- intent parser
- qspec validation
- node normalization
- emitter 代码生成
- report writer
- workspace manager

## 17.2 Integration tests

### 场景 1：GHZ
```bash
qrun init --workspace .quantum
qrun exec --workspace .quantum --intent-file examples/intent-ghz.md --json
```
断言：
- 生成 qspec
- 生成 qiskit 代码
- 生成 qasm3
- 本地仿真成功
- 有 diagram

### 场景 2：QAOA MaxCut
断言：
- 生成参数化电路
- 资源统计可用
- benchmark 报告存在

### 场景 3：Classiq 未安装
断言：
- 返回结构化 `dependency_missing`
- 其他 backend 不受影响

### 场景 4：非法 coupling map
断言：
- transpile validation 失败
- 报告里有清晰错误

## 17.3 Golden tests
固定输入 -> 固定 artifact snapshot：
- GHZ qiskit 代码
- GHZ qasm3
- GHZ report 摘要
- QAOA qspec

## 17.4 CI
- `ruff check .`
- `mypy src`
- `pytest -q`
- 对 qiskit extra 跑 integration tests
- Classiq tests 仅在专门环境跑

---

## 18. PR 切分（让 Codex 按序执行）

## PR1: 项目脚手架
### 目标
- 建立 `pyproject.toml`
- CLI 骨架
- `qrun init`
- workspace 目录生成

### 完成条件
- `qrun init --workspace .quantum` 可运行
- 生成目录和默认配置
- 单元测试通过

## PR2: Intent parser + Workspace manager
### 目标
- 实现 Markdown + front matter 解析
- 实现 revision / manifest / trace

### 完成条件
- 能读取 `examples/intent-ghz.md`
- 写入 `trace/events.ndjson`

## PR3: QSpec model + planner
### 目标
- 实现 Pydantic 模型
- 支持 GHZ / Bell / QFT / HEA / QAOA pattern
- `intent -> qspec`

### 完成条件
- 生成稳定 `specs/current.json`
- snapshot test 通过

## PR4: Qiskit emitter
### 目标
- QSpec -> Python 源码
- 生成可运行 `main.py`

### 完成条件
- GHZ 示例生成的代码可导入并运行
- 代码风格稳定

## PR5: Qiskit local diagnostics
### 目标
- 本地仿真
- 资源统计
- ASCII 图和 PNG 图

### 完成条件
- GHZ 仿真成功
- `reports/latest.json` 含 simulation/resources/diagram

## PR6: QASM3 export
### 目标
- 从 circuit 导出 OpenQASM 3
- 写 artifact

### 完成条件
- `artifacts/qasm/main.qasm` 存在
- snapshot test 通过

## PR7: Target validation
### 目标
- 支持 basis gates / connectivity map
- 报告 transpiled metrics

### 完成条件
- 约束成功/失败路径都可测试

## PR8: Classiq emitter（仅导出）
### 目标
- 支持 QSpec -> Classiq Python SDK
- 支持能力检查

### 完成条件
- GHZ / QFT / HEA 至少可导出
- 不支持 pattern 返回结构化 unsupported

## PR9: Classiq backend（可选 synthesize）
### 目标
- 如果安装/配置正确，则调用 Classiq synthesize
- 记录输出/错误

### 完成条件
- 无 Classiq 环境时 graceful degrade
- 有环境时生成 backend report

## PR10: benchmark + reporter polish
### 目标
- 多 backend 对比
- 统一摘要
- suggestions 生成

### 完成条件
- `qrun bench --json` 可运行
- summary 足够短且稳定

## PR11: aionrs integration assets
### 目标
- 生成 `integrations/aionrs/CLAUDE.md.example`
- hooks 示例
- 文档示例

### 完成条件
- 按文档可在 aionrs 中跑通

## PR12: packaging + docs + release hygiene
### 目标
- README
- architecture docs
- changelog skeleton
- versioning notes

### 完成条件
- 新用户能按 README 安装并运行 GHZ 示例

---

## 19. `exec` 内部伪代码

```python
def exec_command(args: ExecArgs) -> ExecResult:
    ws = WorkspaceManager.load_or_init(args.workspace)
    source = load_input(args)

    if source.kind == "intent":
        intent = parse_intent(source)
        qspec = plan_to_qspec(intent)
    else:
        qspec = load_qspec(source)

    qspec = normalize_qspec(qspec)
    validate_qspec(qspec)

    artifacts = {}
    backend_reports = {}
    warnings = []
    errors = []

    if "qiskit" in requested_exports(qspec, args):
        artifacts["qiskit_code"] = emit_qiskit(qspec, ws)

    if "qasm3" in requested_exports(qspec, args):
        artifacts["qasm3"] = emit_qasm3(qspec, ws)

    if "classiq-python" in requested_exports(qspec, args):
        result = emit_classiq(qspec, ws)
        if result.status == "ok":
            artifacts["classiq_code"] = result.path
        else:
            warnings.append(result.reason)

    diag = run_diagnostics(qspec, ws, artifacts)
    report = write_report(ws, qspec, artifacts, diag, warnings, errors)
    summary = summarize_report(report)

    return ExecResult(
        status=derive_status(warnings, errors),
        workspace=str(ws.root),
        revision=ws.current_revision,
        summary=summary,
        warnings=warnings,
        errors=errors,
        artifacts=artifacts,
        diagnostics=diag,
        next_actions=build_next_actions(report),
    )
```

---

## 20. `backends/base.py` 接口草图

```python
from pathlib import Path
from typing import Protocol

from quantum_runtime.qspec.model import QSpec


class CapabilityReport(TypedDict):
    status: str
    supported: bool
    reasons: list[str]


class EmitResult(TypedDict):
    status: str
    path: str | None
    reason: str | None


class BackendDriver(Protocol):
    name: str

    def supports(self, qspec: QSpec) -> CapabilityReport: ...
    def emit(self, qspec: QSpec, out_dir: Path) -> EmitResult: ...
```

---

## 21. 风险控制

## 风险 1：Classiq 覆盖面不足
应对：
- emitter 只支持明确 pattern
- 不支持时返回结构化 unsupported，而不是瞎生成

## 风险 2：Qiskit API 演进
应对：
- pin major version
- 模板生成，不把 API 细节交给 agent 记忆
- CI 跑 integration tests

## 风险 3：intent 太自由导致 planner 不稳定
应对：
- 前期要求宿主 agent 生成结构化 intent 模板
- planner 只做小范围模板映射

## 风险 4：CLI 输出不稳定导致宿主 agent 难接
应对：
- JSON schema 先冻结
- golden tests 覆盖 `exec --json`

---

## 22. Definition of Done

## v0.1 Done 标准
满足以下全部条件才算完成：
1. `qrun init`、`exec`、`inspect`、`doctor` 可用
2. GHZ / QFT / HEA / 基础 QAOA intent 能跑通
3. 能生成 Qiskit 代码、QASM3、report、diagram
4. 支持 local simulation 和 target validation
5. Classiq emitter 至少覆盖 GHZ/QFT/HEA
6. aionrs 按示例可接通
7. CI 通过，golden tests 稳定

## v0.2 Done 标准
1. 增加 import 能力
2. 加强 Classiq synthesize/report
3. 增加更多 pattern
4. 增加 benchmark 对比维度

---

## 23. 交给 Codex 的执行要求

1. **严格按 PR 顺序实施**，不要试图一口气完成全部功能。
2. 每个 PR 必须：
   - 更新测试
   - 更新文档
   - 给出可运行命令
3. **不要实现内置 LLM planner**。
4. **不要为 aionrs 写 custom tool**；初期只走 Bash + 文件集成。
5. 所有 JSON 输出必须通过 schema 校验。
6. 所有不支持的 backend/path 必须返回结构化错误，不允许 silent fail。
7. 先做 deterministic pipeline，再加 Classiq synthesize。
8. 如果遇到 Classiq 环境不可用，保留接口和测试替身，不阻塞整个项目。

---

## 24. 第一个里程碑验收命令

```bash
uv venv
source .venv/bin/activate
uv pip install -e '.[dev,qiskit]'
qrun init --workspace .quantum
cp examples/intent-ghz.md .quantum/intents/latest.md
qrun exec --workspace .quantum --intent-file .quantum/intents/latest.md --json
cat .quantum/reports/latest.json
python .quantum/artifacts/qiskit/main.py
```

预期：
- `.quantum/specs/current.json` 存在
- `.quantum/artifacts/qiskit/main.py` 存在
- `.quantum/artifacts/qasm/main.qasm` 存在
- `.quantum/figures/circuit.png` 存在
- `.quantum/reports/latest.json` 中 `status=ok`

---

## 25. 第二个里程碑验收命令（Classiq 可选）

```bash
uv pip install -e '.[classiq]'
qrun export --workspace .quantum --format classiq-python
qrun bench --workspace .quantum --backends qiskit-local,classiq --json
```

预期：
- 若 Classiq 可用，导出 Classiq Python 文件
- 若不可用，输出结构化 dependency_missing 或 backend_unavailable
- 不影响已有 Qiskit 路径

