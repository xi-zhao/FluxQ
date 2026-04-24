---
phase: 02-trusted-revision-artifacts
reviewed: 2026-04-12T13:30:01Z
depth: deep
files_reviewed: 6
files_reviewed_list:
  - src/quantum_runtime/runtime/run_manifest.py
  - src/quantum_runtime/runtime/imports.py
  - src/quantum_runtime/runtime/control_plane.py
  - tests/test_runtime_revision_artifacts.py
  - tests/test_runtime_imports.py
  - tests/test_cli_control_plane.py
findings:
  critical: 0
  warning: 2
  info: 0
  total: 2
status: issues_found
---
# Phase 2: Code Review Report

**Reviewed:** 2026-04-12T13:30:01Z
**Depth:** deep
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed the final Phase 2 trust and replay changes with cross-file tracing plus targeted runtime probes. I did not find a remaining `current-workspace` vs legacy replay mismatch in `show` after the gap closure, but two trust-surface gaps remain: the new manifest evidence blocks can be stripped without detection, and copied report-file imports can inherit manifest trust from a workspace manifest that was never validated against the selected report bytes.

## Warnings

### WR-01: Manifest evidence can be removed entirely without tripping integrity checks

**File:** `src/quantum_runtime/runtime/run_manifest.py:184-215,344-377`
**Issue:** `parse_and_validate_run_manifest()` validates `intent`, `plan`, `events.events_jsonl`, and `events.trace_ndjson` only when the block is present. `_validate_optional_artifact_block()` returns success for a missing or empty block, so a fresh Phase 2 manifest can be tampered by deleting those sections entirely and still pass validation. The regression at `tests/test_runtime_revision_artifacts.py:193-217` locks that behavior in. I reproduced this by deleting `intent`, `plan`, and `events` from `manifests/history/rev_000001.json`; `resolve_workspace_current()` still reopened the run as trusted and kept the manifest attached.
**Fix:** Fail closed for missing evidence blocks on manifests produced by the current Phase 2 runtime. The simplest safe approach is to require these blocks whenever the manifest schema/version matches the current writer, while keeping a separate compatibility path only for explicitly recognized pre-gap manifests. Add a regression that deletes each block from a newly written manifest and expects `RunManifestIntegrityError`.

### WR-02: `report_file` resolution can borrow manifest trust from a different file

**File:** `src/quantum_runtime/runtime/imports.py:327-382,424-468`
**Issue:** `_build_resolution()` always loads and advertises the workspace manifest for `reports/history/<revision>.json`, but it never checks that the selected `report_path` bytes match that canonical history report. For copied-report imports, `_resolve_report_file_against_workspace()` passes the external report file into `_build_resolution()`, so a caller can edit non-integrity fields in the copied report and still receive `manifest_path` plus trusted replay metadata from the workspace manifest. I reproduced this by copying `rev_000001.json`, changing only `status`/`warnings`, deleting the source workspace, and resolving the file against another workspace with the same revision: resolution succeeded with `report_summary["status"] == "degraded"` while `report_summary["manifest_path"]` pointed at the target workspace manifest.
**Fix:** When a workspace manifest is present for `source_kind="report_file"`, bind it to the selected report file before surfacing it as trusted metadata. Either compare `report_hash` against `manifest_payload["report"]["hash"]` and fail on mismatch, or suppress `manifest_path` unless `report_path` is the canonical in-workspace history report. Add a copied-report tamper regression that mutates only report metadata and expects failure or an untrusted/no-manifest result.

---

_Reviewed: 2026-04-12T13:30:01Z_
_Reviewer: Codex (gsd-code-reviewer)_
_Depth: deep_
