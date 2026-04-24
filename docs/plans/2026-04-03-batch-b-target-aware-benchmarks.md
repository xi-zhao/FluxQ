# Batch B Target-Aware Benchmarks Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make FluxQ benchmark output decision-grade by explicitly distinguishing structural estimates, target-aware Qiskit transpilation, and Classiq synthesis-backed metrics, including the assumptions and fallback path behind every reported number.

**Architecture:** Add a small provenance contract rather than inventing a fake universal benchmark score. Qiskit target validation should emit normalized target-assumption metadata and benchmark mode. Classiq synthesis should report which constraints/preferences were applied, which were unsupported, and whether the resulting metrics are directly comparable to target-aware Qiskit results. The benchmark aggregator should surface those modes and comparability signals without overclaiming equivalence.

**Tech Stack:** Python 3.11, Pydantic models, Qiskit transpile, optional Classiq backend, pytest, Typer CLI JSON consumers

### Task 1: Normalize target-validation provenance for Qiskit

**Files:**
- Modify: `src/quantum_runtime/diagnostics/transpile_validate.py`
- Test: `tests/test_target_validation.py`
- Test: `tests/test_benchmark.py`

**Step 1: Write the failing tests**

Add tests that prove:
- target validation reports a machine-readable `benchmark_mode`
- target validation emits normalized `target_assumptions`
- skipped transpilation is labeled structural and does not claim target-aware comparability
- successful constrained transpilation is labeled target-aware and records the assumptions that drove it

**Step 2: Run tests to verify they fail**

Run:

```bash
uv run --python 3.11 --extra dev pytest tests/test_target_validation.py tests/test_benchmark.py -q
```

Expected: FAIL because target-validation provenance is not explicit enough yet.

**Step 3: Write minimal implementation**

Implement:
- `benchmark_mode` on `TargetValidationReport`
- `target_assumptions` summary with optimization level, basis gates, connectivity map, and max depth
- explicit comparability hint for skipped vs target-aware transpilation

**Step 4: Run tests to verify they pass**

Run:

```bash
uv run --python 3.11 --extra dev pytest tests/test_target_validation.py tests/test_benchmark.py -q
```

Expected: PASS

### Task 2: Expose Classiq target assumptions and unsupported constraints

**Files:**
- Modify: `src/quantum_runtime/backends/classiq_backend.py`
- Test: `tests/test_classiq_backend.py`
- Test: `tests/test_benchmark.py`

**Step 1: Write the failing tests**

Add tests that prove:
- Classiq backend reports applied preferences and applied constraints
- unsupported target constraints are surfaced explicitly instead of being silently ignored
- synthesis-backed metrics and fallback metrics both expose their assumption/fallback path

**Step 2: Run tests to verify they fail**

Run:

```bash
uv run --python 3.11 --extra dev pytest tests/test_classiq_backend.py tests/test_benchmark.py -q
```

Expected: FAIL because Classiq benchmark provenance is still too implicit.

**Step 3: Write minimal implementation**

Implement:
- structured target-assumption details on `ClassiqBackendReport`
- explicit `unsupported_constraints` reporting for constraints FluxQ cannot honestly claim to have enforced through Classiq
- synthesis provenance details that benchmark aggregation can reuse directly

**Step 4: Run tests to verify they pass**

Run:

```bash
uv run --python 3.11 --extra dev pytest tests/test_classiq_backend.py tests/test_benchmark.py -q
```

Expected: PASS

### Task 3: Aggregate comparable benchmark modes and capability metadata

**Files:**
- Modify: `src/quantum_runtime/diagnostics/benchmark.py`
- Modify: `src/quantum_runtime/runtime/backend_registry.py`
- Modify: `src/quantum_runtime/reporters/summary.py`
- Test: `tests/test_benchmark.py`
- Test: `tests/test_cli_bench.py`
- Test: `tests/test_release_docs.py`

**Step 1: Write the failing tests**

Add tests that prove:
- each backend benchmark entry includes explicit benchmark mode and comparability metadata
- Qiskit structural-only entries are labeled differently from target-aware entries
- Classiq synthesis-backed entries expose whether target parity is partial or unavailable
- backend capability descriptors distinguish target-aware benchmarking from synthesis-backed benchmarking
- user-facing docs mention the benchmark honesty contract

**Step 2: Run tests to verify they fail**

Run:

```bash
uv run --python 3.11 --extra dev pytest tests/test_benchmark.py tests/test_cli_bench.py tests/test_release_docs.py -q
```

Expected: FAIL because benchmark outputs and docs do not yet expose the new contract.

**Step 3: Write minimal implementation**

Implement:
- normalized benchmark mode fields in aggregate benchmark output
- comparability metadata and fallback reasons in backend details
- backend registry capability flags for target-aware vs synthesis-backed benchmark support
- concise summary wording that does not overclaim cross-backend equivalence
- README/CHANGELOG text for target-aware benchmark honesty

**Step 4: Run tests to verify they pass**

Run:

```bash
uv run --python 3.11 --extra dev pytest tests/test_benchmark.py tests/test_cli_bench.py tests/test_release_docs.py -q
```

Expected: PASS

### Task 4: Full verification and commit

**Files:**
- Modify only files touched above

**Step 1: Run focused benchmark suites**

```bash
uv run --python 3.11 --extra dev pytest tests/test_target_validation.py tests/test_classiq_backend.py tests/test_benchmark.py tests/test_cli_bench.py tests/test_release_docs.py -q
```

Expected: PASS

**Step 2: Run project verification gates**

```bash
uv run --python 3.11 --extra dev ruff check src tests
uv run --python 3.11 --extra dev mypy src
uv run --python 3.11 --extra dev --extra qiskit pytest -q
```

Expected: PASS

**Step 3: Commit**

```bash
git add src/quantum_runtime/diagnostics/transpile_validate.py src/quantum_runtime/backends/classiq_backend.py src/quantum_runtime/diagnostics/benchmark.py src/quantum_runtime/runtime/backend_registry.py src/quantum_runtime/reporters/summary.py tests/test_target_validation.py tests/test_classiq_backend.py tests/test_benchmark.py tests/test_cli_bench.py tests/test_release_docs.py README.md CHANGELOG.md docs/plans/2026-04-03-batch-b-target-aware-benchmarks.md
git commit -m "feat: add target-aware benchmark provenance"
```
