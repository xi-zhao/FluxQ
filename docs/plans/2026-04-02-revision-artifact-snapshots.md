# Revision Artifact Snapshots Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make generated artifacts revision-stable so historical reports always point to immutable artifact snapshots instead of mutable current paths.

**Architecture:** Extend the existing append-only workspace model from specs/reports to generated artifacts. The executor should keep writing current convenience paths, but it must also persist per-revision copies and teach reports/inspect/import helpers to surface those stable paths and their provenance.

**Tech Stack:** Python 3.11, Typer CLI, Pydantic, pytest, pathlib

### Task 1: Add revision-stable artifact snapshot layout

**Files:**
- Modify: `src/quantum_runtime/workspace/paths.py`
- Modify: `src/quantum_runtime/runtime/executor.py`
- Modify: `src/quantum_runtime/diagnostics/diagrams.py`
- Test: `tests/test_cli_exec.py`

**Step 1: Write the failing test**

```python
def test_qrun_exec_persists_revision_artifact_snapshots(tmp_path: Path) -> None:
    payload = _run_exec(tmp_path)
    revision = payload["revision"]
    report = json.loads((workspace / "reports" / "latest.json").read_text())
    assert report["artifacts"]["qiskit_code"].endswith(f"artifacts/history/{revision}/qiskit/main.py")
```

**Step 2: Run test to verify it fails**

Run: `uv run --python 3.11 --extra dev --extra qiskit pytest tests/test_cli_exec.py::test_qrun_exec_persists_revision_artifact_snapshots -q`
Expected: `FAIL` because reports currently point at mutable current artifact paths like `artifacts/qiskit/main.py`.

**Step 3: Write minimal implementation**

Implement:
- `artifacts/history/<revision>/...` directories in workspace path setup
- executor writes current artifact as today, then copies/saves a revision snapshot path for each generated artifact
- diagrams also snapshot `circuit.txt` / `circuit.png` per revision
- report artifact block records stable revision paths, not mutable current paths

**Step 4: Run test to verify it passes**

Run: `uv run --python 3.11 --extra dev --extra qiskit pytest tests/test_cli_exec.py::test_qrun_exec_persists_revision_artifact_snapshots -q`
Expected: `PASS`

**Step 5: Commit**

```bash
git add src/quantum_runtime/workspace/paths.py src/quantum_runtime/runtime/executor.py src/quantum_runtime/diagnostics/diagrams.py tests/test_cli_exec.py
git commit -m "feat: snapshot revision artifacts"
```

### Task 2: Preserve stable artifact provenance in reports and inspect output

**Files:**
- Modify: `src/quantum_runtime/reporters/writer.py`
- Modify: `src/quantum_runtime/runtime/imports.py`
- Modify: `src/quantum_runtime/runtime/inspect.py`
- Test: `tests/test_report_writer.py`
- Test: `tests/test_cli_inspect.py`

**Step 1: Write the failing test**

```python
def test_write_report_records_revision_artifact_provenance(tmp_path: Path) -> None:
    payload = write_report(...)
    assert payload["provenance"]["artifacts"]["snapshot_root"].endswith(f"artifacts/history/{revision}")
```

**Step 2: Run test to verify it fails**

Run: `uv run --python 3.11 --extra dev --extra qiskit pytest tests/test_report_writer.py::test_write_report_records_revision_artifact_provenance tests/test_cli_inspect.py::test_qrun_inspect_json_reports_artifact_provenance -q`
Expected: `FAIL` because report provenance does not currently describe stable artifact snapshot roots.

**Step 3: Write minimal implementation**

Implement:
- artifact provenance block in report JSON with snapshot root and current-path aliases
- import summary keeps using report artifact names but now resolves/stores stable revision paths
- inspect output surfaces stable artifact paths and provenance rather than only mutable current paths

**Step 4: Run test to verify it passes**

Run: `uv run --python 3.11 --extra dev --extra qiskit pytest tests/test_report_writer.py tests/test_cli_inspect.py -q`
Expected: `PASS`

**Step 5: Commit**

```bash
git add src/quantum_runtime/reporters/writer.py src/quantum_runtime/runtime/imports.py src/quantum_runtime/runtime/inspect.py tests/test_report_writer.py tests/test_cli_inspect.py
git commit -m "feat: record artifact snapshot provenance"
```

### Task 2A: Canonicalize artifact provenance through one shared contract

**Why this task exists:**
- Repeated Task 2 follow-up fixes exposed a shared design flaw: `writer`, `imports`, and `inspect` each reconstruct artifact provenance differently.
- The product requirement is stronger than “repair the latest report”: any current-path, relative-path, legacy, or partial provenance input must normalize back to revision-stable snapshot paths before downstream logic uses it.

**Files:**
- Create: `src/quantum_runtime/runtime/artifact_provenance.py`
- Modify: `src/quantum_runtime/reporters/writer.py`
- Modify: `src/quantum_runtime/runtime/imports.py`
- Modify: `src/quantum_runtime/runtime/inspect.py`
- Modify: `src/quantum_runtime/runtime/executor.py`
- Test: `tests/test_report_writer.py`
- Test: `tests/test_runtime_imports.py`
- Test: `tests/test_cli_inspect.py`

**Canonical contract:**
- Canonical truth is always the revision-stable path:
  - `specs/history/<revision>.json`
  - `reports/history/<revision>.json`
  - `artifacts/history/<revision>/...`
- `current.json`, `latest.json`, and `artifacts/...` are convenience aliases only.
- Shared canonicalizer input:
  - `workspace_root`
  - `revision`
  - report `artifacts` block
  - optional stored `provenance.artifacts`
- Shared canonicalizer output:
  - absolute `snapshot_root`
  - absolute `current_root`
  - canonical absolute snapshot `paths`
  - canonical absolute `current_aliases`

**Step 1: Write the failing tests**

Add tests that prove:
- legacy/current-path reports normalize to stable snapshot paths in `resolve_report_file()`
- `inspect_workspace()` repairs partial/legacy provenance for relative workspace roots
- writer/import/inspect canonical provenance shapes match for the same report revision

**Step 2: Run tests to verify they fail**

Run:
- `uv run --python 3.11 --extra dev --extra qiskit pytest tests/test_runtime_imports.py::test_resolve_report_file_normalizes_current_alias_artifacts_to_history tests/test_cli_inspect.py::test_inspect_workspace_normalizes_legacy_current_alias_provenance -q`

Expected:
- `FAIL` because current import/inspect logic preserves mutable current-path entries instead of canonical revision-stable snapshot paths.

**Step 3: Write minimal implementation**

Implement:
- one shared artifact provenance canonicalizer module
- writer uses canonicalizer to persist provenance
- imports and inspect use canonicalizer in repair mode instead of rebuilding or blindly merging local rules
- report-based qspec loading should rely on canonicalized/stable report paths rather than raw mutable aliases

**Step 4: Run tests to verify they pass**

Run:
- `uv run --python 3.11 --extra dev --extra qiskit pytest tests/test_report_writer.py tests/test_runtime_imports.py tests/test_cli_inspect.py -q`

Expected:
- `PASS`

**Step 5: Commit**

```bash
git add src/quantum_runtime/runtime/artifact_provenance.py src/quantum_runtime/reporters/writer.py src/quantum_runtime/runtime/imports.py src/quantum_runtime/runtime/inspect.py src/quantum_runtime/runtime/executor.py tests/test_report_writer.py tests/test_runtime_imports.py tests/test_cli_inspect.py
git commit -m "refactor: canonicalize artifact provenance"
```

### Task 3: Keep export and compare workflows replayable from stable artifact-backed reports

**Files:**
- Modify: `src/quantum_runtime/runtime/export.py`
- Modify: `src/quantum_runtime/runtime/compare.py`
- Test: `tests/test_cli_export.py`
- Test: `tests/test_cli_compare.py`

**Step 1: Write the failing test**

```python
def test_qrun_compare_uses_revision_snapshot_artifact_sets(tmp_path: Path) -> None:
    payload = _compare_two_revisions(...)
    assert "artifact_set_changed" in payload["differences"]
```

**Step 2: Run test to verify it fails**

Run: `uv run --python 3.11 --extra dev --extra qiskit pytest tests/test_cli_export.py tests/test_cli_compare.py -q`
Expected: At least one failure because compare/export assumptions still rely on mutable current artifact layout.

**Step 3: Write minimal implementation**

Implement:
- export keeps writing current outputs but re-imported report flows remain anchored to revision-stable qspec/report/artifact provenance
- compare/report summaries use stable artifact names/paths so revision-vs-revision comparisons remain deterministic after later runs

**Step 4: Run test to verify it passes**

Run: `uv run --python 3.11 --extra dev --extra qiskit pytest tests/test_cli_export.py tests/test_cli_compare.py -q`
Expected: `PASS`

**Step 5: Commit**

```bash
git add src/quantum_runtime/runtime/export.py src/quantum_runtime/runtime/compare.py tests/test_cli_export.py tests/test_cli_compare.py
git commit -m "feat: keep replay flows artifact-stable"
```

### Task 4: Run the full release gate and land the slice cleanly

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/plans/2026-04-02-revision-artifact-snapshots.md`
- Test: `tests/test_release_docs.py`

**Step 1: Update release docs**

Document:
- revision-stable artifact snapshots
- report/inspect provenance expectations
- why replay/import now stays stable across later runs

**Step 2: Run doc verification**

Run: `uv run --python 3.11 --extra dev pytest tests/test_release_docs.py -q`
Expected: `PASS`

**Step 3: Run static checks**

Run: `uv run --python 3.11 --extra dev ruff check src tests`
Expected: `All checks passed`

**Step 4: Run type checks**

Run: `uv run --python 3.11 --extra dev mypy src`
Expected: `Success: no issues found`

**Step 5: Run the full suite**

Run: `uv run --python 3.11 --extra dev --extra qiskit pytest -q`
Expected: `PASS`

**Step 6: Commit**

```bash
git add README.md CHANGELOG.md docs/plans/2026-04-02-revision-artifact-snapshots.md tests/test_release_docs.py
git commit -m "docs: describe revision artifact snapshots"
```
