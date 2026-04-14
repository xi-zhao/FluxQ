---
phase: 05
slug: verified-delivery-bundles
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-14
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Frameworks** | `pytest 9.0.2`, `ruff 0.15.8`, `mypy 1.20.0` |
| **Config files** | `pyproject.toml`, `mypy.ini` |
| **Quick run command** | `waves 1-2: ./.venv/bin/python -m pytest tests/test_cli_runtime_gap.py tests/test_pack_bundle.py -q --maxfail=1` / `wave 3: ./.venv/bin/python -m pytest tests/test_cli_runtime_gap.py tests/test_pack_bundle.py tests/test_cli_pack_import.py tests/test_runtime_imports.py -q --maxfail=1` |
| **Full suite command** | `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_runtime_gap.py tests/test_pack_bundle.py tests/test_cli_pack_import.py tests/test_runtime_imports.py -q --maxfail=1` |
| **Estimated runtime** | ~15 seconds for quick bundle checks, ~35 seconds for the full gate |

---

## Sampling Rate

- **After every task commit:** Run the owning plan's targeted pytest command from its `<verify>` block.
- **After plan waves 1-2:** Run `./.venv/bin/python -m pytest tests/test_cli_runtime_gap.py tests/test_pack_bundle.py -q --maxfail=1`
- **After plan wave 3:** Run `./.venv/bin/python -m pytest tests/test_cli_runtime_gap.py tests/test_pack_bundle.py tests/test_cli_pack_import.py tests/test_runtime_imports.py -q --maxfail=1`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 35 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-DELV-01 | 05-01 | 1 | DELV-01 | T-05-01-01 / T-05-01-03 | `qrun pack` rejects malformed revisions, packages immutable revision artifacts plus bundle trust metadata, and never deletes the last good bundle before staged verification passes. | CLI + runtime | `./.venv/bin/python -m pytest tests/test_cli_runtime_gap.py tests/test_pack_bundle.py -q --maxfail=1` | ✅ | ⬜ pending |
| 05-DELV-02 | 05-02 | 2 | DELV-02 | T-05-02-01 / T-05-02-03 | `qrun pack-inspect` verifies copied bundles with bundle-local digests and provenance checks outside the source workspace. | CLI + runtime | `./.venv/bin/python -m pytest tests/test_cli_runtime_gap.py tests/test_pack_bundle.py -q --maxfail=1` | ✅ | ⬜ pending |
| 05-DELV-03 | 05-03 | 3 | DELV-03 | T-05-03-01 / T-05-03-03 | `qrun pack-import` verifies first, imports revision history into a target workspace, and enables downstream runtime commands to continue from the imported revision. | CLI + runtime | `./.venv/bin/python -m pytest tests/test_cli_runtime_gap.py tests/test_pack_bundle.py tests/test_cli_pack_import.py tests/test_runtime_imports.py -q --maxfail=1` | ⚠️ created by plan | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Coverage

- [x] `tests/test_cli_runtime_gap.py` already covers baseline `pack` and `pack-inspect` CLI flows plus pack workspace-safety failures.
- [x] `tests/test_pack_bundle.py` already covers direct bundle inspection shape checks and is the right place to pin bundle-manifest semantics.
- [ ] `tests/test_cli_pack_import.py` does not exist yet; Wave 0 remains incomplete until 05-03 adds the focused import contract coverage.
- [x] `tests/test_runtime_imports.py` already provides trusted replay/import fixtures that can validate downstream imported bundle behavior after 05-03 lands.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | All planned Phase 5 behaviors should be automatable with copied bundle directories and temporary workspaces. | N/A |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Bundle verification uses copied pack roots, not only in-place workspace pack directories
- [ ] No watch-mode flags
- [ ] Feedback latency < 40s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
