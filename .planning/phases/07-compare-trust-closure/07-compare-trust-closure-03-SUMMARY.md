---
phase: 07-compare-trust-closure
plan: 03
subsystem: testing
tags: [pytest, exec, imports, compare, workspace, regression]
requires:
  - phase: 07-compare-trust-closure
    provides: canonical revision writes remain coherent across repeated exec runs
  - phase: 07-compare-trust-closure
    provides: baseline/current compare gate is green again on trusted current revisions
provides:
  - exec suite now asserts rev_000002 report and qspec path/hash/semantic coherence directly
  - import suite now proves healthy multi-revision reopen succeeds before compare runs
  - import suite now proves real rev_000002 canonical tampering still fails closed
affects: [exec, imports, compare, workspace, audit]
tech-stack:
  added: []
  patterns: [cross-phase regression ownership, canonical-history reopen checks, fail-closed tamper regressions]
key-files:
  created: []
  modified: [tests/test_cli_exec.py, tests/test_runtime_imports.py]
key-decisions:
  - "Keep Phase 07 hardening in the existing exec/import suites instead of creating a separate seam-only harness."
  - "Prove healthy reopen from canonical history paths, not from current alias fallback."
  - "Preserve fail-closed trusted import behavior by asserting tampered rev_000002 history raises import errors."
patterns-established:
  - "CLI exec regressions validate report/qspec path, hash, and semantic_hash coherence for later revisions."
  - "Runtime import regressions cover both healthy reopen and canonical-history tamper failure on the latest revision."
requirements-completed: [POLC-01]
duration: 5 min
completed: 2026-04-15
---

# Phase 07 Plan 03: Compare Trust Closure Summary

**Exec and import regressions now catch second-revision coherence drift and canonical-history tampering before compare or milestone audit has to discover them**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-15T14:04:30Z
- **Completed:** 2026-04-15T14:09:23Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Strengthened `tests/test_cli_exec.py` so repeated `qrun exec` runs now assert `rev_000001` stays pinned and `rev_000002` report/qspec metadata stays coherent on disk.
- Added a replay smoke proving `qrun exec --revision rev_000002 --json` succeeds after two healthy executions.
- Added runtime import regressions that prove `resolve_workspace_current()` reopens the latest canonical history revision cleanly and still fails closed when `specs/history/rev_000002.json` is tampered.

## Task Commits

Each task was committed atomically:

1. **Task 1: 在 CLI exec 套件里补上第二次 revision coherence 回归** - `1c0c6d1` (`test`)
2. **Task 2: 在 runtime imports 套件里同时锁住健康 reopen 与真实篡改 fail-closed** - `58e7ada` (`test`)

**Plan metadata:** Summary-only closeout committed separately from task commits. `.planning/STATE.md` and `.planning/ROADMAP.md` remain orchestrator-owned per user instruction.

## Files Created/Modified

- `tests/test_cli_exec.py` - 升级 CLI exec 回归，直接重算 history qspec 的 hash 与 semantic hash，并补 `rev_000002` replay smoke。
- `tests/test_runtime_imports.py` - 新增 `resolve_workspace_current()` 在两次 exec 后直接重开 `rev_000002` history 与篡改后 fail-closed 的回归。

## Decisions Made

- 沿用现有 `tests/test_cli_exec.py` 与 `tests/test_runtime_imports.py` 补强 ownership，不再新建旁路测试 harness。
- 健康路径断言必须落到 `reports/history/rev_000002.json` 与 `specs/history/rev_000002.json`，避免测试被 current alias fallback 假阳性遮住。
- 篡改路径继续接受 `report_qspec_hash_mismatch` 或 `report_qspec_semantic_hash_mismatch`，以保持 trusted import 的 fail-closed 合同而不是放松它。

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Task 2 的首轮红测把 `rev_000001` history qspec 路径少写了 `.json` 后缀；修正测试篡改路径后，计划指定的联合验证恢复为绿色。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 07 的 exec/import/compare 三层 gate 已经都能在本地直接验证，后续再破坏 second-revision coherence 时会先在 exec/import regression 中被拦住。
- 本次执行按用户要求没有更新 `.planning/STATE.md` 或 `.planning/ROADMAP.md`；若 orchestrator 需要推进 phase bookkeeping，应在外层流程中处理。

## Self-Check: PASSED

- Verified file exists: `.planning/phases/07-compare-trust-closure/07-compare-trust-closure-03-SUMMARY.md`
- Verified commits exist: `1c0c6d1`, `58e7ada`

---
*Phase: 07-compare-trust-closure*
*Completed: 2026-04-15*
