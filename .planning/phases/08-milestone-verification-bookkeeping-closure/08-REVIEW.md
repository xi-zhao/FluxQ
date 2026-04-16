---
phase: 08-milestone-verification-bookkeeping-closure
reviewed: 2026-04-16T01:31:40Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - src/quantum_runtime/reporters/writer.py
  - src/quantum_runtime/runtime/executor.py
  - scripts/dev-bootstrap.sh
  - CONTRIBUTING.md
findings:
  critical: 0
  warning: 1
  info: 0
  total: 1
status: issues_found
---

# Phase 08: Code Review Report

**Reviewed:** 2026-04-16T01:31:40Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Reviewed the Phase 08 changes in report persistence ordering plus the updated local verification script/docs. The `CONTRIBUTING.md` and `scripts/dev-bootstrap.sh` changes are consistent with the current tooling contract. One crash-recovery regression remains in the executor path: moving `reports/latest.json` promotion behind manifest persistence was correct, but the active-alias promotion order was not updated to match, so a mid-promotion failure can still expose a newer `specs/current.json` while `reports/latest.json` and `manifests/latest.json` remain stale or missing.

I reproduced the issue by forcing `_promote_exec_aliases()` to fail immediately after copying `specs/current.json`. The workspace was left with `specs/current.json` present, `reports/latest.json` missing, and a subsequent `exec` was not blocked by `_guard_exec_commit_paths()`.

## Warnings

### WR-01: Report Alias Promotion Lags Other Active Aliases

**File:** `src/quantum_runtime/runtime/executor.py:432-441,523-577`
**Issue:** Phase 08 removed the early `reports/latest.json` write from `write_report()` and now relies on `_promote_exec_aliases()` for the active report alias. However, `_promote_exec_aliases()` still copies `specs/current.json` and other active aliases before `reports/latest.json` and `manifests/latest.json`. If the process dies after the qspec alias copy but before the report/manifest alias copies, the workspace can expose a new active QSpec with an old or missing active report. `_restore_workspace_revision()` only rolls back `workspace.json.current_revision`, and `_guard_exec_commit_paths()` only scans pending temp files for the report/manifest aliases, so this partially promoted state can slip past the next `exec`.
**Fix:**
```python
def _promote_exec_aliases(...):
    alias_pairs: list[tuple[Path, Path]] = [
        (report_history_path, handle.root / "reports" / "latest.json"),
        (manifest_history_path, handle.paths.manifests_latest_json),
    ]
    if intent_markdown_history_path is not None:
        alias_pairs.append((intent_markdown_history_path, handle.root / "intents" / "latest.md"))
    alias_pairs.extend(
        [
            (intent_history_path, handle.paths.intents_latest_json),
            (plan_history_path, handle.paths.plans_latest_json),
            (qspec_history_path, handle.root / "specs" / "current.json"),
        ]
    )
```

Also extend `_guard_exec_commit_paths()` to scan every alias target touched by `_promote_exec_aliases()` so interrupted alias updates cannot silently bypass recovery.

---

_Reviewed: 2026-04-16T01:31:40Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
