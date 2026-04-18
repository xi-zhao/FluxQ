---
phase: 07-compare-trust-closure
plan: 01
subsystem: infra
tags: [workspace, exec, compare, provenance, pytest]
requires:
  - phase: 02-trusted-revision-artifacts
    provides: trusted revision artifact contracts and fail-closed replay integrity checks
  - phase: 03-concurrent-workspace-safety
    provides: history-first, alias-last exec persistence for canonical workspace artifacts
provides:
  - second-exec revision artifacts keep report, qspec, and manifest bound to one canonical history revision
  - report qspec hash and semantic hash now derive from the same canonical qspec file
  - regression coverage that reproduces and guards the rev_000002 canonical write seam
affects: [07-02, compare, imports, exec, workspace]
tech-stack:
  added: []
  patterns: [canonical-history-only report writing, producer-side trust repair, red-green regression]
key-files:
  created: []
  modified: [src/quantum_runtime/reporters/writer.py, src/quantum_runtime/runtime/executor.py, tests/test_runtime_revision_artifacts.py]
key-decisions:
  - "Keep import and compare fail-closed semantics unchanged and repair the producer-side write seam instead."
  - "Treat the executor-provided `qspec_path` as the canonical revision truth layer inside `write_report()`."
  - "Derive report qspec hash and semantic hash from the same persisted qspec history file to avoid mixed-source metadata."
patterns-established:
  - "Exec passes canonical revision artifact paths into `write_report()` before any alias promotion."
  - "Report writer describes canonical history artifacts without copying mutable aliases back into revision history."
requirements-completed: [POLC-01]
duration: 6 min
completed: 2026-04-15
---

# Phase 07 Plan 01: Compare Trust Closure Summary

**Canonical revision report writing now keeps `rev_000002` report, qspec, and manifest self-consistent across repeated `exec` runs**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-15T13:56:00Z
- **Completed:** 2026-04-15T14:02:29Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added a failing regression that proves a second `exec` could corrupt `specs/history/rev_000002.json` before compare ever ran.
- Removed the writer-side alias backfill that was copying `current` artifacts back into canonical history during report generation.
- Rebound report qspec metadata to the persisted canonical qspec file so trusted reopen and baseline compare can consume healthy revisions again.

## Task Commits

Each task was committed atomically:

1. **Task 1: 用红测钉住第二次 exec 的 revision coherence** - `ceb373f` (`test`)
2. **Task 2: 修复 writer/executor 的 canonical history 写入契约** - `e9d9160` (`fix`)

**Plan metadata:** Summary-only closeout committed separately from task commits. `STATE.md` and `ROADMAP.md` remain orchestrator-owned per user instruction.

## Files Created/Modified

- `tests/test_runtime_revision_artifacts.py` - 新增第二次 `exec` 的 coherence 回归，直接从磁盘断言 report/qspec/manifest 是否仍绑定同一 revision。
- `src/quantum_runtime/reporters/writer.py` - 删除 alias 回灌逻辑，并改为从同一个 canonical qspec history 文件导出 hash 与 semantic hash。
- `src/quantum_runtime/runtime/executor.py` - 在 producer 边界显式传入 canonical artifact 映射，保持 writer 输入为 revision-scoped history paths。

## Decisions Made

- 修 producer，不修 consumer 宽容度；`imports.py` 的 fail-closed replay integrity 不做放松。
- `write_report()` 不再 materialize canonical history，而是只描述 executor 已经写好的 canonical revision artifacts。
- 第二次 `exec` 的回归测试直接校验跨文件一致性，而不是只校验路径命名。

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- 红测第一轮立即复现了目标故障：`specs/history/rev_000002.json` 与 `rev_000001` 字节完全相同，说明 writer 在第二次 `exec` 时确实把 mutable alias 回灌进了 canonical history。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Baseline/current compare 现在可以重新依赖健康 workspace 的 canonical revision artifacts，而不会在 trusted reopen 前就被 producer 自相矛盾阻断。
- 已被旧 bug 污染的历史 workspace 仍保持 fail-closed，需要 rerun、rebaseline 或人工清理；本计划没有自动修复旧历史。

## Self-Check: PASSED

- Verified file exists: `.planning/phases/07-compare-trust-closure/07-compare-trust-closure-01-SUMMARY.md`
- Verified commits exist: `ceb373f`, `e9d9160`

---
*Phase: 07-compare-trust-closure*
*Completed: 2026-04-15*
