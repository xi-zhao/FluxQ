---
phase: 02-trusted-revision-artifacts
plan: 01
subsystem: runtime
tags: [qiskit, revision-history, manifest, observability, pytest]
requires: []
provides:
  - immutable revision-scoped event and trace snapshots
  - self-describing run manifests with intent, plan, and event history hashes
  - regression coverage for artifact completeness and later-run immutability
affects: [replay, compare, pack, control-plane]
tech-stack:
  added: []
  patterns: [revision-scoped event snapshots, additive manifest evolution]
key-files:
  created:
    - tests/test_runtime_revision_artifacts.py
    - .planning/phases/02-trusted-revision-artifacts/02-01-SUMMARY.md
  modified:
    - src/quantum_runtime/workspace/paths.py
    - src/quantum_runtime/runtime/executor.py
    - src/quantum_runtime/runtime/run_manifest.py
    - tests/test_runtime_revision_artifacts.py
key-decisions:
  - "Snapshot revision events from the shared append-only logs after exec_completed so the immutable copy includes the full run record."
  - "Evolve RunManifestArtifact additively with defaulted intent, plan, and events blocks so legacy manifests still parse."
patterns-established:
  - "Workspace aliases remain mutable while history/{revision} paths become the only persisted evidence referenced by new manifest blocks."
  - "Manifest trust fields are additive and validated when present, rather than breaking older revisions."
requirements-completed: [RUNT-01]
duration: 4min
completed: 2026-04-12
---

# Phase 02 Plan 01: Trusted Revision Artifacts Summary

**Revision manifests now carry immutable intent, plan, and event evidence alongside revision-scoped event snapshots derived from the shared workspace logs**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-12T09:48:23Z
- **Completed:** 2026-04-12T09:51:59Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added `events/history/<revision>.jsonl` and `trace/history/<revision>.ndjson` helpers and directory creation to the workspace path contract.
- Reordered execution finalization so `exec_completed` is appended, revision-specific event snapshots are persisted, and the manifest is written against immutable history paths.
- Added a focused regression suite that proves artifact completeness, manifest linkage, and immutability after later runs.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add regression coverage for immutable revision artifact completeness** - `f009408` (`test`)
2. **Task 2: Persist self-describing revision manifests and event snapshots** - `cad8fd3` (`feat`)

## Files Created/Modified

- `tests/test_runtime_revision_artifacts.py` - Runtime-level regression suite for revision artifact completeness, manifest linkage, and immutability after later executions.
- `src/quantum_runtime/workspace/paths.py` - Added revision-scoped event and trace history helpers plus required directory entries.
- `src/quantum_runtime/runtime/executor.py` - Snapshots revision event records after `exec_completed` and wires immutable history paths into manifest persistence.
- `src/quantum_runtime/runtime/run_manifest.py` - Extends the manifest schema with additive `intent`, `plan`, and `events` blocks and validates those hashes when present.

## Decisions Made

- Persisted event snapshots by filtering the shared append-only logs on `revision`, which preserves existing alias behavior while producing immutable per-run evidence.
- Kept the new manifest blocks additive and defaulted so older manifests remain readable without migration.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pinned `exec_completed` report payloads to history paths**
- **Found during:** Task 2 (Persist self-describing revision manifests and event snapshots)
- **Issue:** The persisted event snapshot would otherwise record `reports/latest.json`, a mutable alias that can drift after later executions.
- **Fix:** Wrote the `exec_completed` trace payload with `reports/history/<revision>.json` before creating revision-scoped event snapshots.
- **Files modified:** `src/quantum_runtime/runtime/executor.py`
- **Verification:** `uv run --python 3.11 --extra dev --extra qiskit pytest -q tests/test_runtime_revision_artifacts.py tests/test_cli_exec.py::test_qrun_exec_history_report_pins_revision_qspec_after_later_runs`
- **Committed in:** `cad8fd3`

**2. [Rule 2 - Missing Critical] Validated new manifest trust blocks when present**
- **Found during:** Task 2 (Persist self-describing revision manifests and event snapshots)
- **Issue:** Writing additive `intent`, `plan`, and `events` blocks without hash validation on load would weaken the trust goal of the new manifest surface.
- **Fix:** Added optional integrity checks for the new manifest artifact blocks while preserving compatibility for legacy manifests that do not include them.
- **Files modified:** `src/quantum_runtime/runtime/run_manifest.py`
- **Verification:** `uv run --python 3.11 --extra dev --extra qiskit pytest -q tests/test_runtime_revision_artifacts.py tests/test_cli_exec.py::test_qrun_exec_history_report_pins_revision_qspec_after_later_runs`
- **Committed in:** `cad8fd3`

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical)
**Impact on plan:** Both changes tightened the intended trust contract without expanding scope beyond Phase 2 runtime artifact work.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Revision manifests can now reopen immutable intent, plan, qspec, report, and event evidence directly from history paths.
- Later replay, compare, and packaging work can depend on stable per-revision event artifacts without consulting mutable aliases.
- `STATE.md` and `ROADMAP.md` were intentionally left untouched for the orchestrator-owned verification step.

## Self-Check: PASSED

- Verified `.planning/phases/02-trusted-revision-artifacts/02-01-SUMMARY.md` exists on disk.
- Verified task commits `f009408` and `cad8fd3` exist in git history.
