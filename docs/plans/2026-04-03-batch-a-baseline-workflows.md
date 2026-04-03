# Batch A Baseline Workflows Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add first-class baseline workflows so FluxQ can persist an approved baseline, compare the current workspace against it, and expose baseline state through compare and inspect.

**Architecture:** Introduce a small workspace-level baseline record instead of bolting more ad hoc compare flags onto the CLI. The baseline record should point at a resolved report/QSpec pair and preserve enough summary data to explain what the baseline is without re-reading old command output. Then wire `qrun compare` and `qrun inspect` to understand that baseline object.

**Tech Stack:** Python 3.11, Typer CLI, Pydantic models, workspace JSON/report imports, pytest

### Task 1: Add workspace baseline persistence

**Files:**
- Create: `src/quantum_runtime/workspace/baseline.py`
- Modify: `src/quantum_runtime/workspace/paths.py`
- Modify: `src/quantum_runtime/workspace/__init__.py`
- Test: `tests/test_workspace_baseline.py`
- Test: `tests/test_cli_baseline.py`

**Step 1: Write the failing tests**

Add tests that prove:
- a workspace baseline record can be saved and loaded from `.quantum/baselines/current.json`
- the stored record preserves source kind, revision, report path, qspec path, hashes, and semantic summary
- `qrun baseline set --revision rev_000001 --json` persists a baseline record
- `qrun baseline show --json` returns the persisted baseline
- `qrun baseline clear --json` removes it cleanly

**Step 2: Run tests to verify they fail**

Run:

```bash
uv run --python 3.11 --extra dev pytest tests/test_workspace_baseline.py tests/test_cli_baseline.py -q
```

Expected: FAIL because the baseline storage module and CLI commands do not exist yet.

**Step 3: Write minimal implementation**

Implement:
- a `WorkspaceBaseline` model with load/save helpers
- `WorkspacePaths` helpers for `.quantum/baselines/current.json`
- a `baseline` Typer subcommand group with `set`, `show`, and `clear`

**Step 4: Run tests to verify they pass**

Run:

```bash
uv run --python 3.11 --extra dev pytest tests/test_workspace_baseline.py tests/test_cli_baseline.py -q
```

Expected: PASS

### Task 2: Make compare baseline-aware

**Files:**
- Modify: `src/quantum_runtime/cli.py`
- Modify: `src/quantum_runtime/runtime/compare.py`
- Modify: `src/quantum_runtime/runtime/__init__.py`
- Modify: `src/quantum_runtime/runtime/exit_codes.py`
- Test: `tests/test_runtime_compare.py`
- Test: `tests/test_cli_compare.py`

**Step 1: Write the failing tests**

Add tests that prove:
- `qrun compare --workspace .quantum --baseline --json` compares saved baseline vs current workspace
- the compare payload includes a `baseline` block that explains which side is the baseline and where it came from
- policy verdicts still work in baseline mode
- compare returns a structured invalid-input error when `--baseline` is requested but no baseline exists

**Step 2: Run tests to verify they fail**

Run:

```bash
uv run --python 3.11 --extra dev pytest tests/test_runtime_compare.py tests/test_cli_compare.py -q
```

Expected: FAIL because compare cannot consume workspace baselines yet.

**Step 3: Write minimal implementation**

Implement:
- CLI `--baseline` mode for compare
- baseline resolution helper that turns the saved record back into an `ImportResolution`
- compare output fields that expose baseline metadata without breaking existing callers

**Step 4: Run tests to verify they pass**

Run:

```bash
uv run --python 3.11 --extra dev pytest tests/test_runtime_compare.py tests/test_cli_compare.py -q
```

Expected: PASS

### Task 3: Surface baseline state in inspect

**Files:**
- Modify: `src/quantum_runtime/runtime/inspect.py`
- Modify: `src/quantum_runtime/runtime/exit_codes.py`
- Test: `tests/test_cli_inspect.py`

**Step 1: Write the failing test**

Add tests that prove:
- `qrun inspect --json` includes a `baseline` block when a workspace baseline exists
- the block reports baseline revision, source, and whether the current workspace semantically matches the baseline
- inspect degrades cleanly when the baseline record exists but points at missing or invalid inputs

**Step 2: Run test to verify it fails**

Run:

```bash
uv run --python 3.11 --extra dev pytest tests/test_cli_inspect.py -q
```

Expected: FAIL because inspect does not expose baseline state yet.

**Step 3: Write minimal implementation**

Implement a baseline summary block for inspect using the saved baseline record plus a compare against current workspace where possible.

**Step 4: Run tests to verify they pass**

Run:

```bash
uv run --python 3.11 --extra dev pytest tests/test_cli_inspect.py -q
```

Expected: PASS

### Task 4: Full verification and commit

**Files:**
- Modify only files touched above

**Step 1: Run the focused suite**

```bash
uv run --python 3.11 --extra dev pytest tests/test_workspace_baseline.py tests/test_cli_baseline.py tests/test_runtime_compare.py tests/test_cli_compare.py tests/test_cli_inspect.py -q
```

Expected: PASS

**Step 2: Run the project verification gates**

```bash
uv run --python 3.11 --extra dev ruff check src tests
uv run --python 3.11 --extra dev mypy src
uv run --python 3.11 --extra dev --extra qiskit pytest -q
```

Expected: PASS

**Step 3: Commit**

```bash
git add src/quantum_runtime/workspace/baseline.py src/quantum_runtime/workspace/paths.py src/quantum_runtime/workspace/__init__.py src/quantum_runtime/cli.py src/quantum_runtime/runtime/compare.py src/quantum_runtime/runtime/__init__.py src/quantum_runtime/runtime/exit_codes.py src/quantum_runtime/runtime/inspect.py tests/test_workspace_baseline.py tests/test_cli_baseline.py tests/test_runtime_compare.py tests/test_cli_compare.py tests/test_cli_inspect.py docs/plans/2026-04-03-batch-a-baseline-workflows.md
git commit -m "feat: add baseline workflow primitives"
```
