# Quantum Runtime PR1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the initial Quantum Runtime CLI scaffold with a working `qrun init` command and deterministic workspace initialization.

**Architecture:** Use a small Python package rooted at `src/quantum_runtime` with a Typer-based CLI entrypoint. Keep workspace creation logic in a dedicated manager module so CLI wiring stays thin and later `exec`/`inspect` commands can reuse the same path and manifest handling.

**Tech Stack:** Python 3.11 target, Typer, Pydantic v2, pytest, uv-compatible packaging.

### Task 1: Package Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/quantum_runtime/__init__.py`
- Create: `src/quantum_runtime/errors.py`

**Step 1: Write the failing test**

Create a CLI smoke test that imports the package version and invokes `python -m quantum_runtime.cli --help`.

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_cli_init.py -q`
Expected: FAIL because the package and CLI module do not exist yet.

**Step 3: Write minimal implementation**

Add `pyproject.toml` with the `qrun` entrypoint and create the minimal package files needed for imports and version metadata.

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_cli_init.py -q`
Expected: PASS for the smoke/import expectations, with the still-missing `init` behavior covered by later tests.

### Task 2: Workspace Initialization

**Files:**
- Create: `src/quantum_runtime/workspace/__init__.py`
- Create: `src/quantum_runtime/workspace/paths.py`
- Create: `src/quantum_runtime/workspace/manager.py`
- Test: `tests/test_cli_init.py`

**Step 1: Write the failing test**

Add tests asserting `qrun init --workspace <tmp> --json` creates:
- `workspace.json`
- `qrun.toml`
- the full `.quantum` directory skeleton

Also assert `workspace.json` contains the expected stable keys from the spec.

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_cli_init.py -q`
Expected: FAIL because `init` does not exist or does not create the expected workspace files.

**Step 3: Write minimal implementation**

Implement a `WorkspaceManager.init_workspace()` helper that creates the directory tree, writes deterministic defaults, and returns a structured result consumed by the CLI.

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_cli_init.py -q`
Expected: PASS with `qrun init` producing the required files and JSON output.

### Task 3: CLI Surface and Docs

**Files:**
- Create: `src/quantum_runtime/cli.py`
- Modify: `README.md`
- Create: `examples/intent-ghz.md`

**Step 1: Write the failing test**

Add tests for:
- `qrun version`
- `qrun init` idempotency
- `qrun init --json` machine-readable response

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_cli_init.py -q`
Expected: FAIL because the CLI contract is still incomplete.

**Step 3: Write minimal implementation**

Wire Typer commands, add stable JSON serialization for `init`, expose package version, and document the step-1 workflow in `README.md`.

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_cli_init.py -q`
Expected: PASS.

### Task 4: Verification

**Files:**
- Test: `tests/test_cli_init.py`

**Step 1: Run the focused test suite**

Run: `python3 -m pytest tests/test_cli_init.py -q`
Expected: PASS.

**Step 2: Run the CLI manually**

Run: `python3 -m quantum_runtime.cli init --workspace .tmp-quantum --json`
Expected: JSON output containing `status`, `workspace`, `workspace_version`, and created paths.

**Step 3: Clean verification note**

If Typer is unavailable in the local interpreter, install project dependencies through `uv` before rerunning the test suite.
