---
phase: 07-compare-trust-closure
plan: 02
subsystem: compare
tags: [compare, baseline, trust, pytest]
requires:
  - phase: 07-compare-trust-closure
    plan: 01
    provides: healthy canonical revision artifacts for baseline/current compare
provides:
  - baseline/current compare now has an explicit tamper regression that preserves fail-closed trust behavior
  - compare/CLI wiring is verified to keep policy failures on exit 2 and trusted import failures on exit 3
affects: [POLC-01, compare, baseline, imports, cli]
tech-stack:
  added: []
  patterns: [fail-closed compare regression, baseline/current policy gate verification]
key-files:
  created: []
  modified: [tests/test_cli_compare.py]
key-decisions:
  - "Keep compare.py and cli.py behavior unchanged because healthy baseline/current compare already matches the Phase 04 policy surface after 07-01."
  - "Add the negative-path regression at the CLI layer by tampering `specs/history/rev_000002.json` and asserting compare still exits through trusted-import failure."
  - "Record Task 2 as a verification-only atomic commit instead of forcing a no-value wiring change."
patterns-established:
  - "Healthy baseline/current compare continues through ComparePolicy verdict evaluation."
  - "Tampered current revision artifacts still stop at trusted import with a machine-readable error."
requirements-completed: [POLC-01]
duration: 8 min
completed: 2026-04-15
---

# Phase 07 Plan 02: Compare Trust Closure Summary

**Baseline/current compare 现在同时锁住健康 policy gate 与篡改后的 fail-closed trust path**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-15T14:00:00Z
- **Completed:** 2026-04-15T14:07:42Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- 在 `tests/test_cli_compare.py` 新增 `test_qrun_compare_json_baseline_preserves_fail_closed_on_tampered_current_revision`，直接污染 `rev_000002` 的 canonical qspec history，固定 baseline compare 继续返回 trust error `exit=3`。
- 重新验证 07-02 的 compare suite，确认健康 baseline/current 与 left/right compare 都回到 Phase 04 的 `verdict`/`gate`/exit `2` surface。
- 复核 `compare_workspace_baseline()` 与 CLI compare wiring，确认 `ImportSourceError` 没有在 `compare.py` 被降级成普通 drift。

## Task Commits

Each task was committed atomically:

1. **Task 1: 绿化 compare gate 红测并补上 fail-closed 负向回归** - `95fd108` (`test`)
2. **Task 2: 仅在必要时做最小 compare/CLI wiring 修补** - `34bbc01` (`chore`)

**Plan metadata:** Summary-only closeout committed separately from task commits. `.planning/STATE.md` and `.planning/ROADMAP.md` remain orchestrator-owned per user instruction.

## Files Created/Modified

- `tests/test_cli_compare.py` - 新增 baseline tamper 回归，断言 `qrun compare --baseline --json` 在当前 revision 被篡改时仍返回 `report_qspec_hash_mismatch`/`report_qspec_semantic_hash_mismatch` 类 trust error。

## Decisions Made

- 不对 `src/quantum_runtime/runtime/compare.py` 或 `src/quantum_runtime/cli.py` 做无意义调整；当前实现已经满足 07-02 的合同。
- 负向回归选择污染 `specs/history/rev_000002.json`，因为这能稳定触发 machine-readable 的 qspec/report hash mismatch，而不会把 corruption 伪装成 policy drift。
- Task 2 用验证型空提交保留原子历史，明确“无 wiring 变更”本身就是本计划的结果。

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Task 1 新增的 tamper 回归在第一次加入后就直接通过，说明 07-01 的 producer-side 修复已经把 fail-closed 路径一并恢复；07-02 因此不需要再补 compare/CLI 实现代码。

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Threat Flags

None.

## Next Phase Readiness

- `POLC-01` 的 live compare gate 现在同时覆盖健康路径与篡改路径：健康 revision 返回 policy verdict，真实 corruption 保持 trusted-import fail closed。
- 已被旧 bug 污染的历史 workspace 仍不在本计划修复范围内；需要 rerun、rebaseline 或人工清理后再比较。

## Self-Check: PASSED

- Verified file exists: `.planning/phases/07-compare-trust-closure/07-compare-trust-closure-02-SUMMARY.md`
- Verified commits exist: `95fd108`, `34bbc01`

---
*Phase: 07-compare-trust-closure*
*Completed: 2026-04-15*
