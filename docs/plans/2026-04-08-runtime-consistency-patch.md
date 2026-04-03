# Runtime Consistency Patch Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `qrun export` emit consistent provenance for workspace-current exports and make `qrun doctor` treat missing optional backends as advisories unless the active workspace actually depends on them.

**Architecture:** Reuse the existing import-resolution contract instead of inventing a second provenance path for export. For doctor, split dependency findings into blocking issues versus optional advisories by combining backend capability metadata with the active workspace QSpec when available.

**Tech Stack:** Python 3.11, Typer CLI, Pydantic models, workspace import helpers, pytest

### Task 1: Add failing tests for export provenance consistency

**Files:**
- Modify: `tests/test_cli_export.py`
- Modify: `src/quantum_runtime/runtime/export.py`

**Step 1: Write the failing test**

Add a CLI export test proving:
- `qrun export --workspace .quantum --format qasm3 --json` returns `source_kind=workspace_current`
- `source_revision`, `source_report_path`, and `source_qspec_path` are populated from the active workspace report/spec

**Step 2: Run test to verify it fails**

Run:

```bash
uv run --python 3.11 --extra dev pytest tests/test_cli_export.py -q
```

Expected: FAIL because workspace-current export does not currently resolve an import source.

**Step 3: Write minimal implementation**

Implement export provenance for workspace-current mode by resolving the active workspace import before building the export result.

**Step 4: Run test to verify it passes**

Run:

```bash
uv run --python 3.11 --extra dev pytest tests/test_cli_export.py -q
```

Expected: PASS

### Task 2: Add failing tests for doctor optional dependency semantics

**Files:**
- Modify: `tests/test_cli_doctor.py`
- Modify: `src/quantum_runtime/runtime/backend_registry.py`
- Modify: `src/quantum_runtime/runtime/doctor.py`
- Modify: `src/quantum_runtime/runtime/exit_codes.py`

**Step 1: Write the failing tests**

Add doctor tests proving:
- missing optional `classiq` is reported as an advisory and returns exit code `0` when the active workspace does not request it
- missing optional `classiq` remains a blocking issue and returns exit code `7` when the active workspace backend preferences include `classiq`

**Step 2: Run tests to verify they fail**

Run:

```bash
uv run --python 3.11 --extra dev pytest tests/test_cli_doctor.py -q
```

Expected: FAIL because doctor currently treats any unavailable backend as an issue.

**Step 3: Write minimal implementation**

Implement:
- explicit optional-backend metadata in the capability registry
- doctor classification into `issues` vs `advisories`
- exit-code mapping that ignores advisories while preserving blocking dependency failures

**Step 4: Run tests to verify they pass**

Run:

```bash
uv run --python 3.11 --extra dev pytest tests/test_cli_doctor.py -q
```

Expected: PASS

### Task 3: Full verification

**Files:**
- Modify only files touched above

**Step 1: Run focused suites**

```bash
uv run --python 3.11 --extra dev pytest tests/test_cli_export.py tests/test_cli_doctor.py -q
```

Expected: PASS

**Step 2: Run project verification gates**

```bash
uv run --python 3.11 --extra dev ruff check src tests
uv run --python 3.11 --extra dev mypy src
uv run --python 3.11 --extra dev --extra qiskit pytest -q
```

Expected: PASS
