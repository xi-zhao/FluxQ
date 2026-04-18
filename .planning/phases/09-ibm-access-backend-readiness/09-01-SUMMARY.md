---
phase: 09-ibm-access-backend-readiness
plan: "01"
subsystem: auth
tags: [ibm, qiskit-ibm-runtime, typer, pydantic, uv]
requires: []
provides:
  - "IBM optional dependency extra and lockfile coverage for qiskit-ibm-runtime~=0.46"
  - "Non-secret IBM profile persistence, resolution, and explicit service factory seam"
  - "Provider-specific `qrun ibm configure` CLI with stable JSON error reasons"
affects: [09-02, 09-03, doctor, backend-list]
tech-stack:
  added: [qiskit-ibm-runtime]
  patterns:
    - "External secret, internal reference persistence in `.quantum/qrun.toml`"
    - "Single IBM service factory seam via `build_ibm_service()` for later monkeypatching"
key-files:
  created:
    - src/quantum_runtime/runtime/ibm_access.py
    - tests/test_cli_ibm_config.py
  modified:
    - pyproject.toml
    - uv.lock
    - src/quantum_runtime/runtime/__init__.py
    - src/quantum_runtime/cli.py
    - src/quantum_runtime/runtime/contracts.py
key-decisions:
  - "Persist only `channel`, `credential_mode`, `instance`, `token_env`, and `saved_account_name` for IBM access; never store raw tokens in `.quantum/`."
  - "Expose IBM configuration through `qrun ibm configure` and reserve `build_ibm_service()` as the only optional IBM SDK import seam."
patterns-established:
  - "Workspace config remains the source of non-secret IBM references, while secret material stays in env vars or external saved-account storage."
  - "CLI validation maps IBM config mistakes to stable reason codes (`ibm_config_invalid`, `ibm_instance_required`, `ibm_token_external_required`) with exit code 3."
requirements-completed: [AUTH-01]
duration: 5m
completed: 2026-04-18
---

# Phase 09 Plan 01: IBM Access Baseline Summary

**IBM optional runtime extra, non-secret IBM profile persistence, and `qrun ibm configure` for explicit instance-bound access setup**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-18T13:45:12+08:00
- **Completed:** 2026-04-18T13:50:27+08:00
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Added the `ibm` optional dependency surface and aligned `uv.lock` with `qiskit-ibm-runtime~=0.46`.
- Introduced `src/quantum_runtime/runtime/ibm_access.py` with profile load/write, config resolution, and a reusable `build_ibm_service()` seam for later waves.
- Added `qrun ibm configure` with stable JSON error payloads and regression coverage proving `.quantum/qrun.toml` never stores raw IBM tokens.

## Task Commits

Each task was committed atomically:

1. **Task 1: 建立 IBM access 合同与 Wave 0 依赖**
   `da82ec2` test
   `c1e7d71` feat
2. **Task 2: 实现 `qrun ibm configure` 的非 secret 配置入口**
   `f54037e` test
   `e66de73` feat
   `84b6034` fix

## Files Created/Modified

- `src/quantum_runtime/runtime/ibm_access.py` - IBM profile model, TOML persistence, access resolution, and service factory seam.
- `tests/test_cli_ibm_config.py` - TDD coverage for non-secret persistence, config resolution, and `qrun ibm configure`.
- `src/quantum_runtime/cli.py` - New `ibm` Typer namespace and `configure` command.
- `src/quantum_runtime/runtime/contracts.py` - IBM remediation strings for stable CLI error payloads.
- `pyproject.toml` - `ibm` optional dependency extra.
- `uv.lock` - Locked optional IBM dependency graph.
- `src/quantum_runtime/runtime/__init__.py` - Re-exported IBM access models and helpers for later plans.

## Decisions Made

- Used `[remote.ibm]` inside `qrun.toml` as the persisted non-secret profile block so later phases can reuse one config location.
- Kept token handling external by persisting only env-var names or saved-account names, matching the phase threat model and project trust boundary.
- Centralized optional IBM SDK loading inside `build_ibm_service()` so Wave 2 can monkeypatch one seam instead of importing `qiskit_ibm_runtime` directly in `doctor` or `backend list`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated `uv.lock` for the new IBM extra**
- **Found during:** Task 1
- **Issue:** Adding `qiskit-ibm-runtime~=0.46` only to `pyproject.toml` left the `uv` lockfile stale.
- **Fix:** Ran `uv lock` and committed the lockfile update with the Task 1 implementation.
- **Files modified:** `uv.lock`
- **Verification:** `uv run pytest tests/test_cli_ibm_config.py -k 'profile or resolution' -q --maxfail=1`
- **Committed in:** `c1e7d71`

**2. [Rule 3 - Blocking] Fixed mypy issues from dynamic IBM typing**
- **Found during:** Plan-level verification
- **Issue:** `mypy` flagged the IBM service seam typing and the CLI error helper as incompatible with the new code paths.
- **Fix:** Marked `_cli_error()` as non-returning and relaxed the dynamic import helper typing in `ibm_access.py`.
- **Files modified:** `src/quantum_runtime/cli.py`, `src/quantum_runtime/runtime/ibm_access.py`
- **Verification:** `uv run python -m mypy src`, `uv run pytest tests/test_cli_ibm_config.py -q --maxfail=1`
- **Committed in:** `84b6034`

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes were required to keep dependency metadata and type gates consistent. No scope creep beyond the plan.

## Issues Encountered

- The first Task 1 implementation check failed on an f-string escaping bug in `ibm_access.py`; it was fixed inline before the feature commit.
- One initial `git commit` attempt reported `.git/index.lock`, but the lock file was already gone on inspection and the retry succeeded without repo cleanup.

## User Setup Required

No repo-side setup file was generated. Live IBM smoke still requires a user-managed `QISKIT_IBM_TOKEN` and an explicit IBM instance CRN outside the workspace.

## Next Phase Readiness

- Phase 09 Wave 2 can now reuse `resolve_ibm_access()` and monkeypatch `build_ibm_service()` without importing the IBM SDK directly in `doctor` or `backend list`.
- The CLI and workspace boundaries for IBM credentials are now fixed, so later work can stay focused on readiness and lifecycle behavior rather than re-designing config storage.

## Known Stubs

None.

## Self-Check: PASSED

- Found `.planning/phases/09-ibm-access-backend-readiness/09-01-SUMMARY.md`
- Found commits `da82ec2`, `c1e7d71`, `f54037e`, `e66de73`, and `84b6034`
