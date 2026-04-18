---
phase: 10
slug: canonical-remote-submit-attempt-records
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-18
---

# Phase 10 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Frameworks** | `pytest 9.0.2`, `ruff 0.15.8`, `mypy 1.20.0` |
| **Config files** | `pyproject.toml`, `mypy.ini` |
| **Quick run command** | `uv run pytest tests/test_runtime_remote_attempts.py tests/test_cli_remote_submit.py -q --maxfail=1` |
| **Full suite command** | `uv run ruff check src tests && uv run python -m mypy src && uv run pytest tests/test_runtime_remote_attempts.py tests/test_cli_remote_submit.py tests/test_cli_observability.py -q --maxfail=1` |
| **Estimated runtime** | ~25 seconds for smoke, ~45 seconds for the full Phase 10 gate |

---

## Sampling Rate

- **After every task commit:** Run the owning task's smallest smoke verify command.
- **After Wave 1:** Run `uv run pytest tests/test_runtime_remote_attempts.py -q --maxfail=1`
- **After Wave 2:** Run `uv run pytest tests/test_cli_remote_submit.py tests/test_cli_observability.py -q --maxfail=1`
- **After every plan wave:** Run `uv run ruff check src tests && uv run python -m mypy src && uv run pytest tests/test_runtime_remote_attempts.py tests/test_cli_remote_submit.py tests/test_cli_observability.py -q --maxfail=1`
- **Before `/gsd-verify-work`:** Full suite must be green and one protected live IBM submit smoke must be documented in the verification artifacts
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 10-REMT-01-A | 10-01 | 1 | REMT-01 | T-10-01-01 / T-10-01-02 | Canonical remote submit reuses the existing ingress selectors and resolves one trusted `QSpec` without bumping `current_revision`. | runtime + persistence | `uv run pytest tests/test_runtime_remote_attempts.py::test_remote_attempt_persistence_does_not_bump_workspace_revision tests/test_runtime_remote_attempts.py::test_remote_attempt_snapshots_reuse_resolved_qspec_metadata -q --maxfail=1` | ❌ Wave 0 | ⬜ pending |
| 10-REMT-02-B | 10-01 | 1 | REMT-02 | T-10-01-03 / T-10-01-04 | Submit persistence writes a durable attempt record with `attempt_id`, `job_id`, `backend`, `instance`, and submit-time provenance, but no final report alias and no secret material. | runtime + integrity | `uv run pytest tests/test_runtime_remote_attempts.py::test_remote_attempt_record_persists_provider_handle_and_provenance tests/test_runtime_remote_attempts.py::test_remote_attempt_record_redacts_secret_material -q --maxfail=1` | ❌ Wave 0 | ⬜ pending |
| 10-REMT-01-C | 10-02 | 2 | REMT-01 | T-10-02-01 / T-10-02-02 | `qrun remote submit` accepts the same single-input selector family as `qrun exec` and requires an explicit backend instead of implicit provider selection. | CLI + input parity | `uv run pytest tests/test_cli_remote_submit.py::test_remote_submit_json_accepts_exec_input_selectors tests/test_cli_remote_submit.py::test_remote_submit_json_requires_explicit_backend -q --maxfail=1` | ❌ Wave 0 | ⬜ pending |
| 10-REMT-02-D | 10-02 | 2 | REMT-02 | T-10-02-03 / T-10-02-04 | Successful submit returns a schema-versioned payload with stable attempt metadata and writes the corresponding attempt record to `.quantum/remote/...` immediately. | CLI + workspace | `uv run pytest tests/test_cli_remote_submit.py::test_remote_submit_json_persists_attempt_record tests/test_cli_remote_submit.py::test_remote_submit_json_keeps_revision_aliases_unchanged -q --maxfail=1` | ❌ Wave 0 | ⬜ pending |
| 10-REMT-02-E | 10-03 | 2 | REMT-02 | T-10-03-01 / T-10-03-02 | `qrun remote submit --jsonl` emits submit lifecycle events with the same reason-code / gate semantics as JSON mode and does not leak token bytes or provider headers. | CLI + observability | `uv run pytest tests/test_cli_observability.py::test_remote_submit_jsonl_preserves_attempt_reason_codes tests/test_cli_observability.py::test_remote_submit_jsonl_redacts_ibm_secret_material -q --maxfail=1` | ❌ Wave 0 | ⬜ pending |
| 10-REMT-01-F | 10-03 | 2 | REMT-01 | T-10-03-03 / T-10-03-04 | Report-file and revision-backed submit paths reuse trusted import resolution rather than reparsing or mutating the active finalized revision. | runtime + imports | `uv run pytest tests/test_cli_remote_submit.py::test_remote_submit_json_accepts_report_file_input tests/test_cli_remote_submit.py::test_remote_submit_json_accepts_revision_input_without_finalizing_new_report -q --maxfail=1` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_runtime_remote_attempts.py` must be created for attempt sequencing, persistence, integrity, and revision-separation checks.
- [ ] `tests/test_cli_remote_submit.py` must be created for input parity, explicit backend requirement, JSON payload, and workspace-safety regressions.
- [ ] `src/quantum_runtime/runtime/remote_attempts.py` (or equivalent) must exist as the typed persistence seam before CLI work lands.
- [ ] `src/quantum_runtime/runtime/remote_submit.py` (or equivalent) must exist as the canonical submit orchestrator instead of branching submit logic inside `executor.py`.
- [ ] Remote attempt workspace paths must be defined in `src/quantum_runtime/workspace/paths.py`, and the chosen attempt-counter strategy must be persisted safely.
- [ ] A protected live IBM submit smoke recipe must be written into the final verification artifacts.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real IBM job-mode submit returns a usable provider job ID and local attempt record | REMT-01 / REMT-02 | Live IBM credentials, instance access, and spend-bearing provider submission must stay outside the fast mocked lane | `QISKIT_IBM_TOKEN=... uv run qrun remote submit --workspace .quantum --intent-file examples/ghz.md --backend <ibm-backend> --json` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all missing remote-attempt test references
- [ ] No watch-mode flags
- [ ] Feedback latency < 50s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
