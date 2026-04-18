---
phase: 09-ibm-access-backend-readiness
verified: 2026-04-18T07:02:46Z
status: human_needed
score: 8/8 must-haves verified
overrides_applied: 0
human_verification:
  - test: "在安装 `uv sync --extra ibm` 且持有有效 `QISKIT_IBM_TOKEN` 与 IBM instance CRN 的环境里运行 `qrun ibm configure`、`qrun backend list --json`、`qrun doctor --json --ci`"
    expected: "`.quantum/qrun.toml` 只保存非 secret IBM 引用；`backend list` 返回真实 IBM target 与 readiness；`doctor.gate.ready=true` 或在实例/授权失配时以 IBM-specific reason fail-closed"
    why_human: "需要真实 IBM Quantum Platform 凭证、实例权限、可选 extra 和网络访问；仓库自动化只覆盖 mocked 路径与 missing-extra 退化路径"
  - test: "在 trusted machine 上用已存在的 IBM saved account 名称运行 `qrun ibm configure --credential-mode saved_account ...` 后执行 `qrun doctor --json --ci` 与 `qrun backend list --json`"
    expected: "saved-account 模式可在不持久化 token 的前提下解析真实账号，并继续输出相同的 IBM reason codes、next actions 与 readiness 结构"
    why_human: "saved-account 文件位于用户主目录，依赖真实本地 IBM account 状态，仓库内自动化无法安全构造"
---

# Phase 09: IBM Access & Backend Readiness Verification Report

**Phase Goal:** Users can establish explicit IBM Quantum Platform access and validate remote backend readiness before FluxQ submits any canonical run.
**Verified:** 2026-04-18T07:02:46Z
**Status:** human_needed
**Re-verification:** No — refreshed full verification; previous report had no `gaps:` section

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | 用户可以非交互式配置 IBM Quantum Platform 凭证引用和显式 instance 选择。 | ✓ VERIFIED | `src/quantum_runtime/cli.py:829-917` defines `ibm configure`, validates the credential-mode / instance contract, and calls `write_ibm_profile()`. `tests/test_cli_ibm_config.py:170-344` covers `env` / `saved_account` success and failure paths. Direct spot-check `uv run qrun ibm configure --json` returned `status=ok` with the configured instance and token env name only. |
| 2 | `.quantum/qrun.toml` 只持久化非 secret IBM access 引用，不保存 token 本体。 | ✓ VERIFIED | `src/quantum_runtime/runtime/ibm_access.py:96-117` writes `profile.model_dump(..., exclude_none=True)` into `[remote.ibm]`. `tests/test_cli_ibm_config.py:26-67,170-211` asserts raw token absence. Direct spot-check produced a `qrun.toml` containing only `channel`, `credential_mode`, `instance`, and `token_env`. |
| 3 | 仓库安装面通过 optional `ibm` extra 暴露 `qiskit-ibm-runtime~=0.46`。 | ✓ VERIFIED | `pyproject.toml:24-31` declares `[project.optional-dependencies].ibm = ["qiskit-ibm-runtime~=0.46"]`. `tests/test_cli_ibm_config.py:162-167` verifies the exact extra value. |
| 4 | 用户可以在提交前通过 `qrun backend list --json --workspace <path>` 查看 IBM remote inventory。 | ✓ VERIFIED | `src/quantum_runtime/cli.py:1837-1855` passes `--workspace` into `list_backends(workspace_root=...)`. `src/quantum_runtime/runtime/backend_list.py:27-147` returns a top-level `remote` block plus backend descriptors. `tests/test_cli_backend_list.py:130-209` covers workspace-aware CLI wiring, IBM descriptor presence, and no auto-selection fields. |
| 5 | backend discovery 会给出足够的 readiness 细节，让用户判断一个 pinned backend 当前是否可用。 | ✓ VERIFIED | `src/quantum_runtime/runtime/backend_list.py:198-230` projects `name`, `operational`, `status_msg`, `pending_jobs`, `num_qubits`, `backend_version`, and a nested `readiness` block for each target. `tests/test_cli_backend_list.py:212-304` covers ready and blocked paths. Direct CLI spot-check, in an env without the IBM extra, still returned a readable blocked `remote.readiness` payload with `ibm_runtime_dependency_missing`. |
| 6 | `doctor --json --ci` 只在显式 opt-in 的 `[remote.ibm]` workspace 上检查 IBM 访问面，并对未就绪状态 fail-close。 | ✓ VERIFIED | `src/quantum_runtime/runtime/doctor.py:344-386` gates IBM checks on `[remote.ibm]`, resolves access via `resolve_ibm_access()`, and fails closed on unresolved access or service construction failures. `tests/test_cli_doctor.py:384-514` covers missing token env, skip without opt-in, and missing IBM runtime dependency. Direct CLI spot-check returned exit code `2` with `gate.ready=false` and `ibm_runtime_dependency_missing`. |
| 7 | IBM doctor 的 JSON 与 JSONL 输出共享同一组 IBM reason codes、next actions 与 gate 语义。 | ✓ VERIFIED | `src/quantum_runtime/runtime/policy.py:81-142,407-436` preserves provider-specific reason codes and derives next actions from them. `src/quantum_runtime/runtime/observability.py:63-105` maps IBM reason codes to shared action names. `src/quantum_runtime/cli.py:1810-1832` emits `doctor_completed` from the same `DoctorReport`. `tests/test_cli_observability.py:509-627` verifies JSON/JSONL parity and redaction. |
| 8 | Wave 2 的 `doctor` / `backend list` 通过显式 IBM service factory seam 复用 access 解析，而不是各自直接导入 IBM SDK。 | ✓ VERIFIED | `src/quantum_runtime/runtime/doctor.py:348-360` and `src/quantum_runtime/runtime/backend_list.py:51-83` both call `resolve_ibm_access()` and `build_ibm_service()`. Repository-wide search found `qiskit_ibm_runtime` usage only in `src/quantum_runtime/runtime/ibm_access.py:285-297` plus the capability registry’s dependency probe in `src/quantum_runtime/runtime/backend_registry.py:40-47`; neither `doctor.py` nor `backend_list.py` imports the IBM SDK directly. |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `pyproject.toml` | IBM optional extra | ✓ VERIFIED | `pyproject.toml:24-31` contains `ibm = ["qiskit-ibm-runtime~=0.46"]`. |
| `src/quantum_runtime/runtime/ibm_access.py` | IBM profile persistence, access resolution, and service factory seam | ✓ VERIFIED | `src/quantum_runtime/runtime/ibm_access.py:31-81` defines `IbmAccessProfile`, `IbmAccessResolution`, and `IbmConfigureResult`; `:84-241` implements load/write/resolve/build logic; `:285-297` centralizes optional IBM SDK loading. |
| `tests/test_cli_ibm_config.py` | IBM configure and non-secret persistence regression coverage | ✓ VERIFIED | `tests/test_cli_ibm_config.py:26-67` validates non-secret persistence, `:117-160` validates the service seam, and `:170-456` exercises the CLI success and failure paths. `gsd-tools verify artifacts` reported a false negative because it searched for the literal string `qrun ibm configure`; the file drives the command via split argv `["ibm", "configure", ...]`, and the substantive coverage is present. |
| `src/quantum_runtime/runtime/contracts.py` | Stable IBM remediation vocabulary | ✓ VERIFIED | `src/quantum_runtime/runtime/contracts.py:35-58` includes `ibm_config_invalid`, `ibm_instance_required`, `ibm_token_external_required`, `ibm_profile_missing`, `ibm_instance_unset`, `ibm_token_env_missing`, `ibm_saved_account_missing`, `ibm_runtime_dependency_missing`, and `ibm_access_unresolved`. |
| `src/quantum_runtime/runtime/doctor.py` | IBM auth/profile doctor gate | ✓ VERIFIED | `src/quantum_runtime/runtime/doctor.py:93-120,344-458` adds IBM gate generation, issue mapping, and fail-closed behavior. |
| `src/quantum_runtime/runtime/policy.py` | IBM-specific doctor reason-code preservation | ✓ VERIFIED | `src/quantum_runtime/runtime/policy.py:95-105,128-142,407-436` merges provider-specific IBM reason codes into the CI gate instead of flattening them away. |
| `src/quantum_runtime/runtime/observability.py` | Shared IBM next-action vocabulary | ✓ VERIFIED | `src/quantum_runtime/runtime/observability.py:63-105` maps IBM reason codes to `configure_ibm_profile`, `set_ibm_token_env`, `verify_ibm_saved_account`, and `install_ibm_extra`. |
| `tests/test_cli_doctor.py` | IBM doctor CI regressions | ✓ VERIFIED | `tests/test_cli_doctor.py:384-514` covers fail-closed missing token env, skip without opt-in, and missing-runtime dependency behavior. |
| `tests/test_cli_observability.py` | IBM doctor JSON/JSONL parity and redaction | ✓ VERIFIED | `tests/test_cli_observability.py:509-627` verifies shared IBM reason codes, next actions, gate parity, and absence of secret material in JSONL output. |
| `src/quantum_runtime/runtime/backend_registry.py` | IBM runtime backend descriptor | ✓ VERIFIED | `src/quantum_runtime/runtime/backend_registry.py:72-93` publishes the readiness-only `ibm-runtime` descriptor with `remote_readiness=true` and `remote_submit=false`. |
| `src/quantum_runtime/runtime/backend_list.py` | Workspace-aware backend list and IBM readiness payload | ✓ VERIFIED | `src/quantum_runtime/runtime/backend_list.py:27-230` builds the `remote` summary, blocked fallbacks, and per-target readiness details. |
| `tests/test_cli_backend_list.py` | IBM backend-list readiness regressions | ✓ VERIFIED | `tests/test_cli_backend_list.py:130-304` covers workspace routing, descriptor contents, no auto-selection fields, target projection, and blocked IBM-service fallback. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `src/quantum_runtime/cli.py` | `src/quantum_runtime/runtime/ibm_access.py` | `qrun ibm configure` -> `write_ibm_profile()` | ✓ WIRED | `src/quantum_runtime/cli.py:904-908` calls `write_ibm_profile()` with the validated `IbmAccessProfile`. |
| `src/quantum_runtime/runtime/ibm_access.py` | `.quantum/qrun.toml` | `WorkspacePaths.qrun_toml` | ✓ WIRED | `src/quantum_runtime/runtime/ibm_access.py:86,107-117` loads and rewrites `qrun.toml` through `WorkspacePaths`. |
| `src/quantum_runtime/runtime/doctor.py` | `src/quantum_runtime/runtime/ibm_access.py` | `resolve_ibm_access()` + `build_ibm_service()` | ✓ WIRED | `src/quantum_runtime/runtime/doctor.py:348-360` resolves the profile and builds the IBM service seam. |
| `src/quantum_runtime/runtime/doctor.py` | `src/quantum_runtime/runtime/policy.py` | `apply_doctor_policy()` | ✓ WIRED | `src/quantum_runtime/runtime/doctor.py:116-120` runs the CI gate projection on the assembled `DoctorReport`. |
| `src/quantum_runtime/runtime/policy.py` | `src/quantum_runtime/runtime/observability.py` | `_doctor_next_actions()` -> `next_actions_for_reason_codes()` | ✓ WIRED | `src/quantum_runtime/runtime/policy.py:101-105,413-416` delegates IBM next-action derivation to `observability.py:63-105`. |
| `src/quantum_runtime/cli.py` | `src/quantum_runtime/runtime/backend_list.py` | `backend list --workspace` -> `list_backends(workspace_root=...)` | ✓ WIRED | `src/quantum_runtime/cli.py:1837-1853` passes the selected workspace root to `list_backends()`. |
| `src/quantum_runtime/runtime/backend_list.py` | `src/quantum_runtime/runtime/ibm_access.py` | `resolve_ibm_access()` + `build_ibm_service()` | ✓ WIRED | `src/quantum_runtime/runtime/backend_list.py:51-83` reuses the shared IBM access seam instead of loading the IBM SDK directly. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `src/quantum_runtime/runtime/ibm_access.py` | `[remote.ibm]` profile block | `qrun ibm configure` -> `write_ibm_profile()` -> `qrun.toml` -> `resolve_ibm_access()` | Direct CLI spot-check wrote a real `[remote.ibm]` block containing only non-secret fields, and `resolve_ibm_access()` uses that block as its single source of truth. | ✓ FLOWING |
| `src/quantum_runtime/runtime/doctor.py` | `ibm_reason_codes` and CI gate | `_ibm_doctor_findings()` -> `resolve_ibm_access()` / `build_ibm_service()` -> `apply_doctor_policy()` | Direct CLI spot-check on a configured temp workspace produced a real fail-closed doctor payload with `ibm_runtime_dependency_missing` and `next_actions=["install_ibm_extra"]`; `tests/test_cli_doctor.py` covers additional fail-closed branches. | ✓ FLOWING |
| `src/quantum_runtime/runtime/backend_list.py` | `remote` summary and `targets[*].readiness` | `_ibm_remote_summary()` -> `resolve_ibm_access()` -> `build_ibm_service().backends()` or blocked fallback | `tests/test_cli_backend_list.py:212-304` proves the code projects dynamic target attributes from a service object, while the direct CLI spot-check proves the blocked fallback path emits a readable reason-coded payload instead of static placeholders. | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Phase 09 regression suite | `uv run pytest tests/test_cli_ibm_config.py tests/test_cli_backend_list.py tests/test_cli_doctor.py tests/test_cli_observability.py -q --maxfail=1` | `48 passed in 3.26s` | ✓ PASS |
| Lint gate | `uv run ruff check src tests` | `All checks passed!` | ✓ PASS |
| Type gate | `uv run python -m mypy src` | `Success: no issues found in 55 source files` | ✓ PASS |
| Real CLI degraded-path probe | `uv run qrun init` + `uv run qrun ibm configure --json` + `uv run qrun backend list --json` + `uv run qrun doctor --json --ci` on a temp workspace | `qrun.toml` contained only non-secret IBM references; `backend list` returned `remote.status="blocked"` with `ibm_runtime_dependency_missing`; `doctor` exited `2` with `gate.ready=false` and `recommended_action="install_ibm_extra"` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `AUTH-01` | `09-01`, `09-02` | User can configure IBM Quantum Platform credentials and instance selection non-interactively for local agents and CI | ✓ SATISFIED | `src/quantum_runtime/cli.py:829-917`, `src/quantum_runtime/runtime/ibm_access.py:96-241`, `src/quantum_runtime/runtime/doctor.py:344-386`, `tests/test_cli_ibm_config.py`, `tests/test_cli_doctor.py`, and `tests/test_cli_observability.py` cover configuration, persistence, and CI gating. |
| `BACK-01` | `09-03` | User can list compatible remote backends and see readiness details before remote submission | ✓ SATISFIED | `src/quantum_runtime/cli.py:1837-1855`, `src/quantum_runtime/runtime/backend_registry.py:72-93`, `src/quantum_runtime/runtime/backend_list.py:27-230`, and `tests/test_cli_backend_list.py:130-304` cover backend inventory, provider context, per-target readiness, and blocked fallback behavior. |

No orphaned Phase 09 requirement IDs were found. The plan frontmatter accounts for both requested IDs, `AUTH-01` and `BACK-01`, and `REQUIREMENTS.md` does not assign any other requirement IDs to Phase 9.

### Anti-Patterns Found

No blocker- or warning-level anti-patterns were found in the Phase 09 implementation files. One bookkeeping drift remains:

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `.planning/ROADMAP.md` | `11,13,35,104` | Current-status and progress bookkeeping still say Phase 9 is “ready to plan”, unchecked, and `0/3 Not started`, despite all three plans and summaries existing and this verification confirming the implementation | ℹ️ Info | Does not block Phase 09 goal achievement, but the roadmap state is stale relative to the codebase and phase directory |

### Human Verification Required

### 1. Live Env-Token IBM Smoke

**Test:** 在已执行 `uv sync --extra ibm`、持有有效 `QISKIT_IBM_TOKEN` 和 IBM instance CRN 的环境里，运行 `qrun init --workspace <path>`，然后运行 `qrun ibm configure --credential-mode env --token-env QISKIT_IBM_TOKEN --instance <crn> --workspace <path> --json`、`qrun backend list --json --workspace <path>`、`qrun doctor --json --ci --workspace <path>`。  
**Expected:** `qrun.toml` 只包含 `channel` / `credential_mode` / `instance` / `token_env` 等非 secret 字段；`backend list` 返回真实 IBM target 与 readiness 细节；`doctor.gate.ready=true`，或在 IBM 拒绝该实例时给出 IBM-specific fail-closed reason。  
**Why human:** 需要真实 IBM Quantum Platform 凭证、实例授权、IBM optional extra 与网络访问；当前自动化只验证 mocked 路径和 missing-extra blocked fallback。  

### 2. Live Saved-Account IBM Smoke

**Test:** 在 trusted machine 上，先确保本机已经存在 IBM saved account，然后运行 `qrun ibm configure --credential-mode saved_account --saved-account-name <name> --instance <crn> --workspace <path> --json`，再运行 `qrun doctor --json --ci --workspace <path>` 和 `qrun backend list --json --workspace <path>`。  
**Expected:** FluxQ 可解析真实 saved account，而不把 token 写入 `.quantum/`；输出继续保留相同的 IBM reason codes、next actions 与 readiness 结构；如 saved account 与 instance 不匹配，则以 IBM-specific reason fail-closed。  
**Why human:** saved-account 文件位于用户主目录并依赖真实本地 IBM account state，仓库自动化无法安全构造或审计。  

### Gaps Summary

没有发现阻断 Phase 09 目标的代码级 gaps。当前未完成的是外部 IBM 集成人工验收，以及一个不影响功能正确性的 ROADMAP 台账漂移。

---

_Verified: 2026-04-18T07:02:46Z_  
_Verifier: Codex (gsd-verifier)_
