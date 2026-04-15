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
| **Quick run command** | `./.venv/bin/python -m pytest tests/test_cli_workspace_safety.py tests/test_runtime_workspace_safety.py -q --maxfail=1` |
| **Full suite command** | `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_workspace_safety.py tests/test_runtime_workspace_safety.py tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_cli_observability.py -q --maxfail=1` |
| **Estimated runtime** | ~35 seconds for the quick truth probe, ~55 seconds for the full closeout gate |

---

## Sampling Rate

- **After every task commit:** Run the owning plan's targeted verify command from its `<verify>` block.
- **After `08-01`:** Run `./.venv/bin/python -m pytest tests/test_cli_workspace_safety.py tests/test_runtime_workspace_safety.py -q --maxfail=1`
- **After `08-02`:** Run `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_cli_observability.py -q --maxfail=1`
- **After `08-03`:** Run `test -f .planning/phases/03-concurrent-workspace-safety/03-VERIFICATION.md && test -f .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md && rg -n "Phase 4|Phase 8|RUNT-02|POLC-01|INT-02|FLOW-02" .planning/ROADMAP.md .planning/STATE.md .planning/REQUIREMENTS.md .planning/v1.0-MILESTONE-AUDIT.md`
- **Before `/gsd-verify-work`:** Full suite must be green and ledger audit must pass
- **Max feedback latency:** 55 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-RUNT-02-A | 08-01 | 1 | RUNT-02 | T-08-01-01 / T-08-01-02 | Shared-workspace writes stay coherent under interruption, and Phase 03 only regains verified status after current truth probes are green. | runtime + CLI integration | `./.venv/bin/python -m pytest tests/test_cli_workspace_safety.py tests/test_runtime_workspace_safety.py -q --maxfail=1` | ✅ | ⬜ pending |
| 08-INT-02-B | 08-02 | 2 | RUNT-02 | T-08-02-01 / T-08-02-02 | The canonical Phase 04 local gate is explicit and truthful: docs, helper script behavior, and `04-VERIFICATION.md` no longer disagree about what was actually verified. | tooling + docs + targeted CLI | `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_cli_observability.py -q --maxfail=1` | ✅ | ⬜ pending |
| 08-FLOW-02-C | 08-03 | 3 | RUNT-02 | T-08-03-01 / T-08-03-02 | Milestone closeout has one consistent proof chain across phase verification artifacts, roadmap/state/requirements ledgers, and the milestone audit snapshot. | ledger audit + documentation | `test -f .planning/phases/03-concurrent-workspace-safety/03-VERIFICATION.md && test -f .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md && rg -n "Phase 4|Phase 8|RUNT-02|POLC-01|INT-02|FLOW-02" .planning/ROADMAP.md .planning/STATE.md .planning/REQUIREMENTS.md .planning/v1.0-MILESTONE-AUDIT.md` | ⚠️ `03-VERIFICATION.md` missing in Wave 0 | ⬜ pending |

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
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
