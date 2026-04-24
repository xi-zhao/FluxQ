---
phase: 10-canonical-remote-submit-attempt-records
verified: 2026-04-18T15:40:00Z
status: human_needed
score: 8/8 must-haves verified
overrides_applied: 0
human_verification_approved: false
human_verification:
  - test: "在已执行 `uv sync --extra ibm`、持有有效 `QISKIT_IBM_TOKEN`、显式 IBM instance CRN 和可用 backend 的环境里运行 `qrun remote submit --workspace <path> --backend <backend> --intent-file examples/intent-ghz.md --json`"
    expected: "命令返回 `status=ok`、稳定 `attempt_id`、provider `job.id`、显式 `backend.instance`，并在 `.quantum/remote/...` 持久化 attempt record 与 submit-time snapshots，同时不改写 `reports/latest.json` 或 `manifests/latest.json`"
    why_human: "需要真实 IBM Quantum Platform 凭证、实例权限、远端作业提交能力与可能的花费；仓库自动化只覆盖 mocked submit 路径"
  - test: "在同一受信环境中运行 `qrun remote submit --workspace <path> --backend <backend> --intent-file examples/intent-ghz.md --jsonl`"
    expected: "JSONL 输出包含 `submit_started`、`submit_persisted`、`submit_completed`，并与 JSON 模式共享相同的 reason-code / decision vocabulary，且不泄露 token 或 Authorization 信息"
    why_human: "需要真实 provider job-mode submit 与事件流落地验证；自动化只验证 mocked provider / persistence failures"
---

# Phase 10: Canonical Remote Submit & Attempt Records Verification Report

**Phase Goal:** Users can submit canonical FluxQ runtime objects to IBM Quantum Platform and immediately receive a durable local remote attempt record.  
**Verified:** 2026-04-18T15:40:00Z  
**Status:** human_needed

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Users can submit through the same prompt / markdown / structured JSON / `QSpec` / report-backed ingress surface used locally. | ✓ VERIFIED | `src/quantum_runtime/runtime/remote_submit.py` calls `resolve_runtime_input()` directly, and `tests/test_cli_remote_submit.py` covers prompt text, report file, and revision-backed submit paths along with the exact-one-input contract. |
| 2 | Remote attempt identity is separate from immutable terminal revision identity. | ✓ VERIFIED | `src/quantum_runtime/workspace/manifest.py` adds `current_attempt` plus `next_attempt()` / `bump_attempt()` without reusing `current_revision`; `tests/test_runtime_remote_attempts.py` verifies no revision bump on submit persistence. |
| 3 | Submit-time persistence writes canonical `.quantum/remote/...` artifacts and leaves finalized report/manifest aliases untouched. | ✓ VERIFIED | `src/quantum_runtime/runtime/remote_attempts.py` persists `qspec.json`, `intent.json`, `plan.json`, `submit_payload.json`, history/latest attempt records; `tests/test_runtime_remote_attempts.py` and `tests/test_cli_remote_submit.py` assert `reports/latest.json` and `manifests/latest.json` remain unchanged. |
| 4 | The user-facing submit command is `qrun remote submit` and enforces explicit backend selection. | ✓ VERIFIED | `src/quantum_runtime/cli.py` exposes the `remote` Typer namespace and `submit` command; blank backend values now raise `remote_backend_required` and `tests/test_cli_remote_submit.py` locks the exit-code / payload contract. |
| 5 | IBM submit uses explicit backend lookup and V2 primitive job mode instead of `least_busy()` or deprecated `backend.run()`. | ✓ VERIFIED | `src/quantum_runtime/runtime/ibm_remote_submit.py` uses explicit `service.backend(...)`, `SamplerV2`, and transpilation against the selected backend; `tests/test_cli_remote_submit.py` asserts `backend.run()` and `least_busy()` are not used. |
| 6 | Successful submit immediately yields a durable local attempt record with provider job handle, backend, instance, and canonical provenance. | ✓ VERIFIED | `src/quantum_runtime/runtime/remote_submit.py` returns `RemoteSubmitResult` with `attempt_id`, `job`, `backend`, `input`, `qspec`, and artifact paths; `tests/test_cli_remote_submit.py` confirms the persisted record and provider status. |
| 7 | Blocked submit paths and JSON/JSONL success paths share one fail-closed machine vocabulary. | ✓ VERIFIED | `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/runtime/observability.py`, and `src/quantum_runtime/runtime/remote_submit.py` emit shared `reason_codes`, `next_actions`, `gate` / `decision`, and `submit_*` lifecycle events; `tests/test_cli_observability.py` verifies JSON / JSONL parity plus recovery-handle preservation. |
| 8 | Phase 10 remains scoped to submit-time persistence only and does not finalize remote results or add lifecycle reopen/cancel flows. | ✓ VERIFIED | No Phase 10 file writes `reports/history/rev_*.json` for remote submit or adds lifecycle commands; the shipped surface ends at submit + attempt record, matching the roadmap boundary. |

**Score:** 8/8 truths verified

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Phase 10 focused regression suite | `uv run pytest tests/test_runtime_remote_attempts.py tests/test_cli_remote_submit.py tests/test_cli_backend_list.py tests/test_cli_observability.py -q --maxfail=1` | `57 passed in 3.65s` | ✓ PASS |
| Phase 09 regression gate | `uv run pytest tests/test_cli_ibm_config.py tests/test_cli_backend_list.py tests/test_cli_doctor.py tests/test_cli_observability.py -q --maxfail=1` | `55 passed in 3.42s` | ✓ PASS |
| Lint gate | `uv run ruff check src tests` | `All checks passed!` | ✓ PASS |
| Type gate | `uv run python -m mypy src` | `Success: no issues found in 58 source files` | ✓ PASS |
| Code review gate | `10-REVIEW.md` | `status: clean`, `0 findings` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `REMT-01` | `10-01`, `10-02`, `10-03` | User can submit a canonical run through the same ingress and `QSpec` surface used locally | ✓ SATISFIED | `src/quantum_runtime/runtime/remote_submit.py`, `src/quantum_runtime/cli.py`, and `tests/test_cli_remote_submit.py` cover canonical ingress reuse and explicit remote submit wiring. |
| `REMT-02` | `10-01`, `10-02`, `10-03` | User receives a persisted FluxQ remote attempt record with provider job handle, backend, instance, and submit-time provenance immediately after successful submission | ✓ SATISFIED | `src/quantum_runtime/runtime/remote_attempts.py`, `src/quantum_runtime/runtime/remote_submit.py`, and `tests/test_runtime_remote_attempts.py` / `tests/test_cli_remote_submit.py` cover attempt persistence, provider handle capture, and blocked recovery payloads. |

No orphaned Phase 10 requirement IDs were found. All plan frontmatter and the delivered code account for both `REMT-01` and `REMT-02`.

## Human Verification Required

### 1. Live Env-Token IBM Submit Smoke

**Test:** In an environment with `uv sync --extra ibm`, a valid `QISKIT_IBM_TOKEN`, an explicit IBM instance CRN, and a usable IBM backend, run:

```bash
uv run qrun remote submit \
  --workspace <path> \
  --backend <backend> \
  --intent-file examples/intent-ghz.md \
  --json
```

**Expected:** The command returns `status=ok`, a stable `attempt_id`, provider `job.id`, explicit `backend.instance`, and durable `.quantum/remote/...` artifacts without rewriting `reports/latest.json` or `manifests/latest.json`.

**Why human:** This requires real IBM credentials, instance access, network connectivity, and a spend-bearing provider submission path.

### 2. Live IBM Submit JSONL Smoke

**Test:** In the same environment, run:

```bash
uv run qrun remote submit \
  --workspace <path> \
  --backend <backend> \
  --intent-file examples/intent-ghz.md \
  --jsonl
```

**Expected:** The event stream emits `submit_started`, `submit_persisted`, and `submit_completed`; the completion payload matches the JSON-mode vocabulary and does not leak token or authorization material.

**Why human:** This validates the real provider-side lifecycle event path, which automated tests only simulate with mocked submit seams.

## Gaps Summary

No code-level gaps remain. Automated verification, regression checks, and code review all pass. The only remaining work is live IBM human verification of the real remote submit path.

---

_Verified: 2026-04-18T15:40:00Z_  
_Verifier: Codex (local fallback after gsd-verifier timeout)_
