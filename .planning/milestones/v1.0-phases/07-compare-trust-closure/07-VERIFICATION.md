---
phase: 07-compare-trust-closure
verified: 2026-04-15T14:15:46Z
status: passed
score: 7/7 must-haves verified
overrides_applied: 0
---

# Phase 07: Compare Trust Closure Verification Report

**Phase Goal:** Restore the baseline/current compare gate so revision-to-revision policy decisions fail on drift classes instead of failing early on artifact inconsistency.
**Verified:** 2026-04-15T14:15:46Z
**Status:** passed
**Re-verification:** No - initial verification

Phase 07 has no structured `success_criteria` block in [ROADMAP.md](/Users/xizhao/my_projects/Fluxq/Qcli/.planning/ROADMAP.md), and `gsd-tools roadmap get-phase 07` returned `found: false`. The must-haves below are therefore derived from the roadmap goal plus the Phase 07 gap-closure lines (`POLC-01`, `INT-01`, `FLOW-01`) and merged with the three PLAN frontmatter `must_haves` blocks.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Healthy `exec -> baseline set -> exec -> compare --baseline --fail-on subject_drift --json` returns the policy verdict path instead of `report_qspec_semantic_hash_mismatch`. | `VERIFIED` | Direct spot-check returned `exit_code=2`, `status=different_subject`, `verdict.status=fail`, `failed_checks=["subject_drift"]`, `gate.ready=false`. The same contract is asserted in [tests/test_cli_compare.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_cli_compare.py:811) and wired through [compare.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/compare.py:110) plus [cli.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/cli.py:1547). |
| 2 | Explicit left/right revision compare also reaches the compare policy surface instead of failing early on replay-integrity mismatch. | `VERIFIED` | [tests/test_cli_runtime_gap.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_cli_runtime_gap.py:137) asserts `rev_000001` vs `rev_000002` returns `exit_code=2`, `failed_checks=["subject_drift"]`, and `gate.severity="error"`. Policy evaluation for `subject_drift` is implemented at [compare.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/compare.py:770). |
| 3 | A second `exec` keeps `rev_000002` report, qspec, and manifest bound to the same canonical history revision while `rev_000001` stays immutable. | `VERIFIED` | Producer writes `specs/history/<revision>.json` before report generation and delays alias promotion until after manifest persistence in [executor.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/executor.py:218), [executor.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/executor.py:373), and [executor.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/executor.py:411). Disk-level regression coverage exists in [tests/test_runtime_revision_artifacts.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_runtime_revision_artifacts.py:221) and [tests/test_runtime_revision_artifacts.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_runtime_revision_artifacts.py:269). |
| 4 | `resolve_workspace_current()` can reopen the latest healthy revision directly from canonical history with `replay_integrity.status == "ok"` after two execs. | `VERIFIED` | Current resolution prefers `reports/history/<current_revision>.json` and rebuilds trust from canonical qspec/report artifacts in [imports.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/imports.py:131), [imports.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/imports.py:347), and [imports.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/imports.py:590). Regression coverage is in [tests/test_runtime_imports.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_runtime_imports.py:101). |
| 5 | Real canonical-history tampering still fails closed; compare/import does not downgrade corruption into ordinary drift. | `VERIFIED` | `_evaluate_replay_integrity()` still raises `report_qspec_hash_mismatch` / `report_qspec_semantic_hash_mismatch` at [imports.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/imports.py:608), and CLI compare still maps `ImportSourceError` to exit `3` at [cli.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/cli.py:1601). This is asserted in [tests/test_cli_compare.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_cli_compare.py:878) and [tests/test_runtime_imports.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_runtime_imports.py:120), and confirmed by a direct tampered-flow spot-check returning `exit_code=3`, `reason=report_qspec_hash_mismatch`. |
| 6 | Baseline/current compare uses the saved baseline record and carries baseline metadata into the compare result. | `VERIFIED` | `compare_workspace_baseline()` resolves the saved baseline record and current workspace before policy evaluation at [compare.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/compare.py:110). Runtime coverage in [tests/test_runtime_compare.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_runtime_compare.py:410) confirms `baseline.revision == "rev_000001"` and left/right revisions are `rev_000001` / `rev_000002`. |
| 7 | Exec/import suites now own this seam, so future regressions surface before compare or milestone audit. | `VERIFIED` | CLI exec hardening in [tests/test_cli_exec.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_cli_exec.py:381) and [tests/test_cli_exec.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_cli_exec.py:419) asserts rev_000002 report/qspec coherence and replay from `--revision rev_000002`; runtime import hardening in [tests/test_runtime_imports.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_runtime_imports.py:101) and [tests/test_runtime_imports.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_runtime_imports.py:120) asserts healthy reopen plus fail-closed tamper behavior. |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `src/quantum_runtime/reporters/writer.py` | Report writer describes canonical revision artifacts without alias backfill. | `VERIFIED` | `write_report()` rebuilds provenance from the passed `qspec_path`, reloads the canonical qspec from disk, and derives both `hash` and `semantic_hash` from that same file at [writer.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/reporters/writer.py:15). |
| `src/quantum_runtime/runtime/executor.py` | Exec path remains history-first and alias-last. | `VERIFIED` | `qspec_history_path` is written first, `write_report()` receives that history path, `write_run_manifest(..., promote_latest=False)` persists the manifest, and alias promotion happens only afterward at [executor.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/executor.py:218) and [executor.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/executor.py:431). |
| `src/quantum_runtime/runtime/imports.py` | Trusted reopen resolves canonical history and fails closed on mismatch. | `VERIFIED` | `resolve_workspace_current()` prefers history artifacts and `_evaluate_replay_integrity()` still blocks hash/semantic drift at [imports.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/imports.py:131) and [imports.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/imports.py:590). |
| `src/quantum_runtime/runtime/compare.py` | Baseline/current compare reuses trusted resolutions and existing policy surface. | `VERIFIED` | `compare_workspace_baseline()` resolves baseline/current and delegates to `compare_import_resolutions()` at [compare.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/compare.py:110). |
| `src/quantum_runtime/cli.py` | CLI compare maps policy failure to exit `2` and trust failure to exit `3`. | `VERIFIED` | Compare entrypoint constructs `ComparePolicy`, calls `compare_workspace_baseline()` / `compare_import_resolutions()`, and only catches `ImportSourceError` to emit error payloads at [cli.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/cli.py:1525) and [cli.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/cli.py:1601). |
| `tests/test_runtime_revision_artifacts.py` | Regression coverage for second-exec revision coherence. | `VERIFIED` | Coherence and immutability checks exist at [tests/test_runtime_revision_artifacts.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_runtime_revision_artifacts.py:221) and [tests/test_runtime_revision_artifacts.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_runtime_revision_artifacts.py:269). |
| `tests/test_cli_compare.py` | Baseline compare regressions for healthy and tampered paths. | `VERIFIED` | Healthy policy path and tamper fail-closed path are asserted at [tests/test_cli_compare.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_cli_compare.py:811) and [tests/test_cli_compare.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_cli_compare.py:878). |
| `tests/test_cli_runtime_gap.py` | Milestone-audit flow regression for explicit left/right compare. | `VERIFIED` | The original audited failure path now asserts compare policy failure at [tests/test_cli_runtime_gap.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_cli_runtime_gap.py:137). |
| `tests/test_runtime_compare.py` | Runtime-level baseline compare contract. | `VERIFIED` | Saved-baseline record usage is asserted at [tests/test_runtime_compare.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_runtime_compare.py:410). |
| `tests/test_runtime_imports.py` and `tests/test_cli_exec.py` | Cross-phase regression hardening in import and exec suites. | `VERIFIED` | Latest-history reopen, tamper fail-closed, and second-revision report/qspec checks are asserted at [tests/test_runtime_imports.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_runtime_imports.py:101) and [tests/test_cli_exec.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_cli_exec.py:381). |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `src/quantum_runtime/runtime/executor.py` | `src/quantum_runtime/reporters/writer.py` | Pass canonical revision paths into `write_report()` before alias promotion. | `VERIFIED` | Manual check: [executor.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/executor.py:373) passes `qspec_history_path`; alias promotion starts later at [executor.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/executor.py:431). |
| `src/quantum_runtime/reporters/writer.py` | `src/quantum_runtime/runtime/imports.py` | Report `qspec.hash` and `qspec.semantic_hash` come from the same canonical qspec file that imports later reopen. | `VERIFIED` | Writer reloads `canonical_qspec_path` and derives both values at [writer.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/reporters/writer.py:39); imports compares those values against reopened qspec content at [imports.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/imports.py:600). |
| `src/quantum_runtime/runtime/compare.py` | `src/quantum_runtime/runtime/imports.py` | Trusted resolution must succeed before compare policy evaluation begins. | `VERIFIED` | `compare_workspace_baseline()` calls `resolve_workspace_baseline()` and `resolve_workspace_current()` before `compare_import_resolutions()` at [compare.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/compare.py:116). |
| `src/quantum_runtime/cli.py` | `src/quantum_runtime/runtime/compare.py` | CLI compare must reuse compare helpers rather than synthesize verdicts in the wrapper. | `VERIFIED` | [cli.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/cli.py:1574) and [cli.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/cli.py:1600) call the runtime helpers directly. |
| `tests/test_cli_exec.py` | `src/quantum_runtime/runtime/executor.py` | Two `qrun exec` calls must prove second-revision coherence from the public CLI path. | `VERIFIED` | The regression asserts rev_000002 history report/qspec alignment at [tests/test_cli_exec.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_cli_exec.py:419). |
| `tests/test_runtime_imports.py` | `src/quantum_runtime/runtime/imports.py` | Reopen must succeed on healthy latest history and fail closed on tampered history. | `VERIFIED` | Healthy and tampered reopen checks live at [tests/test_runtime_imports.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_runtime_imports.py:101) and [tests/test_runtime_imports.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_runtime_imports.py:120). |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `src/quantum_runtime/reporters/writer.py` | `payload["qspec"]`, `payload["replay_integrity"]` | Canonical qspec bytes loaded from `qspec_path.resolve()` and hashed/semantically summarized in [writer.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/reporters/writer.py:39). | Yes | `FLOWING` |
| `src/quantum_runtime/runtime/executor.py` | `canonical_artifacts`, `artifacts["report"]`, manifest inputs | History-root qspec/artifact writers populate `canonical_artifacts`; those paths feed `write_report()` and `write_run_manifest()` before alias promotion at [executor.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/executor.py:370). | Yes | `FLOWING` |
| `src/quantum_runtime/runtime/imports.py` | `ImportResolution.replay_integrity` | Report payload + reopened qspec history are checked in `_evaluate_replay_integrity()` at [imports.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/imports.py:590). | Yes | `FLOWING` |
| `src/quantum_runtime/runtime/compare.py` | `CompareResult.verdict`, `CompareResult.gate`, `CompareResult.baseline` | Trusted baseline/current resolutions are compared and then evaluated by `_evaluate_policy()` at [compare.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/compare.py:196). | Yes | `FLOWING` |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Healthy FLOW-01 returns policy verdict path | `./.venv/bin/python - <<'PY' ... compare --baseline --fail-on subject_drift --json ... PY` | `exit_code=2`, `status=different_subject`, `baseline_revision=rev_000001`, `verdict_status=fail`, `failed_checks=["subject_drift"]`, `gate_ready=false` | `PASS` |
| Tampered current revision still fails closed | `./.venv/bin/python - <<'PY' ... tamper rev_000002 qspec ... compare --baseline --json ... PY` | `exit_code=3`, `status=error`, `reason=report_qspec_hash_mismatch` | `PASS` |
| Targeted Phase 07 regression bundle | `./.venv/bin/python -m pytest tests/test_runtime_revision_artifacts.py tests/test_runtime_compare.py::test_compare_workspace_baseline_uses_saved_baseline_record tests/test_cli_runtime_gap.py::test_qrun_compare_json_fail_on_subject_drift_returns_failed_gate tests/test_cli_compare.py::test_qrun_compare_json_baseline_fail_on_subject_drift_returns_failed_gate tests/test_cli_compare.py::test_qrun_compare_json_baseline_preserves_fail_closed_on_tampered_current_revision tests/test_runtime_imports.py::test_resolve_workspace_current_after_two_execs_uses_latest_revision_history tests/test_runtime_imports.py::test_resolve_workspace_current_rejects_tampered_second_revision_history tests/test_cli_exec.py -q --maxfail=1` | `40 passed in 7.24s` | `PASS` |
| Full Phase 07 gate | `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_runtime_compare.py tests/test_runtime_imports.py tests/test_runtime_revision_artifacts.py tests/test_cli_exec.py -q --maxfail=1` | `All checks passed!`, `Success: no issues found in 54 source files`, `102 passed in 16.68s` | `PASS` |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `POLC-01` | `07-01-PLAN.md`, `07-02-PLAN.md`, `07-03-PLAN.md` | Agent can compare current state against baseline and fail on specific drift classes without external wrapper logic. | `SATISFIED` | Healthy baseline/current flow returns policy verdict and exit `2`; explicit left/right compare returns `subject_drift` policy failure; tampered revisions still fail closed with exit `3`. Evidence: [tests/test_cli_compare.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_cli_compare.py:811), [tests/test_cli_runtime_gap.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_cli_runtime_gap.py:137), [tests/test_runtime_compare.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_runtime_compare.py:410), direct spot-check summary above. |

No orphaned Phase 07 requirements were found: [REQUIREMENTS.md](/Users/xizhao/my_projects/Fluxq/Qcli/.planning/REQUIREMENTS.md) maps only `POLC-01` to Phase 07, and all three Phase 07 plans declare `POLC-01`.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `src/quantum_runtime/runtime/compare.py` | `835-843` | Empty-collection fallback helpers (`_string_list`, `_string_mapping`) | `INFO` | Normal type-normalization helpers, not stubs; they do not drive user-visible placeholder behavior. |
| `src/quantum_runtime/runtime/imports.py` | `1097-1173` | Empty summary fallbacks in internal parsers | `INFO` | Internal summarizers for optional payload blocks; no blocker or warning-level stub pattern found in Phase 07 artifacts. |

### Disconfirmation Pass

- **Partially re-verified scope:** Phase 07 directly re-executed the audited `subject_drift` compare flow. Other `fail_on` classes (`qspec_drift`, `report_drift`, `backend_regression`, `replay_integrity_regression`) still rely on prior Phase 04 coverage rather than new Phase 07 end-to-end runs.
- **Passing test that is narrower than its headline:** [tests/test_runtime_compare.py](/Users/xizhao/my_projects/Fluxq/Qcli/tests/test_runtime_compare.py:410) proves saved-baseline wiring and baseline metadata, but by itself does not prove CLI exit behavior or policy failure. Those guarantees come from the CLI tests and direct flow spot-check.
- **Untested error path found:** `baseline_integrity_invalid` is raised in [imports.py](/Users/xizhao/my_projects/Fluxq/Qcli/src/quantum_runtime/runtime/imports.py:221), but no direct test hit for that exact code path was found. Existing negative coverage exercises `baseline_missing`, `run_manifest_integrity_invalid`, qspec hash/semantic mismatches, and artifact digest drift instead.

### Human Verification Required

None. This phase's deliverables are CLI/runtime trust flows and are fully automatable from the local codebase.

### Gaps Summary

No blocking gaps found.

`POLC-01` is satisfied in live code, the cross-phase integration break `INT-01` is closed, and the broken flow `FLOW-01` now returns the documented policy verdict path on healthy revisions instead of failing early on `report_qspec_semantic_hash_mismatch`. Producer-side trust repair and downstream fail-closed behavior both remain intact.

---

_Verified: 2026-04-15T14:15:46Z_
_Verifier: Claude (gsd-verifier)_
