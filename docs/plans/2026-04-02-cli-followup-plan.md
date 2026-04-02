# CLI Follow-up Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the highest-value CLI gaps left after PR12 by adding `inspect`, `doctor`, richer `exec` inputs, and basic exit-code coverage.

**Architecture:** Reuse the existing runtime pipeline, workspace manifest, reports, and diagnostics instead of inventing parallel code paths. Keep new commands read-mostly and JSON-first so agent hosts and CI can consume them deterministically.

**Tech Stack:** Python 3.11, Typer, Pydantic, pytest, existing Quantum Runtime modules

### Task 1: Extend `qrun exec` inputs

**Files:**
- Modify: `src/quantum_runtime/cli.py`
- Modify: `src/quantum_runtime/runtime/executor.py`
- Test: `tests/test_cli_exec.py`

**Steps:**
1. Write a failing test for `qrun exec --qspec-file ... --json`.
2. Run the focused test to verify it fails for the expected reason.
3. Implement minimal support for `qspec` input while preserving current intent flow.
4. Re-run the focused test and make sure it passes.

### Task 2: Add `qrun inspect`

**Files:**
- Modify: `src/quantum_runtime/cli.py`
- Create: `src/quantum_runtime/runtime/inspect.py`
- Test: `tests/test_cli_inspect.py`

**Steps:**
1. Write a failing JSON-mode inspect test against a populated workspace.
2. Run the focused test to verify it fails.
3. Implement a minimal inspect summary: revision, qspec summary, artifact paths, latest diagnostics, backend capability snapshot.
4. Re-run the focused test and make sure it passes.

### Task 3: Add `qrun doctor`

**Files:**
- Modify: `src/quantum_runtime/cli.py`
- Create: `src/quantum_runtime/runtime/doctor.py`
- Test: `tests/test_cli_doctor.py`
- Modify: `integrations/aionrs/hooks.example.toml`

**Steps:**
1. Write a failing JSON-mode doctor test for dependency and workspace health output.
2. Run the focused test to verify it fails.
3. Implement minimal checks for workspace integrity plus import availability for `qiskit`, `qiskit_aer`, and `classiq`.
4. Switch the sample aionrs hook back to `qrun doctor`.
5. Re-run the focused tests and make sure they pass.

### Task 4: Tighten CLI exit codes

**Files:**
- Modify: `src/quantum_runtime/cli.py`
- Test: `tests/test_cli_exec.py`
- Test: `tests/test_cli_bench.py`

**Steps:**
1. Write failing tests for missing-input or missing-qspec exit code `3`.
2. Run the focused tests to verify they fail.
3. Implement the minimal exit-code handling needed for invalid input cases.
4. Re-run the focused tests and make sure they pass.

### Task 5: Full verification and commit

**Files:**
- No code changes unless verification exposes regressions.

**Steps:**
1. Run `uv run --python 3.11 --extra dev --extra qiskit pytest -q`.
2. If green, commit the batch with a focused message.
