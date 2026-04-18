---
phase: 07
slug: compare-trust-closure
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-15
---

# Phase 07 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Frameworks** | `pytest 9.0.2`, `ruff 0.15.8`, `mypy 1.20.0` |
| **Config files** | `pyproject.toml`, `mypy.ini` |
| **Quick run command** | `./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_runtime_compare.py tests/test_runtime_imports.py tests/test_runtime_revision_artifacts.py tests/test_cli_exec.py -q --maxfail=1` |
| **Full suite command** | `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_runtime_compare.py tests/test_runtime_imports.py tests/test_runtime_revision_artifacts.py tests/test_cli_exec.py -q --maxfail=1` |
| **Estimated runtime** | ~20 seconds for the targeted compare-trust suite, ~35 seconds for the full gate |

---

## Sampling Rate

- **After every task commit:** Run the owning plan’s targeted pytest command from its `<verify>` block.
- **After every plan wave:** Run `./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_runtime_compare.py tests/test_runtime_imports.py tests/test_runtime_revision_artifacts.py tests/test_cli_exec.py -q --maxfail=1`
- **Wave 3 rule:** `07-03` only runs after `07-02` compare suites are green, because it reuses the full Phase 07 gate rather than an exec/import-only subset.
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 35 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 07-POLC-01-A | 07-01 | 1 | POLC-01 | T-07-01-01 / T-07-01-02 | Exec writes one coherent revision truth layer: `qspec`, `report`, and manifest all describe the same canonical history artifact instead of alias-backfilled content. | runtime + exec | `./.venv/bin/python -m pytest tests/test_runtime_revision_artifacts.py tests/test_cli_exec.py tests/test_runtime_imports.py -q --maxfail=1` | ✅ | ⬜ pending |
| 07-POLC-01-B | 07-02 | 2 | POLC-01 | T-07-02-01 / T-07-02-02 | Baseline/current compare returns the existing `ComparePolicy` verdict/gate path with `exit=2` on subject drift instead of failing early on artifact inconsistency. | CLI + runtime | `./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_runtime_compare.py -q --maxfail=1` | ✅ | ⬜ pending |
| 07-POLC-01-C | 07-03 | 3 | POLC-01 | T-07-03-01 / T-07-03-02 | Final hardening gate after 07-01 writer repair and 07-02 compare recovery; cross-phase regressions catch any future drift between exec artifact writing and compare/import trust consumers before milestone audit. | regression + integration | `./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_runtime_compare.py tests/test_runtime_imports.py tests/test_runtime_revision_artifacts.py tests/test_cli_exec.py -q --maxfail=1` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] Existing focused suites already cover the red path we need: `tests/test_cli_compare.py`, `tests/test_cli_runtime_gap.py`, `tests/test_runtime_compare.py`, `tests/test_runtime_imports.py`, `tests/test_runtime_revision_artifacts.py`, and `tests/test_cli_exec.py`.
- [ ] Add at least one regression that proves a second `exec` cannot leave `reports/history/<revision>.json` and `specs/history/<revision>.json` semantically inconsistent for the same revision.
- [ ] Add at least one regression that proves baseline compare returns `subject_drift` gate output again after the writer-side fix lands.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | This phase should remain fully automatable because the break is in runtime artifact consistency and compare policy wiring, both of which already have reproducible pytest coverage. | N/A |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Baseline compare and explicit revision compare are both green
- [ ] No watch-mode flags
- [ ] Feedback latency < 40s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
