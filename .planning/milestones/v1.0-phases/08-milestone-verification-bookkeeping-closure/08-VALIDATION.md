---
phase: 08
slug: milestone-verification-bookkeeping-closure
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-16
---

# Phase 08 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

> Gap replanning note: Waves 1-3 have already executed. Remaining work is the reopened alias-promotion fix (`08-04`) and proof-chain regeneration (`08-05`).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Frameworks** | `pytest 9.0.2`, `ruff 0.15.8`, `mypy 1.20.0` |
| **Config files** | `pyproject.toml`, `mypy.ini` |
| **Quick run command** | `./.venv/bin/python -m pytest tests/test_runtime_workspace_safety.py -q --maxfail=1` |
| **Full suite command** | `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_workspace_safety.py tests/test_runtime_workspace_safety.py tests/test_report_writer.py tests/test_runtime_imports.py tests/test_runtime_revision_artifacts.py tests/test_cli_exec.py tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_cli_observability.py tests/test_runtime_policy.py -q --maxfail=1` |
| **Estimated runtime** | ~10 seconds for the reopened alias-promotion smoke, task-owned smoke probes stay under ~30 seconds, and the full regression + closeout gate stays ~60 seconds at wave boundaries |

---

## Sampling Rate

- **After every task commit:** Run the active task's smallest smoke verify command; keep task-level feedback under ~30 seconds and reserve the full closeout gate for plan or wave boundaries.
- **Task-level smoke example (`08-04` alias-promotion gap):** `./.venv/bin/python -m pytest tests/test_runtime_workspace_safety.py -q --maxfail=1`
- **Task-level smoke example (`08-05` proof-chain refresh):** `rg -n "^status: passed$|alias-promotion|WorkspaceRecoveryRequiredError|RUNT-02" .planning/phases/03-concurrent-workspace-safety/03-VERIFICATION.md && rg -n "^status: passed$|alias-promotion|WorkspaceRecoveryRequiredError|RUNT-02" .planning/phases/08-milestone-verification-bookkeeping-closure/08-VERIFICATION.md && ! rg -n '^status: gaps_found$|RUNT-02 therefore remains open|Phase 08 should stay open until|✗ FAILED|✗ BLOCKED' .planning/phases/08-milestone-verification-bookkeeping-closure/08-VERIFICATION.md && rg -n "^\\- \\[x\\] \\*\\*RUNT-02\\*\\*" .planning/REQUIREMENTS.md && rg -n "RUNT-02 \\| Phase 08 \\| Complete" .planning/REQUIREMENTS.md`
- **After Wave 4 / `08-04` closeout:** Run `./.venv/bin/python -m pytest tests/test_runtime_workspace_safety.py tests/test_runtime_imports.py tests/test_runtime_revision_artifacts.py tests/test_cli_exec.py -q --maxfail=1`
- **After Wave 5 / `08-05` closeout:** Run `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_workspace_safety.py tests/test_runtime_workspace_safety.py tests/test_report_writer.py tests/test_runtime_imports.py tests/test_runtime_revision_artifacts.py tests/test_cli_exec.py tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_cli_observability.py tests/test_runtime_policy.py -q --maxfail=1 && rg -n "\\[x\\] \\*\\*Phase 8: Verification And Bookkeeping Closure\\*\\*" .planning/ROADMAP.md && test "$(rg -n '^- \\[x\\] 08-0[1-5]-PLAN\\.md' .planning/ROADMAP.md | wc -l | tr -d ' ')" = "5" && rg -n "^\\| 8\\. Verification And Bookkeeping Closure \\| 5/5 \\| Complete \\| " .planning/ROADMAP.md && rg -n "^\\- \\[x\\] \\*\\*RUNT-02\\*\\*" .planning/REQUIREMENTS.md && rg -n "RUNT-02 \\| Phase 08 \\| Complete" .planning/REQUIREMENTS.md && rg -n "Phase: 08 .*COMPLETE" .planning/STATE.md && rg -n "Phase complete" .planning/STATE.md && rg -n "No blockers" .planning/STATE.md && rg -n "alias-promotion recovery hole is closed|proof chain has been regenerated" .planning/STATE.md && rg -n "^status: passed$" .planning/v1.0-MILESTONE-AUDIT.md && rg -n "03-VERIFICATION\\.md" .planning/v1.0-MILESTONE-AUDIT.md && rg -n "08-VERIFICATION\\.md" .planning/v1.0-MILESTONE-AUDIT.md && rg -n "08-04-PLAN\\.md" .planning/v1.0-MILESTONE-AUDIT.md && rg -n "08-05-PLAN\\.md" .planning/v1.0-MILESTONE-AUDIT.md && rg -n "corrected alias-promotion proof|corrected proof chain" .planning/v1.0-MILESTONE-AUDIT.md`
- **Before `/gsd-verify-work`:** Full suite must be green and ledger audit must pass
- **Max feedback latency:** ~25 seconds for task-level smoke; ~60 seconds is reserved for wave-boundary closeout gates

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-RUNT-02-D | 08-04 | 4 | RUNT-02 | T-08-04-01 / T-08-04-02 | Forced failure after `specs/current.json` promotion can no longer leave the next `exec` running past recovery with mixed active aliases. | runtime seam smoke | `./.venv/bin/python -m pytest tests/test_runtime_workspace_safety.py -q --maxfail=1` | ✅ | ⬜ pending |
| 08-FLOW-02-E | 08-05 | 5 | RUNT-02 | T-08-05-01 / T-08-05-02 | The regenerated Phase 03 / Phase 08 verification artifacts and the reopened bookkeeping chain only re-close once the corrected alias-promotion proof is in place. | verification + ledger audit | `rg -n "^status: passed$|alias-promotion|WorkspaceRecoveryRequiredError|RUNT-02" .planning/phases/03-concurrent-workspace-safety/03-VERIFICATION.md && rg -n "^status: passed$|alias-promotion|WorkspaceRecoveryRequiredError|RUNT-02" .planning/phases/08-milestone-verification-bookkeeping-closure/08-VERIFICATION.md && ! rg -n '^status: gaps_found$|RUNT-02 therefore remains open|Phase 08 should stay open until|✗ FAILED|✗ BLOCKED' .planning/phases/08-milestone-verification-bookkeeping-closure/08-VERIFICATION.md && rg -n "^\\- \\[x\\] \\*\\*RUNT-02\\*\\*" .planning/REQUIREMENTS.md && rg -n "RUNT-02 \\| Phase 08 \\| Complete" .planning/REQUIREMENTS.md && rg -n "Phase: 08 .*COMPLETE" .planning/STATE.md && rg -n "Phase complete" .planning/STATE.md && rg -n "No blockers" .planning/STATE.md && rg -n "alias-promotion recovery hole is closed|proof chain has been regenerated" .planning/STATE.md && rg -n "^status: passed$" .planning/v1.0-MILESTONE-AUDIT.md && rg -n "03-VERIFICATION\\.md" .planning/v1.0-MILESTONE-AUDIT.md && rg -n "08-VERIFICATION\\.md" .planning/v1.0-MILESTONE-AUDIT.md && rg -n "08-04-PLAN\\.md" .planning/v1.0-MILESTONE-AUDIT.md && rg -n "08-05-PLAN\\.md" .planning/v1.0-MILESTONE-AUDIT.md && rg -n "corrected alias-promotion proof|corrected proof chain" .planning/v1.0-MILESTONE-AUDIT.md` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/quantum_runtime/runtime/executor.py` still allows `_promote_exec_aliases()` to stop after `specs/current.json` moves and before `reports/latest.json` / `manifests/latest.json` move.
- [ ] `tests/test_runtime_workspace_safety.py` does not yet force alias-promotion interruption after qspec alias movement.
- [ ] `.planning/phases/03-concurrent-workspace-safety/03-VERIFICATION.md` and `.planning/phases/08-milestone-verification-bookkeeping-closure/08-VERIFICATION.md` need regeneration from the corrected proof.
- [ ] `ROADMAP.md`, `STATE.md`, `REQUIREMENTS.md`, and `.planning/v1.0-MILESTONE-AUDIT.md` currently overstate Phase 08 closure and must be re-synchronized after `08-04`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | Phase 08 should stay automatable: the blocker is proof-chain drift, and the owned truth sets are already expressible as pytest, lint/type, and ledger-audit commands. | N/A |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] The alias-promotion interruption path is covered and green before `03-VERIFICATION.md` and `08-VERIFICATION.md` are rewritten
- [ ] Ledger audit passes only after the reopened proof chain is regenerated
- [ ] No watch-mode flags
- [ ] Task-level feedback latency stays below ~30s; longer gates are reserved for wave boundaries
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
