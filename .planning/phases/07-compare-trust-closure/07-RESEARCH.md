# Phase 07: Compare Trust Closure - Research

**Researched:** 2026-04-15 [VERIFIED: system date]  
**Domain:** FluxQ `exec -> report writer -> import resolution -> compare gate` 信任闭环修复。[VERIFIED: user prompt][VERIFIED: .planning/ROADMAP.md][VERIFIED: src/quantum_runtime/runtime/executor.py][VERIFIED: src/quantum_runtime/reporters/writer.py][VERIFIED: src/quantum_runtime/runtime/imports.py][VERIFIED: src/quantum_runtime/runtime/compare.py]  
**Confidence:** HIGH [VERIFIED: local reproduction 2026-04-15][VERIFIED: local test run 2026-04-15]

<user_constraints>
## User Constraints

Phase 07 没有现成的 `*-CONTEXT.md`；本次研究以用户提示、`ROADMAP.md`、`REQUIREMENTS.md`、`STATE.md` 和里程碑审计为准。[VERIFIED: gsd-tools init phase-op 07][VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/REQUIREMENTS.md][VERIFIED: .planning/STATE.md][VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md]

- 锁定目标：恢复 baseline/current compare gate，使 revision-to-revision 决策在 drift class 上失败，而不是先因为 artifact inconsistency 提前失败。[VERIFIED: user prompt][VERIFIED: .planning/ROADMAP.md]
- 锁定 requirement：只要求 Phase 07 收口 `POLC-01`，同时补上跨阶段缺口 `INT-01` 和流程缺口 `FLOW-01`。[VERIFIED: user prompt][VERIFIED: .planning/REQUIREMENTS.md][VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md]
- 锁定实现边界：不要引入新的 IR、不要改写 `QSpec` 产品中心、不要把问题扩散成远程执行或更大范围的产品重构。[VERIFIED: AGENTS.md][VERIFIED: .planning/PROJECT.md]
- 研究输出必须聚焦 Phase 2 artifact writing 与 Phase 4 compare gating 的接缝，而不是重新设计 compare policy 语义。[VERIFIED: user prompt][VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md]
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| `POLC-01` | Agent can compare current state against baseline and fail on specific drift classes without external wrapper logic. [VERIFIED: .planning/REQUIREMENTS.md] | Phase 07 需要先修复 exec/report 写入侧对 active revision QSpec/report 一致性的破坏，再让 `compare_workspace_baseline()` 和 `ComparePolicy` 走到既有 verdict/gate/exit=2 路径。[VERIFIED: src/quantum_runtime/runtime/compare.py][VERIFIED: src/quantum_runtime/cli.py][VERIFIED: src/quantum_runtime/runtime/exit_codes.py][VERIFIED: local test run 2026-04-15] |
</phase_requirements>

## Summary

当前断点不在 compare policy 本身，而在 compare 之前的 trusted import 阶段。`compare_workspace_baseline()`、`compare_import_resolutions()` 和 `exit_code_for_compare()` 已经具备在 `subject_drift` 上返回 `verdict=fail`、`gate.ready=false`、`exit=2` 的能力；实际失败发生在 `resolve_workspace_current()` 期间，由 `ImportSourceError("report_qspec_semantic_hash_mismatch")` 抢先中断，CLI 因此返回输入错误 `exit=3`。[VERIFIED: src/quantum_runtime/runtime/compare.py:110-248][VERIFIED: src/quantum_runtime/runtime/exit_codes.py:108-124][VERIFIED: src/quantum_runtime/cli.py:1547-1618][VERIFIED: local test run 2026-04-15]

高置信根因已经复现：第二次 `exec` 时，`write_report()` 会在 alias promotion 之前调用 `_materialize_canonical_artifacts()`，把旧的 `specs/current.json` 与当前 artifact alias 回拷到新 revision 的 canonical history 路径；由于此时 `current.json` 仍然指向旧 revision，`specs/history/rev_000002.json` 会被旧内容覆盖。随后 report 又从被覆盖后的文件读取 `qspec_hash`，却继续使用内存中“新 QSpec”的 `semantic_hash`，于是 report 自身就变成了“哈希对旧文件、语义对新对象”的自相矛盾状态。[VERIFIED: src/quantum_runtime/reporters/writer.py:16-49][VERIFIED: src/quantum_runtime/reporters/writer.py:92-109][VERIFIED: src/quantum_runtime/runtime/executor.py:218-224][VERIFIED: src/quantum_runtime/runtime/executor.py:370-437][VERIFIED: local reproduction 2026-04-15]

Phase 07 的最佳策略不是放松 import/compare 的 fail-closed 行为，而是修复写入契约并补齐跨阶段回归。这样可以同时保住 Phase 2 的 trust model 和 Phase 4 的 policy surface：trusted import 继续拦截真实篡改，而 baseline/current compare 在正常 revision 上重新返回 drift verdict，而不是提前报 artifact inconsistency。[VERIFIED: src/quantum_runtime/runtime/imports.py:590-711][VERIFIED: src/quantum_runtime/runtime/compare.py:196-248][VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][VERIFIED: local test run 2026-04-15]

**Primary recommendation:** 先修复 `write_report()` 对 canonical history 的 alias 回写，再把 compare/baseline 的现有红测转为绿色契约，并用一条 exec-side coherence regression 把这个 seam 永久钉住。[VERIFIED: src/quantum_runtime/reporters/writer.py:92-109][VERIFIED: tests/test_cli_compare.py:811-876][VERIFIED: tests/test_cli_runtime_gap.py:137-189][VERIFIED: tests/test_runtime_compare.py:410-438][VERIFIED: local test run 2026-04-15]

## Root Cause Hypotheses

| ID | Hypothesis | Confidence | Evidence |
|----|------------|------------|----------|
| `H1` | Phase 07 的主故障来自 `write_report()` 在 alias promotion 前把 mutable alias 复制回 canonical history，破坏了新 revision 的 `specs/history/<revision>.json` 和部分 artifact history 文件。 | HIGH [VERIFIED: local reproduction 2026-04-15] | `_materialize_canonical_artifacts()` 对除 `report` 外的所有 artifact 都执行 `shutil.copy2(alias_path, canonical_path)`；`qspec` 的 alias 是 `specs/current.json`。[VERIFIED: src/quantum_runtime/reporters/writer.py:92-109][VERIFIED: src/quantum_runtime/artifact_provenance.py:32-39][VERIFIED: src/quantum_runtime/artifact_provenance.py:317-345] |
| `H2` | report 的 `qspec.hash` 与 `qspec.semantic_hash` 当前可能来自两个不同来源：哈希来自已被旧 alias 覆盖的磁盘文件，语义哈希来自新的内存 QSpec。 | HIGH [VERIFIED: local reproduction 2026-04-15] | `write_report()` 先 canonicalize artifacts，再从 `canonical_qspec_path` 读 `qspec_hash`，但 `semantic_hash` 直接来自 `summarize_qspec_semantics(qspec)`。[VERIFIED: src/quantum_runtime/reporters/writer.py:30-49] |
| `H3` | compare 提前失败是正确的 downstream 行为，不是 compare policy 算法错误：`resolve_workspace_current()` 偏向 history report/QSpec，`_evaluate_replay_integrity()` 对语义哈希不一致 fail closed，然后 `compare_command()` 把 `ImportSourceError` 映射为 `_json_error()`。 | HIGH [VERIFIED: local test run 2026-04-15] | `resolve_workspace_current()` 优先 `reports/history/<current_revision>.json`，再从 artifact provenance 解析 canonical qspec；语义不一致时 `_evaluate_replay_integrity()` 抛 `report_qspec_semantic_hash_mismatch`；CLI 在 compare 之前捕获并退出 3。[VERIFIED: src/quantum_runtime/runtime/imports.py:131-187][VERIFIED: src/quantum_runtime/runtime/imports.py:506-516][VERIFIED: src/quantum_runtime/runtime/imports.py:590-626][VERIFIED: src/quantum_runtime/cli.py:1600-1604] |
| `H4` | run manifest 不是第一道发现此 bug 的地方，因为 manifest 在覆盖发生之后才生成，它会记录“已被污染的 canonical qspec 文件”的 hash/path，因此 manifest 与错误的文件是一致的。 | HIGH [VERIFIED: local reproduction 2026-04-15] | `write_run_manifest()` 在 `write_report()` 之后执行，且从 `qspec_path` / `report_path` 直接计算 hash；它校验的是 path/hash，不会对 report 内的 `qspec.semantic_hash` 与磁盘 qspec 语义再次比对。[VERIFIED: src/quantum_runtime/runtime/executor.py:370-437][VERIFIED: src/quantum_runtime/runtime/run_manifest.py:251-313][VERIFIED: src/quantum_runtime/runtime/run_manifest.py:143-248] |

## Recommended Plan Split

### Plan 1: Repair Canonical Revision Writes

- 目标：让 `exec` 对新 revision 的 `qspec/report/artifact` history 只写一次，禁止从 `current`/`latest` alias 回灌 canonical history。[VERIFIED: src/quantum_runtime/runtime/executor.py:218-224][VERIFIED: src/quantum_runtime/runtime/executor.py:408-437][VERIFIED: src/quantum_runtime/reporters/writer.py:92-109]
- 主文件：`src/quantum_runtime/reporters/writer.py`，必要时配合 `src/quantum_runtime/runtime/executor.py` 明确“history-first, alias-last”契约。[VERIFIED: src/quantum_runtime/reporters/writer.py][VERIFIED: src/quantum_runtime/runtime/executor.py]
- 完成标准：第二次 `exec` 之后，`specs/history/rev_000002.json`、`reports/history/rev_000002.json`、`manifests/history/rev_000002.json` 三者对同一 revision 语义一致，不再回指或回写旧 alias 内容。[VERIFIED: local reproduction 2026-04-15][VERIFIED: tests/test_runtime_revision_artifacts.py:220-266][ASSUMED]

### Plan 2: Reopen Compare/Baseline Policy Gate

- 目标：保持 import fail-closed 语义不变，只在写入侧修复后重新让 `compare --baseline --fail-on subject_drift` 与 revision-to-revision compare 走到既有 `ComparePolicy`/`verdict`/`gate` 路径。[VERIFIED: src/quantum_runtime/runtime/imports.py:590-711][VERIFIED: src/quantum_runtime/runtime/compare.py:110-248][VERIFIED: src/quantum_runtime/cli.py:1547-1618]
- 主文件：理论上以测试恢复为主；若 compare 层需要最小调整，只允许补充更清晰的 reason code / detail，不允许吞掉 `ImportSourceError` 假装成功比较。[VERIFIED: src/quantum_runtime/cli.py:1600-1604][ASSUMED]
- 完成标准：现有三条红测变绿，并稳定返回 `exit=2`、`failed_checks=["subject_drift"]`、`gate.ready=false`。[VERIFIED: tests/test_cli_compare.py:811-876][VERIFIED: tests/test_cli_runtime_gap.py:137-189][VERIFIED: tests/test_runtime_compare.py:410-438][VERIFIED: local test run 2026-04-15]

### Plan 3: Harden Cross-Phase Regression Ownership

- 目标：把“只检查文件存在/路径”的旧强度测试升级为“检查 revision 语义一致性”的 Phase 7 合同，避免以后又从 Phase 2 回归到 Phase 4。[VERIFIED: tests/test_runtime_revision_artifacts.py:152-217][VERIFIED: tests/test_cli_exec.py:360-392][VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md]
- 主文件：`tests/test_runtime_revision_artifacts.py`、`tests/test_cli_exec.py`，必要时保留 `tests/test_cli_runtime_gap.py` 作为里程碑 gap smoke。[VERIFIED: tests/test_runtime_revision_artifacts.py][VERIFIED: tests/test_cli_exec.py][VERIFIED: tests/test_cli_runtime_gap.py]
- 完成标准：新 regression 能在 compare 之前、甚至不调用 compare 时就发现“report 语义与 qspec history 不一致”的写入破坏。[VERIFIED: src/quantum_runtime/runtime/imports.py:614-626][ASSUMED]

## Standard Stack

本 phase 不需要新增依赖；应继续使用仓库当前 Python/CLI/runtime stack，并把修复限制在现有 runtime modules 和 pytest 回归上。[VERIFIED: AGENTS.md][VERIFIED: pyproject.toml][VERIFIED: .planning/PROJECT.md]

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | `>=3.11,<3.12` in project, `.venv` 实际为 `3.11.15`。[VERIFIED: pyproject.toml][VERIFIED: ./.venv/bin/python --version] | 运行 CLI/runtime 与本 phase 验证命令。[VERIFIED: AGENTS.md][VERIFIED: README.md] | 这是仓库与 CI 的既定运行时；不应在 Phase 07 引入版本漂移。[VERIFIED: AGENTS.md][VERIFIED: .planning/PROJECT.md] |
| Typer | `0.24.1`。[VERIFIED: AGENTS.md] | `qrun compare` / `qrun exec` CLI surface 与错误映射。[VERIFIED: AGENTS.md][VERIFIED: src/quantum_runtime/cli.py] | compare gate 已经在现有 CLI surface 暴露完成，Phase 07 不应重做命令层。[VERIFIED: src/quantum_runtime/cli.py][VERIFIED: .planning/phases/04-policy-acceptance-gates/04-RESEARCH.md] |
| Pydantic | `2.12.5`。[VERIFIED: AGENTS.md] | `ComparePolicy`、`CompareResult`、`ImportResolution`、manifest/report contract。[VERIFIED: AGENTS.md][VERIFIED: src/quantum_runtime/runtime/compare.py][VERIFIED: src/quantum_runtime/runtime/imports.py][VERIFIED: src/quantum_runtime/runtime/run_manifest.py] | 现有 machine-readable contract 全部建立在 Pydantic 模型上；新逻辑应复用它们。[VERIFIED: AGENTS.md][VERIFIED: src/quantum_runtime/runtime/contracts.py] |
| Qiskit-first runtime path | Repo current (`qiskit 2.3.1`, `qiskit-aer 0.17.2`)。[VERIFIED: AGENTS.md] | 生成第二次 exec 的真实 revision 差异 fixture；本 phase 的红测都走这一执行路径。[VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_cli_runtime_gap.py][VERIFIED: tests/test_runtime_compare.py] | bug 发生在 runtime object lifecycle，不在新依赖选择；继续用现有执行栈即可复现并验证修复。[VERIFIED: local test run 2026-04-15] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | `9.0.2` in `.venv`。[VERIFIED: ./.venv/bin/python -m pytest --version] | 回归 `exec -> baseline -> compare`、runtime import、revision artifact coherence。[VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_cli_runtime_gap.py][VERIFIED: tests/test_runtime_compare.py][VERIFIED: tests/test_runtime_imports.py][VERIFIED: tests/test_runtime_revision_artifacts.py] | 每个计划完成后都应跑 targeted suite；Phase gate 跑 full Phase 7 suite。[VERIFIED: .planning/config.json][ASSUMED] |
| Ruff | `0.15.8` in `.venv`。[VERIFIED: ./.venv/bin/ruff --version] | 保持 `src/` 与 `tests/` 的既有 lint gate 绿色。[VERIFIED: AGENTS.md][VERIFIED: pyproject.toml] | 计划完成后跑 phase gate；host PATH 没有 `ruff` 时使用 `.venv/bin/ruff` 或 `uv run ruff`。[VERIFIED: local env 2026-04-15] |
| MyPy | `1.20.0` in `.venv`。[VERIFIED: ./.venv/bin/python -m mypy --version] | 保持 `src` 的类型检查绿色。[VERIFIED: AGENTS.md][VERIFIED: mypy.ini] | phase gate 与最终验证使用 `.venv/bin/python -m mypy src`。[VERIFIED: AGENTS.md][VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md] |
| uv | `0.11.1`。[VERIFIED: uv --version] | 在 host Python 不是 3.11 时提供可重复的 Phase 7 验证入口。[VERIFIED: local env 2026-04-15][VERIFIED: README.md] | host `python3` 当前是 `3.13.2`，不满足项目 runtime；优先通过 `uv run --python 3.11 ...` 或 `.venv` 执行。[VERIFIED: python3 --version 2026-04-15][VERIFIED: pyproject.toml] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| 修补 compare，吞掉 `report_qspec_semantic_hash_mismatch` 再继续做 drift 判定。[ASSUMED] | 直接在 `compare_command()` 捕获 `ImportSourceError` 并降级成 compare difference。[ASSUMED] | 不推荐；这会把真实的 trusted artifact 破坏伪装成普通 drift，破坏 Phase 2 的 fail-closed 契约。[VERIFIED: src/quantum_runtime/runtime/imports.py:590-711][VERIFIED: src/quantum_runtime/cli.py:1600-1604] |
| 新增一套 provenance/trust helper。[ASSUMED] | 自定义路径归一化或自定义 compare side preload。[ASSUMED] | 不推荐；现有 `canonicalize_artifact_provenance()`、`load_run_manifest()`、`resolve_workspace_current()` 已经构成标准 trust path，再造一套只会放大 seam。[VERIFIED: src/quantum_runtime/artifact_provenance.py][VERIFIED: src/quantum_runtime/runtime/imports.py][VERIFIED: src/quantum_runtime/runtime/run_manifest.py] |

**Installation:** [VERIFIED: README.md][VERIFIED: pyproject.toml]

```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e '.[dev,qiskit]'
```

## Architecture Patterns

### Recommended Project Structure

```text
src/quantum_runtime/
├── runtime/executor.py      # exec 的 history-first commit graph
├── reporters/writer.py      # report 写入与 artifact provenance canonicalization
├── runtime/imports.py       # trusted import / replay integrity / baseline resolution
├── runtime/compare.py       # compare evidence、policy verdict、compare persistence
├── runtime/run_manifest.py  # immutable revision manifest
└── workspace/paths.py       # canonical workspace/history path helpers

tests/
├── test_cli_compare.py              # baseline/current compare gate 合同
├── test_cli_runtime_gap.py          # 里程碑 gap smoke
├── test_runtime_compare.py          # runtime-level baseline compare 合同
├── test_cli_exec.py                 # exec/report/replay integration
├── test_runtime_imports.py          # trusted import / replay-integrity fail-closed
└── test_runtime_revision_artifacts.py # revision artifact immutability/coherence
```

### Pattern 1: History-First, Alias-Last Writes

**What:** canonical history 文件必须先写完，再做 `current` / `latest` alias promotion；任何 helper 都不能从 mutable alias 回写 canonical history。[VERIFIED: src/quantum_runtime/runtime/executor.py:218-224][VERIFIED: src/quantum_runtime/runtime/executor.py:408-437][VERIFIED: .planning/phases/03-concurrent-workspace-safety/03-concurrent-workspace-safety-03-SUMMARY.md][VERIFIED: .planning/phases/03-concurrent-workspace-safety/03-concurrent-workspace-safety-04-SUMMARY.md]  
**When to use:** `exec` 写 revision artifacts、report、manifest，以及任何未来需要 canonical artifact 的 writer。[VERIFIED: src/quantum_runtime/runtime/executor.py][VERIFIED: src/quantum_runtime/reporters/writer.py]  
**Example:** [VERIFIED: src/quantum_runtime/runtime/executor.py:218-224][VERIFIED: src/quantum_runtime/runtime/executor.py:408-437]

```python
# Source: src/quantum_runtime/runtime/executor.py
atomic_write_text(qspec_history_path, qspec.model_dump_json(indent=2))
atomic_write_text(intent_history_path, intent_payload)
atomic_write_text(plan_history_path, plan_payload)

report = write_report(..., qspec_path=qspec_history_path, ...)
write_run_manifest(..., promote_latest=False)
_promote_exec_aliases(...)
```

### Pattern 2: Trust Resolution Before Policy Evaluation

**What:** compare 先解析 trusted baseline/current inputs，再跑 drift/policy；Phase 07 应修 producer，不应削弱 consumer。[VERIFIED: src/quantum_runtime/runtime/compare.py:110-133][VERIFIED: src/quantum_runtime/runtime/imports.py:131-187][VERIFIED: src/quantum_runtime/runtime/imports.py:590-711]  
**When to use:** baseline compare、explicit revision compare、report replay compare。[VERIFIED: src/quantum_runtime/runtime/compare.py][VERIFIED: src/quantum_runtime/cli.py]  
**Example:** [VERIFIED: src/quantum_runtime/runtime/compare.py:110-133]

```python
# Source: src/quantum_runtime/runtime/compare.py
baseline = resolve_workspace_baseline(workspace_root)
current = resolve_workspace_current(workspace_root)
result = compare_import_resolutions(baseline.resolution, current, policy=policy)
```

### Pattern 3: Semantic Coherence Must Be Derived From One Truth Source

**What:** `qspec.hash` 与 `qspec.semantic_hash` 必须来自同一个 canonical qspec artifact；不要一个来自磁盘文件、一个来自内存对象。[VERIFIED: src/quantum_runtime/reporters/writer.py:30-49][VERIFIED: src/quantum_runtime/runtime/imports.py:608-626][VERIFIED: local reproduction 2026-04-15]  
**When to use:** report writer、manifest builder、任何 future inspect/export trust envelope。[VERIFIED: src/quantum_runtime/reporters/writer.py][VERIFIED: src/quantum_runtime/runtime/run_manifest.py][ASSUMED]  
**Example:** [VERIFIED: src/quantum_runtime/runtime/imports.py:608-626]

```python
# Source: src/quantum_runtime/runtime/imports.py
if expected_qspec_hash is not None and qspec_hash != expected_qspec_hash:
    raise ImportSourceError("report_qspec_hash_mismatch", ...)
if expected_semantic_hash is not None and actual_semantic_hash != expected_semantic_hash:
    raise ImportSourceError("report_qspec_semantic_hash_mismatch", ...)
```

### Anti-Patterns to Avoid

- **Alias-to-history backfill:** 不要在 report writer 里把 `specs/current.json`、`artifacts/qiskit/main.py` 等 alias 复制回 revision history；Phase 3 已经规定 canonical history 是写入源，不是回填目标。[VERIFIED: src/quantum_runtime/reporters/writer.py:92-109][VERIFIED: .planning/phases/03-concurrent-workspace-safety/03-concurrent-workspace-safety-03-SUMMARY.md]
- **Consumer-side trust downgrade:** 不要通过“捕获 `report_qspec_semantic_hash_mismatch` 然后继续 compare”来修这个 bug；那是在掩盖 producer corruption。[VERIFIED: src/quantum_runtime/runtime/imports.py:590-711][VERIFIED: src/quantum_runtime/cli.py:1600-1604]
- **Path-only tests:** 不要只断言 report/qspec 路径长得像 history 路径；这次 bug 证明路径正确并不代表内容仍是该 revision 的语义。[VERIFIED: tests/test_cli_exec.py:360-392][VERIFIED: tests/test_runtime_revision_artifacts.py:220-266][VERIFIED: local reproduction 2026-04-15]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Canonical artifact path normalization | 自定义 `specs/`、`reports/`、`artifacts/` 路径拼接器。[ASSUMED] | `canonicalize_artifact_provenance()` + `select_accessible_artifact_paths()`。[VERIFIED: src/quantum_runtime/artifact_provenance.py] | 现有 helper 已经同时处理 canonical path、current alias、relative legacy path 和 revision validation。[VERIFIED: src/quantum_runtime/artifact_provenance.py:21-126][VERIFIED: tests/test_runtime_imports.py:263-303][VERIFIED: tests/test_runtime_imports.py:376-426] |
| Replay trust validation | compare 前再写一层自定义 “safe compare preload”。[ASSUMED] | `resolve_workspace_current()`、`resolve_workspace_baseline()`、`_evaluate_replay_integrity()`。[VERIFIED: src/quantum_runtime/runtime/imports.py] | 这些 helper 已经承担 Phase 2 的 fail-closed 责任；重复实现只会制造新的 seam。[VERIFIED: src/quantum_runtime/runtime/imports.py:131-230][VERIFIED: src/quantum_runtime/runtime/imports.py:590-711] |
| Compare gate schema | 新的 policy/verdict/gate payload 结构。[ASSUMED] | `ComparePolicy`、`CompareResult`、`gate_block()`、`exit_code_for_compare()`。[VERIFIED: src/quantum_runtime/runtime/compare.py][VERIFIED: src/quantum_runtime/runtime/exit_codes.py] | Phase 4 已经定义了标准 gate 词汇；Phase 07 需要恢复通路，不需要重写协议。[VERIFIED: .planning/phases/04-policy-acceptance-gates/04-RESEARCH.md][VERIFIED: src/quantum_runtime/runtime/compare.py] |
| Compare artifact persistence | 直接 `Path.write_text()` 或手写 schema 封装。[ASSUMED] | `ensure_schema_payload()` + `acquire_workspace_lock()` + `atomic_write_text()`。[VERIFIED: src/quantum_runtime/runtime/compare.py:251-276][VERIFIED: src/quantum_runtime/runtime/contracts.py:142-160] | compare/latest 与 compare/history 已经有标准写法；Phase 07 只需保持其可达性与稳定性。[VERIFIED: src/quantum_runtime/runtime/compare.py:251-276][VERIFIED: tests/test_cli_compare.py:878-934] |

**Key insight:** Phase 07 不需要新的 trust framework；它需要让现有的 Phase 2 trust writer 与 Phase 4 compare consumer 重新遵守同一份 canonical history 合同。[VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][VERIFIED: src/quantum_runtime/runtime/executor.py][VERIFIED: src/quantum_runtime/reporters/writer.py][VERIFIED: src/quantum_runtime/runtime/imports.py]

## Common Pitfalls

### Pitfall 1: Hash 看起来对，但语义已经错了

**What goes wrong:** report 的 `qspec.hash` 与磁盘 qspec 文件一致，但 `qspec.semantic_hash` 来自另一个对象来源，结果 compare/import 只在语义校验时才炸裂。[VERIFIED: src/quantum_runtime/reporters/writer.py:30-49][VERIFIED: src/quantum_runtime/runtime/imports.py:614-626][VERIFIED: local reproduction 2026-04-15]  
**Why it happens:** writer 当前先 canonicalize artifact，再读文件 hash，却仍沿用内存 QSpec 的语义摘要。[VERIFIED: src/quantum_runtime/reporters/writer.py:30-49]  
**How to avoid:** 让 canonical qspec 文件在 report writer 期间保持只读，或确保 hash/semantic 都从同一个 canonical artifact 导出。[VERIFIED: src/quantum_runtime/runtime/executor.py:218-224][ASSUMED]  
**Warning signs:** `report.qspec.hash` 与 `specs/history/<revision>.json` 匹配，但 `report_qspec_semantic_hash_mismatch` 仍然出现；两个 revision 的 qspec history digest 意外完全相同。[VERIFIED: local reproduction 2026-04-15]

### Pitfall 2: 试图在 compare 层吞掉 trusted import 错误

**What goes wrong:** 为了让红测变绿，直接把 `ImportSourceError` 转成普通 compare diff，结果 artifact corruption 被掩盖成“正常 drift”。[ASSUMED]  
**Why it happens:** 表面现象出现在 `qrun compare`，容易误以为 compare gate 需要“更宽容”。[VERIFIED: local test run 2026-04-15]  
**How to avoid:** 保持 `_evaluate_replay_integrity()` fail closed，修 writer 和 exec contract，而不是削弱 consumer。[VERIFIED: src/quantum_runtime/runtime/imports.py:590-711][VERIFIED: src/quantum_runtime/reporters/writer.py:92-109]  
**Warning signs:** compare 开始返回 drift verdict，但 `resolve_workspace_current()` / `resolve_report_file()` 不再对真实的 semantic mismatch 报错。[ASSUMED]

### Pitfall 3: 把旧 verification 文档当作当前真相

**What goes wrong:** `04-VERIFICATION.md` 记载 baseline compare 曾经通过，但当前 live code 已经红掉，导致 planner 低估真实修复量。[VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md][VERIFIED: local test run 2026-04-15]  
**Why it happens:** Phase 4 文档记录的是当时的验证结果，不保证后续 Phase 5/6 或其它合并后仍然成立。[VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md][VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md]  
**How to avoid:** Phase 07 规划与验证都以 live regression 为准，把旧文档当线索而不是当 current proof。[VERIFIED: local test run 2026-04-15][ASSUMED]  
**Warning signs:** 文档声称 `68 passed` 或 baseline compare smoke 通过，但当前 targeted run 在 `tests/test_cli_compare.py` / `tests/test_cli_runtime_gap.py` / `tests/test_runtime_compare.py` 直接失败。[VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md][VERIFIED: local test run 2026-04-15]

## Code Examples

Verified patterns from official local sources:

### Exec Commit Graph Should Stay History-First

```python
# Source: src/quantum_runtime/runtime/executor.py [VERIFIED: src/quantum_runtime/runtime/executor.py:218-224][VERIFIED: src/quantum_runtime/runtime/executor.py:408-437]
atomic_write_text(qspec_history_path, qspec.model_dump_json(indent=2))
atomic_write_text(intent_history_path, intent_payload)
atomic_write_text(plan_history_path, plan_payload)

report = write_report(
    workspace=handle,
    revision=revision,
    qspec=qspec,
    qspec_path=qspec_history_path,
    artifacts=artifacts,
    ...
)
write_run_manifest(..., promote_latest=False)
_promote_exec_aliases(...)
```

### Compare Gate Should Compose Trusted Inputs, Not Raw Files

```python
# Source: src/quantum_runtime/runtime/compare.py [VERIFIED: src/quantum_runtime/runtime/compare.py:110-133]
baseline = resolve_workspace_baseline(workspace_root)
current = resolve_workspace_current(workspace_root)
result = compare_import_resolutions(
    baseline.resolution,
    current,
    policy=policy,
)
```

### Semantic Mismatch Is Supposed To Block Before Policy

```python
# Source: src/quantum_runtime/runtime/imports.py [VERIFIED: src/quantum_runtime/runtime/imports.py:608-626]
if expected_qspec_hash is not None and qspec_hash != expected_qspec_hash:
    raise ImportSourceError("report_qspec_hash_mismatch", ...)
if expected_semantic_hash is not None and actual_semantic_hash != expected_semantic_hash:
    raise ImportSourceError("report_qspec_semantic_hash_mismatch", ...)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `write_report()` 在 canonicalization 阶段把 mutable alias 复制回 history path。[VERIFIED: src/quantum_runtime/reporters/writer.py:92-109] | Phase 07 应恢复为“history write-once，alias promotion 只允许 history -> alias”。[VERIFIED: .planning/phases/03-concurrent-workspace-safety/03-concurrent-workspace-safety-03-SUMMARY.md][ASSUMED] | Phase 03 已建立该模式，但 writer 当前仍违背它；Phase 07 需要把 writer 拉回这条线。[VERIFIED: .planning/phases/03-concurrent-workspace-safety/03-concurrent-workspace-safety-03-SUMMARY.md][VERIFIED: src/quantum_runtime/reporters/writer.py:92-109] | 修复后 compare 会回到 drift verdict，而不是 semantic mismatch 提前失败。[VERIFIED: local test run 2026-04-15][ASSUMED] |
| baseline/current compare 被认为“已验证通过”。[VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md] | 当前 live code 需要以 targeted red tests 为准重新收口。[VERIFIED: local test run 2026-04-15] | 文档写于 2026-04-13；live run 失败发生在 2026-04-15。[VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md][VERIFIED: system date][VERIFIED: local test run 2026-04-15] | planner 不能假设 Phase 4 的 baseline compare 已经稳定完成。[VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][VERIFIED: local test run 2026-04-15] |

**Deprecated/outdated:**

- 把 `04-VERIFICATION.md` 里的 baseline compare smoke 视为当前可信绿灯已经过时；当前仓库的 live targeted run 明确显示该路径红掉了。[VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md][VERIFIED: local test run 2026-04-15]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| `A1` | RESOLVED 2026-04-15：Phase 07 只修新写入路径与健康/fresh workspace 的 compare reopen，不自动迁移或修复历史上已经写坏的真实用户 workspace；这类 workspace 继续通过 rerun、rebaseline 或人工清理处理。[VERIFIED: user revision instructions][VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/REQUIREMENTS.md] | `Resolved Questions`, `Recommended Plan Split`, `07-01/07-02 plans` | 若错误，用户可能需要一个显式 migration/doctor repair 才能重新使用旧 workspace。 |
| `A2` | RESOLVED 2026-04-15：`tests/test_cli_runtime_gap.py`、`tests/test_cli_compare.py` 与 `tests/test_runtime_compare.py` 的 compare gate coverage 在 Phase 07 保留，不在本 phase 做去重；是否合并留到 Phase 8/closeout 再决策。[VERIFIED: user revision instructions][VERIFIED: .planning/ROADMAP.md] | `Validation Architecture`, `Resolved Questions`, `07-02/07-03 plans` | 若错误，Phase 07 的测试面会过于重复，导致后续维护噪音上升。 |

## Open Questions — RESOLVED (2026-04-15)

1. **是否需要处理已经被旧 bug 污染的真实 workspace？**  
   What we know: 当前红测和本地复现都使用 fresh workspace；它们证明“新写入路径”有 bug，但没有回答“历史上已写坏的用户 workspace 是否必须自动修复”。[VERIFIED: local reproduction 2026-04-15][VERIFIED: local test run 2026-04-15]  
   Decision: **RESOLVED — Phase 07 不处理已经被旧 bug 污染的真实 workspace，也不新增 migration/doctor repair。** 本 phase 的范围限定为修复 producer 新写入契约，让修复后的 revision 与 fresh/healthy workspace 重新通过 trusted reopen 和 compare gate。[VERIFIED: user revision instructions][VERIFIED: .planning/REQUIREMENTS.md]  
   Operator consequence: **已经被污染的旧 workspace 不会因为 Phase 07 自动恢复。** 操作者仍可能在 compare/import 上看到 `report_qspec_semantic_hash_mismatch` 或同类 replay-integrity 阻断；要恢复使用，需要 rerun 受影响 revision、重新设置 baseline，或手工清理/重建该 workspace。[VERIFIED: user revision instructions][VERIFIED: src/quantum_runtime/runtime/imports.py][ASSUMED]  
   Plan mapping: 该决策已落到 `07-01` 与 `07-02` 的 objective/success criteria，明确声明只保证修复后的健康路径恢复，不承诺历史污染 workspace 自动自愈。[VERIFIED: .planning/phases/07-compare-trust-closure/07-01-PLAN.md][VERIFIED: .planning/phases/07-compare-trust-closure/07-02-PLAN.md]

2. **Phase 07 是否要顺手合并重复的 compare regression？**  
   What we know: `tests/test_cli_compare.py`、`tests/test_cli_runtime_gap.py`、`tests/test_runtime_compare.py` 都在表达同一条 cross-phase trust closure，只是层级不同。[VERIFIED: tests/test_cli_compare.py:811-876][VERIFIED: tests/test_cli_runtime_gap.py:137-189][VERIFIED: tests/test_runtime_compare.py:410-438]  
   Decision: **RESOLVED — Phase 07 保留现有三层 compare regression coverage，不在本 phase 做测试去重。** `07-02` 继续把这三层 compare 合同绿化，`07-03` 在其之上执行完整 Phase 07 gate 与 exec/import regression hardening。[VERIFIED: user revision instructions][VERIFIED: .planning/ROADMAP.md]  
   Reason: 当前 blocker 是 trust closure 断裂，不是测试组织方式；先保留多层 coverage 能最大化锁住 producer fix、compare policy surface、以及 runtime reopen 三个边界。[VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][VERIFIED: local test run 2026-04-15]  
   Follow-up: 若 Phase 07 完成后仍认为 compare suites 噪音过高，再由 Phase 8/closeout 单独决策是否做去重，不让本 phase 的主修复路径被测试重组干扰。[ASSUMED]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `.venv/bin/python` | 运行 Phase 07 pytest / mypy。[VERIFIED: .planning/config.json][VERIFIED: README.md] | ✓ [VERIFIED: local env 2026-04-15] | `3.11.15`。[VERIFIED: ./.venv/bin/python --version] | `uv run --python 3.11 ...`。[VERIFIED: uv --version] |
| `uv` | 在 host Python 不是 3.11 时跑 repo-consistent validation。[VERIFIED: pyproject.toml][VERIFIED: README.md] | ✓ [VERIFIED: local env 2026-04-15] | `0.11.1`。[VERIFIED: uv --version] | `.venv` 已装好时可直接用 `.venv/bin/python` / `.venv/bin/pytest`。[VERIFIED: local env 2026-04-15] |
| `.venv/bin/pytest` | targeted compare/runtime suites。[VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_runtime_compare.py] | ✓ [VERIFIED: local env 2026-04-15] | `9.0.2`。[VERIFIED: ./.venv/bin/python -m pytest --version] | `uv run --python 3.11 --extra dev --extra qiskit pytest ...`。[VERIFIED: local test run 2026-04-15] |
| `.venv/bin/ruff` | lint gate。[VERIFIED: pyproject.toml][VERIFIED: AGENTS.md] | ✓ [VERIFIED: local env 2026-04-15] | `0.15.8`。[VERIFIED: ./.venv/bin/ruff --version] | host PATH 上没有 `ruff`；改用 `.venv/bin/ruff` 或 `uv run ruff`。[VERIFIED: local env 2026-04-15] |
| `.venv/bin/python -m mypy` | type gate。[VERIFIED: mypy.ini][VERIFIED: AGENTS.md] | ✓ [VERIFIED: local env 2026-04-15] | `1.20.0`。[VERIFIED: ./.venv/bin/python -m mypy --version] | `uv run --python 3.11 mypy src`。[VERIFIED: uv --version][ASSUMED] |
| host `python3` | 直接跑项目命令。[VERIFIED: local env 2026-04-15] | ✓ but wrong version [VERIFIED: local env 2026-04-15] | `3.13.2`。[VERIFIED: python3 --version 2026-04-15] | 不要用于 Phase 07 验证；使用 `.venv` 或 `uv run --python 3.11`。[VERIFIED: pyproject.toml][VERIFIED: ./.venv/bin/python --version] |

**Missing dependencies with no fallback:**

- None in the current workspace for Phase 07 research and validation.[VERIFIED: local env 2026-04-15]

**Missing dependencies with fallback:**

- host PATH 没有 `ruff`，但 `.venv/bin/ruff` 可用。[VERIFIED: local env 2026-04-15]
- host `python3` 版本不满足项目要求，但 `.venv` 与 `uv run --python 3.11` 都可用。[VERIFIED: python3 --version 2026-04-15][VERIFIED: ./.venv/bin/python --version][VERIFIED: uv --version]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest 9.0.2`。[VERIFIED: ./.venv/bin/python -m pytest --version] |
| Config file | `pyproject.toml`。[VERIFIED: pyproject.toml] |
| Quick run command | `./.venv/bin/python -m pytest tests/test_runtime_compare.py tests/test_cli_compare.py tests/test_cli_runtime_gap.py -q --maxfail=1`。[VERIFIED: tests/test_runtime_compare.py][VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_cli_runtime_gap.py][ASSUMED] |
| Full suite command | `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_runtime_compare.py tests/test_cli_exec.py tests/test_runtime_imports.py tests/test_runtime_revision_artifacts.py -q --maxfail=1`。[VERIFIED: pyproject.toml][VERIFIED: mypy.ini][VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_cli_runtime_gap.py][VERIFIED: tests/test_runtime_compare.py][VERIFIED: tests/test_cli_exec.py][VERIFIED: tests/test_runtime_imports.py][VERIFIED: tests/test_runtime_revision_artifacts.py][ASSUMED] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| `POLC-01` | `qrun compare --baseline --fail-on subject_drift --json` 应返回 policy failure (`exit=2`) 而不是 `report_qspec_semantic_hash_mismatch` (`exit=3`)。[VERIFIED: .planning/REQUIREMENTS.md][VERIFIED: local test run 2026-04-15] | integration | `./.venv/bin/python -m pytest tests/test_cli_compare.py::test_qrun_compare_json_baseline_fail_on_subject_drift_returns_failed_gate -q`。[VERIFIED: tests/test_cli_compare.py:811-876] | ✅ [VERIFIED: tests/test_cli_compare.py] |
| `POLC-01` | explicit revision compare `rev_000001` vs `rev_000002` 在 `subject_drift` 上同样返回 compare gate failure，不提前报 trusted import 错误。[VERIFIED: .planning/REQUIREMENTS.md][VERIFIED: local test run 2026-04-15] | integration | `./.venv/bin/python -m pytest tests/test_cli_runtime_gap.py::test_qrun_compare_json_fail_on_subject_drift_returns_failed_gate -q`。[VERIFIED: tests/test_cli_runtime_gap.py:137-189] | ✅ [VERIFIED: tests/test_cli_runtime_gap.py] |
| `POLC-01` | runtime baseline compare 必须能完成 baseline/current resolution 并返回 `different_subject` result，而不是在 `resolve_workspace_current()` 处抛错。[VERIFIED: .planning/REQUIREMENTS.md][VERIFIED: local test run 2026-04-15] | integration | `./.venv/bin/python -m pytest tests/test_runtime_compare.py::test_compare_workspace_baseline_uses_saved_baseline_record -q`。[VERIFIED: tests/test_runtime_compare.py:410-438] | ✅ [VERIFIED: tests/test_runtime_compare.py] |

### Sampling Rate

- **Per task commit:** `./.venv/bin/python -m pytest tests/test_runtime_compare.py tests/test_cli_compare.py tests/test_cli_runtime_gap.py -q --maxfail=1`。[VERIFIED: tests/test_runtime_compare.py][VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_cli_runtime_gap.py][ASSUMED]
- **Per wave merge:** `./.venv/bin/python -m pytest tests/test_cli_exec.py tests/test_runtime_imports.py tests/test_runtime_revision_artifacts.py tests/test_runtime_compare.py tests/test_cli_compare.py tests/test_cli_runtime_gap.py -q --maxfail=1`。[VERIFIED: tests/test_cli_exec.py][VERIFIED: tests/test_runtime_imports.py][VERIFIED: tests/test_runtime_revision_artifacts.py][VERIFIED: tests/test_runtime_compare.py][VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_cli_runtime_gap.py][ASSUMED]
- **Phase gate:** full suite green，再加 Ruff/MyPy 绿色后才能进入 `/gsd-verify-work` 或 Phase 07 closeout。[VERIFIED: .planning/config.json][VERIFIED: pyproject.toml][ASSUMED]

### Wave 0 Gaps

- [ ] `tests/test_runtime_revision_artifacts.py` — 现有 `test_revision_history_artifacts_remain_immutable_after_later_exec()` 只断言 manifest/intent/plan/events 不变，应该升级为显式断言 `rev_000002` 的 qspec/report 语义不同于 `rev_000001`，并与 report/manifest 一致。[VERIFIED: tests/test_runtime_revision_artifacts.py:220-266][VERIFIED: local reproduction 2026-04-15]
- [ ] `tests/test_cli_exec.py` — 现有 `test_qrun_exec_history_report_pins_revision_qspec_after_later_runs()` 只检查 `rev_000001` history report 的 pinned path，应该补一条对 `rev_000002` canonical qspec/report coherence 的断言。[VERIFIED: tests/test_cli_exec.py:360-392][VERIFIED: local reproduction 2026-04-15]
- [ ] 新增一条 exec-side writer regression，直接在两次不同 intent 的 `exec` 后验证 `reports/history/rev_000002.json` 的 `qspec.hash`、`qspec.semantic_hash`、`specs/history/rev_000002.json` 和 run manifest 是同一 revision 的真值，而不是等 compare 才发现问题。[VERIFIED: local reproduction 2026-04-15][ASSUMED]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no。[VERIFIED: codebase grep `auth|authentication|session|login|access control|rbac|permission` in reviewed scope] | none in this local CLI phase scope。[VERIFIED: README.md][VERIFIED: docs/agent-ci-adoption.md][VERIFIED: codebase grep] |
| V3 Session Management | no。[VERIFIED: codebase grep `auth|authentication|session|login|access control|rbac|permission` in reviewed scope] | none in this local CLI phase scope。[VERIFIED: README.md][VERIFIED: docs/agent-ci-adoption.md][VERIFIED: codebase grep] |
| V4 Access Control | no for this phase scope。[VERIFIED: codebase grep `auth|authentication|session|login|access control|rbac|permission` in reviewed scope] | none in this local CLI phase scope。[VERIFIED: README.md][VERIFIED: docs/agent-ci-adoption.md][VERIFIED: codebase grep] |
| V5 Input Validation | yes。[VERIFIED: src/quantum_runtime/runtime/imports.py:91-99][VERIFIED: src/quantum_runtime/runtime/imports.py:752-795][VERIFIED: src/quantum_runtime/runtime/compare.py:91-99][VERIFIED: src/quantum_runtime/cli.py:1525-1543] | `validate_revision()`、Pydantic model validation、JSON payload validation、Typer option parsing。[VERIFIED: src/quantum_runtime/runtime/imports.py][VERIFIED: src/quantum_runtime/runtime/compare.py][VERIFIED: src/quantum_runtime/cli.py] |
| V6 Cryptography | yes。[VERIFIED: src/quantum_runtime/reporters/writer.py:112-170][VERIFIED: src/quantum_runtime/runtime/imports.py:1109-1111][VERIFIED: src/quantum_runtime/runtime/run_manifest.py:447-449] | 现有 SHA-256 digest path；不要 hand-roll 新 integrity scheme。[VERIFIED: src/quantum_runtime/reporters/writer.py][VERIFIED: src/quantum_runtime/runtime/imports.py][VERIFIED: src/quantum_runtime/runtime/run_manifest.py] |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| mutable alias 被写回 canonical history，伪装成合法 revision state。[VERIFIED: local reproduction 2026-04-15] | Tampering | 保持 history-first write contract，禁止 alias -> history 回写，并继续用 replay-integrity/manifest validation 检出真正篡改。[VERIFIED: src/quantum_runtime/runtime/executor.py:218-224][VERIFIED: src/quantum_runtime/reporters/writer.py:92-109][VERIFIED: src/quantum_runtime/runtime/imports.py:590-711][VERIFIED: src/quantum_runtime/runtime/run_manifest.py:143-248] |
| report file / relocated workspace 路径混淆导致 compare 读取错误 qspec。[VERIFIED: tests/test_runtime_imports.py:205-222][VERIFIED: tests/test_runtime_imports.py:376-426] | Spoofing / Tampering | 继续使用 `canonicalize_artifact_provenance()` 与 candidate-root resolution，不信任裸路径字符串。[VERIFIED: src/quantum_runtime/artifact_provenance.py][VERIFIED: src/quantum_runtime/runtime/imports.py:233-279][VERIFIED: src/quantum_runtime/runtime/imports.py:798-861] |
| compare/latest 或 compare/history 写入被中断，后续 CI 读取到半写文件。[VERIFIED: .planning/phases/03-concurrent-workspace-safety/03-concurrent-workspace-safety-04-SUMMARY.md][VERIFIED: src/quantum_runtime/runtime/compare.py:251-276] | Repudiation / Tampering | `acquire_workspace_lock()` + `pending_atomic_write_files()` + `atomic_write_text()`，并保留 `schema_version`。[VERIFIED: src/quantum_runtime/runtime/compare.py:251-276][VERIFIED: src/quantum_runtime/runtime/contracts.py:142-160] |

## Sources

### Primary (HIGH confidence)

- `AGENTS.md` - 项目约束、技术栈、架构和 GSD workflow 约束。[VERIFIED: AGENTS.md]
- `.planning/ROADMAP.md` - Phase 07 目标、依赖和 gap closure 范围。[VERIFIED: .planning/ROADMAP.md]
- `.planning/REQUIREMENTS.md` - `POLC-01` 的正式 requirement 文本。[VERIFIED: .planning/REQUIREMENTS.md]
- `.planning/STATE.md` - 当前已知 blocker，明确记录 `report_qspec_semantic_hash_mismatch` 仍在阻塞 compare gap test。[VERIFIED: .planning/STATE.md]
- `.planning/v1.0-MILESTONE-AUDIT.md` - `POLC-01` / `INT-01` / `FLOW-01` 的缺口描述与 cross-phase seam 定位。[VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md]
- `.planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md` - 旧的 Phase 4 baseline compare pass claim，与 live run 对照可确认其已过时。[VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md]
- `.planning/phases/02-trusted-revision-artifacts/02-RESEARCH.md` and `02-VERIFICATION.md` - Phase 2 trust model 与 revision artifact contract 的既有承诺。[VERIFIED: .planning/phases/02-trusted-revision-artifacts/02-RESEARCH.md][VERIFIED: .planning/phases/02-trusted-revision-artifacts/02-VERIFICATION.md]
- `src/quantum_runtime/runtime/executor.py` - history-first exec graph、manifest timing、alias promotion timing。[VERIFIED: src/quantum_runtime/runtime/executor.py]
- `src/quantum_runtime/reporters/writer.py` - root cause 所在的 alias -> canonical copy 行为。[VERIFIED: src/quantum_runtime/reporters/writer.py]
- `src/quantum_runtime/runtime/imports.py` - trusted import / replay integrity / semantic mismatch fail-closed 行为。[VERIFIED: src/quantum_runtime/runtime/imports.py]
- `src/quantum_runtime/runtime/compare.py` - baseline compare composition、policy verdict 和 compare persistence。[VERIFIED: src/quantum_runtime/runtime/compare.py]
- `src/quantum_runtime/runtime/run_manifest.py` - manifest build/validation 范围与为何未先发现此 seam。[VERIFIED: src/quantum_runtime/runtime/run_manifest.py]
- `tests/test_cli_compare.py`, `tests/test_cli_runtime_gap.py`, `tests/test_runtime_compare.py`, `tests/test_cli_exec.py`, `tests/test_runtime_imports.py`, `tests/test_runtime_revision_artifacts.py` - 当前 contract、红测和缺失的 exec-side coherence coverage。[VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_cli_runtime_gap.py][VERIFIED: tests/test_runtime_compare.py][VERIFIED: tests/test_cli_exec.py][VERIFIED: tests/test_runtime_imports.py][VERIFIED: tests/test_runtime_revision_artifacts.py]
- 本地复现：两次不同 intent 的 `exec` 后，`rev_000002` 的 qspec history 被旧 GHZ 内容覆盖，且 compare/baseline 相关三条红测实际失败。[VERIFIED: local reproduction 2026-04-15][VERIFIED: local test run 2026-04-15]

### Secondary (MEDIUM confidence)

- None. 本次研究没有依赖外部非官方资料。[VERIFIED: research process 2026-04-15]

### Tertiary (LOW confidence)

- None. 本次研究中的不确定项已经单独列入 `Assumptions Log`。[VERIFIED: research process 2026-04-15]

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - Phase 07 不引入新依赖，现有 stack 与本地 `.venv` 环境都已核对。[VERIFIED: AGENTS.md][VERIFIED: pyproject.toml][VERIFIED: ./.venv/bin/python --version][VERIFIED: ./.venv/bin/ruff --version][VERIFIED: ./.venv/bin/python -m mypy --version][VERIFIED: ./.venv/bin/python -m pytest --version]
- Architecture: HIGH - 已完成代码路径追踪、最小复现，并确认 root cause 在 writer/executor seam 而不是 compare policy。[VERIFIED: src/quantum_runtime/runtime/executor.py][VERIFIED: src/quantum_runtime/reporters/writer.py][VERIFIED: src/quantum_runtime/runtime/imports.py][VERIFIED: src/quantum_runtime/runtime/compare.py][VERIFIED: local reproduction 2026-04-15]
- Pitfalls: HIGH - 关键 pitfall 都能用现有红测或本地复现直接证明。[VERIFIED: local test run 2026-04-15][VERIFIED: local reproduction 2026-04-15]

**Research date:** 2026-04-15 [VERIFIED: system date]  
**Valid until:** 2026-04-22；这是一条活跃的跨阶段 seam，建议在 7 天内完成计划与实现，避免后续分支继续漂移。[ASSUMED]
