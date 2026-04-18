---
phase: 06-runtime-adoption-surface
plan: "01"
subsystem: docs
tags: [readme, release-notes, testing, adoption, control-plane]
requires:
  - phase: 01-canonical-ingress-resolution
    provides: side-effect-free ingress surfaces for `prompt`, `resolve`, and `plan`
  - phase: 04-policy-acceptance-gates
    provides: CI-facing `compare --fail-on ...` and `doctor --ci` policy surfaces
  - phase: 05-verified-delivery-bundles
    provides: `pack`, `pack-inspect`, and `pack-import` delivery handoff commands
provides:
  - shared GHZ runtime-first quickstart across README and release notes
  - README docs index entry for the existing QAOA MaxCut case study
  - regression coverage locking the adoption loop ordering and legacy-command removals
affects: [runtime-adoption-surface, docs, release, onboarding]
tech-stack:
  added: []
  patterns:
    - reuse one exact GHZ runtime loop across README and release-facing docs
    - lock public adoption surfaces with focused string-and-order assertions instead of snapshots
key-files:
  created:
    - .planning/phases/06-runtime-adoption-surface/06-runtime-adoption-surface-01-SUMMARY.md
  modified:
    - README.md
    - docs/releases/v0.3.1.md
    - tests/test_release_docs.py
key-decisions:
  - "Made the first supported path explicitly baseline-first and CI-gated: `baseline set -> compare --fail-on subject_drift -> doctor --ci`."
  - "Removed generator-style QAOA prompt mixing from release notes so the first-run surface stays single-workload and copyable."
  - "Pointed README docs readers to the existing QAOA MaxCut case study instead of inventing a new adoption asset."
patterns-established:
  - "Top-level docs should describe FluxQ as an agent-first runtime control plane while preserving the existing `Natural language is ingress` narrative."
  - "Release-facing quickstarts should end with delivery handoff commands (`pack -> pack-inspect -> pack-import`) rather than stopping at local execution."
requirements-completed: [SURF-01]
duration: 2min
completed: 2026-04-15
---

# Phase 06 Plan 01: Runtime Adoption Surface Summary

**Unified README and release notes around one GHZ runtime-control-plane quickstart with baseline, CI gate, and delivery handoff**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-15T18:15:03+08:00
- **Completed:** 2026-04-15T18:16:47+08:00
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added a dedicated failing regression that locks README and release notes to one ordered GHZ adoption loop.
- Replaced the old mixed first-run docs with one runtime-first command chain covering baseline, compare gate, doctor CI gate, and bundle handoff.
- Added the QAOA MaxCut case study to the README docs index so top-level readers can reach an existing adoption asset.

## Task Commits

Each task was committed atomically:

1. **Task 1: 先把 README 与 release notes 的 runtime-first quickstart 合同锁进测试** - `f8e935c` (`test`)
2. **Task 2: 修正文档入口面，输出一条可直接采用的 runtime/control-plane 首跑链路** - `df8c37b` (`feat`)

## Files Created/Modified

- `README.md` - Replaced `## First Run` with the baseline-first GHZ runtime loop, added the required explanatory sentence, and linked the QAOA MaxCut case study in `## Docs`.
- `docs/releases/v0.3.1.md` - Rewrote `## What To Try First` to match the README runtime loop and removed the legacy QAOA/`doctor --jsonl --fix` first-run guidance.
- `tests/test_release_docs.py` - Added the new quickstart contract test and updated the existing smoke assertions to match the current public docs surface.
- `.planning/phases/06-runtime-adoption-surface/06-runtime-adoption-surface-01-SUMMARY.md` - Records plan execution, commits, and deviations.

## Decisions Made

- Kept the first-run story on the GHZ example because it already maps cleanly onto the validated ingress, policy, and bundle surfaces.
- Used `doctor --workspace .quantum --json --ci` as the public gate instead of `doctor --fix`, matching Phase 04's CI-verdict contract.
- Moved delivery handoff into the top-level quickstart so adoption messaging reflects the verified bundle workflow from Phase 05.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reconciled the existing smoke test with the new quickstart contract**
- **Found during:** Task 2
- **Issue:** `tests/test_release_docs.py::test_release_docs_cover_runnable_readme_and_release_assets` still pinned the removed README/release first-run commands, so the planned doc updates would have failed verification even after the new contract test passed.
- **Fix:** Updated the existing smoke assertions to match the new runtime-first public surface while keeping the dedicated ordering test separate.
- **Files modified:** `tests/test_release_docs.py`
- **Verification:** `./.venv/bin/python -m pytest tests/test_release_docs.py -q --maxfail=1`
- **Committed in:** `df8c37b`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The adjustment was necessary to keep the existing docs regression suite aligned with the plan's new public contract. No scope creep.

## Issues Encountered

- A self-inflicted `.git/index.lock` race happened when `git status` and `git commit` were launched in parallel during Task 2. Retrying the commit serially resolved it without changing repository content.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- README and release-facing messaging now present the same runtime-first adoption loop, so Phase 06-02 can extend that loop into integration assets and case studies without re-litigating top-level messaging.
- The docs regression suite now has an explicit place to lock future adoption-loop changes.

## Self-Check: PASSED

- Found summary file at `.planning/phases/06-runtime-adoption-surface/06-runtime-adoption-surface-01-SUMMARY.md`
- Verified task commits `f8e935c` and `df8c37b` exist in git history
