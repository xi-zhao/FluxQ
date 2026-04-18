---
phase: 06
slug: runtime-adoption-surface
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-15
---

# Phase 06 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Frameworks** | `pytest 9.0.2`, `ruff 0.15.8`, `mypy 1.20.0`, `build 1.3.0` |
| **Config files** | `pyproject.toml`, `mypy.ini` |
| **Quick run command** | `./.venv/bin/python -m pytest tests/test_release_docs.py tests/test_aionrs_assets.py tests/test_open_source_release.py tests/test_packaging_release.py -q --maxfail=1` |
| **Full suite command** | `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_release_docs.py tests/test_aionrs_assets.py tests/test_open_source_release.py tests/test_packaging_release.py -q --maxfail=1 && ./.venv/bin/python -m build` |
| **Estimated runtime** | ~20 seconds for the targeted docs/adoption suite, ~40 seconds for the full gate |

---

## Sampling Rate

- **After every task commit:** Run the owning plan's targeted pytest command from its `<verify>` block.
- **After every plan wave:** Run `./.venv/bin/python -m pytest tests/test_release_docs.py tests/test_aionrs_assets.py tests/test_open_source_release.py tests/test_packaging_release.py -q --maxfail=1`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 40 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-SURF-01 | 06-01 | 1 | SURF-01 | T-06-01-01 / T-06-01-02 | README / release-facing docs consistently present FluxQ as an agent-first runtime/control-plane product, and package metadata no longer undermines that story. | docs + metadata | `./.venv/bin/python -m pytest tests/test_release_docs.py tests/test_packaging_release.py -q --maxfail=1` | ✅ | ⬜ pending |
| 06-SURF-02 | 06-02 | 2 | SURF-02 | T-06-02-01 / T-06-02-03 | Repo docs and integration assets expose one coherent end-to-end adoption workflow covering ingress, execution, policy, and delivery handoff. | docs + integration | `./.venv/bin/python -m pytest tests/test_release_docs.py tests/test_aionrs_assets.py -q --maxfail=1` | ✅ | ⬜ pending |
| 06-SURF-03 | 06-03 | 2 | SURF-03 | T-06-03-01 / T-06-03-02 | Versioning and release artifacts clearly distinguish stable / evolving / optional runtime contracts and safe adopter consumption guidance. | docs + packaging | `./.venv/bin/python -m pytest tests/test_release_docs.py tests/test_open_source_release.py tests/test_packaging_release.py -q --maxfail=1` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_release_docs.py` needs new assertions for one coherent runtime adoption loop, including `baseline set` before `compare --baseline` and explicit delivery handoff commands.
- [ ] `tests/test_aionrs_assets.py` needs to lock at least one policy surface and one handoff surface in the aionrs integration assets.
- [ ] `docs/versioning.md` needs test-covered stable / evolving / optional contract sections instead of only release-line summaries.
- [ ] If the QAOA case study becomes a primary adoption asset, either `README.md` or `tests/test_release_docs.py` must explicitly reference and lock it.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | This phase should remain fully automatable because it is a docs/examples/metadata phase and all target surfaces can be locked through repository tests and build checks. | N/A |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Quickstart / release / integration docs describe one coherent adoption flow
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
