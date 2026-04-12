---
phase: 02-trusted-revision-artifacts
plan: 02
subsystem: runtime
tags: [python, qiskit, replay-integrity, imports, baseline, cli]
requires: []
provides:
  - trusted replay imports fail closed on artifact digest drift
  - legacy-compatible reports remain reopenable without trusted digest evidence
  - baseline and CLI regressions cover trusted versus legacy replay behavior
affects: [control-plane, inspect, compare, baseline]
tech-stack:
  added: []
  patterns:
    - fail-closed replay validation for trusted revision artifacts
    - explicit replay trust classification for trusted versus legacy inputs
key-files:
  created: []
  modified:
    - src/quantum_runtime/runtime/imports.py
    - tests/test_runtime_imports.py
    - tests/test_cli_exec.py
    - tests/test_cli_control_plane.py
    - tests/test_workspace_baseline.py
key-decisions:
  - "Persisted artifact output digests are trusted evidence when present and now block replay/import on drift."
  - "Reports without persisted artifact digests stay legacy-compatible and surface replay_integrity.trust_level='legacy'."
patterns-established:
  - "Trusted replay path: qspec hash, semantic hash, and artifact digests must all agree before import resolution succeeds."
  - "Legacy replay path: manifestless reports without digest evidence remain reopenable when revision, report hash, and qspec hash still match."
requirements-completed: [RUNT-03]
duration: 8min
completed: 2026-04-12
---

# Phase 2 Plan 2: Trusted Replay Integrity Summary

**Fail-closed replay import enforcement for trusted artifact digests with explicit legacy-compatible reopen semantics**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-12T09:46:30Z
- **Completed:** 2026-04-12T09:54:35Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Added red regressions that distinguish trusted artifact drift from legacy-compatible reopen paths across importer, CLI exec, show, and baseline flows.
- Updated `runtime/imports.py` so trusted replay inputs raise stable `ImportSourceError` codes for missing or mismatched artifact outputs.
- Added explicit replay trust classification (`trusted` vs `legacy`) while preserving baseline reopening for older manifestless report inputs.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add trusted-versus-legacy replay/import regression coverage** - `a9c8417` (test)
2. **Task 2: Implement fail-closed trusted replay enforcement without regressing legacy or baseline flows** - `6a49d11` (fix)

**Summary metadata:** recorded in a separate docs commit for `02-02-SUMMARY.md`

## Files Created/Modified
- `src/quantum_runtime/runtime/imports.py` - Enforces trusted artifact digest drift as blocking import errors and emits replay trust classification.
- `tests/test_runtime_imports.py` - Covers trusted drift rejection, legacy compatibility, and trust-level assertions on importer resolutions.
- `tests/test_cli_exec.py` - Covers `qrun exec --report-file/--revision --json` fail-closed behavior for trusted replay drift.
- `tests/test_cli_control_plane.py` - Verifies `qrun show --json` still exposes legacy replay integrity without failing legacy-compatible inputs.
- `tests/test_workspace_baseline.py` - Verifies baseline reopening accepts legacy-compatible report resolutions when identity hashes still match.

## Decisions Made
- Treated persisted artifact output digests as policy-grade replay evidence instead of advisory metadata because trusted revisions should not silently degrade.
- Kept legacy compatibility scoped to reports that genuinely lack digest evidence, rather than weakening manifest or hash checks for current trusted runs.

## Deviations from Plan

Execution matched the implementation plan.

Per explicit user instruction, this run did **not** update `.planning/STATE.md` or `.planning/ROADMAP.md`; those writes are deferred to the orchestrator after verification.

## Issues Encountered

- Initial legacy test fixtures modified current trusted reports in place and triggered manifest hash failures. The fixtures were corrected to model genuine legacy inputs by removing manifests and legacy-only report metadata together.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Replay/import now distinguishes trusted and legacy evidence in a machine-readable way and blocks trusted artifact drift.
- Baseline and control-plane reopen flows have targeted regression coverage for the new trust contract.
- Full-repository verification was not run; later phases that depend on `inspect` or compare-side replay degradation semantics should re-verify those broader surfaces against the new fail-closed importer behavior.

## Known Stubs

- `tests/test_cli_exec.py:607` - Intentional empty `errors`, `artifacts`, `backend_reports`, and `next_actions` fields in a monkeypatched `ExecResult` used only for CLI exit-code regression coverage.
- `tests/test_cli_exec.py:653` - Intentional empty `warnings`, `errors`, `artifacts`, `backend_reports`, and `next_actions` fields in a monkeypatched simulation-failure `ExecResult` fixture.
- `tests/test_cli_exec.py:697` - Intentional empty `errors`, `artifacts`, and `next_actions` fields in a monkeypatched backend-missing `ExecResult` fixture.

## Self-Check: PASSED

- Verified `.planning/phases/02-trusted-revision-artifacts/02-02-SUMMARY.md` exists.
- Verified task commits `a9c8417` and `6a49d11` exist in `git log --oneline --all`.

---
*Phase: 02-trusted-revision-artifacts*
*Completed: 2026-04-12*
