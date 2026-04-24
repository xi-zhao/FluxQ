# Phase 09: IBM Access & Backend Readiness - Research

**Researched:** 2026-04-18  
**Domain:** IBM Quantum Platform 认证、实例绑定与后端就绪性  
**Confidence:** HIGH

## User Constraints

本 phase 目录下不存在 `*-CONTEXT.md`，因此没有来自 discuss-phase 的额外锁定决策可逐字复制；planner 需要以下面的项目级约束作为本 phase 的硬边界。 [VERIFIED: `node ~/.codex/get-shit-done/bin/gsd-tools.cjs init phase-op "09"` + phase dir scan]

### Locked Decisions

- 仅做 **IBM Quantum Platform** 单一 provider 路径，不扩展多 provider。 [VERIFIED: local file `.planning/ROADMAP.md`; local file `.planning/REQUIREMENTS.md`; local file `.planning/STATE.md`]
- 仅做 **job mode 之前** 的访问与就绪性，不做 submit、poll、cancel、finalize。 [VERIFIED: local file `.planning/ROADMAP.md`; local file `.planning/REQUIREMENTS.md`]
- secrets 必须留在 `.quantum/` 之外；FluxQ 只能持久化引用和 provenance，不能持久化凭证本体。 [VERIFIED: local file `.planning/STATE.md`; local file `.planning/PROJECT.md`]
- 远端执行必须显式实例选择，且项目级方向已经禁止默认自动 backend 选择与静默重试。 [VERIFIED: local file `.planning/STATE.md`; local file `.planning/REQUIREMENTS.md`]
- 现有 `QSpec`、CLI 和 schema-versioned JSON/JSONL 合同必须兼容演进，不能引入 breaking IR 重写。 [VERIFIED: local file `.planning/PROJECT.md`; local file `src/quantum_runtime/runtime/contracts.py`; local file `src/quantum_runtime/cli.py`]

### Claude's Discretion

- 现有 roadmap 明确说 Phase 09 还缺 “credential configuration and backend discovery” 的精确 CLI 形状，因此命令命名和内部模块拆分仍由本 research 决策。 [VERIFIED: local file `.planning/STATE.md`]
- 现有代码已经把 `backend list`、`doctor`、schema-versioned JSON/JSONL 和 backend registry 做成稳定接缝，因此 IBM 接入应优先复用这些接缝，而不是新增第二套观测面。 [VERIFIED: local file `src/quantum_runtime/cli.py`; local file `src/quantum_runtime/runtime/backend_list.py`; local file `src/quantum_runtime/runtime/backend_registry.py`; local file `src/quantum_runtime/runtime/doctor.py`; local file `src/quantum_runtime/runtime/observability.py`]

### Deferred Ideas (OUT OF SCOPE)

- 多 provider 支持。 [VERIFIED: local file `.planning/REQUIREMENTS.md`]
- session 或 batch 作为 v1.1 默认体验。 [VERIFIED: local file `.planning/REQUIREMENTS.md`; local file `.planning/ROADMAP.md`]
- 默认 automatic backend selection。 [VERIFIED: local file `.planning/REQUIREMENTS.md`]
- automatic retry / silent resubmission。 [VERIFIED: local file `.planning/REQUIREMENTS.md`]
- provider-private 或 destructive remote mutation flows。 [VERIFIED: local file `.planning/REQUIREMENTS.md`]
- compare/pack/import 的远端终态兼容扩展；这些属于后续 phase。 [VERIFIED: local file `.planning/ROADMAP.md`]

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-01 | User can configure IBM Quantum Platform credentials and instance selection non-interactively for local agents and CI | 本 research 推荐 “external secret, internal reference” 模式、`qrun ibm configure` 最小配置入口、`doctor` 的 IBM profile gate、以及 env/saved-account 双模式。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/initialize-account] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/save-credentials] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/cloud-setup-untrusted] [VERIFIED: local file `src/quantum_runtime/workspace/manager.py`] |
| BACK-01 | User can list compatible remote backends and see readiness details before remote submission | 本 research 推荐复用 `qrun backend list`，在现有 JSON 合同上增量加入 IBM provider context、target readiness block、以及 `doctor --ci` 的 blocking/advisory gate。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/qpu-information] [CITED: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service] [VERIFIED: local file `src/quantum_runtime/runtime/backend_list.py`; local file `src/quantum_runtime/runtime/doctor.py`; local file `tests/test_cli_backend_list.py`; local file `tests/test_cli_doctor.py`] |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

仓库根目录不存在 `./CLAUDE.md`，因此没有额外的 CLAUDE 级项目指令。 [VERIFIED: repo root file check]

## Summary

Phase 09 应该只解决 “IBM access/profile resolution + backend readiness visibility + CI gate” 这三个问题，不应提前引入 remote submit、provider job handle、poll/cancel/finalization，因为这些能力已经分别被 roadmap 放在 Phases 10-13。 [VERIFIED: local file `.planning/ROADMAP.md`; local file `.planning/REQUIREMENTS.md`]

IBM 官方当前支持的 Python 接入面是 `qiskit-ibm-runtime` 的 `QiskitRuntimeService`；它支持两条认证路径：一条是显式传入 `token`/`instance` 的直接实例化路径，另一条是 trusted machine 上的 saved-account 路径。 官方同时明确提醒 API key 不应写进源码，saved account 会写到 `$HOME/.qiskit/qiskit-ibm.json`，而不是写进你的应用 workspace。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/initialize-account] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/save-credentials] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/cloud-setup-untrusted]

因此，FluxQ 在 Phase 09 的最窄可信实现应当是：把 secret 继续留在环境变量或 IBM 官方 saved-account 文件里，只在 `.quantum/qrun.toml` 存非 secret 引用，例如 `credential_mode`、`saved_account_name`、`token_env`、`instance`；然后把 IBM readiness 统一投影到已经存在的 `backend list` 和 `doctor` 机器合同中，而不是新增一套 provider-specific 输出模型。 [VERIFIED: local file `src/quantum_runtime/workspace/manager.py`; local file `src/quantum_runtime/runtime/backend_list.py`; local file `src/quantum_runtime/runtime/doctor.py`] [ASSUMED]

**Primary recommendation:** 使用 `qiskit-ibm-runtime~=0.46` 作为唯一 IBM SDK，新增一个只写非 secret profile 引用的 `qrun ibm configure`，并把远端可见性/就绪性放进现有 `qrun backend list` 与 `qrun doctor`。 [VERIFIED: PyPI https://pypi.org/project/qiskit-ibm-runtime/] [VERIFIED: local file `src/quantum_runtime/cli.py`] [ASSUMED]

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `qiskit-ibm-runtime` | `0.46.1` latest on PyPI, uploaded 2026-03-23. [VERIFIED: PyPI https://pypi.org/project/qiskit-ibm-runtime/] | IBM 官方 Python client；提供 `QiskitRuntimeService`、`save_account()`、`backends()`、`backend()`、`instances()`、`active_instance()`。 [CITED: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service] | 这是 IBM Quantum Platform 当前官方接入面；Phase 09 不需要自写 REST 客户端。 [CITED: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service] |
| `qiskit` | repo 当前使用 `2.3.1`；PyPI 最新 `2.4.0`。 [VERIFIED: local file `.planning/research/STACK.md`; VERIFIED: `python3 -m pip index versions qiskit`] | FluxQ 现有 Qiskit-first lowering / diagnostics 基线。 [VERIFIED: local file `.planning/PROJECT.md`; local file `pyproject.toml`] | Phase 09 只扩 IBM access，不应该改写现有 Qiskit spine。 [VERIFIED: local file `.planning/PROJECT.md`] |
| `Typer` | repo 当前与 PyPI 最新均为 `0.24.1`。 [VERIFIED: local file `.planning/research/STACK.md`; VERIFIED: `python3 -m pip index versions typer`] | 现有 CLI surface；`backend list`、`doctor`、JSON/JSONL 输出都通过它暴露。 [VERIFIED: local file `src/quantum_runtime/cli.py`] | Phase 09 的最窄落点是扩已有命令和子命名空间，不是引入新 CLI 框架。 [VERIFIED: local file `src/quantum_runtime/cli.py`] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `qiskit-aer` | repo 当前与 PyPI 最新均为 `0.17.2`。 [VERIFIED: local file `.planning/research/STACK.md`; VERIFIED: `python3 -m pip index versions qiskit-aer`] | 保持本地 baseline；Phase 09 不替换本地路径。 [VERIFIED: local file `pyproject.toml`] | 继续作为本地 deterministic baseline；不要把远端 backend list 逻辑耦合进本地模拟。 [VERIFIED: local file `.planning/PROJECT.md`] |
| `Pydantic` | repo 当前 `2.12.5`；PyPI 最新 `2.13.2`。 [VERIFIED: local file `.planning/research/STACK.md`; VERIFIED: `python3 -m pip index versions pydantic`] | 继续承载 schema-versioned payload、doctor report、backend list report。 [VERIFIED: local file `src/quantum_runtime/runtime/contracts.py`; local file `src/quantum_runtime/runtime/backend_list.py`; local file `src/quantum_runtime/runtime/doctor.py`] | 只做 additive schema 变更。 [VERIFIED: local file `.planning/PROJECT.md`] |
| `pytest` | repo 当前 `9.0.2`；PyPI 最新 `9.0.3`。 [VERIFIED: local file `.planning/research/STACK.md`; VERIFIED: `python3 -m pip index versions pytest`] | 现有 CLI/JSON/JSONL regression 测试框架。 [VERIFIED: local file `pyproject.toml`; local file `tests/test_cli_doctor.py`; local file `tests/test_cli_observability.py`] | 用于 Phase 09 的 fast regression lane。 [VERIFIED: local file `pyproject.toml`] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `qiskit-ibm-runtime` | 直接打 IBM Runtime REST API | 需要手写认证、instance 解析、backend 查询、error mapping，Phase 09 没有任何控制面收益。 [CITED: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service] [ASSUMED] |
| `.quantum/` 内自管 secrets | env 注入或 IBM 官方 saved account | IBM 官方已经给出 trusted/untrusted 两条路；FluxQ 自管 secrets 会直接破坏 workspace/packs 的信任边界。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/save-credentials] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/cloud-setup-untrusted] [VERIFIED: local file `src/quantum_runtime/workspace/manager.py`] |
| 新建 `qrun ibm backends` 发现命令 | 扩 `qrun backend list` | 现有 CLI 已经有 backend registry/list 流程和测试；分叉命令只会增加第二套 contract。 [VERIFIED: local file `src/quantum_runtime/cli.py`; local file `src/quantum_runtime/runtime/backend_list.py`; local file `tests/test_cli_backend_list.py`] [ASSUMED] |

**Installation:** 以下是本 phase 的推荐安装形状；仓库已经用 optional extra 管理 `classiq`，因此为 IBM 复用同一模式是最窄变更。 [VERIFIED: local file `pyproject.toml`] [ASSUMED]

```bash
uv add --optional ibm qiskit-ibm-runtime~=0.46
uv sync --extra dev --extra ibm
```

**Version verification:**  
- `qiskit-ibm-runtime` latest = `0.46.1`, upload date `2026-03-23`. [VERIFIED: PyPI https://pypi.org/project/qiskit-ibm-runtime/]  
- `qiskit` latest = `2.4.0`; repo 的当前研究基线仍是 `2.3.1`. [VERIFIED: `python3 -m pip index versions qiskit`; VERIFIED: local file `.planning/research/STACK.md`]  
- `qiskit-aer` latest = `0.17.2`. [VERIFIED: `python3 -m pip index versions qiskit-aer`]  

## Architecture Patterns

### Recommended Project Structure

```text
src/
├── quantum_runtime/
│   ├── cli.py                     # 扩 `qrun ibm configure` 与 `backend list` / `doctor` flags [VERIFIED: local file `src/quantum_runtime/cli.py`] [ASSUMED]
│   ├── runtime/
│   │   ├── backend_registry.py    # 新增 `ibm-runtime` descriptor [VERIFIED: local file `src/quantum_runtime/runtime/backend_registry.py`] [ASSUMED]
│   │   ├── backend_list.py        # 增量加入 IBM provider context + targets readiness [VERIFIED: local file `src/quantum_runtime/runtime/backend_list.py`] [ASSUMED]
│   │   ├── doctor.py              # 新增 IBM auth/profile/instance/backend checks [VERIFIED: local file `src/quantum_runtime/runtime/doctor.py`] [ASSUMED]
│   │   └── ibm_access.py          # 新的最小模块：profile 解析 + service factory [ASSUMED]
│   └── workspace/
│       └── manager.py             # `.quantum/qrun.toml` 继续只放 workspace/non-secret config [VERIFIED: local file `src/quantum_runtime/workspace/manager.py`]
└── tests/
    ├── test_cli_backend_list.py   # 扩 IBM readiness JSON cases [VERIFIED: local file `tests/test_cli_backend_list.py`]
    ├── test_cli_doctor.py         # 扩 IBM gate cases [VERIFIED: local file `tests/test_cli_doctor.py`]
    ├── test_cli_observability.py  # 扩 doctor JSONL IBM events [VERIFIED: local file `tests/test_cli_observability.py`]
    └── test_cli_ibm_config.py     # 新增 IBM profile config regression [ASSUMED]
```

### Pattern 1: External Secret, Internal Reference

**What:** `.quantum/qrun.toml` 只保存非 secret profile 引用，例如 `credential_mode`、`saved_account_name`、`token_env`、`instance`、`channel`；真正的 token 要么来自环境变量，要么来自 IBM 官方 saved-account 文件。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/save-credentials] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/cloud-setup-untrusted] [VERIFIED: local file `src/quantum_runtime/workspace/manager.py`] [ASSUMED]

**When to use:**  
- 本地受信任机器：允许显式 opt-in 到 IBM 官方 `save_account()`；FluxQ 只记住 saved account 名称与 instance。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/save-credentials] [ASSUMED]  
- CI / untrusted 环境：只允许 env-injected token；FluxQ 绝不把 token 写入 `.quantum/`。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/cloud-setup-untrusted] [ASSUMED]

**Example:** 下面示例是基于当前 workspace 形状和 IBM 官方 account 模式综合出来的建议 TOML，不是现有仓库已实现格式。 [VERIFIED: local file `src/quantum_runtime/workspace/manager.py`] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/initialize-account] [ASSUMED]

```toml
[workspace]
default_exports = ["qiskit", "qasm3"]
history_limit = 50

[remote.ibm]
enabled = true
channel = "ibm_quantum_platform"
credential_mode = "saved_account"
saved_account_name = "fluxq-dev"
instance = "crn:v1:bluemix:public:quantum-computing:us-east:a/..."
```

### Pattern 2: Extend `backend list`, Do Not Fork Discovery

**What:** 保留 `qrun backend list` 作为唯一 backend discovery 命令；对 JSON 输出做 additive 扩展：本地 backend descriptors 继续保留，另外增量加入 IBM provider context 和具体 target readiness 列表。 [VERIFIED: local file `src/quantum_runtime/cli.py`; local file `src/quantum_runtime/runtime/backend_list.py`] [ASSUMED]

**When to use:** 在任何 remote submit 之前，用同一命令回答两个问题：`SDK 装没装？` 与 `当前 profile / instance 下可见哪些 IBM 目标，它们现在是否 usable？` [VERIFIED: local file `.planning/ROADMAP.md`] [ASSUMED]

**Example:** 下列 JSON 结构是 Phase 09 推荐合同；现有 `BackendListReport` 只有 `backends`，因此这是 additive contract，不是破坏性替换。 [VERIFIED: local file `src/quantum_runtime/runtime/backend_list.py`] [ASSUMED]

```json
{
  "schema_version": "0.3.0",
  "backends": {
    "qiskit-local": { "available": true },
    "classiq": { "available": false }
  },
  "remote": {
    "provider": "ibm-runtime",
    "configured": true,
    "auth_source": "saved_account",
    "instance": "crn:v1:...",
    "targets": [
      {
        "name": "ibm_fez",
        "operational": true,
        "status_msg": "active",
        "pending_jobs": 3,
        "num_qubits": 156,
        "backend_version": "1.3.37",
        "readiness": {
          "status": "ready",
          "reason_codes": [],
          "next_actions": []
        }
      }
    ]
  }
}
```

### Pattern 3: Make `doctor` the Gate, Not `backend list`

**What:** `backend list` 负责枚举与解释；`doctor` 负责 gate。 这与当前代码已经存在的职责一致：`doctor` 生成结构化 issues / advisories / verdict / gate / next_actions，并且已有 `--ci` 与 JSONL 观测面。 [VERIFIED: local file `src/quantum_runtime/runtime/doctor.py`; local file `src/quantum_runtime/runtime/policy.py`; local file `src/quantum_runtime/runtime/observability.py`; local file `tests/test_cli_doctor.py`; local file `tests/test_cli_observability.py`]

**When to use:**  
- agent 想看候选目标：`backend list`。 [VERIFIED: local file `src/quantum_runtime/cli.py`]  
- CI 要判定 “这个 workspace/profile 现在是否 remote-ready”：`doctor --ci`。 [VERIFIED: local file `src/quantum_runtime/cli.py`; local file `src/quantum_runtime/runtime/exit_codes.py`]  

**Example:** 推荐新增 doctor 的 IBM 检查事件与 gate 理由码，例如 `ibm_profile_missing`、`ibm_token_env_missing`、`ibm_instance_unset`、`ibm_backend_not_found`、`ibm_backend_not_operational`。 这些是设计建议，不是现有仓库事实。 [VERIFIED: local file `src/quantum_runtime/runtime/observability.py`; local file `src/quantum_runtime/runtime/contracts.py`] [ASSUMED]

### Anti-Patterns to Avoid

- **把 API key 写入 `.quantum/qrun.toml`、`workspace.json`、`events.jsonl`、`trace/events.ndjson`、report 或 pack：** IBM 官方明确要求不要把 key 写进源码或共享文件，而 FluxQ 的 `.quantum/` 恰好就是可复制、可导出、可打包的 runtime 边界。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/cloud-setup-untrusted] [VERIFIED: local file `src/quantum_runtime/workspace/manager.py`; local file `.planning/PROJECT.md`]
- **在 FluxQ 内部用 `least_busy()` 做默认选择：** IBM SDK 提供 `least_busy()`，但 roadmap 已经要求显式 instance/backend selection；把它设成默认会破坏可复现性。 [CITED: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service] [VERIFIED: local file `.planning/STATE.md`; local file `.planning/REQUIREMENTS.md`]
- **用 `operational=True` 过滤掉所有非 operational backend 再展示：** 这样会把 “为什么 pinned backend 现在不可用” 的 readiness 证据直接隐藏掉。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/qpu-information] [ASSUMED]
- **在 Phase 09 创建 remote attempt / job record：** 这是 Phase 10 之后的工作，会把当前 phase 从 access/readiness 滑向 lifecycle design。 [VERIFIED: local file `.planning/ROADMAP.md`]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| IBM 凭证持久化 | 自定义 secret store 放进 `.quantum/` | 环境变量或 `QiskitRuntimeService.save_account()`；FluxQ 仅存引用。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/save-credentials] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/cloud-setup-untrusted] | IBM 官方已经给出 trusted / untrusted 两套路径；FluxQ 的 workspace 是版本化 artifact store，不是密钥库。 [VERIFIED: local file `src/quantum_runtime/workspace/manager.py`; local file `.planning/PROJECT.md`] |
| Backend inventory / target lookup | 手写 REST 封装与分页/过滤 | `QiskitRuntimeService.backends()`、`backend()`、`instances()`、`active_instance()`。 [CITED: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service] | 这些能力已经由官方 client 覆盖；Phase 09 只需要把结果投影到 FluxQ 合同。 [CITED: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service] |
| Queue heuristic / auto-target policy | 自定义 least-busy 或 region-plan 选择器 | 显式 instance + explicit backend pin + readiness display。 [VERIFIED: local file `.planning/STATE.md`; local file `.planning/REQUIREMENTS.md`] | FluxQ 的产品核心是可复现 control plane，不是 provider-side scheduler。 [VERIFIED: local file `.planning/PROJECT.md`] |
| Phase 09 compatibility proof | 远端 submit 预提交 transpile / ISA pipeline | 仅做 coarse readiness：auth、instance、backend visibility、status、pending jobs、qubit count。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/qpu-information] [ASSUMED] | 真正的 submit-time compatibility 和 lifecycle 证据属于后续 phase。 [VERIFIED: local file `.planning/ROADMAP.md`] |

**Key insight:** Phase 09 要证明的是 “FluxQ 能可信地知道自己是否可以进入 remote world”，不是 “FluxQ 已经实现 remote world”。 [VERIFIED: local file `.planning/ROADMAP.md`; local file `.planning/STATE.md`] [ASSUMED]

## Common Pitfalls

### Pitfall 1: Secret Leakage Into `.quantum/`

**What goes wrong:** token、bearer token、或原始 auth header 被写进 `qrun.toml`、workspace report、JSONL 事件或导出包。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/cloud-setup-untrusted] [VERIFIED: local file `src/quantum_runtime/workspace/manager.py`]

**Why it happens:** `.quantum/` 在当前架构里是 workspace truth 和 delivery artifact 的一部分，工程师容易把“可配置”误解成“可以存 secret”。 [VERIFIED: local file `.planning/PROJECT.md`; local file `src/quantum_runtime/workspace/manager.py`]

**How to avoid:** 只持久化 `credential_mode`、`saved_account_name`、`token_env`、`instance` 这类非 secret 引用；error payload 只返回稳定 reason code，不回显 token 值或原始 headers。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/cloud-setup-untrusted] [VERIFIED: local file `src/quantum_runtime/runtime/contracts.py`] [ASSUMED]

**Warning signs:** 测试里开始断言 token 出现在文件内容里，或 CLI `--json` 输出里出现 `Authorization` / `api_key` 字段。 [ASSUMED]

### Pitfall 2: 把 Saved Account 与 CI Env Mode 混成一个状态机

**What goes wrong:** 本地 saved account、显式 token、默认 account 和 CI env 注入被揉成一套“自动兜底”逻辑，最终 agent 不知道实际使用的是哪条认证路径。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/initialize-account] [CITED: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service]

**Why it happens:** `QiskitRuntimeService` 会在未显式给 token 时尝试从文件加载 account；如果又叠加 FluxQ 自己的 fallback，行为会变得不透明。 [CITED: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service]

**How to avoid:** 在 FluxQ profile 里显式区分 `credential_mode = "saved_account"` 与 `credential_mode = "env"`；resolved output 必须把 `auth_source` 明确写进 JSON。 [ASSUMED]

**Warning signs:** `doctor` 明明读到了 env token，却报告自己使用 default saved account，或同一个 workspace 在不同机器上解析出不同 active instance。 [ASSUMED]

### Pitfall 3: 用 `least_busy()` 代替 Readiness

**What goes wrong:** 系统直接返回一个“推荐 backend”，却不给出该决定背后的 operational/status/pending_jobs 证据。 [CITED: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service]

**Why it happens:** `least_busy()` API 很方便，但它服务于 provider-side convenience，不服务于 FluxQ 的可复现性。 [CITED: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service] [VERIFIED: local file `.planning/PROJECT.md`] [ASSUMED]

**How to avoid:** `backend list` 只展示候选 backend 与 readiness，不替用户做默认选择；backend pin 留给后续 phase 的 submit 命令。 [VERIFIED: local file `.planning/STATE.md`] [ASSUMED]

**Warning signs:** JSON 只有 `recommended_backend`，却没有 `status_msg`、`pending_jobs`、`instance`。 [ASSUMED]

### Pitfall 4: 把 Phase 09 扩成 Pre-Submit Compiler

**What goes wrong:** 为了回答“这个 backend 能不能用”，实现了 full transpile / ISA / primitive submit preflight，结果直接滑进 Phase 10 的范围。 [VERIFIED: local file `.planning/ROADMAP.md`] [ASSUMED]

**Why it happens:** “compatible backend” 这个词容易被理解成“已经证明可以提交并跑通”。 [ASSUMED]

**How to avoid:** Phase 09 只做 coarse readiness：`SDK available`、`auth resolved`、`instance explicit`、`backend visible`、`operational/status/pending_jobs`、`num_qubits`；ISA/transpile/primitive shape 一律 deferred。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/qpu-information] [ASSUMED]

**Warning signs:** 新代码开始引入 `SamplerV2` / `EstimatorV2.run()`、job ID、attempt record、remote artifacts。 [VERIFIED: local file `.planning/ROADMAP.md`] [ASSUMED]

## Code Examples

Verified patterns from official sources. [CITED: https://quantum.cloud.ibm.com/docs/en/guides/initialize-account] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/save-credentials] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/qpu-information]

### Env-Based Service Resolution For CI / Untrusted Execution

这个例子综合了 IBM 官方 “显式 token + instance 初始化” 与 “untrusted environment 不使用 saved account” 两个文档，示例代码为研究阶段合成示例。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/initialize-account] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/cloud-setup-untrusted]

```python
from __future__ import annotations

import os

from qiskit_ibm_runtime import QiskitRuntimeService


def build_ibm_service_from_env(*, token_env: str, instance: str) -> QiskitRuntimeService:
    token = os.environ[token_env]
    return QiskitRuntimeService(
        channel="ibm_quantum_platform",
        token=token,
        instance=instance,
    )
```

### Trusted-Local Save-Account Helper

这个例子对应 IBM 官方保存 credentials 的 trusted-machine 路径；FluxQ 可以把它包装进 `qrun ibm configure --save-account-from-env ...`，但该包装是推荐设计，不是现有实现。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/save-credentials] [ASSUMED]

```python
from __future__ import annotations

import os

from qiskit_ibm_runtime import QiskitRuntimeService


def save_named_ibm_account(*, token_env: str, account_name: str, instance: str) -> None:
    QiskitRuntimeService.save_account(
        channel="ibm_quantum_platform",
        token=os.environ[token_env],
        name=account_name,
        instance=instance,
        overwrite=True,
    )
```

### Backend Readiness Projection

这个例子基于 IBM 官方 backend 属性与 status 文档，把 provider 对象投影成 FluxQ 应该输出的最小 readiness 信息。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/qpu-information] [CITED: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service]

```python
from __future__ import annotations


def project_backend_readiness(backend) -> dict[str, object]:
    status = backend.status()
    return {
        "name": backend.name,
        "backend_version": backend.backend_version,
        "num_qubits": backend.num_qubits,
        "processor_type": backend.processor_type,
        "operational": bool(status.operational),
        "status_msg": status.status_msg,
        "pending_jobs": status.pending_jobs,
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 依赖 legacy channel 名称或模糊 channel 默认值 | 统一以 `ibm_quantum_platform` 作为推荐 channel；`ibm_cloud` 在当前 API 文档中已被标为 legacy alias。 [CITED: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service] | 以 2026-04-18 可见的最新 IBM API 文档为准。 [CITED: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service] | FluxQ 的 profile 与 JSON 输出应规范化成 `ibm_quantum_platform`。 [ASSUMED] |
| 仅知道“backend 名单” | 同时读取 `backend.status().status_msg` 与 `pending_jobs`，把 discovery 升级成 readiness。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/qpu-information] | 当前 IBM 文档已明确记录这些属性。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/qpu-information] | Phase 09 可以在不做 submit 的前提下给 agent 足够的 pre-submit 信号。 [ASSUMED] |
| 把自动 instance/backend 选择当成默认便利特性 | IBM 文档推荐显式提供 `instance` 以减少 API 调用，而 FluxQ 项目级约束也已经锁定 explicit selection。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/initialize-account] [CITED: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service] [VERIFIED: local file `.planning/STATE.md`] | 当前 IBM 文档与当前项目约束都指向这一点。 [CITED: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service] [VERIFIED: local file `.planning/STATE.md`] | Phase 09 不应默认暴露 `least_busy()` 驱动的 auto-pick。 [ASSUMED] |

**Deprecated/outdated:**

- 把 `ibm_cloud` 当成推荐 channel 名称已经过时；当前 API 文档明确把它标成 legacy option，并建议使用 `ibm_quantum_platform`。 [CITED: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service]
- 在不受信任环境里保存本地 credentials 是不推荐的；IBM 官方要求这种场景直接传 token，并在必要时轮换 API key。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/cloud-setup-untrusted]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Phase 09 最窄 CLI 入口应新增 `qrun ibm configure`，而不是先造通用 `qrun config` 框架。 | Summary / Architecture Patterns | 低到中；如果团队更想要通用配置框架，planner 需要把命名和模块边界改掉。 |
| A2 | `.quantum/qrun.toml` 应新增 `[remote.ibm]` 或等价非 secret profile 块。 | Architecture Patterns | 中；如果项目想把 remote config 放到别处，tests 与 migration 位置都会变化。 |
| A3 | `backend list` 应通过 additive `remote` block 暴露 IBM targets，而不是新开一条 discovery 命令。 | Architecture Patterns | 低；如果未来想保留 provider-specific 命令，contract 形状会不同。 |
| A4 | Phase 09 的 “compatible backend” 只做 coarse readiness，不做 full ISA/transpile compatibility。 | Don't Hand-Roll / Common Pitfalls | 中；如果产品要求 Phase 09 就做 submit-time proof，工作量会跨进 Phase 10。 |
| A5 | trusted-local `save_account` 可以由 FluxQ 可选封装，但 CI/untrusted mode 不应触发它。 | Summary / Code Examples | 低；即使不封装，也可以靠文档和 env mode 满足需求。 |

如果这个表为空，表示本研究中的所有关键结论都已在本 session 验证。当前不为空，planner 需要把这些设计推断视为 implementation choice，而不是已锁定用户决策。 [VERIFIED: this document]

## Resolved Questions (for planning)

1. **命令命名采用 provider-specific 入口：`qrun ibm configure`。**
   - 结论：Phase 09 先用 `qrun ibm configure`，不先抽象出通用 `qrun config` 框架。
   - 理由：当前 CLI 只有 `backend` 和 `baseline` 子命名空间；provider-specific 入口是最窄、最不易越界的增量。 [VERIFIED: local file `src/quantum_runtime/cli.py`] [ASSUMED]

2. **`instance` 默认以显式值持久化到 `qrun.toml`，而不是默认走 env ref。**
   - 结论：token 只走 env ref 或 IBM 官方 saved account；`instance` 默认写显式非 secret 值。仅当调用者明确要求时，后续设计才考虑 `instance_env`。
   - 理由：IBM 官方推荐显式提供 `instance`，而 `instance` 本身不是 secret；把它固定进 profile 更符合可复现 control plane。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/initialize-account] [CITED: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service] [ASSUMED]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `uv` | 项目安装、测试、optional extra 安装 | ✓ [VERIFIED: `uv --version`] | `0.11.1` [VERIFIED: `uv --version`] | — |
| `uv run python` | 项目受支持解释器 | ✓ [VERIFIED: `uv run python --version`] | `3.11.15` [VERIFIED: `uv run python --version`] | — |
| `pytest` | 自动化验证 | ✓ [VERIFIED: `uv run pytest --version`] | `9.0.2` [VERIFIED: `uv run pytest --version`] | — |
| `qiskit-ibm-runtime` in project env | IBM access / backend readiness implementation | ✗ [VERIFIED: `uv run python -c/importlib.util.find_spec`] | — | 先新增 optional `ibm` extra 并 `uv sync --extra ibm`。 [ASSUMED] |
| Live IBM token + instance | 手工 smoke / provider contract check | unknown [ASSUMED] | — | 自动化快路径全部用 mock/monkeypatch；live smoke 保持手工/受保护 CI lane。 [ASSUMED] |

**Missing dependencies with no fallback:**

- 项目虚拟环境里还没有 `qiskit-ibm-runtime`；任何 Phase 09 实现代码在合并前都需要补上 `ibm` extra 与安装步骤。 [VERIFIED: `uv run python -c/importlib.util.find_spec`] [ASSUMED]

**Missing dependencies with fallback:**

- live IBM credentials 不是 fast test lane 的前置条件；Phase 09 的主验证可以完全依赖 monkeypatch/mocks，live smoke 只作为补充。 [VERIFIED: local file `tests/test_cli_backend_list.py`; local file `tests/test_cli_doctor.py`; local file `tests/test_cli_observability.py`] [ASSUMED]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest 9.0.2` in project env. [VERIFIED: `uv run pytest --version`] |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]`. [VERIFIED: local file `pyproject.toml`] |
| Quick run command | `uv run pytest tests/test_cli_ibm_config.py tests/test_cli_backend_list.py tests/test_cli_doctor.py tests/test_cli_observability.py -x` [ASSUMED] |
| Full suite command | `uv run ruff check src tests && uv run mypy src && uv run pytest` [VERIFIED: local file `pyproject.toml`; local file `AGENTS.md`] [ASSUMED] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | `qrun ibm configure --json` 写入的 profile 只包含 non-secret 引用，且不会把 token 持久化进 `.quantum/`。 [ASSUMED] | unit / CLI | `uv run pytest tests/test_cli_ibm_config.py::test_qrun_ibm_config_json_writes_non_secret_profile_reference -x` [ASSUMED] | ❌ Wave 0 |
| AUTH-01 | env mode 在缺少 token env、缺少 instance、saved account 不存在时，`doctor --json --ci` 返回稳定 issues / reason_codes / gate。 [VERIFIED: local file `tests/test_cli_doctor.py`; local file `src/quantum_runtime/runtime/doctor.py`] [ASSUMED] | unit / CLI | `uv run pytest tests/test_cli_doctor.py -k ibm_profile -x` [ASSUMED] | ✅ |
| BACK-01 | `backend list --json` 返回 IBM provider context、target list，以及每个 target 的 readiness block。 [VERIFIED: local file `tests/test_cli_backend_list.py`; local file `src/quantum_runtime/runtime/backend_list.py`] [ASSUMED] | unit / CLI | `uv run pytest tests/test_cli_backend_list.py -k ibm -x` [ASSUMED] | ✅ |
| BACK-01 | `doctor --jsonl` 为 IBM 依赖、auth、instance、backend readiness 发出可消费事件，并在完成事件中投影 gate。 [VERIFIED: local file `tests/test_cli_observability.py`; local file `src/quantum_runtime/runtime/observability.py`] [ASSUMED] | unit / CLI | `uv run pytest tests/test_cli_observability.py -k ibm_doctor -x` [ASSUMED] | ✅ |
| AUTH-01 / BACK-01 | 在真实 IBM env 下，env-injected profile 能完成 auth check，且 `backend list --json` 能列出至少一个 target。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/initialize-account] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/qpu-information] | manual smoke | `QISKIT_IBM_TOKEN=... QISKIT_IBM_INSTANCE=... uv run qrun backend list --json` [ASSUMED] | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_cli_ibm_config.py tests/test_cli_backend_list.py tests/test_cli_doctor.py tests/test_cli_observability.py -x` [ASSUMED]
- **Per wave merge:** `uv run ruff check src tests && uv run mypy src && uv run pytest` [ASSUMED]
- **Phase gate:** fast suite + one protected manual smoke 都通过之后，才能进入 `/gsd-verify-work`。 [ASSUMED]

### Wave 0 Gaps

- [ ] `tests/test_cli_ibm_config.py` — 覆盖 profile 写入、非 secret persistence、env mode / saved-account mode 分支。 [ASSUMED]
- [ ] 扩 `tests/test_cli_backend_list.py` — 覆盖 IBM provider descriptor、target readiness JSON、degraded-but-readable 场景。 [ASSUMED]
- [ ] 扩 `tests/test_cli_doctor.py` — 覆盖 `qiskit-ibm-runtime` 缺失、token env 缺失、saved account 不存在、instance/backend 不可用。 [ASSUMED]
- [ ] 扩 `tests/test_cli_observability.py` — 覆盖 IBM doctor JSONL 事件类型和完成 payload。 [ASSUMED]
- [ ] 增加一条受保护 manual smoke recipe 到后续 `09-VALIDATION.md`。 [ASSUMED]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes [CITED: https://quantum.cloud.ibm.com/docs/en/guides/initialize-account] | token 只来自 env 或 IBM saved account；FluxQ 不持久化 token 本体。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/save-credentials] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/cloud-setup-untrusted] |
| V3 Session Management | no [VERIFIED: local file `.planning/ROADMAP.md`] | Phase 09 不实现 FluxQ 会话状态，也不实现 IBM session mode。 [VERIFIED: local file `.planning/ROADMAP.md`; CITED: https://quantum.cloud.ibm.com/docs/en/guides/execution-modes] |
| V4 Access Control | yes [CITED: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service] | 显式 instance 绑定、`instances()` / `backend()` 可见性检查、禁止默认 auto-selection。 [VERIFIED: local file `.planning/STATE.md`] [ASSUMED] |
| V5 Input Validation | yes [VERIFIED: local file `src/quantum_runtime/runtime/contracts.py`; local file `src/quantum_runtime/runtime/doctor.py`] | 校验 `credential_mode`、`saved_account_name`、env var 名、instance 和 backend 名；失败时返回稳定 reason code。 [ASSUMED] |
| V6 Cryptography | yes [CITED: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service] | 只依赖 IBM SDK / TLS 验证；不要手写加密或 token “保护” 文件格式。 [ASSUMED] |

### Known Threat Patterns for IBM access readiness

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key 泄漏到 workspace/report/events | Information Disclosure | 只持久化 env ref 或 saved-account name；tests 明确断言 `.quantum/` 中没有 token。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/cloud-setup-untrusted] [ASSUMED] |
| 隐式 instance 选择导致跨实例/跨计划漂移 | Elevation / Tampering | 默认要求显式 `instance`，并把 resolved `active_instance` 暴露给 JSON 输出。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/initialize-account] [CITED: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service] [ASSUMED] |
| 默认 `least_busy()` 导致 backend pin 不可复现 | Tampering | readiness 只展示，不自动选择；真正 pin 留给 submit phase。 [CITED: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service] [ASSUMED] |
| 非 operational backend 被静默过滤，agent 看不到原因 | Denial of Service | 枚举 real backends 后单独投影 `status_msg` / `pending_jobs` / readiness。 [CITED: https://quantum.cloud.ibm.com/docs/en/guides/qpu-information] [ASSUMED] |
| 错误 payload 回显敏感 auth 信息 | Information Disclosure | 只返回 reason code、next actions、gate；不要回显 token 值或 raw headers。 [VERIFIED: local file `src/quantum_runtime/runtime/contracts.py`] [ASSUMED] |

## Sources

### Primary (HIGH confidence)

- local file `.planning/PROJECT.md` - milestone scope、compatibility、observability、product constraints。  
- local file `.planning/ROADMAP.md` - Phase 09/10/11/12/13 边界与 success criteria。  
- local file `.planning/REQUIREMENTS.md` - AUTH-01 / BACK-01 与 out-of-scope 边界。  
- local file `.planning/STATE.md` - explicit instance/backend、secrets outside `.quantum` 等项目级近期决策。  
- local file `src/quantum_runtime/cli.py` - 现有命令形状、JSON/JSONL 模式、`backend list` 与 `doctor` 接缝。  
- local file `src/quantum_runtime/runtime/backend_registry.py` - backend capability registry 现状。  
- local file `src/quantum_runtime/runtime/backend_list.py` - backend list JSON 合同现状。  
- local file `src/quantum_runtime/runtime/doctor.py` - 现有 dependency/CI gate / persistence 语义。  
- local file `src/quantum_runtime/runtime/contracts.py` - schema-versioned error payload contract。  
- local file `src/quantum_runtime/runtime/observability.py` - JSONL event envelope。  
- local file `src/quantum_runtime/workspace/manager.py` - `.quantum/qrun.toml` 与 workspace seed 现状。  
- local file `tests/test_cli_backend_list.py` - backend list regression 模式。  
- local file `tests/test_cli_doctor.py` - doctor JSON / CI regression 模式。  
- local file `tests/test_cli_observability.py` - doctor/CLI JSONL regression 模式。  
- IBM docs: Initialize your Qiskit Runtime service account - https://quantum.cloud.ibm.com/docs/en/guides/initialize-account  
- IBM docs: Save your login credentials - https://quantum.cloud.ibm.com/docs/en/guides/save-credentials  
- IBM docs: Initialize the service in an untrusted environment - https://quantum.cloud.ibm.com/docs/en/guides/cloud-setup-untrusted  
- IBM docs: QiskitRuntimeService API - https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service  
- IBM docs: View backend details - https://quantum.cloud.ibm.com/docs/en/guides/qpu-information  
- IBM docs: Introduction to execution modes - https://quantum.cloud.ibm.com/docs/en/guides/execution-modes  

### Secondary (MEDIUM confidence)

- IBM docs: Retrieve and save job results - https://quantum.cloud.ibm.com/docs/en/guides/save-jobs  
- IBM docs: Maximum execution time for Qiskit Runtime workloads - https://quantum.cloud.ibm.com/docs/en/guides/max-execution-time  
- PyPI: `qiskit-ibm-runtime` release history - https://pypi.org/project/qiskit-ibm-runtime/  
- local env probes: `uv --version`, `uv run python --version`, `uv run pytest --version`, `python3 -m pip index versions ...`  

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**  
- Standard stack: HIGH - IBM 官方 API 文档 + PyPI 当前版本 + 本地项目依赖面都一致。  
- Architecture: MEDIUM-HIGH - 现有 CLI/runtime seams 已验证，但 `qrun ibm configure` 与 `remote` JSON block 属于设计推断。  
- Pitfalls: HIGH - IBM 官方 auth 警告与 FluxQ 现有 workspace / contract 形状高度一致。  

**Research date:** 2026-04-18  
**Valid until:** 2026-04-25
