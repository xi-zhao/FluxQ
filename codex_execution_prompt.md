# 给 Codex 的执行提示词

你要实现一个新的仓库：**Quantum Runtime CLI**。

先完整阅读同目录下的 `quantum_runtime_cli_build_plan.md`，并严格按其中定义的目标、边界、目录结构、命令契约、QSpec、workspace、backend driver 和 PR 顺序执行。

## 最高优先级原则

1. 这是一个**独立 CLI runtime**，不是聊天 agent。
2. 它必须能被任意 coding agent 平台通过**写文件 + 调命令 + 读 JSON**的方式调用。
3. **不要实现内置 LLM planner**。
4. **不要为 aionrs 写 custom tool**。
5. 首版只需要让 aionrs 通过 Bash + 文件集成用起来。
6. **QSpec 是唯一真相**；Qiskit / Classiq 只是 backend / exporter。
7. 所有机器输出必须稳定、可测、可 schema 校验。
8. 对不支持的 backend / pattern / 依赖缺失，必须返回**结构化错误**，不能 silent fail。

## 当前执行方式

按以下顺序逐步实现，每一步都：
- 写代码
- 补测试
- 运行测试
- 更新文档
- 给出验收命令

## 实施顺序（必须按序）

### Step 1
实现 PR1：
- `pyproject.toml`
- `src/quantum_runtime/cli.py`
- `qrun init`
- workspace 初始化
- 基础测试

完成后运行：
```bash
pytest -q
qrun init --workspace .quantum
```

### Step 2
实现 PR2：
- intent parser
- workspace manager
- manifest
- trace

### Step 3
实现 PR3：
- QSpec Pydantic 模型
- planner
- 支持 pattern: `ghz`, `bell`, `qft`, `hardware_efficient_ansatz`, `qaoa_ansatz`

### Step 4
实现 PR4 + PR5：
- Qiskit emitter
- 本地 simulation
- resource report
- 图输出

### Step 5
实现 PR6 + PR7：
- OpenQASM 3 导出
- transpile validation
- basis gates / connectivity map 支持

### Step 6
实现 PR8：
- Classiq emitter（仅导出）
- 支持能力检查
- 未安装 Classiq 时 graceful degrade

### Step 7
实现 PR9 + PR10：
- 可选 Classiq synthesize backend
- benchmark
- summary/report polish

### Step 8
实现 PR11 + PR12：
- aionrs integration assets
- README
- docs
- packaging 完整化

## 强制工程约束

1. Python 版本固定按方案执行。
2. CLI 使用 `typer`。
3. 数据模型使用 `pydantic v2`。
4. 所有 `exec --json` 输出必须有明确 schema。
5. Qiskit 相关逻辑放在 `backends/` + `lowering/`，不要把后端细节散落到 CLI 层。
6. Classiq 相关逻辑必须是可选依赖。
7. 不允许把宿主平台逻辑写进 runtime 核心。
8. 所有路径写入必须通过 workspace manager，不能到处手写字符串路径。

## 代码风格要求

- 类型标注完整
- 错误处理清晰
- 禁止大函数堆砌
- 优先可读性，不要过度抽象
- 所有 public 接口写 docstring
- JSON 字段名保持 snake_case

## 测试要求

至少包含：
- unit tests
- integration tests
- golden snapshot tests

必须覆盖：
- GHZ intent -> qspec
- GHZ qspec -> qiskit code
- GHZ 本地仿真
- GHZ qasm3 export
- 非法 connectivity_map 失败路径
- classiq 未安装时的结构化错误

## 对你的输出要求

每完成一个 step，都输出：
1. 改了哪些文件
2. 新增了哪些测试
3. 运行了哪些命令
4. 当前还缺什么
5. 下一步做什么

## 第一个验收目标

让以下命令成功：

```bash
uv venv
source .venv/bin/activate
uv pip install -e '.[dev,qiskit]'
qrun init --workspace .quantum
cp examples/intent-ghz.md .quantum/intents/latest.md
qrun exec --workspace .quantum --intent-file .quantum/intents/latest.md --json
python .quantum/artifacts/qiskit/main.py
```

## 绝对不要做的事

- 不要加内置聊天模式
- 不要依赖某一个 agent 平台私有协议
- 不要把 aionrs 当成唯一宿主
- 不要先做 web UI
- 不要在 v1 试图复刻完整 Classiq synthesis engine
- 不要实现 native `.qmod` parser
- 不要跳过测试

现在从 **PR1 / Step 1** 开始执行。
