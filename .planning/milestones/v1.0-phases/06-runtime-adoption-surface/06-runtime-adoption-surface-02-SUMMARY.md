---
phase: 06-runtime-adoption-surface
plan: "02"
subsystem: docs
tags: [adoption, integration, ci, docs, testing]
requires:
  - phase: 06-01
    provides: runtime-first README and release-note positioning for the public adoption surface
  - phase: 04-policy-acceptance-gates
    provides: `qrun compare --fail-on ...` and `qrun doctor --ci` gate contracts
  - phase: 05-verified-delivery-bundles
    provides: `qrun pack`, `qrun pack-inspect`, and `qrun pack-import` delivery handoff commands
provides:
  - canonical `Runtime Adoption Workflow` documentation for agent and CI adopters
  - aligned aionrs integration assets with explicit stop-on-gate and delivery handoff rules
  - regression coverage locking policy-gated handoff language in the adoption doc, aionrs assets, and QAOA case study
affects: [runtime-adoption-surface, docs, onboarding, ci, integrations]
tech-stack:
  added: []
  patterns:
    - reuse one exact runtime adoption command chain across canonical docs, host examples, and case studies
    - require compare and doctor gates before bundle handoff, with `pack-inspect` before `pack-import`
key-files:
  created:
    - .planning/phases/06-runtime-adoption-surface/06-runtime-adoption-surface-02-SUMMARY.md
    - docs/agent-ci-adoption.md
    - tests/test_runtime_adoption_workflow.py
  modified:
    - docs/aionrs-integration.md
    - docs/fluxq-qaoa-maxcut-case-study.md
    - integrations/aionrs/CLAUDE.md.example
    - integrations/aionrs/hooks.example.toml
    - tests/test_aionrs_assets.py
key-decisions:
  - "Promoted one canonical runtime loop into `docs/agent-ci-adoption.md` instead of letting integration docs invent their own command sequences."
  - "Made `compare --fail-on subject_drift` and `doctor --json --ci` explicit stop points before any bundle handoff."
  - "Required machine consumers to read `reason_codes`, `next_actions`, and `gate` across both docs and examples."
patterns-established:
  - "Host integration docs should stay file-plus-shell and reuse the same policy and handoff contract as the main adoption workflow."
  - "Case studies should end with policy gate and verified delivery handoff guidance, not stop at local execution results."
requirements-completed: [SURF-02]
duration: 2min
completed: 2026-04-15
---

# Phase 06 Plan 02: Runtime Adoption Surface Summary

**Canonical runtime adoption workflow for agent hosts and CI, with aionrs stop-on-gate rules and verified bundle handoff stitched onto the QAOA case study**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-15T18:20:18+08:00
- **Completed:** 2026-04-15T18:21:38+08:00
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- Added RED regressions that lock the aionrs integration doc, host rules, hooks sample, canonical adoption workflow, and QAOA case study to one runtime contract.
- Created `docs/agent-ci-adoption.md` with the full ingress -> exec -> baseline -> compare -> doctor -> pack -> pack-inspect -> pack-import loop for agent hosts and CI.
- Aligned the aionrs integration assets and QAOA case study so policy gates and delivery handoff both require machine-readable `reason_codes`, `next_actions`, and `gate`.

## Task Commits

Each task was committed atomically:

1. **Task 1: 先把 adoption workflow、aionrs asset 和 case study 的缺口锁进测试** - `50dfca5` (`test`)
2. **Task 2: 编写 canonical adoption workflow，并把 integration/case-study surface 拉齐到同一条 runtime contract** - `5ecec23` (`feat`)

## Files Created/Modified

- `tests/test_aionrs_assets.py` - Adds focused policy and handoff assertions for the aionrs doc, CLAUDE example, and hooks example.
- `tests/test_runtime_adoption_workflow.py` - Locks the canonical adoption workflow doc and the QAOA case study sections, command blocks, signal vocabulary, and `pack-inspect` before `pack-import`.
- `docs/agent-ci-adoption.md` - New canonical adoption workflow doc covering agent-host, CI-gate, and delivery-handoff usage.
- `docs/aionrs-integration.md` - Rewritten host workflow showing baseline, compare, doctor CI, pack, pack-inspect, and pack-import on the same contract.
- `integrations/aionrs/CLAUDE.md.example` - Expanded to an 8-step runtime workflow with the required stop-on-gate sentence.
- `integrations/aionrs/hooks.example.toml` - Switches the post-tool hook to the CI-oriented `doctor --json --ci` invocation.
- `docs/fluxq-qaoa-maxcut-case-study.md` - Adds `Agent/CI continuation` and `Delivery handoff` sections that teach gate consumption and verified bundle import order.
- `.planning/phases/06-runtime-adoption-surface/06-runtime-adoption-surface-02-SUMMARY.md` - Records execution, decisions, and verification for this plan.

## Decisions Made

- Centralized the adoption story in one dedicated doc so integrations and case studies can reference a shared command contract instead of drifting.
- Treated compare and doctor as mandatory promotion gates for docs and sample host rules, matching the threat model for stop-on-gate behavior.
- Kept the aionrs surface on files plus shell commands and avoided any host-specific plugin or tool abstraction.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Another in-flight branch commit (`96ea8fe`) landed between this plan's two task commits. The execution stayed isolated by staging only this plan's files and leaving unrelated worktree changes untouched.
- A stale `.git/index.lock` blocked the SUMMARY commit. Verifying that no git process was running and retrying after clearing the lock resolved it without changing repository content.
- Per user/orchestrator constraint, `.planning/STATE.md` and `.planning/ROADMAP.md` were intentionally left unchanged.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- SURF-02 now has one owner document and matching host assets, so later versioning and release work can reference a stable adoption loop instead of reconstructing it.
- The targeted doc-contract suite now catches regressions in gate ordering, stop-on-gate language, and bundle handoff sequencing.

## Self-Check: PASSED

- Found summary file at `.planning/phases/06-runtime-adoption-surface/06-runtime-adoption-surface-02-SUMMARY.md`
- Verified task commits `50dfca5` and `5ecec23` exist in git history
