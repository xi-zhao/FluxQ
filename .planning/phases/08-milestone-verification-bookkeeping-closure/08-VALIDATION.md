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

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Frameworks** | `pytest 9.0.2`, `ruff 0.15.8`, `mypy 1.20.0` |
| **Config files** | `pyproject.toml`, `mypy.ini` |
| **Quick run command** | `./scripts/dev-bootstrap.sh --help >/tmp/fluxq-dev-bootstrap-help.txt && rg -n "verify|smoke|pytest" /tmp/fluxq-dev-bootstrap-help.txt CONTRIBUTING.md scripts/dev-bootstrap.sh` |
| **Full suite command** | `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_workspace_safety.py tests/test_runtime_workspace_safety.py tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_cli_observability.py tests/test_runtime_policy.py -q --maxfail=1` |
| **Estimated runtime** | ~5 seconds for the smallest task-level smoke, task-owned smoke probes stay under ~30 seconds, and the full closeout gate stays ~55 seconds at wave boundaries |

---

## Sampling Rate

- **After every task commit:** Run the active task's smallest smoke verify command; keep task-level feedback under ~30 seconds and reserve the full closeout gate for plan or wave boundaries.
- **Task-level smoke example (`08-01` seam work):** `./.venv/bin/python -m pytest tests/test_runtime_workspace_safety.py tests/test_report_writer.py -q --maxfail=1`
- **Task-level smoke example (`08-02` docs/tooling work):** `./scripts/dev-bootstrap.sh --help >/tmp/fluxq-dev-bootstrap-help.txt && rg -n "verify|smoke|pytest" /tmp/fluxq-dev-bootstrap-help.txt CONTRIBUTING.md scripts/dev-bootstrap.sh`
- **Task-level smoke example (`08-03` ledger sync work):** `test -f .planning/phases/03-concurrent-workspace-safety/03-VERIFICATION.md && test -f .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md && rg -n "\\[x\\] \\*\\*Phase 4: Policy Acceptance Gates\\*\\*|\\[x\\] \\*\\*Phase 8: Verification And Bookkeeping Closure\\*\\*" .planning/ROADMAP.md && rg -n "^- \\[x\\] 04-0[1-4]-PLAN\\.md" .planning/ROADMAP.md | wc -l | grep -x 4 && rg -n "^- \\[x\\] 08-0[1-3]-PLAN\\.md" .planning/ROADMAP.md | wc -l | grep -x 3`
- **After Wave 1 / `08-01` closeout:** Run `./.venv/bin/python -m pytest tests/test_cli_workspace_safety.py tests/test_runtime_workspace_safety.py tests/test_report_writer.py tests/test_runtime_imports.py tests/test_runtime_revision_artifacts.py tests/test_cli_exec.py -q --maxfail=1`
- **After Wave 2 / `08-02` closeout:** Run `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_cli_observability.py tests/test_runtime_policy.py -q --maxfail=1`
- **After Wave 3 / `08-03` closeout:** Run `test -f .planning/phases/03-concurrent-workspace-safety/03-VERIFICATION.md && test -f .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md && rg -n "\\[x\\] \\*\\*Phase 4: Policy Acceptance Gates\\*\\*|\\[x\\] \\*\\*Phase 8: Verification And Bookkeeping Closure\\*\\*" .planning/ROADMAP.md && rg -n "^- \\[x\\] 04-0[1-4]-PLAN\\.md" .planning/ROADMAP.md | wc -l | grep -x 4 && rg -n "^- \\[x\\] 08-0[1-3]-PLAN\\.md" .planning/ROADMAP.md | wc -l | grep -x 3 && rg -n "RUNT-02|INT-02|FLOW-02" .planning/ROADMAP.md .planning/STATE.md .planning/REQUIREMENTS.md .planning/v1.0-MILESTONE-AUDIT.md`
- **Before `/gsd-verify-work`:** Full suite must be green and ledger audit must pass
- **Max feedback latency:** ~25 seconds for task-level smoke; ~55 seconds is reserved for wave-boundary closeout gates

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-RUNT-02-A | 08-01 | 1 | RUNT-02 | T-08-01-01 / T-08-01-02 | Shared-workspace writes stay coherent under interruption, and Phase 03 only regains verified status after the report/commit seam smoke is green. | runtime seam smoke | `./.venv/bin/python -m pytest tests/test_runtime_workspace_safety.py tests/test_report_writer.py -q --maxfail=1` | ✅ | ⬜ pending |
| 08-INT-02-B | 08-02 | 2 | RUNT-02 | T-08-02-01 / T-08-02-02 | The canonical Phase 04 local gate is explicit and truthful: docs, helper script behavior, and `04-VERIFICATION.md` no longer disagree about what was actually verified. | tooling + docs smoke (exact gate stays at wave boundary) | `./scripts/dev-bootstrap.sh --help >/tmp/fluxq-dev-bootstrap-help.txt && rg -n "verify|smoke|pytest" /tmp/fluxq-dev-bootstrap-help.txt CONTRIBUTING.md scripts/dev-bootstrap.sh && rg -n "tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_cli_observability.py tests/test_runtime_policy.py" CONTRIBUTING.md` | ✅ | ⬜ pending |
| 08-FLOW-02-C | 08-03 | 3 | RUNT-02 | T-08-03-01 / T-08-03-02 | Milestone closeout has one consistent proof chain across phase verification artifacts, checked roadmap phase/plan checkboxes, roadmap/state/requirements ledgers, and the milestone audit snapshot. | ledger audit + documentation | `test -f .planning/phases/03-concurrent-workspace-safety/03-VERIFICATION.md && test -f .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md && rg -n "\\[x\\] \\*\\*Phase 4: Policy Acceptance Gates\\*\\*|\\[x\\] \\*\\*Phase 8: Verification And Bookkeeping Closure\\*\\*" .planning/ROADMAP.md && rg -n "^- \\[x\\] 04-0[1-4]-PLAN\\.md" .planning/ROADMAP.md | wc -l | grep -x 4 && rg -n "^- \\[x\\] 08-0[1-3]-PLAN\\.md" .planning/ROADMAP.md | wc -l | grep -x 3 && rg -n "RUNT-02|INT-02|FLOW-02" .planning/ROADMAP.md .planning/STATE.md .planning/REQUIREMENTS.md .planning/v1.0-MILESTONE-AUDIT.md` | ⚠️ `03-VERIFICATION.md` missing in Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `.planning/phases/03-concurrent-workspace-safety/03-VERIFICATION.md` does not exist yet.
- [ ] `tests/test_runtime_workspace_safety.py::test_interrupted_commit_keeps_previous_current_revision_authoritative` is currently red and blocks truthful Phase 03 closure.
- [ ] `.planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md` still reports `status: gaps_found`.
- [ ] `CONTRIBUTING.md` and `scripts/dev-bootstrap.sh` still disagree about whether `./scripts/dev-bootstrap.sh verify` is the exact Phase 4 gate or a broader repo smoke command.
- [ ] Final ledger sync across `.planning/ROADMAP.md`, `.planning/STATE.md`, `.planning/REQUIREMENTS.md`, and `.planning/v1.0-MILESTONE-AUDIT.md` still needs one explicit closeout pass.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | Phase 08 should stay automatable: the blocker is proof-chain drift, and the owned truth sets are already expressible as pytest, lint/type, and ledger-audit commands. | N/A |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Phase 03 truth probe is green before `03-VERIFICATION.md` is written
- [ ] Phase 04 canonical gate decision is explicit before `04-VERIFICATION.md` is refreshed
- [ ] Ledger audit passes before milestone closeout is marked complete
- [ ] No watch-mode flags
- [ ] Task-level feedback latency stays below ~30s; longer gates are reserved for wave boundaries
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
