# Phase 06: Runtime Adoption Surface - Research

**Researched:** 2026-04-15
**Domain:** 采用面文档、集成示例、发布说明、版本契约与锁定这些对外合同的测试面
**Confidence:** HIGH

<user_constraints>
## User Constraints

本阶段没有单独的 `06-CONTEXT.md`，所以约束来自用户提示、路线图、需求文档和已签入的项目约束。 [VERIFIED: gsd init phase-op 06][VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/REQUIREMENTS.md][VERIFIED: AGENTS.md]

### Locked Decisions

- 只研究 runtime/control-plane adoption surface：主文档、示例、release/versioning 说明、integration example，以及锁定这些合同的测试。 [VERIFIED: user prompt][VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/REQUIREMENTS.md]
- 保持 FluxQ 的定位为 `agent-first quantum runtime CLI`，并保持“prompt 是 ingress，`QSpec` 与 revisioned artifacts 是 durable runtime truth”的叙事。 [VERIFIED: AGENTS.md][VERIFIED: .planning/PROJECT.md][VERIFIED: README.md][VERIFIED: ARCHITECTURE.md]
- 不把本阶段扩展成 remote-submit、provider breadth、DSL、或 chat-assistant 方向。 [VERIFIED: .planning/PROJECT.md][VERIFIED: .planning/REQUIREMENTS.md][VERIFIED: docs/product-strategy.md]

### Claude's Discretion

- 推荐 Phase 06 的实际 plan 拆分方式。 [VERIFIED: user prompt][VERIFIED: .planning/ROADMAP.md]
- 推荐应优先扩展哪些现有 surface，哪些缺口值得新增文档或示例文件。 [VERIFIED: user prompt]

### Deferred Ideas (OUT OF SCOPE)

- Remote execution、optimizer platform 扩展、provider matrix 扩展、general chat assistant UX 仍然延期。 [VERIFIED: .planning/REQUIREMENTS.md][VERIFIED: docs/product-strategy.md]
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SURF-01 | Public docs and examples consistently describe FluxQ as an agent-first quantum runtime CLI. [VERIFIED: .planning/REQUIREMENTS.md] | 现有 README、ARCHITECTURE、product strategy、CHANGELOG、release notes 大体已 runtime-first，但 `pyproject.toml` 仍带 `Code Generators` classifier，且 release/adoption tests 还没有锁住全部 public surfaces。 [VERIFIED: README.md][VERIFIED: ARCHITECTURE.md][VERIFIED: docs/product-strategy.md][VERIFIED: CHANGELOG.md][VERIFIED: docs/releases/v0.3.1.md][VERIFIED: pyproject.toml][VERIFIED: tests/test_release_docs.py] |
| SURF-02 | Repository includes concrete CI or agent integration examples that show end-to-end runtime workflows. [VERIFIED: .planning/REQUIREMENTS.md] | 代码和测试已经证明 `prompt/resolve/plan -> exec -> compare policy -> doctor --ci -> pack-inspect -> pack-import` 这些 surface 分别存在，但 README/release/aionrs/docs/case study 还没有一条被测试锁定的端到端 adoption path。 [VERIFIED: tests/test_cli_ingress_resolution.py][VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_cli_doctor.py][VERIFIED: tests/test_cli_runtime_gap.py][VERIFIED: tests/test_cli_pack_import.py][VERIFIED: README.md][VERIFIED: docs/aionrs-integration.md][VERIFIED: docs/releases/v0.3.1.md][VERIFIED: docs/fluxq-qaoa-maxcut-case-study.md] |
| SURF-03 | Release/versioning artifacts clearly describe what runtime contracts are stable and what is still evolving. [VERIFIED: .planning/REQUIREMENTS.md] | `docs/versioning.md` 目前只有 release-line 摘要和 4 条 compatibility rules，`docs/releases/v0.3.1.md` 与 `CHANGELOG.md` 也没有 stable/evolving/optional matrix；Phase 06 应补齐这一层并用 tests 锁定。 [VERIFIED: docs/versioning.md][VERIFIED: docs/releases/v0.3.1.md][VERIFIED: CHANGELOG.md][VERIFIED: tests/test_release_docs.py] |
</phase_requirements>

## Summary

FluxQ 的 public runtime narrative 已经基本完成“从 generator demo 到 runtime control plane”的转向：README、ARCHITECTURE、product strategy、CHANGELOG、release notes 都明确强调 agent-first、prompt 只是 ingress、`QSpec` 是 truth layer、以及 revisioned artifacts / machine-readable control plane。 [VERIFIED: README.md][VERIFIED: ARCHITECTURE.md][VERIFIED: docs/product-strategy.md][VERIFIED: CHANGELOG.md][VERIFIED: docs/releases/v0.3.1.md]

真正的 Phase 06 缺口不是重新发明定位，而是把已经存在的 runtime surfaces 组织成一条 adoption contract，并把这条合同锁进测试。 当前 README 的 `First Run` 到 `qrun pack` 为止，没有继续展示 `pack-inspect` / `pack-import` 或显式的 policy gate；`docs/aionrs-integration.md` 和 `integrations/aionrs/CLAUDE.md.example` 基本还是 `plan/exec/show/doctor/bench` 或直接 `exec -> read report` 的部分流程；`docs/fluxq-qaoa-maxcut-case-study.md` 是目前最强的 runtime-first case study，但 README 没有把它列入 docs 索引，现有 release-doc tests 也没有覆盖它。 [VERIFIED: README.md][VERIFIED: docs/aionrs-integration.md][VERIFIED: integrations/aionrs/CLAUDE.md.example][VERIFIED: docs/fluxq-qaoa-maxcut-case-study.md][VERIFIED: tests/test_release_docs.py][VERIFIED: tests/test_aionrs_assets.py]

最明显的 public contradiction 在 `docs/releases/v0.3.1.md`：`What To Try First` 把一条 QAOA `prompt` 命令和一条 GHZ `resolve/exec` 链路混在同一个“first run”里，而且在没有 `baseline set` 的前提下调用 `qrun compare --baseline --json`。 这会把 release notes 变成不可直接照抄的 adoption surface。 另外，`pyproject.toml` 的 description 已经是 runtime-first，但 classifier 仍保留 `Topic :: Software Development :: Code Generators`，这会把 PyPI/package metadata 的读者拉回“生成器”视角。 [VERIFIED: docs/releases/v0.3.1.md][VERIFIED: pyproject.toml]

**Primary recommendation:** 把 Phase 06 拆成三个 plan：先统一顶层消息与 quickstart，再补一条被测试锁定的 agent/CI/handoff workflow，最后补 stable/evolving runtime contract 说明并同步 release/versioning/package metadata。

### Concrete Repo Surfaces

- `README.md`：继续作为最高优先级 quickstart 与 decision-loop surface，但要补 policy gate 和 handoff。 [VERIFIED: README.md]
- `docs/releases/v0.3.1.md`：当前有最明显的命令序列矛盾，需要先修正。 [VERIFIED: docs/releases/v0.3.1.md]
- `docs/versioning.md`：需要从“版本摘要”升级成“稳定性/演进性消费说明”。 [VERIFIED: docs/versioning.md]
- `docs/aionrs-integration.md`、`integrations/aionrs/CLAUDE.md.example`、`integrations/aionrs/hooks.example.toml`：需要从部分 runtime 用法升级为明确的 host adoption contract。 [VERIFIED: docs/aionrs-integration.md][VERIFIED: integrations/aionrs/CLAUDE.md.example][VERIFIED: integrations/aionrs/hooks.example.toml]
- `docs/fluxq-qaoa-maxcut-case-study.md` 与 `examples/*.md`：可以复用为可信的 end-to-end case study，而不是重新发明 demo input。 [VERIFIED: docs/fluxq-qaoa-maxcut-case-study.md][VERIFIED: examples/intent-ghz.md][VERIFIED: examples/intent-qaoa-maxcut.md][VERIFIED: examples/intent-qaoa-maxcut-sweep.md]
- `tests/test_release_docs.py`、`tests/test_aionrs_assets.py`、`tests/test_packaging_release.py`：当前是 adoption contract 的锁，但覆盖面仍不够。 [VERIFIED: tests/test_release_docs.py][VERIFIED: tests/test_aionrs_assets.py][VERIFIED: tests/test_packaging_release.py]

### Practical Phase Split

1. `06-01` 统一顶层 product messaging 与 quickstart：修 README、release notes、docs index、必要时补 package metadata 对齐。 这一组对应 SURF-01 的主冲突点。 [VERIFIED: README.md][VERIFIED: docs/releases/v0.3.1.md][VERIFIED: pyproject.toml]
2. `06-02` 建立一条被测试锁定的 adoption workflow：至少覆盖 ingress、execution、policy evaluation、delivery handoff，并把这条链路贯穿 README、aionrs integration、case study 或新增 CI doc。 这一组对应 SURF-02。 [VERIFIED: tests/test_cli_ingress_resolution.py][VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_cli_doctor.py][VERIFIED: tests/test_cli_pack_import.py]
3. `06-03` 写清 stable/evolving/optional runtime contracts，并更新 release/versioning/tests。 这一组对应 SURF-03。 [VERIFIED: docs/versioning.md][VERIFIED: docs/releases/v0.3.1.md][VERIFIED: CHANGELOG.md][VERIFIED: tests/test_release_docs.py]

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Repository Markdown docs (`README.md`, `docs/*.md`, release notes) | N/A | 作为 public adoption contract 的主要承载面。 [VERIFIED: README.md][VERIFIED: docs/product-strategy.md][VERIFIED: docs/versioning.md][VERIFIED: docs/releases/v0.3.1.md] | 这些 surface 已经被 README 索引和 release-doc tests 当作公开合同使用。 [VERIFIED: README.md][VERIFIED: tests/test_release_docs.py] |
| Example intent files (`examples/*.md`) | 当前仓库 fixture | 保证示例基于真实可执行 input，而不是再造 demo-only 输入。 [VERIFIED: examples/intent-ghz.md][VERIFIED: examples/intent-qaoa-maxcut.md][VERIFIED: examples/intent-qaoa-maxcut-sweep.md] | 现有 CLI 和 runtime tests 已经反复复用这些示例。 [VERIFIED: tests/test_cli_control_plane.py][VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_cli_doctor.py] |
| `pytest` | local env `9.0.2`; dependency floor `>=8.0` | 锁定文档文本、命令序列、集成示例与 package metadata。 [VERIFIED: ./.venv/bin/python -m pytest --version][VERIFIED: pyproject.toml] | 当前 release/adoption tests 全部建立在 pytest 上，并且本地基线为绿。 [VERIFIED: tests/test_release_docs.py][VERIFIED: tests/test_aionrs_assets.py][VERIFIED: local pytest tests/test_release_docs.py tests/test_open_source_release.py tests/test_packaging_release.py -q][VERIFIED: local pytest tests/test_aionrs_assets.py -q] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `uv` | `0.11.1` | 与 README / dev flow / 本地验证路径保持一致。 [VERIFIED: uv --version][VERIFIED: README.md] | 本地创建/恢复 `.venv`、执行 dev 安装和 phase 验证时使用。 [VERIFIED: README.md] |
| repo `.venv` Python | `3.11.15` | 与项目 `requires-python >=3.11,<3.12` 对齐。 [VERIFIED: ./.venv/bin/python --version][VERIFIED: pyproject.toml] | 运行本阶段测试、build 和任何本地验证命令时使用。 [VERIFIED: pyproject.toml] |
| `build` | `1.3.0` local env; dependency floor `>=1.2` | 验证 release/packaging metadata 仍可构建。 [VERIFIED: ./.venv/bin/python -m build --version][VERIFIED: pyproject.toml][VERIFIED: .github/workflows/ci.yml] | 调整 `pyproject.toml`、release metadata、README install contract 时使用。 [VERIFIED: tests/test_packaging_release.py][VERIFIED: .github/workflows/ci.yml] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| 继续沿用 repo-native Markdown docs + pytest string assertions。 [VERIFIED: README.md][VERIFIED: tests/test_release_docs.py] | 新增 MkDocs/Docusaurus/docsite tooling。 | 这个阶段的问题是 adoption contract 不完整，不是文档托管技术不够；新增 docsite 只会扩大 surface 而不会自动修复消息一致性。 [VERIFIED: tests/test_release_docs.py][VERIFIED: docs/releases/v0.3.1.md] |
| 继续使用 file + shell 的 host integration 示例。 [VERIFIED: docs/aionrs-integration.md][VERIFIED: integrations/aionrs/CLAUDE.md.example] | 为 aionrs 再做一个自定义工具或协议层。 | 仓库现有集成文档已经明确要求不要这么做；Phase 06 应强化这个约束而不是反着扩 scope。 [VERIFIED: docs/aionrs-integration.md][VERIFIED: tests/test_aionrs_assets.py] |
| 扩展现有 focused doc-contract tests。 [VERIFIED: tests/test_release_docs.py][VERIFIED: tests/test_aionrs_assets.py] | 引入大体量 snapshot/golden docs 测试。 | 本阶段更需要锁“关键短语、关键命令顺序、关键 contract blocks”，而不是锁整页文本。 [VERIFIED: tests/test_release_docs.py][VERIFIED: tests/test_aionrs_assets.py] |

**Installation:**

```bash
uv pip install -e '.[dev]'
```

**Version verification:** 本地环境已验证 `uv 0.11.1`、repo `.venv` Python `3.11.15`、`pytest 9.0.2`、`build 1.3.0` 可用；系统 `python3` 是 `3.13.2`，不应当作为本阶段验证解释器，因为它不满足仓库的 `<3.12` 约束。 [VERIFIED: uv --version][VERIFIED: ./.venv/bin/python --version][VERIFIED: ./.venv/bin/python -m pytest --version][VERIFIED: ./.venv/bin/python -m build --version][VERIFIED: python3 --version][VERIFIED: pyproject.toml]

## Architecture Patterns

### Recommended Project Structure

- `README.md`：顶层定位、quickstart、decision loop、docs index。 [VERIFIED: README.md]
- `docs/product-strategy.md`：category / ICP / non-goals / anti-overclaim。 [VERIFIED: docs/product-strategy.md]
- `docs/versioning.md` 与 `docs/releases/*.md`：稳定性规则、release-line 变化说明、adopter consumption guidance。 [VERIFIED: docs/versioning.md][VERIFIED: docs/releases/v0.3.1.md]
- `docs/aionrs-integration.md` 与 `integrations/aionrs/*.example`：host integration contract。 [VERIFIED: docs/aionrs-integration.md][VERIFIED: integrations/aionrs/CLAUDE.md.example][VERIFIED: integrations/aionrs/hooks.example.toml]
- `docs/fluxq-qaoa-maxcut-case-study.md` 与 `examples/*.md`：用真实 intent fixture 讲 end-to-end workflow。 [VERIFIED: docs/fluxq-qaoa-maxcut-case-study.md][VERIFIED: examples/intent-ghz.md][VERIFIED: examples/intent-qaoa-maxcut.md][VERIFIED: examples/intent-qaoa-maxcut-sweep.md]
- `tests/test_release_docs.py`、`tests/test_aionrs_assets.py`、`tests/test_open_source_release.py`、`tests/test_packaging_release.py`：public adoption contract 的回归锁。 [VERIFIED: tests/test_release_docs.py][VERIFIED: tests/test_aionrs_assets.py][VERIFIED: tests/test_open_source_release.py][VERIFIED: tests/test_packaging_release.py]

### Pattern 1: One Canonical Decision Loop

**What:** 所有 public quickstarts 都应该复用同一条 runtime decision loop，而不是每个文档都拼一条不同的命令串。 现有能力已经分散验证了 ingress、execution、policy、handoff 各段，但文档还没把它们串成一个统一 adoption path。 [VERIFIED: tests/test_cli_ingress_resolution.py][VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_cli_doctor.py][VERIFIED: tests/test_cli_runtime_gap.py][VERIFIED: tests/test_cli_pack_import.py]

**When to use:** README first-run、release notes、host integration doc、case study、未来 CI doc 都应该复用这条主线。

**Example:**

```bash
# Recommended composed flow from already-verified command surfaces.
qrun prompt "Build a 4-qubit GHZ circuit and measure all qubits." --json
qrun resolve --workspace .quantum --intent-file examples/intent-ghz.md --json
qrun init --workspace .quantum --json
qrun plan --workspace .quantum --intent-file examples/intent-ghz.md --json
qrun exec --workspace .quantum --intent-file examples/intent-ghz.md --jsonl
qrun baseline set --workspace .quantum --revision rev_000001 --json
qrun compare --workspace .quantum --baseline --fail-on subject_drift --json
qrun doctor --workspace .quantum --json --ci
qrun pack --workspace .quantum --revision rev_000001 --json
qrun pack-inspect --pack-root .quantum/packs/rev_000001 --json
qrun pack-import --pack-root .quantum/packs/rev_000001 --workspace downstream/.quantum --json
```

Source capability coverage: `prompt/resolve/plan` are verified in `tests/test_cli_ingress_resolution.py`; policy compare in `tests/test_cli_compare.py`; `doctor --ci` in `tests/test_cli_doctor.py`; `pack-inspect` in `tests/test_cli_runtime_gap.py`; `pack-import` in `tests/test_cli_pack_import.py`. [VERIFIED: tests/test_cli_ingress_resolution.py][VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_cli_doctor.py][VERIFIED: tests/test_cli_runtime_gap.py][VERIFIED: tests/test_cli_pack_import.py]

### Pattern 2: File + Shell Host Integration

**What:** host integration doc 继续坚持 file + shell 的 runtime contract，而不是 host-specific plugin protocol。 [VERIFIED: ARCHITECTURE.md][VERIFIED: docs/aionrs-integration.md]

**When to use:** `aionrs`、CI shell examples、未来 agent host docs 都适用。

**Example:**

```bash
# Source: docs/aionrs-integration.md + existing verified command surfaces.
qrun init --workspace .quantum --json
qrun plan --workspace .quantum --intent-file .quantum/intents/latest.md --json
qrun exec --workspace .quantum --intent-file .quantum/intents/latest.md --jsonl
qrun show --workspace .quantum --json
qrun compare --workspace .quantum --baseline --fail-on subject_drift --json
qrun doctor --workspace .quantum --json --ci
qrun pack --workspace .quantum --revision rev_000001 --json
```

目前文档只写到了 `plan/exec/show/doctor/bench`，Phase 06 应把 policy/handoff 补上。 [VERIFIED: docs/aionrs-integration.md][VERIFIED: tests/test_aionrs_assets.py]

### Pattern 3: Stability Matrix, Not Loose Prose

**What:** `docs/versioning.md` 与 release notes 应采用 “stable / evolving / optional” 的明确矩阵，而不是只有 release-line 摘要。 当前已经存在的 compatibility rules 是好基础，但还不够支持 adopter 安全消费。 [VERIFIED: docs/versioning.md]

**When to use:** `docs/versioning.md`、`docs/releases/v0.3.1.md`、README 的 compatibility / release references。

**Example:**

```markdown
Stable:
- `QSpec.version` stays explicit in serialized specs.
- CLI/result/artifact `schema_version` is separate from `QSpec.version`.
- Released CLI JSON fields may add keys, but should not rename/remove released keys.
- Workspace history for generated specs/plans/reports is append-only.

Evolving:
- The recommended end-to-end workflow narrative and supporting examples.
- Optional backend breadth and capability-dependent guidance.

Optional / capability-dependent:
- `classiq` remains optional.
```

Current source rules for the stable portion already exist in `docs/versioning.md`, `pyproject.toml`, and CI/classiq workflows. [VERIFIED: docs/versioning.md][VERIFIED: pyproject.toml][VERIFIED: .github/workflows/ci.yml][VERIFIED: .github/workflows/classiq.yml]

### Anti-Patterns to Avoid

- **Broken linear demos:** 不要再发布“未 `baseline set` 就 `compare --baseline`”或把不同 workload 混成一条 first-run 的命令链。 当前 `docs/releases/v0.3.1.md` 就有这个问题。 [VERIFIED: docs/releases/v0.3.1.md]
- **Exec-only host examples:** 不要把集成文档收缩成“写 intent -> exec -> 读 report”，这样会把 FluxQ 重新叙述成生成器而不是 control plane。 [VERIFIED: integrations/aionrs/CLAUDE.md.example][VERIFIED: docs/aionrs-integration.md]
- **Untested public surfaces:** 不要把 case study、integration examples、stability notes 放在测试盲区。 当前 release docs tests 和 aionrs tests 都没有锁住完整 adoption flow。 [VERIFIED: tests/test_release_docs.py][VERIFIED: tests/test_aionrs_assets.py]
- **Metadata drift:** 不要让 README/runtime docs 讲 runtime，而 package classifier 继续强调 `Code Generators`。 [VERIFIED: README.md][VERIFIED: pyproject.toml]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Public adoption docs | 新 docsite / marketing microsite | 继续用 repo 内 Markdown docs + README 索引 + pytest contract tests | 现有问题是消息与 workflow contract 缺口，不是文档承载工具缺失。 [VERIFIED: README.md][VERIFIED: tests/test_release_docs.py] |
| Agent host integration | 自定义 aionrs 工具或专用协议 | 文件 + shell 的 runtime workflow | 现有 integration docs 和 architecture 已明确把 file I/O + shell commands 当成 host contract。 [VERIFIED: ARCHITECTURE.md][VERIFIED: docs/aionrs-integration.md][VERIFIED: tests/test_aionrs_assets.py] |
| Demo input | 新造一批 marketing-only inputs | 复用 `examples/intent-ghz.md`、`intent-qaoa-maxcut.md`、`intent-qaoa-maxcut-sweep.md` | 这些 inputs 已经被 CLI/runtime tests 证明可执行，也能支撑不同 adoption story。 [VERIFIED: examples/intent-ghz.md][VERIFIED: examples/intent-qaoa-maxcut.md][VERIFIED: examples/intent-qaoa-maxcut-sweep.md][VERIFIED: tests/test_cli_control_plane.py][VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_cli_doctor.py] |
| Docs regression locking | 整页 snapshot / screenshot tests | focused string-and-sequence assertions | 本阶段需要锁关键词、关键命令、关键 contract block，而不是锁整页排版。 [VERIFIED: tests/test_release_docs.py][VERIFIED: tests/test_aionrs_assets.py] |

**Key insight:** Phase 06 应复用“已经被 runtime tests 证明存在的命令表面”，而不是再造新功能表面。 [VERIFIED: tests/test_cli_ingress_resolution.py][VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_cli_doctor.py][VERIFIED: tests/test_cli_runtime_gap.py][VERIFIED: tests/test_cli_pack_import.py]

## Common Pitfalls

### Pitfall 1: Release Notes Lock In A Broken Workflow

**What goes wrong:** release notes 成为 public quickstart，但命令顺序本身不可直接照抄。 [VERIFIED: docs/releases/v0.3.1.md]
**Why it happens:** 当前 `What To Try First` 混用了 QAOA prompt 与 GHZ resolve/exec，并在没有 `baseline set` 的情况下执行 `compare --baseline`。 [VERIFIED: docs/releases/v0.3.1.md]
**How to avoid:** 让 release notes 只复用一条单 workload、单 decision loop 的命令链，并在 tests 中显式要求 `baseline set` 出现在 `compare --baseline` 之前。 [VERIFIED: docs/releases/v0.3.1.md][VERIFIED: tests/test_release_docs.py]
**Warning signs:** 文档里同一段 “first run” 同时出现多个 workload 文本，或者出现 `compare --baseline` 但没有 `baseline set`。 [VERIFIED: docs/releases/v0.3.1.md]

### Pitfall 2: Integration Example Regresses To “Run The Generator”

**What goes wrong:** 集成示例只展示写 intent、跑 `exec`、读 report，从而弱化 `prompt/resolve/plan/status/show/compare/pack` 这些 control-plane surfaces。 [VERIFIED: docs/aionrs-integration.md][VERIFIED: integrations/aionrs/CLAUDE.md.example]
**Why it happens:** 当前 aionrs assets 的 tests 只锁了 exec/doctor/bench 的存在，没有锁 policy 或 delivery handoff。 [VERIFIED: tests/test_aionrs_assets.py]
**How to avoid:** 扩展 aionrs doc/example 与其 tests，使其至少覆盖 `plan`、`show`、一个 policy surface、以及一个 handoff surface。 [VERIFIED: docs/aionrs-integration.md][VERIFIED: tests/test_aionrs_assets.py]
**Warning signs:** 文档里出现 “generated code” 的人工检查路径，但没有对应的 revision/baseline/gate/handoff 说明。 [VERIFIED: integrations/aionrs/CLAUDE.md.example]

### Pitfall 3: Strong Case Study Lives Outside The Public Contract

**What goes wrong:** 仓库已经有一个 runtime-first 的强案例，但顶层 docs 不导向它，tests 也不锁它，所以 public readers 很可能根本看不到。 [VERIFIED: docs/fluxq-qaoa-maxcut-case-study.md][VERIFIED: README.md][VERIFIED: tests/test_release_docs.py]
**Why it happens:** README 的 docs 列表没有 case study，现有 release-doc tests 也没有覆盖该文件。 [VERIFIED: README.md][VERIFIED: tests/test_release_docs.py]
**How to avoid:** 把 case study 纳入 README docs index，并决定是直接锁这份文档，还是新增一个更短的 English/CI-facing sibling doc。 [VERIFIED: README.md][VERIFIED: docs/fluxq-qaoa-maxcut-case-study.md]
**Warning signs:** public docs 只有概念说明和 quickstart，没有一个展示 baseline/compare/benchmark/doctor/export/handoff 串联价值的长案例。 [VERIFIED: README.md][VERIFIED: docs/fluxq-qaoa-maxcut-case-study.md]

### Pitfall 4: Tests Lock Slogans, Not Adoption Semantics

**What goes wrong:** 文档测试是绿的，但 adoption contract 依然不完整。 [VERIFIED: local pytest tests/test_release_docs.py tests/test_open_source_release.py tests/test_packaging_release.py -q][VERIFIED: local pytest tests/test_aionrs_assets.py -q]
**Why it happens:** 当前 release tests 主要锁词句和单条命令存在，不锁 workflow coherence、policy coverage、handoff coverage、或 stability matrix。 [VERIFIED: tests/test_release_docs.py][VERIFIED: tests/test_aionrs_assets.py]
**How to avoid:** 新增或扩展测试，要求一条完整 flow 覆盖 ingress、execution、policy evaluation、delivery handoff、stable/evolving notes。 [VERIFIED: tests/test_release_docs.py][VERIFIED: tests/test_aionrs_assets.py]
**Warning signs:** README / release docs 中已经有 `pack` 或 `compare` 命令，但 tests 没有同时要求 `pack-inspect` / `pack-import` / `baseline set` / `--ci`。 [VERIFIED: README.md][VERIFIED: docs/releases/v0.3.1.md][VERIFIED: tests/test_release_docs.py]

## Code Examples

Verified patterns from repository sources and tests:

### Runtime Adoption Loop

```bash
# Source capabilities: README.md + tests/test_cli_ingress_resolution.py
# + tests/test_cli_compare.py + tests/test_cli_doctor.py
# + tests/test_cli_runtime_gap.py + tests/test_cli_pack_import.py
qrun prompt "Build a 4-qubit GHZ circuit and measure all qubits." --json
qrun resolve --workspace .quantum --intent-file examples/intent-ghz.md --json
qrun init --workspace .quantum --json
qrun plan --workspace .quantum --intent-file examples/intent-ghz.md --json
qrun exec --workspace .quantum --intent-file examples/intent-ghz.md --jsonl
qrun baseline set --workspace .quantum --revision rev_000001 --json
qrun compare --workspace .quantum --baseline --fail-on subject_drift --json
qrun doctor --workspace .quantum --json --ci
qrun pack --workspace .quantum --revision rev_000001 --json
qrun pack-inspect --pack-root .quantum/packs/rev_000001 --json
qrun pack-import --pack-root .quantum/packs/rev_000001 --workspace downstream/.quantum --json
```

Command availability and machine-facing behavior are already covered by the referenced tests. [VERIFIED: tests/test_cli_ingress_resolution.py][VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_cli_doctor.py][VERIFIED: tests/test_cli_runtime_gap.py][VERIFIED: tests/test_cli_pack_import.py]

### Host Integration Loop

```bash
# Source: docs/aionrs-integration.md + existing runtime command tests
qrun init --workspace .quantum --json
qrun plan --workspace .quantum --intent-file .quantum/intents/latest.md --json
qrun exec --workspace .quantum --intent-file .quantum/intents/latest.md --jsonl
qrun show --workspace .quantum --json
qrun doctor --workspace .quantum --json --ci
```

The existing doc already proves the file + shell shape; Phase 06 should extend it with policy and handoff, not replace the integration model. [VERIFIED: docs/aionrs-integration.md][VERIFIED: tests/test_aionrs_assets.py]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| “agent-facing workflow CLI” / codegen-adjacent public framing。 [VERIFIED: CHANGELOG.md] | “runtime control plane” with machine-readable contracts, immutable manifests, and explicit read-mostly control-plane commands。 [VERIFIED: CHANGELOG.md][VERIFIED: docs/versioning.md] | `0.3.0`。 [VERIFIED: CHANGELOG.md][VERIFIED: docs/versioning.md] | Phase 06 不需要重新造定位，只需要把 adoption docs 追上这个已落地的 runtime framing。 |
| one-shot JSON result emphasis。 [VERIFIED: CHANGELOG.md] | JSON + JSONL + `health` / `reason_codes` / `next_actions` / `decision` / `gate` observability。 [VERIFIED: CHANGELOG.md][VERIFIED: docs/releases/v0.3.1.md] | `0.3.1`。 [VERIFIED: CHANGELOG.md][VERIFIED: docs/releases/v0.3.1.md] | adoption examples 应该展示 agent/CI 如何消费这些 machine signals，而不只是“命令能跑”。 |
| bundle creation as a feature bullet。 [VERIFIED: README.md][VERIFIED: docs/releases/v0.3.1.md] | bundle creation + inspect + import as a downstream handoff contract already covered by tests。 [VERIFIED: tests/test_cli_runtime_gap.py][VERIFIED: tests/test_cli_pack_import.py] | Phase 5 completed on `2026-04-14`。 [VERIFIED: .planning/STATE.md][VERIFIED: .planning/phases/05-verified-delivery-bundles/05-VERIFICATION.md] | public docs 应该升级为“delivery handoff”叙事，而不是停在 `qrun pack`。 |

**Deprecated/outdated:**

- 把 FluxQ 当成“natural-language demo surface”或“narrow codegen demo”的 public framing 已经过时。 [VERIFIED: CHANGELOG.md][VERIFIED: docs/product-strategy.md]
- 只给出 `exec` happy path 而不解释 baseline/policy/handoff 的示例，对当前产品阶段已经不够。 [VERIFIED: README.md][VERIFIED: docs/aionrs-integration.md][VERIFIED: docs/releases/v0.3.1.md]

## Assumptions Log

所有关键事实都已在当前仓库或本地验证命令中核实；本研究没有保留需要用户额外确认的 `[ASSUMED]` 事实。

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| None | No unverified factual claims remain. [VERIFIED: repo audit 2026-04-15] | All | Low |

## Open Questions

1. **Phase 06 是否顺手修正内部 Phase 4 bookkeeping。**
What we know: `ROADMAP.md` 仍把 Phase 4 标成未开始，但 `REQUIREMENTS.md` 把 `POLC-01/02/03` 标为 complete，`04-VERIFICATION.md` 也已存在且验证了大部分 truth。 [VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/REQUIREMENTS.md][VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md]
What's unclear: 这是不是当前阶段的一部分，还是留到 milestone cleanup。 
Recommendation: 如果 Phase 06 会修改 release/versioning/storytelling，顺带修一次 contributor-facing bookkeeping 成本最低。

2. **最强 case study 是不是要进入顶层 docs index。**
What we know: `docs/fluxq-qaoa-maxcut-case-study.md` 已经是一份强 runtime-first 长案例，但 README docs 列表没有它，tests 也没覆盖它。 [VERIFIED: docs/fluxq-qaoa-maxcut-case-study.md][VERIFIED: README.md][VERIFIED: tests/test_release_docs.py]
What's unclear: 维护者更想直接链接这份中文文档，还是新增一份更短的 English/CI-facing sibling doc。
Recommendation: 计划阶段先决定“链接现有 case study”还是“新建 adoption doc”，避免 scope 在执行中漂移。

3. **`pyproject.toml` 的 `Code Generators` classifier 是否还要保留。**
What we know: package description 已经是 runtime-first，但 classifier 仍然指向 `Code Generators`。 [VERIFIED: pyproject.toml]
What's unclear: 维护者是否把这个 classifier 看作仍有搜索价值，还是认为它已经与当前定位冲突。
Recommendation: 把这个问题作为 `06-01` 的显式决策点，而不是顺手修改。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `uv` | README/local install & validation workflow | ✓ | `0.11.1` | 仅在 CI 中可退回 `python -m pip install -e '.[dev]'`。 [VERIFIED: uv --version][VERIFIED: README.md][VERIFIED: .github/workflows/ci.yml] |
| repo `.venv` Python | 本阶段本地测试与 build | ✓ | `3.11.15` | 用 `uv venv --python 3.11` 重建。 [VERIFIED: ./.venv/bin/python --version][VERIFIED: README.md] |
| system `python3` | ad hoc shell checks only | ✓ but wrong target version | `3.13.2` | 不用于 phase validation。 [VERIFIED: python3 --version][VERIFIED: pyproject.toml] |
| `pytest` in `.venv` | adoption/release contract tests | ✓ | `9.0.2` | `uv pip install -e '.[dev]'`。 [VERIFIED: ./.venv/bin/python -m pytest --version][VERIFIED: pyproject.toml] |
| `build` in `.venv` | packaging metadata validation | ✓ | `1.3.0` | `uv pip install -e '.[dev]'`。 [VERIFIED: ./.venv/bin/python -m build --version][VERIFIED: pyproject.toml] |

**Missing dependencies with no fallback:**

- None. [VERIFIED: local environment audit 2026-04-15]

**Missing dependencies with fallback:**

- None. [VERIFIED: local environment audit 2026-04-15]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest` `9.0.2` in repo `.venv`; dependency floor `>=8.0` in `pyproject.toml`. [VERIFIED: ./.venv/bin/python -m pytest --version][VERIFIED: pyproject.toml] |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` with `testpaths = ["tests"]`. [VERIFIED: pyproject.toml] |
| Quick run command | `./.venv/bin/python -m pytest tests/test_release_docs.py tests/test_aionrs_assets.py tests/test_open_source_release.py tests/test_packaging_release.py -q` |
| Full suite command | `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest -q --ignore tests/test_classiq_backend.py --ignore tests/test_classiq_emitter.py --ignore tests/test_qspec_validation.py && ./.venv/bin/python -m build` [VERIFIED: .github/workflows/ci.yml][VERIFIED: pyproject.toml] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SURF-01 | README / architecture / release-facing docs 一致讲 runtime/control-plane，而不是 generator demo。 [VERIFIED: .planning/REQUIREMENTS.md] | doc contract | `./.venv/bin/python -m pytest tests/test_release_docs.py tests/test_packaging_release.py -q` | ✅ extend |
| SURF-02 | 仓库内存在一条端到端 agent 或 CI workflow，覆盖 ingress、execution、policy evaluation、delivery handoff。 [VERIFIED: .planning/REQUIREMENTS.md] | doc contract + workflow contract | `./.venv/bin/python -m pytest tests/test_aionrs_assets.py tests/test_release_docs.py -q` | ✅ extend or add one new test file |
| SURF-03 | versioning / release notes 明确 stable / evolving / optional contracts 与安全消费方式。 [VERIFIED: .planning/REQUIREMENTS.md] | doc contract | `./.venv/bin/python -m pytest tests/test_release_docs.py tests/test_packaging_release.py -q` | ✅ extend |

### Sampling Rate

- **Per task commit:** 运行本阶段 targeted docs/adoption suite：`./.venv/bin/python -m pytest tests/test_release_docs.py tests/test_aionrs_assets.py tests/test_open_source_release.py tests/test_packaging_release.py -q`
- **Per wave merge:** 运行 phase gate：`./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_release_docs.py tests/test_aionrs_assets.py tests/test_open_source_release.py tests/test_packaging_release.py -q && ./.venv/bin/python -m build`
- **Phase gate:** 至少 targeted docs/adoption suite + `python -m build` 绿，再进入 `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_release_docs.py` 需要新增对 coherent workflow 的锁：同一 workload、`baseline set` 在 `compare --baseline` 之前、并包含 `pack-inspect` / `pack-import` 或等价 handoff surface。 [VERIFIED: tests/test_release_docs.py][VERIFIED: docs/releases/v0.3.1.md]
- [ ] `tests/test_aionrs_assets.py` 需要从 “exec/doctor/bench exists” 扩到 policy/handoff contract，或者新增 `tests/test_runtime_adoption_docs.py` 专门锁集成/CI workflow。 [VERIFIED: tests/test_aionrs_assets.py][VERIFIED: docs/aionrs-integration.md]
- [ ] `docs/versioning.md` 需要被测试要求出现 stable / evolving / optional 结构与 safe consumption guidance。 当前只锁了 release-line 和 4 条 compatibility rules。 [VERIFIED: docs/versioning.md][VERIFIED: tests/test_release_docs.py]
- [ ] 如果 Phase 06 要把 case study 作为主 adoption asset，需要在 README docs index 和 tests 中显式纳入。 [VERIFIED: README.md][VERIFIED: docs/fluxq-qaoa-maxcut-case-study.md]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 本阶段不涉及认证面。 |
| V3 Session Management | no | 本阶段不涉及会话面。 |
| V4 Access Control | no | 本阶段不涉及授权控制逻辑。 |
| V5 Input Validation | yes | 文档必须明确展示 fail-closed usage，例如 `baseline set` 之后再 `compare --baseline`、`pack-inspect` 之后再 `pack-import`、以及 `doctor --ci` / compare gate 的 machine-readable verdict 消费。 [VERIFIED: docs/releases/v0.3.1.md][VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_cli_doctor.py][VERIFIED: tests/test_cli_pack_import.py][VERIFIED: tests/test_cli_runtime_gap.py] |
| V6 Cryptography | no | 本阶段不改动加密实现；bundle digest verification 已在 runtime/tests 中存在。 [VERIFIED: tests/test_pack_bundle.py][VERIFIED: tests/test_cli_runtime_gap.py] |

### Known Threat Patterns for this phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 文档跳过 bundle verification 直接导入下游 workspace | Tampering | 在 public workflow 中固定 `pack-inspect` 先于 `pack-import`，并在 tests 中锁这一顺序。 [VERIFIED: tests/test_cli_runtime_gap.py][VERIFIED: tests/test_cli_pack_import.py] |
| 文档把 advisory/degraded 当成 pass | Repudiation | 强调 `compare` 的 `verdict/gate`、`doctor --ci` 的 blocking/advisory 区分、以及 `reason_codes` / `next_actions` 的机器消费。 [VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_cli_doctor.py][VERIFIED: tests/test_cli_observability.py] |
| 文档继续混淆 runtime contract 与 generator demo | Tampering | 统一 README / release / integration / packaging metadata 的 runtime-first wording，并把矛盾处写进回归测试。 [VERIFIED: README.md][VERIFIED: docs/releases/v0.3.1.md][VERIFIED: docs/aionrs-integration.md][VERIFIED: pyproject.toml][VERIFIED: tests/test_release_docs.py] |

## Sources

### Primary (HIGH confidence)

- `AGENTS.md` - 项目定位、技术约束、GSD workflow 约束。 [VERIFIED: AGENTS.md]
- `.planning/PROJECT.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md` - Phase 06 目标、SURF-01/02/03、当前项目状态。 [VERIFIED: .planning/PROJECT.md][VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/REQUIREMENTS.md][VERIFIED: .planning/STATE.md]
- `README.md`, `ARCHITECTURE.md`, `docs/product-strategy.md`, `docs/versioning.md`, `docs/releases/v0.3.1.md`, `docs/aionrs-integration.md`, `docs/fluxq-qaoa-maxcut-case-study.md` - 当前 public adoption narrative。 [VERIFIED: README.md][VERIFIED: ARCHITECTURE.md][VERIFIED: docs/product-strategy.md][VERIFIED: docs/versioning.md][VERIFIED: docs/releases/v0.3.1.md][VERIFIED: docs/aionrs-integration.md][VERIFIED: docs/fluxq-qaoa-maxcut-case-study.md]
- `integrations/aionrs/CLAUDE.md.example`, `integrations/aionrs/hooks.example.toml` - 当前 host integration assets。 [VERIFIED: integrations/aionrs/CLAUDE.md.example][VERIFIED: integrations/aionrs/hooks.example.toml]
- `tests/test_release_docs.py`, `tests/test_aionrs_assets.py`, `tests/test_open_source_release.py`, `tests/test_packaging_release.py` - 当前 adoption/release contract locks。 [VERIFIED: tests/test_release_docs.py][VERIFIED: tests/test_aionrs_assets.py][VERIFIED: tests/test_open_source_release.py][VERIFIED: tests/test_packaging_release.py]
- `tests/test_cli_ingress_resolution.py`, `tests/test_cli_compare.py`, `tests/test_cli_doctor.py`, `tests/test_cli_observability.py`, `tests/test_cli_runtime_gap.py`, `tests/test_cli_pack_import.py` - 证明组成 end-to-end adoption flow 的命令表面已经存在。 [VERIFIED: tests/test_cli_ingress_resolution.py][VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_cli_doctor.py][VERIFIED: tests/test_cli_observability.py][VERIFIED: tests/test_cli_runtime_gap.py][VERIFIED: tests/test_cli_pack_import.py]
- `.github/workflows/ci.yml`, `.github/workflows/classiq.yml`, `pyproject.toml` - 当前 validation 与 package metadata contract。 [VERIFIED: .github/workflows/ci.yml][VERIFIED: .github/workflows/classiq.yml][VERIFIED: pyproject.toml]

### Secondary (MEDIUM confidence)

- `.planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md` - 证明 policy surfaces 已经存在，但 roadmap bookkeeping 仍有落差。 [VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md]
- `.planning/phases/05-verified-delivery-bundles/05-VERIFICATION.md` - 证明 handoff surfaces 已经存在，但 public docs 尚未采用同一叙事。 [VERIFIED: .planning/phases/05-verified-delivery-bundles/05-VERIFICATION.md]
- `.planning/codebase/CONCERNS.md` - 提供历史 concern map，但其中 dirty-worktree 警告与当前 `git status --short` 已不一致。 [VERIFIED: .planning/codebase/CONCERNS.md][VERIFIED: git status --short]

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - 主要是 repo-native surfaces 与本地工具版本，均已直接核实。 [VERIFIED: README.md][VERIFIED: pyproject.toml][VERIFIED: local environment audit 2026-04-15]
- Architecture: HIGH - adoption gaps 与推荐 split 直接来自现有 docs/tests/metadata 的聚类。 [VERIFIED: README.md][VERIFIED: docs/releases/v0.3.1.md][VERIFIED: docs/aionrs-integration.md][VERIFIED: docs/versioning.md][VERIFIED: pyproject.toml][VERIFIED: tests/test_release_docs.py][VERIFIED: tests/test_aionrs_assets.py]
- Pitfalls: HIGH - 关键矛盾点都能在当前 repo 中直接复现或直接读到。 [VERIFIED: docs/releases/v0.3.1.md][VERIFIED: integrations/aionrs/CLAUDE.md.example][VERIFIED: pyproject.toml][VERIFIED: tests/test_release_docs.py][VERIFIED: tests/test_aionrs_assets.py]

**Research date:** 2026-04-15
**Valid until:** 2026-05-15
