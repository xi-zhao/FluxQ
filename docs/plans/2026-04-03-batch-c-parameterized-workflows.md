# Batch C Parameterized Workflows Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn FluxQ `0.2.3` into a credible local parameter-evaluation runtime for `qaoa_ansatz` and `hardware_efficient_ansatz`, with explicit parameter workflow metadata, explicit observable specs, and exact local expectation diagnostics.

**Architecture:** Treat a parameterized run as a first-class workflow contract: `QSpec parameter schema + parameter workflow + observable set + exact local evaluation`. Do not add an optimizer, gradient engine, or remote backend story. Keep the implementation local, deterministic, and honest.

**Tech Stack:** Python 3.11, Pydantic QSpec/report models, Qiskit circuit/statevector evaluation, Typer CLI via existing `exec`, pytest

### Task 1: Add parameter workflow and observable semantics to QSpec

**Files:**
- Modify: `src/quantum_runtime/intent/planner.py`
- Modify: `src/quantum_runtime/qspec/validation.py`
- Modify: `src/quantum_runtime/qspec/semantics.py`
- Test: `tests/test_planner.py`
- Test: `tests/test_qspec_validation.py`

**Step 1: Write failing tests**

Add tests that prove:
- QAOA planning emits an explicit MaxCut cost observable as weighted Pauli terms
- HEA planning can carry explicit user-declared Pauli-sum observables
- intent constraints can declare either a single parameter binding set or a small parameter sweep grid
- validation rejects unknown parameter names, non-numeric values, invalid observable terms, or unsupported mixed workflow modes

**Step 2: Run tests to verify they fail**

```bash
uv run --python 3.11 --extra dev pytest tests/test_planner.py tests/test_qspec_validation.py -q
```

Expected: FAIL because parameter workflow and observable semantics are not first-class yet.

**Step 3: Write minimal implementation**

Implement:
- normalized metadata contract for `parameter_workflow`
- explicit observable contract for weighted Pauli terms
- automatic QAOA MaxCut cost observable lowering
- HEA observable passthrough from intent constraints
- semantic summaries that distinguish workload identity from execution/sample choices

**Step 4: Run tests to verify they pass**

```bash
uv run --python 3.11 --extra dev pytest tests/test_planner.py tests/test_qspec_validation.py -q
```

Expected: PASS

### Task 2: Add exact local expectation diagnostics

**Files:**
- Modify: `src/quantum_runtime/diagnostics/simulate.py`
- Modify: `src/quantum_runtime/runtime/executor.py`
- Modify: `src/quantum_runtime/reporters/writer.py`
- Modify: `src/quantum_runtime/runtime/inspect.py`
- Test: `tests/test_diagnostics.py`
- Test: `tests/test_cli_exec.py`
- Test: `tests/test_runtime_compare.py`

**Step 1: Write failing tests**

Add tests that prove:
- local simulation can evaluate exact expectation values from the pre-measure circuit state
- single-binding workflows report explicit bound values and expectation outputs
- small sweep workflows report multiple evaluated points plus a clearly labeled sampled best point when an objective observable exists
- reports and inspect output expose observables, parameter workflow, and evaluation provenance
- compare can tell the difference between workload drift and changed parameter workflow execution choices

**Step 2: Run tests to verify they fail**

```bash
uv run --python 3.11 --extra dev pytest tests/test_diagnostics.py tests/test_cli_exec.py tests/test_runtime_compare.py -q
```

Expected: FAIL because parameterized evaluation is not implemented yet.

**Step 3: Write minimal implementation**

Implement:
- exact local expectation evaluation mode using statevector
- representative count simulation that stays explicit about which parameter point it used
- structured parameter-point results and expectation-value results in diagnostics/report payloads
- inspect/compare summaries that include observables and parameter workflow semantics

**Step 4: Run tests to verify they pass**

```bash
uv run --python 3.11 --extra dev pytest tests/test_diagnostics.py tests/test_cli_exec.py tests/test_runtime_compare.py -q
```

Expected: PASS

### Task 3: Documentation, verification, and commit

**Files:**
- Modify only files touched above plus docs if needed

**Step 1: Update docs**

Document the `0.2.3` contract in:
- `README.md`
- `CHANGELOG.md`
- this plan file if needed

Keep the wording honest:
- local exact expectation evaluation only
- no optimizer
- no backend parity claims

**Step 2: Run focused and full verification**

```bash
uv run --python 3.11 --extra dev pytest tests/test_planner.py tests/test_qspec_validation.py tests/test_diagnostics.py tests/test_cli_exec.py tests/test_runtime_compare.py -q
uv run --python 3.11 --extra dev ruff check src tests
uv run --python 3.11 --extra dev mypy src
uv run --python 3.11 --extra dev --extra qiskit pytest -q
```

Expected: PASS

**Step 3: Commit**

```bash
git add src/quantum_runtime/intent/planner.py src/quantum_runtime/qspec/validation.py src/quantum_runtime/qspec/semantics.py src/quantum_runtime/diagnostics/simulate.py src/quantum_runtime/runtime/executor.py src/quantum_runtime/reporters/writer.py src/quantum_runtime/runtime/inspect.py tests/test_planner.py tests/test_qspec_validation.py tests/test_diagnostics.py tests/test_cli_exec.py tests/test_runtime_compare.py README.md CHANGELOG.md docs/plans/2026-04-03-batch-c-parameterized-workflows.md
git commit -m "feat: add parameterized expectation workflows"
```
