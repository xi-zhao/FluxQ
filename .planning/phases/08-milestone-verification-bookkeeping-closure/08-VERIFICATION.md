---
phase: 08-milestone-verification-bookkeeping-closure
verified: 2026-04-16T01:38:24Z
status: gaps_found
score: 8/11 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Phase 03 has a truthful `03-VERIFICATION.md` with `status: passed` backed by the current rerun, not by historical summaries alone."
    status: failed
    reason: "A forced failure immediately after promoting `specs/current.json` still leaves the workspace in a mixed state that `_guard_exec_commit_paths()` does not detect. `RUNT-02` therefore remains open, so the downstream verification and bookkeeping closure is premature."
    artifacts:
      - path: "src/quantum_runtime/runtime/executor.py"
        issue: "`_promote_exec_aliases()` updates `specs/current.json` before `reports/latest.json` and `manifests/latest.json`, while `_guard_exec_commit_paths()` only scans report/manifest temp files."
      - path: "tests/test_runtime_workspace_safety.py"
        issue: "The current workspace-safety probe covers manifest-write interruption and pending temp files, but not alias-promotion interruption after `specs/current.json` moves."
      - path: ".planning/phases/03-concurrent-workspace-safety/03-VERIFICATION.md"
        issue: "Marks `RUNT-02` satisfied and reports no blocking gaps despite the remaining mixed-alias recovery hole."
      - path: ".planning/STATE.md"
        issue: "Declares no blockers from the Phase 08 proof chain even though the owned `RUNT-02` gap is still reproducible."
      - path: ".planning/REQUIREMENTS.md"
        issue: "Marks `RUNT-02` complete under Phase 08 before the interrupted-alias failure mode is closed."
      - path: ".planning/v1.0-MILESTONE-AUDIT.md"
        issue: "Closes `RUNT-02` and `FLOW-02` using the premature Phase 03/08 proof chain."
    missing:
      - "Reorder or harden exec alias promotion so `reports/latest.json` and `manifests/latest.json` cannot lag behind `specs/current.json`, or make the alias move atomic as one coherent step."
      - "Extend `_guard_exec_commit_paths()` and workspace-safety tests to detect interrupted alias promotion for every mutable alias touched by exec."
      - "Regenerate `03-VERIFICATION.md`, `STATE.md`, `REQUIREMENTS.md`, and `v1.0-MILESTONE-AUDIT.md` from the corrected proof."
---

# Phase 08: Verification And Bookkeeping Closure Verification Report

**Phase Goal:** Close the remaining milestone verification and bookkeeping gaps so the shipped control-plane phases can be archived consistently.
**Verified:** 2026-04-16T01:38:24Z
**Status:** gaps_found
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | The current Phase 03 truth probe passes, including the interrupted-commit path that keeps the previous `reports/latest.json` authoritative. | ✓ VERIFIED | `./.venv/bin/python -m pytest tests/test_cli_workspace_safety.py tests/test_runtime_workspace_safety.py tests/test_report_writer.py tests/test_runtime_imports.py tests/test_runtime_revision_artifacts.py tests/test_cli_exec.py -q --maxfail=1` returned `67 passed in 6.78s`, including `test_interrupted_commit_keeps_previous_current_revision_authoritative`. |
| 2 | Exec no longer promotes `reports/latest.json` before the same revision's manifest is durably written. | ✓ VERIFIED | `src/quantum_runtime/runtime/executor.py:373-424` calls `write_report(..., promote_latest=False)` and `write_run_manifest(..., promote_latest=False)` before alias promotion. |
| 3 | Report payloads and summaries point at canonical history artifacts for the evaluated revision instead of mutable aliases. | ✓ VERIFIED | `src/quantum_runtime/reporters/writer.py:33-99` writes `reports/history/<revision>.json` and canonicalizes provenance to history paths; `tests/test_report_writer.py:19-239` passed the relevant assertions. |
| 4 | The shared writer/executor history contract still satisfies the focused Phase 07 import/exec regression subset after the seam fix. | ✓ VERIFIED | The focused Phase 07 regression subset is included in the `67 passed` command above and stayed green. |
| 5 | Phase 03 has a truthful `03-VERIFICATION.md` with `status: passed` backed by the current rerun, not by historical summaries alone. | ✗ FAILED | `.planning/phases/03-concurrent-workspace-safety/03-VERIFICATION.md:24-45` says `RUNT-02` is satisfied and no blocking gaps remain. An ad hoc repro that forces a failure immediately after promoting `specs/current.json` leaves `workspace.json.current_revision`, `reports/latest.json`, and `manifests/latest.json` at `rev_000001` while `specs/current.json` changes, and a subsequent `execute_intent()` still succeeds as `rev_000002`. |
| 6 | The canonical Phase 04 local gate is the exact targeted Ruff + module-form MyPy + policy-gate pytest sequence, and that gate is still green in the current workspace. | ✓ VERIFIED | `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_cli_observability.py tests/test_runtime_policy.py -q --maxfail=1` returned `70 passed in 8.72s`. |
| 7 | `./scripts/dev-bootstrap.sh verify` is described truthfully as a broader repo smoke command, not as the same Phase 04 gate. | ✓ VERIFIED | `CONTRIBUTING.md:22-38` and `scripts/dev-bootstrap.sh:17-20,94-108` now agree that `verify` runs `qrun version`, Ruff, module-form MyPy, and full `pytest -q`. |
| 8 | Phase 04 no longer stays at `gaps_found` because of docs/script bookkeeping drift once the exact gate and wording are reconciled. | ✓ VERIFIED | `.planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md:1-115` is a current `status: passed` verification tied to the exact gate. |
| 9 | ROADMAP phase rows, checked plan bullets for `04-01..04-04` and `08-01..08-03`, STATE, REQUIREMENTS, and the milestone audit all agree that `RUNT-02`, `INT-02`, and `FLOW-02` are closed. | ✗ FAILED | The bookkeeping files are synchronized (`.planning/ROADMAP.md:136-151`, `.planning/STATE.md:101-103`, `.planning/REQUIREMENTS.md:78`, `.planning/v1.0-MILESTONE-AUDIT.md:43-71`), but the alias-promotion repro above shows `RUNT-02` is still open. The agreement is therefore not truthful enough to archive against the phase goal. |
| 10 | Phase 4 and Phase 8 are no longer shown as unchecked at either the phase row or per-plan bullet level once their verification artifacts are passed. | ✓ VERIFIED | `.planning/ROADMAP.md:16,19,136-151` marks both phases and all `04-*` / `08-*` plan bullets complete. |
| 11 | The milestone audit closes only the owned gaps and does not reintroduce unrelated repo-smoke failures as Phase 08 blockers. | ✗ FAILED | `.planning/v1.0-MILESTONE-AUDIT.md:26-29,73-79` correctly narrows repo-smoke debt, but it also closes `RUNT-02` and `FLOW-02` prematurely while the owned workspace-safety gap above is still reproducible. |

**Score:** 8/11 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `src/quantum_runtime/reporters/writer.py` | History-first report persistence and canonical report/qspec provenance for one revision | ✓ VERIFIED | Substantive implementation at `writer.py:18-99`; report writes are revision-history-first and canonicalized. |
| `src/quantum_runtime/runtime/executor.py` | Exec-side sequencing that promotes latest report only after manifest persistence succeeds | ✗ FAILED | `executor.py:523-557` still promotes `specs/current.json` before `reports/latest.json` and `manifests/latest.json`; `executor.py:560-577` only guards report/manifest temp files. |
| `tests/test_runtime_workspace_safety.py` | Live interrupted-commit regression proof for authoritative latest report behavior | ⚠️ PARTIAL | Covers manifest-write interruption and pending temp recovery (`tests/test_runtime_workspace_safety.py:209-284`) but not alias-promotion interruption after `specs/current.json` moves. |
| `tests/test_report_writer.py` | Writer-side canonical history path and suggestion regressions tied to the same seam | ✓ VERIFIED | Canonical path and suggestion coverage exists at `tests/test_report_writer.py:19-239,330-357`. |
| `.planning/phases/03-concurrent-workspace-safety/03-VERIFICATION.md` | Phase 03 proof artifact closing `RUNT-02` with current evidence | ✗ FAILED | Exists and is substantive, but its `status: passed` claim is not truthful given the remaining alias-promotion recovery hole. |
| `CONTRIBUTING.md` | Canonical contributor-facing description of the exact Phase 04 local gate | ✓ VERIFIED | Documents the exact Phase 4 gate and distinguishes the broader smoke path. |
| `scripts/dev-bootstrap.sh` | Truthful usage/help/logging for the broader local smoke command | ✓ VERIFIED | Help and execution text match the broader smoke scope. |
| `.planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md` | Refreshed passed verification artifact grounded in the exact Phase 04 gate | ✓ VERIFIED | Passed verification exists and matches the current exact gate. |
| `.planning/ROADMAP.md` | Canonical phase list, per-plan checkbox inventory, and progress snapshot with corrected Phase 4/8 state | ⚠️ PARTIAL | Synchronized correctly, but now overstates Phase 08 completion because `RUNT-02` remains open. |
| `.planning/STATE.md` | Current project position and blocker list after closeout | ✗ FAILED | `STATE.md:101-103` says there are no blockers, which is contradicted by the alias-promotion repro. |
| `.planning/REQUIREMENTS.md` | Requirement traceability showing `RUNT-02` complete under Phase 08 | ✗ FAILED | `REQUIREMENTS.md:78` marks `RUNT-02` complete prematurely. |
| `.planning/v1.0-MILESTONE-AUDIT.md` | Final proof chain that records `RUNT-02`, `INT-02`, and `FLOW-02` as closed | ✗ FAILED | The audit is internally consistent, but the `RUNT-02` closure claim is not supported by the current code behavior. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `src/quantum_runtime/runtime/executor.py` | `src/quantum_runtime/reporters/writer.py` | history-only report write before alias promotion | ✓ WIRED | `executor.py:373-385` calls `write_report(..., promote_latest=False)`; `writer.py:96-99` only promotes latest when requested. |
| `src/quantum_runtime/runtime/executor.py` | `src/quantum_runtime/runtime/run_manifest.py` | manifest write completes before latest alias promotion | ✓ WIRED | `executor.py:412-424` calls `write_run_manifest(..., promote_latest=False)` before `_promote_exec_aliases()`. |
| `src/quantum_runtime/runtime/executor.py` | mutable alias set | alias promotion after manifest persistence | ✗ NOT_WIRED SAFELY | `_promote_exec_aliases()` orders `specs/current.json` ahead of `reports/latest.json` and `manifests/latest.json` (`executor.py:523-554`), so a mid-sequence failure can expose mixed active aliases. |
| `src/quantum_runtime/runtime/executor.py` | recovery guard | detect interrupted exec alias updates | ✗ NOT_WIRED | `_guard_exec_commit_paths()` only scans `reports/latest.json` and `manifests/latest.json` temp files (`executor.py:560-577`), so interrupted `specs/current.json` promotion is invisible. |
| `tests/test_runtime_workspace_safety.py` | `src/quantum_runtime/runtime/executor.py` | interrupted-commit coverage for the exec seam | ⚠️ PARTIAL | The suite proves manifest-write interruption and temp-file recovery, but not failure after `specs/current.json` promotion. |
| `src/quantum_runtime/reporters/writer.py` / `src/quantum_runtime/runtime/executor.py` | `tests/test_runtime_imports.py`, `tests/test_runtime_revision_artifacts.py`, `tests/test_cli_exec.py` | focused Phase 07 regression subset guards the shared writer/executor history contract | ✓ WIRED | The targeted regression command passed `67` tests including those files. |
| `CONTRIBUTING.md` | `scripts/dev-bootstrap.sh` | matching wording about exact phase gate versus broader smoke command | ✓ WIRED | Docs and script help now describe the same scope distinction. |
| `.planning/phases/03-concurrent-workspace-safety/03-VERIFICATION.md` | `.planning/REQUIREMENTS.md`, `.planning/v1.0-MILESTONE-AUDIT.md` | closeout proof chain for `RUNT-02` | ✗ UNSOUND | The bookkeeping is linked, but it is fed by a premature Phase 03 pass claim. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `src/quantum_runtime/reporters/writer.py` | `payload["qspec"]`, `payload["artifacts"]`, `payload["provenance"]` | `QSpec` + canonicalized artifact provenance -> `reports/history/<revision>.json` | Yes | ✓ FLOWING |
| `src/quantum_runtime/runtime/executor.py` | active aliases (`specs/current.json`, `reports/latest.json`, `manifests/latest.json`) | `_promote_exec_aliases()` after history writes | No | ✗ BROKEN — a forced failure after `specs/current.json` promotion leaves mixed active aliases and no recovery signal |
| Phase 08 bookkeeping chain | `RUNT-02` / `FLOW-02` closure state | `03-VERIFICATION.md` -> `STATE.md` / `REQUIREMENTS.md` / audit | No | ✗ UNSOUND — downstream ledgers close over an incomplete Phase 03 proof |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Phase 03 closeout probe stays green | `./.venv/bin/python -m pytest tests/test_cli_workspace_safety.py tests/test_runtime_workspace_safety.py tests/test_report_writer.py tests/test_runtime_imports.py tests/test_runtime_revision_artifacts.py tests/test_cli_exec.py -q --maxfail=1` | `67 passed in 6.78s` | ✓ PASS |
| Exact Phase 04 gate stays green | `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_cli_observability.py tests/test_runtime_policy.py -q --maxfail=1` | `All checks passed!`, `Success: no issues found in 54 source files`, `70 passed in 8.72s` | ✓ PASS |
| Final ledger audit command passes | `test -f ...03-VERIFICATION.md && test -f ...04-VERIFICATION.md && rg ...` | All file-existence and `rg` checks passed | ✓ PASS |
| Interrupted alias promotion keeps workspace coherent and blocks the next exec | Ad hoc Python repro that monkeypatches `executor.atomic_copy_file` to raise immediately after promoting `specs/current.json` | `first_error RuntimeError fail after qspec alias promotion`; `workspace_current_revision_after_failure rev_000001`; `report_revision_after_failure rev_000001`; `manifest_revision_after_failure rev_000001`; `qspec_changed_after_failure True`; `second_exec_revision rev_000002` | ✗ FAIL |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `RUNT-02` | `08-01-PLAN.md`, `08-02-PLAN.md`, `08-03-PLAN.md` | Workspace writes are safe under concurrent agent or CI activity instead of assuming a single writer | ✗ BLOCKED | The targeted Phase 03/07 regression suite passes, but the alias-promotion repro shows a remaining interrupted-write path where `specs/current.json` outruns the last durable report/manifest state and the next exec is not blocked. |

No orphaned Phase 08 requirements were found. All three Phase 08 plans declare `RUNT-02`, and `REQUIREMENTS.md` maps `RUNT-02` to Phase 08.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `src/quantum_runtime/runtime/executor.py` | 523-577 | Alias promotion order and recovery guard scope diverge | 🛑 Blocker | `specs/current.json` can advance ahead of `reports/latest.json` / `manifests/latest.json`, and the next exec is not forced into recovery. |
| `tests/test_runtime_workspace_safety.py` | 209-284 | Narrow interrupted-write coverage | ⚠️ Warning | The green Phase 03 probe misses the surviving alias-promotion interruption path, so downstream verification docs over-trust the suite. |

### Disconfirmation Notes

- Partial requirement: `RUNT-02` is only partially met. Report/manifest latest promotion was fixed, but interrupted alias promotion can still corrupt active workspace state.
- Misleading test: `test_interrupted_commit_keeps_previous_current_revision_authoritative` passes because it fails during `write_run_manifest()`, before `_promote_exec_aliases()` begins. It does not exercise the surviving failure mode after `specs/current.json` is copied.
- Uncovered error path: no regression currently forces `_promote_exec_aliases()` to fail after promoting `specs/current.json` and before promoting `reports/latest.json` / `manifests/latest.json`.

### Human Verification Required

None. The blocking gap is programmatically reproducible.

### Gaps Summary

Phase 08 succeeded at its narrow report/manifest seam fix and at the bookkeeping updates, but it did not actually finish the owned `RUNT-02` closure. The remaining failure mode is in `src/quantum_runtime/runtime/executor.py`: alias promotion can still stop after `specs/current.json` moves and before `reports/latest.json` / `manifests/latest.json` move, leaving a mixed active workspace state that `_guard_exec_commit_paths()` does not detect.

Because Phase 03 is the proof source for `RUNT-02`, that remaining gap makes the rest of the Phase 08 closeout chain premature. `03-VERIFICATION.md`, `STATE.md`, `REQUIREMENTS.md`, and `v1.0-MILESTONE-AUDIT.md` are internally consistent, but they are consistent about a claim that is not yet true. Phase 08 should stay open until the alias-promotion failure mode is closed, covered by a regression, and the verification/bookkeeping artifacts are regenerated from that corrected proof.

---

_Verified: 2026-04-16T01:38:24Z_  
_Verifier: Codex (gsd-verifier)_
