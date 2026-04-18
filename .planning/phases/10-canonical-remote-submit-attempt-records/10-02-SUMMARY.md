---
phase: 10-canonical-remote-submit-attempt-records
plan: "02"
subsystem: runtime
tags: [python, typer, qiskit, ibm, remote-submit, workspace]
requires:
  - phase: 10-01
    provides: remote attempt persistence and additive attempt identities
provides:
  - canonical `qrun remote submit` command with exec-parity ingress selectors
  - IBM Runtime job-mode submit adapter using explicit backend lookup and `SamplerV2`
  - immediate local attempt records with provider job status, backend instance, and canonical hashes
affects: [10-03, remote-submit, ibm, cli]
tech-stack:
  added: []
  patterns:
    - canonical remote submit reuses `resolve_runtime_input()` before any provider call
    - IBM submit stays behind one adapter seam with explicit `service.backend(...)` lookup
    - remote submit persists attempt records without mutating finalized report or manifest aliases
key-files:
  created:
    - src/quantum_runtime/runtime/ibm_remote_submit.py
    - src/quantum_runtime/runtime/remote_submit.py
  modified:
    - src/quantum_runtime/cli.py
    - src/quantum_runtime/runtime/contracts.py
    - src/quantum_runtime/runtime/backend_registry.py
    - src/quantum_runtime/runtime/__init__.py
    - src/quantum_runtime/runtime/remote_attempts.py
    - tests/test_cli_remote_submit.py
    - tests/test_cli_backend_list.py
key-decisions:
  - "Expose remote submit as `qrun remote submit` while keeping IBM SDK usage isolated in `ibm_remote_submit.py`."
  - "Treat submit-time provider status as part of the durable attempt record, but keep `reports/latest.json` and `manifests/latest.json` unchanged until later finalization phases."
  - "Keep remote submit fail-closed and machine-readable by adding explicit remediation codes for missing backend selection and backend lookup failure."
patterns-established:
  - "CLI remote submit mirrors exec's one-input validation and workspace-safety error handling."
  - "Provider submit adapters may return models or mappings; orchestration normalizes them before persistence."
requirements-completed: [REMT-01, REMT-02]
duration: 12min
completed: 2026-04-18
---

# Phase 10 Plan 02: Canonical Remote Submit Summary

**Canonical `qrun remote submit` over exec-parity ingress, IBM job-mode `SamplerV2`, and durable local attempt records with provider job status**

## Performance

- **Duration:** 12 min
- **Started:** 2026-04-18T14:48:51Z
- **Completed:** 2026-04-18T15:00:54Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Added a canonical runtime submit seam that reuses `resolve_runtime_input()` for prompt text, markdown intents, JSON intents, `QSpec`, report files, and revisions.
- Added an IBM adapter that uses explicit `service.backend(...)` lookup plus `SamplerV2` job mode and persists the provider job status alongside the job ID.
- Added `qrun remote submit` with exec-parity input validation, structured JSON output, workspace-safety passthrough, and regression coverage proving finalized aliases remain untouched.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add canonical remote-submit orchestration and IBM job-mode adapter** - `d40697b` (`test`), `cec5eb4` (`feat`)
2. **Task 2: Add the `qrun remote submit` CLI surface with exec-parity inputs** - `ae12546` (`test`), `6550289` (`feat`)

**Additional auto-fix:** `b18ce2e` (`fix`) for post-task verification cleanup

## Files Created/Modified

- `src/quantum_runtime/runtime/remote_submit.py` - canonical remote-submit orchestration and machine-readable submit result payload.
- `src/quantum_runtime/runtime/ibm_remote_submit.py` - IBM Runtime job-mode submit adapter using explicit backend lookup and `SamplerV2`.
- `src/quantum_runtime/cli.py` - `remote` Typer namespace, `remote submit` command, and structured remote-submit error handling.
- `src/quantum_runtime/runtime/remote_attempts.py` - extends remote attempt job records to persist the initial provider job status.
- `src/quantum_runtime/runtime/backend_registry.py` - flips IBM `remote_submit` capability to `True`.
- `src/quantum_runtime/runtime/contracts.py` - adds structured remediation text for explicit backend selection and backend lookup failure.
- `src/quantum_runtime/runtime/__init__.py` - exports the remote submit orchestration seam from the runtime barrel.
- `tests/test_cli_remote_submit.py` - runtime and CLI regressions for canonical submit inputs, workspace safety, blank backend rejection, and alias immutability.
- `tests/test_cli_backend_list.py` - updates IBM backend capability expectations for the newly shipped remote submit surface.

## Decisions Made

- `qrun remote submit` is the user-facing surface, but provider mechanics stay isolated behind `submit_ibm_job()` so later lifecycle phases do not leak SDK details into CLI code.
- Submit success is modeled as a local attempt record, not a finalized revision, preserving the existing trust boundary around completed local reports and manifests.
- Remote submit errors remain schema-driven: explicit backend validation and backend lookup failures now have stable remediation text instead of falling back to generic runtime errors.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Persisted provider job status on remote attempts**
- **Found during:** Task 1 (Add canonical remote-submit orchestration and IBM job-mode adapter)
- **Issue:** Phase 10 required capture of the initial provider status, but the 10-01 remote attempt schema only stored `job.id`.
- **Fix:** Extended `RemoteAttemptJob` with an optional `status` field and persisted the initial provider status with every successful submit.
- **Files modified:** `src/quantum_runtime/runtime/remote_attempts.py`
- **Verification:** `uv run pytest tests/test_cli_remote_submit.py -k 'submit or backend' -q --maxfail=1`
- **Committed in:** `cec5eb4`

**2. [Rule 2 - Missing Critical] Added structured remediation codes for remote submit failures**
- **Found during:** Task 2 (Add the `qrun remote submit` CLI surface with exec-parity inputs)
- **Issue:** The planned CLI command needed stable machine-readable remediation for blank backend input and explicit backend lookup failure, but those error codes were not yet defined.
- **Fix:** Added `remote_backend_required` and `ibm_backend_lookup_failed` remediations and routed remote-submit CLI errors through structured payloads.
- **Files modified:** `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/cli.py`
- **Verification:** `uv run pytest tests/test_cli_remote_submit.py -q --maxfail=1`
- **Committed in:** `6550289`

**3. [Rule 3 - Blocking] Relaxed IBM service typing for MyPy**
- **Found during:** Plan-level verification
- **Issue:** MyPy rejected the explicit `service.backend(...)` call because the adapter seam typed `service` as `object`.
- **Fix:** Typed the adapter service seam as `Any` while keeping the explicit backend lookup path intact.
- **Files modified:** `src/quantum_runtime/runtime/ibm_remote_submit.py`
- **Verification:** `uv run pytest tests/test_cli_remote_submit.py -q --maxfail=1`; `uv run ruff check src tests`; `uv run python -m mypy src`
- **Committed in:** `b18ce2e`

---

**Total deviations:** 3 auto-fixed (2 missing critical, 1 blocking)
**Impact on plan:** All deviations were contained within the shipped submit surface and were required to preserve schema-driven behavior or pass the mandated verification gates.

## Issues Encountered

- A transient `.git/index.lock` blocked the Task 1 implementation commit. The lock was verified as inactive and the commit was retried sequentially without touching other agents' work.

## User Setup Required

Live IBM submit still requires a configured `[remote.ibm]` profile plus either the configured token environment variable or a valid saved account. This plan used mocked submit seams for verification and did not produce a separate `USER-SETUP` file.

## Next Phase Readiness

- Later remote lifecycle phases can reopen, poll, or finalize jobs against durable `attempt_id` records that now carry provider job ID, initial status, backend name, backend instance, and canonical hashes.
- The user-facing remote namespace now exists, so later work can extend it without widening `qrun exec`.
- No blockers remain in this plan; only live IBM credentials and optional IBM runtime installation are still required for protected end-to-end smoke coverage.

## Self-Check: PASSED

- Verified summary file exists at `.planning/phases/10-canonical-remote-submit-attempt-records/10-02-SUMMARY.md`.
- Verified task and verification-fix commits exist: `d40697b`, `cec5eb4`, `ae12546`, `6550289`, `b18ce2e`.
