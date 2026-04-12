---
phase: 04
slug: policy-acceptance-gates
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-13
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Frameworks** | `pytest 9.0.2`, `ruff 0.15.8`, `mypy 1.20.0` |
| **Config files** | `pyproject.toml`, `mypy.ini` |
| **Quick run command** | `waves 1-2: ./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py -q --maxfail=1` / `waves 3-4: ./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_runtime_policy.py -q --maxfail=1` |
| **Full suite command** | `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_cli_observability.py tests/test_runtime_policy.py -q --maxfail=1` |
| **Estimated runtime** | ~25 seconds for wave smoke, ~35 seconds for the full suite |

---

## Sampling Rate

- **After every task commit:** Run the owning plan's targeted pytest command from its `<verify>` block.
- **After plan waves 1-2:** Run `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py -q --maxfail=1`
- **After plan waves 3-4:** Run `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_runtime_policy.py -q --maxfail=1`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 25 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-VAL-01 | 04-01 | 1 | — validation enablement | T-04-01-01 / T-04-01-02 | Repo-local verification includes Ruff, path-safe MyPy, and the executable pre-04-03 Phase 4 smoke gate. | Tooling + docs | `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py -q --maxfail=1` | ✅ | ⬜ pending |
| 04-POLC-01 | 04-02 | 2 | POLC-01 | T-04-02-01 / T-04-02-02 | Compare baseline/current policy decisions fail on selected drift classes through FluxQ-owned JSON, gate output, and exit code `2`. | CLI + runtime | `./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py -q --maxfail=1` | ✅ | ⬜ pending |
| 04-POLC-02 | 04-03 | 3 | POLC-02 | T-04-03-01 / T-04-03-03 | Benchmark evidence is policy-evaluable only when subject identity, saved baseline evidence, and comparability checks pass. | CLI + runtime | `./.venv/bin/python -m pytest tests/test_cli_bench.py tests/test_cli_observability.py tests/test_runtime_policy.py -q --maxfail=1` | ⚠️ created by plan | ⬜ pending |
| 04-POLC-03 | 04-04 | 4 | POLC-03 | T-04-04-01 / T-04-04-03 | Doctor CI mode emits explicit blocking versus advisory output with stable machine-readable gate metadata. | CLI + runtime | `./.venv/bin/python -m pytest tests/test_cli_doctor.py tests/test_cli_observability.py tests/test_runtime_policy.py -q --maxfail=1` | ⚠️ updated by plan | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Coverage

- [x] `04-01` owns the path-safe MyPy verification path and the pre-04-03 Ruff/MyPy/pytest smoke gate.
- [x] `04-02` owns baseline/current compare fail-on coverage plus persisted compare `schema_version` regression checks.
- [ ] `tests/test_runtime_policy.py` does not exist until `04-03`, so Wave 0 is not complete and the post-04-03 smoke command only becomes valid after Wave 3 lands.
- [x] `04-03` creates `tests/test_runtime_policy.py` and owns benchmark policy plus imported-revision persistence coverage.
- [x] `04-04` owns `doctor --ci` blocking/advisory JSON and JSONL coverage.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | All planned Phase 4 behaviors should be automatable once Wave 0 gaps are closed. | N/A |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Pre-04-03 and post-04-03 smoke commands are used in the correct waves
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
