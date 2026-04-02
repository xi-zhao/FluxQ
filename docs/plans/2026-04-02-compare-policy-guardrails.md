# Compare Policy Guardrails Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn `qrun compare` into a CI- and agent-friendly guardrail command that can evaluate explicit expectations and return a machine-readable verdict.

**Architecture:** Extend the existing compare pipeline instead of introducing a parallel policy system. The runtime compare layer should compute stable drift/regression signals, the CLI should expose them as explicit policy flags, and exit codes should reflect verdicts so CI can consume the command directly.

**Tech Stack:** Python 3.11, Typer, Pydantic, pytest

### Task 1: Add compare policy and verdict models

**Files:**
- Modify: `src/quantum_runtime/runtime/compare.py`
- Modify: `src/quantum_runtime/runtime/__init__.py`
- Test: `tests/test_runtime_compare.py`

**Step 1: Write the failing test**

```python
def test_compare_import_resolutions_policy_fails_on_backend_regression() -> None:
    result = compare_import_resolutions(
        left,
        right,
        policy=ComparePolicy(expect="same-subject", forbid_backend_regressions=True),
    )
    assert result.verdict["status"] == "fail"
    assert "backend_regressions:forbidden" in result.verdict["failed_checks"]
```

**Step 2: Run test to verify it fails**

Run: `uv run --python 3.11 --extra dev --extra qiskit pytest tests/test_runtime_compare.py::test_compare_import_resolutions_policy_fails_on_backend_regression -q`
Expected: `FAIL` because compare results do not yet produce policy verdicts or backend regression checks.

**Step 3: Write minimal implementation**

Add:
- `ComparePolicy`
- `CompareVerdict`
- report drift detection
- backend regression detection
- policy evaluation wired into `CompareResult`

**Step 4: Run tests to verify they pass**

Run: `uv run --python 3.11 --extra dev --extra qiskit pytest tests/test_runtime_compare.py -q`
Expected: `PASS`

**Step 5: Commit**

```bash
git add src/quantum_runtime/runtime/compare.py src/quantum_runtime/runtime/__init__.py tests/test_runtime_compare.py
git commit -m "feat: add compare policy verdicts"
```

### Task 2: Expose policy controls through the CLI

**Files:**
- Modify: `src/quantum_runtime/cli.py`
- Modify: `src/quantum_runtime/runtime/exit_codes.py`
- Test: `tests/test_cli_compare.py`

**Step 1: Write the failing test**

```python
def test_qrun_compare_json_policy_fails_for_subject_mismatch(tmp_path: Path) -> None:
    compare_result = RUNNER.invoke(
        app,
        ["compare", "--workspace", str(workspace), "--left-revision", "rev_000001", "--right-revision", "rev_000002", "--expect", "same-subject", "--json"],
    )
    assert compare_result.exit_code == 2
```

**Step 2: Run test to verify it fails**

Run: `uv run --python 3.11 --extra dev --extra qiskit pytest tests/test_cli_compare.py::test_qrun_compare_json_policy_fails_for_subject_mismatch -q`
Expected: `FAIL` because the CLI does not yet accept expectation flags or map verdict failure to exit code `2`.

**Step 3: Write minimal implementation**

Add:
- `--expect`
- `--allow-report-drift/--forbid-report-drift`
- `--forbid-backend-regressions`
- compare output summary that includes verdict information
- exit code mapping from policy verdicts

**Step 4: Run tests to verify they pass**

Run: `uv run --python 3.11 --extra dev --extra qiskit pytest tests/test_cli_compare.py -q`
Expected: `PASS`

**Step 5: Commit**

```bash
git add src/quantum_runtime/cli.py src/quantum_runtime/runtime/exit_codes.py tests/test_cli_compare.py
git commit -m "feat: add compare CLI guardrail flags"
```

### Task 3: Document the guardrail contract and verify release docs

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Test: `tests/test_release_docs.py`

**Step 1: Write the failing test**

```python
def test_readme_mentions_compare_expectation_guardrail() -> None:
    assert "--expect same-subject" in README_TEXT
```

**Step 2: Run test to verify it fails**

Run: `uv run --python 3.11 --extra dev pytest tests/test_release_docs.py -q`
Expected: `FAIL` because the release docs do not yet describe the compare guardrail flow.

**Step 3: Write minimal implementation**

Update:
- README command examples
- compare command positioning as CI/agent guardrail
- changelog entry for the new compare verdict layer

**Step 4: Run tests to verify they pass**

Run: `uv run --python 3.11 --extra dev pytest tests/test_release_docs.py -q`
Expected: `PASS`

**Step 5: Commit**

```bash
git add README.md CHANGELOG.md tests/test_release_docs.py
git commit -m "docs: describe compare policy guardrails"
```

### Task 4: Verify the full batch and land as one focused product increment

**Files:**
- Modify: `src/quantum_runtime/cli.py`
- Modify: `src/quantum_runtime/runtime/__init__.py`
- Modify: `src/quantum_runtime/runtime/compare.py`
- Modify: `src/quantum_runtime/runtime/exit_codes.py`
- Modify: `tests/test_cli_compare.py`
- Modify: `tests/test_runtime_compare.py`
- Modify: `tests/test_release_docs.py`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Step 1: Run static checks**

Run: `uv run --python 3.11 --extra dev ruff check src tests`
Expected: `All checks passed`

**Step 2: Run type checks**

Run: `uv run --python 3.11 --extra dev mypy src`
Expected: `Success: no issues found`

**Step 3: Run the full test suite**

Run: `uv run --python 3.11 --extra dev --extra qiskit pytest -q`
Expected: `PASS`

**Step 4: Commit the product slice**

```bash
git add README.md CHANGELOG.md src/quantum_runtime/cli.py src/quantum_runtime/runtime/__init__.py src/quantum_runtime/runtime/compare.py src/quantum_runtime/runtime/exit_codes.py tests/test_cli_compare.py tests/test_runtime_compare.py tests/test_release_docs.py docs/plans/2026-04-02-compare-policy-guardrails.md
git commit -m "feat: add compare policy guardrails"
```
