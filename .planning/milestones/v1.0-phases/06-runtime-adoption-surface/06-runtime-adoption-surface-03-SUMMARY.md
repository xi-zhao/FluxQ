---
phase: 06-runtime-adoption-surface
plan: "03"
subsystem: docs
tags: [versioning, release-notes, packaging, metadata, control-plane]
requires:
  - phase: 04-policy-acceptance-gates
    provides: additive `reason_codes`, `next_actions`, `decision`, and `gate` machine signals
  - phase: 05-verified-delivery-bundles
    provides: `qrun pack`, `qrun pack-inspect`, and `qrun pack-import` as released delivery surfaces
  - phase: 06-runtime-adoption-surface
    provides: release-facing runtime-first framing from Plan 01
provides:
  - stable/evolving/optional runtime contract taxonomy in `docs/versioning.md`
  - v0.3.1 release-note guidance for adopter consumption of runtime contracts
  - packaging metadata aligned with FluxQ's runtime control plane positioning
affects: [runtime-adoption-surface, docs, release, packaging]
tech-stack:
  added: []
  patterns:
    - lock public runtime contract wording with focused docs and packaging assertions
    - treat package metadata as part of the runtime adoption contract
key-files:
  created:
    - .planning/phases/06-runtime-adoption-surface/06-runtime-adoption-surface-03-SUMMARY.md
  modified:
    - docs/versioning.md
    - docs/releases/v0.3.1.md
    - CHANGELOG.md
    - pyproject.toml
    - tests/test_release_docs.py
    - tests/test_packaging_release.py
key-decisions:
  - "Kept the existing released-line history and layered the stability taxonomy underneath it instead of replacing the version timeline."
  - "Documented `reason_codes`, `next_actions`, `decision`, and `gate` as additive machine signals so adopters know to consume them by presence checks."
  - "Removed the generator-first classifier and added `control-plane` keywords so package metadata matches the runtime-first public narrative."
patterns-established:
  - "Versioning and release docs must separate stable, evolving, and optional runtime contracts explicitly."
  - "Metadata drift is a release regression and should be locked by tests, not left to manual release review."
requirements-completed: [SURF-03]
duration: 2min
completed: 2026-04-15
---

# Phase 06 Plan 03: Runtime Adoption Surface Summary

**Stable/evolving/optional runtime contract taxonomy with v0.3.1 adopter guidance and control-plane-aligned packaging metadata**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-15T18:20:20+08:00
- **Completed:** 2026-04-15T18:22:06+08:00
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added focused regression tests that lock the stable/evolving/optional taxonomy, release-note guidance, changelog bullets, and packaging metadata rules for SURF-03.
- Expanded `docs/versioning.md` and `docs/releases/v0.3.1.md` so adopters can distinguish stable runtime contracts from additive machine signals and optional integration surfaces.
- Removed the generator-first package classifier, added the `control-plane` keyword, and recorded the positioning change in `CHANGELOG.md`.

## Task Commits

Each task was committed atomically:

1. **Task 1: 先把 stable/evolving/optional contract、release-note guidance 与 package metadata 对齐要求锁进测试** - `96ea8fe` (`test`)
2. **Task 2: 写清 runtime contract taxonomy，并把 release/package metadata 与之对齐** - `80af9ee` (`feat`)

## Files Created/Modified

- `docs/versioning.md` - Added the stable/evolving/optional runtime contract taxonomy and safe consumption rules while preserving the release-line history.
- `docs/releases/v0.3.1.md` - Added a `Runtime Contract Stability` section for the current released line with adopter-facing guidance.
- `CHANGELOG.md` - Recorded the taxonomy and metadata-alignment change under `Unreleased`.
- `pyproject.toml` - Replaced generator-first metadata with a `control-plane` keyword and removed the `Code Generators` classifier.
- `tests/test_release_docs.py` - Added the focused release-note stability regression and aligned the legacy versioning smoke assertion with SURF-03 wording.
- `tests/test_packaging_release.py` - Added the focused runtime-contract stability regression and aligned the existing packaging smoke assertion with the new metadata contract.
- `.planning/phases/06-runtime-adoption-surface/06-runtime-adoption-surface-03-SUMMARY.md` - Records plan execution, commits, and deviations.

## Decisions Made

- Kept `docs/versioning.md` anchored around the released-line timeline so the new taxonomy clarifies compatibility instead of hiding release history.
- Put the consumption guidance directly in `docs/releases/v0.3.1.md` so adopters do not need to infer stable versus optional surfaces from highlights alone.
- Treated package metadata as part of the public runtime contract, not just PyPI decoration, because it shapes first-contact product positioning.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reconciled legacy smoke tests with the new SURF-03 contract wording**
- **Found during:** Task 2
- **Issue:** Existing smoke assertions in `tests/test_packaging_release.py` and `tests/test_release_docs.py` still expected the old generator classifier and pre-taxonomy versioning sentence, so the planned documentation and metadata changes would have failed the regression suite.
- **Fix:** Updated the existing smoke assertions to match the new runtime-contract wording while keeping the new focused SURF-03 tests separate.
- **Files modified:** `tests/test_packaging_release.py`, `tests/test_release_docs.py`
- **Verification:** `./.venv/bin/python -m pytest tests/test_release_docs.py tests/test_packaging_release.py -q --maxfail=1 && ./.venv/bin/python -m build`
- **Committed in:** `80af9ee`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary to keep the existing release/docs regression suite coherent with the planned contract update. No scope creep.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Release notes, versioning notes, changelog, and packaging metadata now describe the same runtime control plane positioning.
- Future release-line docs can extend additive or optional guidance without re-litigating the stable contract taxonomy.

## Self-Check: PASSED

- Found summary file at `.planning/phases/06-runtime-adoption-surface/06-runtime-adoption-surface-03-SUMMARY.md`
- Verified task commits `96ea8fe` and `80af9ee` exist in git history
