---
phase: 03-concurrent-workspace-safety
plan: 02
subsystem: infra
tags: [workspace, cli, observability, pytest]
requires:
  - phase: 03-concurrent-workspace-safety
    provides: workspace lease metadata and interrupted-write detection from Plan 01
provides:
  - concrete workspace conflict and recovery-required exceptions on the public runtime error surface
  - schema-versioned CLI error payloads with holder and interrupted-write metadata
  - regression coverage for JSON and text workspace-safety failures in `qrun exec`
affects: [03-03, 03-04, workspace, cli]
tech-stack:
  added: []
  patterns: [structured runtime errors with metadata, typed error payload builders, workspace safety gate hints]
key-files:
  created: [tests/test_cli_workspace_safety.py]
  modified: [src/quantum_runtime/cli.py, src/quantum_runtime/errors.py, src/quantum_runtime/runtime/contracts.py, src/quantum_runtime/runtime/exit_codes.py, src/quantum_runtime/runtime/observability.py]
key-decisions:
  - "Catch concrete `WorkspaceConflictError` and `WorkspaceRecoveryRequiredError` in the CLI instead of inferring workspace safety from generic `ValueError` text."
  - "Keep workspace-safety failures inside the existing `ErrorPayload` envelope and attach reason/gate guidance under `details` rather than introducing a new top-level error schema."
  - "Reuse the existing `exec --jsonl` event sink to emit a terminal structured error payload when workspace safety blocks execution."
patterns-established:
  - "Workspace mutation blockers surface through `StructuredQuantumRuntimeError.details` with path-safe metadata."
  - "CLI workspace-safety serialization uses typed payload helpers plus observability-generated reason codes, next actions, and gate blocks."
requirements-completed: [RUNT-02]
duration: 8 min
completed: 2026-04-12
---

# Phase 03 Plan 02: Workspace Safety Error Surface Summary

**Concrete workspace conflict and recovery-required CLI contracts with structured holder metadata, recovery file state, and deterministic machine-facing exits**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-12T15:05:24Z
- **Completed:** 2026-04-12T15:13:52Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added failing-first CLI contract coverage for held-workspace conflicts and interrupted-write recovery in JSON and text modes.
- Introduced concrete `WorkspaceConflictError` and `WorkspaceRecoveryRequiredError` types with stable codes and structured metadata on the shared runtime error surface.
- Mapped `qrun exec` workspace-safety failures to schema-versioned payload helpers and observability gate hints without changing the existing top-level error envelope.

## Task Commits

Each task was committed atomically:

1. **Task 1: Lock the CLI contract for workspace conflict and recovery signals** - `0b34bc3` (`test`)
2. **Task 2: Add structured workspace-safety payloads and CLI mapping** - `1cb064d` (`feat`)

**Plan metadata:** Summary-only closeout by design. `STATE.md` and `ROADMAP.md` were intentionally left untouched for the orchestrator.

## Files Created/Modified

- `tests/test_cli_workspace_safety.py` - red/green CLI regression coverage for workspace conflict and recovery-required JSON/text behavior
- `src/quantum_runtime/errors.py` - structured workspace-safety exceptions with stable codes and metadata payloads
- `src/quantum_runtime/runtime/contracts.py` - typed workspace conflict and recovery-required error payload builders
- `src/quantum_runtime/runtime/observability.py` - reason-code, next-action, and gate helpers for shared-workspace failure states
- `src/quantum_runtime/runtime/exit_codes.py` - explicit deterministic exit-code helper for workspace-safety failures
- `src/quantum_runtime/cli.py` - explicit `exec`-path handling for concrete workspace-safety exceptions across JSON, JSONL, and text output

## Decisions Made

- Used real runtime exception classes from `src/quantum_runtime/errors.py` as the public CLI decision point so future mutation paths can raise the same concrete failures.
- Kept the error contract compatible by continuing to emit `ErrorPayload`-shaped JSON with workspace-safety specifics nested inside `details`.
- Preserved exit code `3` for blocked mutations instead of inventing a new CLI code in this plan, because the existing contract already treats invalid or blocked machine-facing failures deterministically there.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added JSONL terminal error emission for workspace-safety failures**
- **Found during:** Task 2
- **Issue:** `qrun exec --jsonl` would otherwise lose a deterministic machine-readable terminal payload if a workspace conflict or recovery-required exception occurred before normal completion.
- **Fix:** Routed workspace-safety payloads through the existing JSONL emitter as an error `run_completed` event before exiting with the deterministic workspace-safety code.
- **Files modified:** `src/quantum_runtime/cli.py`
- **Verification:** `PYTHONPATH=src ./.venv/bin/python -m pytest tests/test_cli_workspace_safety.py tests/test_cli_observability.py -q`
- **Committed in:** `1cb064d`

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** The deviation tightened machine-consumer coverage for an existing output mode without widening the workspace-safety contract surface.

## Issues Encountered

- The first green run exposed a case-sensitive mismatch in the conflict text assertion (`Retry` vs `retry`); the human-facing message was tightened immediately and the full target suite was rerun.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The CLI now exposes stable workspace-safety reason codes and metadata that Plan `03-03` can reuse when broader mutation flows adopt the same concrete exceptions.
- JSON, text, and JSONL `exec` consumers can distinguish retryable lease conflicts from recovery-required interrupted-write states without parsing traceback text.
- Remaining follow-up: expand these concrete exceptions from `qrun exec` into any additional mutating commands that become lock-aware in later plans.

## Self-Check: PASSED

- Verified file exists: `.planning/phases/03-concurrent-workspace-safety/03-concurrent-workspace-safety-02-SUMMARY.md`
- Verified commits exist: `0b34bc3`, `1cb064d`

---
*Phase: 03-concurrent-workspace-safety*
*Completed: 2026-04-12*
