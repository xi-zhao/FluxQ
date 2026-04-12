---
phase: 04
slug: policy-acceptance-gates
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 9.0.2` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_runtime_compare.py -q --maxfail=1` |
| **Full suite command** | `./.venv/bin/python -m pytest -q --ignore tests/test_classiq_backend.py --ignore tests/test_classiq_emitter.py --ignore tests/test_qspec_validation.py` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** Run `./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_runtime_compare.py -q --maxfail=1`
- **After every plan wave:** Run `./.venv/bin/python -m pytest -q --ignore tests/test_classiq_backend.py --ignore tests/test_classiq_emitter.py --ignore tests/test_qspec_validation.py`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-POLC-01 | TBD | TBD | POLC-01 | T-04-01 / — | Compare baseline/current policy decisions fail on selected drift classes through FluxQ-owned JSON + exit behavior. | CLI + runtime | `./.venv/bin/python -m pytest tests/test_runtime_compare.py tests/test_cli_compare.py tests/test_cli_runtime_gap.py -q --maxfail=1` | ✅ | ⬜ pending |
| 04-POLC-02 | TBD | TBD | POLC-02 | T-04-02 / — | Benchmark evidence is policy-evaluable only when subject identity and comparability checks pass. | CLI + runtime | `./.venv/bin/python -m pytest tests/test_cli_bench.py -q --maxfail=1` | ✅ | ⬜ pending |
| 04-POLC-03 | TBD | TBD | POLC-03 | T-04-03 / — | Doctor CI mode emits explicit blocking vs advisory output with stable machine-readable gate metadata. | CLI + runtime | `./.venv/bin/python -m pytest tests/test_cli_doctor.py -q --maxfail=1` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_runtime_policy.py` — shared benchmark/doctor policy evaluator coverage
- [ ] `tests/test_cli_bench.py` — imported-revision benchmark persistence regression coverage
- [ ] `tests/test_cli_compare.py` or `tests/test_cli_runtime_gap.py` — persisted compare artifact `schema_version` regression coverage
- [ ] `tests/test_cli_doctor.py` — `--ci` blocking/advisory JSON and JSONL coverage
- [ ] repair or recreate the local `mypy` entrypoint in `.venv` before claiming type-check completion

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | All planned Phase 4 behaviors should be automatable once Wave 0 gaps are closed. | N/A |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all missing references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
