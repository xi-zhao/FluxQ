---
phase: 09
slug: ibm-access-backend-readiness
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-18
---

# Phase 09 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Frameworks** | `pytest 9.0.2`, `ruff 0.15.8`, `mypy 1.20.0` |
| **Config files** | `pyproject.toml`, `mypy.ini` |
| **Quick run command** | `uv run pytest tests/test_cli_ibm_config.py tests/test_cli_backend_list.py tests/test_cli_doctor.py tests/test_cli_observability.py -x` |
| **Full suite command** | `uv run ruff check src tests && uv run python -m mypy src && uv run pytest tests/test_cli_ibm_config.py tests/test_cli_backend_list.py tests/test_cli_doctor.py tests/test_cli_observability.py -q --maxfail=1` |
| **Estimated runtime** | ~20 seconds for the task-level smoke, ~35 seconds for the full Phase 09 gate |

---

## Sampling Rate

- **After every task commit:** Run the owning task's smallest smoke verify command.
- **After Wave 1:** Run `uv run pytest tests/test_cli_ibm_config.py -q --maxfail=1`
- **After Wave 2:** Run `uv run pytest tests/test_cli_backend_list.py tests/test_cli_doctor.py tests/test_cli_observability.py -q --maxfail=1`
- **After every plan wave:** Run `uv run ruff check src tests && uv run python -m mypy src && uv run pytest tests/test_cli_ibm_config.py tests/test_cli_backend_list.py tests/test_cli_doctor.py tests/test_cli_observability.py -q --maxfail=1`
- **Before `/gsd-verify-work`:** Full suite must be green, and one protected manual IBM smoke recipe must be available in the verification artifacts
- **Max feedback latency:** 35 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-AUTH-01-A | 09-01 | 1 | AUTH-01 | T-09-01-01 / T-09-01-02 | `qrun ibm configure` writes only non-secret profile references and never persists tokens into `.quantum/`. | CLI + config | `uv run pytest tests/test_cli_ibm_config.py -q --maxfail=1` | ❌ Wave 0 | ⬜ pending |
| 09-AUTH-01-B | 09-02 | 2 | AUTH-01 | T-09-02-01 / T-09-02-03 | 仅当 workspace 显式配置 `[remote.ibm]` 时，IBM auth/profile resolution 才会 fail-close；未 opt-in workspace 保持现有 local-only doctor 行为。 | CLI + runtime | `uv run pytest tests/test_cli_doctor.py::test_doctor_ci_blocks_missing_ibm_token_env_when_remote_ibm_configured tests/test_cli_doctor.py::test_doctor_ci_skips_ibm_checks_without_remote_ibm_profile tests/test_cli_doctor.py::test_doctor_ci_reports_ibm_runtime_dependency_missing_when_opted_in -q --maxfail=1` | ✅ | ⬜ pending |
| 09-AUTH-01-C | 09-02 | 2 | AUTH-01 | T-09-02-02 / T-09-02-03 | `doctor --jsonl --ci` emits the same IBM reason codes / next_actions / gate as JSON mode, without leaking secret material. | CLI + observability | `uv run pytest tests/test_cli_observability.py::test_doctor_jsonl_ci_preserves_ibm_reason_codes_and_gate tests/test_cli_observability.py::test_doctor_jsonl_ci_redacts_ibm_secret_material -q --maxfail=1` | ✅ | ⬜ pending |
| 09-BACK-01-D | 09-03 | 2 | BACK-01 | T-09-03-01 / T-09-03-03 | `backend list --json --workspace <path>` exposes IBM provider context and inventory summary without silently auto-selecting a backend. | CLI + runtime | `uv run pytest tests/test_cli_backend_list.py::test_backend_list_json_accepts_workspace_option tests/test_cli_backend_list.py::test_backend_list_json_reports_ibm_runtime_descriptor tests/test_cli_backend_list.py::test_backend_list_json_omits_auto_selection_fields -q --maxfail=1` | ✅ | ⬜ pending |
| 09-BACK-01-E | 09-03 | 2 | BACK-01 | T-09-03-01 / T-09-03-02 | `backend list --json` projects IBM target readiness through the shared `build_ibm_service()` seam and still returns a blocked-but-readable payload when the IBM service cannot be built. | CLI + runtime | `uv run pytest tests/test_cli_backend_list.py::test_backend_list_json_projects_ibm_target_readiness tests/test_cli_backend_list.py::test_backend_list_json_returns_blocked_remote_state_when_ibm_service_unavailable -q --maxfail=1` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cli_ibm_config.py` must be created for non-secret profile persistence and configure JSON output.
- [ ] `src/quantum_runtime/runtime/ibm_access.py` must export `build_ibm_service()` so Wave 2 can fake provider access and handle missing optional extras without direct IBM SDK imports.
- [ ] `qiskit-ibm-runtime` optional `ibm` extra and documented install path must be added before merge.
- [ ] `tests/test_cli_backend_list.py` must gain IBM provider context and target readiness coverage.
- [ ] `tests/test_cli_doctor.py` must gain IBM profile / instance / backend readiness gate coverage.
- [ ] `tests/test_cli_observability.py` must gain IBM doctor JSONL event coverage.
- [ ] A protected manual smoke recipe for live IBM auth plus backend discovery must be written into the final verification artifacts.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real IBM profile can authenticate and list at least one target backend | AUTH-01 / BACK-01 | Live credentials and instance access should stay outside the fast mocked lane | `QISKIT_IBM_TOKEN=... QISKIT_IBM_INSTANCE=... uv run qrun backend list --json` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Phase 09 stays scoped to access/readiness only and does not leak into remote submit/job lifecycle work
- [ ] No watch-mode flags
- [ ] Feedback latency < 40s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
