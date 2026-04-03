# Replay Integrity Guardrails Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make report-based replay fail safely when the resolved QSpec or artifact set no longer matches the original recorded run.

**Architecture:** Extend report writing to persist replay-integrity metadata for replay-critical outputs, then make import resolution verify QSpec identity and artifact digests before downstream commands trust a report input. Surface the resulting trust status through import summaries and `inspect --json` so agent hosts can make decisions without reverse-engineering exit codes.

**Tech Stack:** Python 3.11, Typer CLI, Pydantic, pytest, pathlib, hashlib

### Task 1: Persist replay-integrity metadata in reports

**Files:**
- Modify: `src/quantum_runtime/reporters/writer.py`
- Test: `tests/test_report_writer.py`

**Step 1: Write the failing tests**

Add tests that prove:
- `write_report()` stores the recorded QSpec hash and semantic hash in a replay-integrity block.
- `write_report()` stores per-artifact output digests for replay-critical outputs.

**Step 2: Run tests to verify they fail**

Run:
`uv run --python 3.11 --extra dev --extra qiskit pytest tests/test_report_writer.py -q`

Expected:
- `FAIL` because reports currently do not persist a dedicated replay-integrity contract for artifact digests.

**Step 3: Write minimal implementation**

Implement:
- a stable report field for replay integrity metadata
- per-artifact digest persistence for replay-critical outputs
- backward-compatible behavior for reports that do not yet contain the new field

**Step 4: Run tests to verify they pass**

Run:
`uv run --python 3.11 --extra dev --extra qiskit pytest tests/test_report_writer.py -q`

Expected:
- `PASS`

**Step 5: Commit**

```bash
git add src/quantum_runtime/reporters/writer.py tests/test_report_writer.py
git commit -m "feat: persist replay integrity metadata"
```

### Task 2: Reject unsafe QSpec replay and classify artifact integrity

**Files:**
- Modify: `src/quantum_runtime/runtime/imports.py`
- Modify: `src/quantum_runtime/artifact_provenance.py`
- Test: `tests/test_runtime_imports.py`

**Step 1: Write the failing tests**

Add tests that prove:
- report imports reject a resolved QSpec whose content hash no longer matches the recorded report
- report imports reject a resolved QSpec whose semantic hash no longer matches the recorded report
- missing history snapshots do not silently fall back to mutable current aliases unless integrity can be proven
- intact copied-report replay still succeeds and exposes replay-integrity status

**Step 2: Run tests to verify they fail**

Run:
`uv run --python 3.11 --extra dev --extra qiskit pytest tests/test_runtime_imports.py -q`

Expected:
- `FAIL` because report imports currently validate path structure more strictly than content identity.

**Step 3: Write minimal implementation**

Implement:
- QSpec hash verification against `report["qspec"]["hash"]`
- semantic hash verification against `report["qspec"]["semantic_hash"]`
- explicit replay-integrity classification on import resolution
- safe handling for legacy reports without new integrity metadata

**Step 4: Run tests to verify they pass**

Run:
`uv run --python 3.11 --extra dev --extra qiskit pytest tests/test_runtime_imports.py -q`

Expected:
- `PASS`

**Step 5: Commit**

```bash
git add src/quantum_runtime/runtime/imports.py src/quantum_runtime/artifact_provenance.py tests/test_runtime_imports.py
git commit -m "feat: verify report replay integrity"
```

### Task 3: Surface replay-integrity trust in inspect and report-backed commands

**Files:**
- Modify: `src/quantum_runtime/runtime/inspect.py`
- Modify: `src/quantum_runtime/runtime/executor.py`
- Modify: `src/quantum_runtime/runtime/export.py`
- Modify: `src/quantum_runtime/runtime/benchmark.py`
- Test: `tests/test_cli_exec.py`
- Test: `tests/test_cli_export.py`
- Test: `tests/test_cli_bench.py`
- Test: `tests/test_cli_inspect.py`

**Step 1: Write the failing tests**

Add tests that prove:
- `inspect --json` exposes explicit replay-integrity status/errors/warnings
- `exec/export/bench` from tampered report inputs fail with structured import reasons
- intact report replay still succeeds

**Step 2: Run tests to verify they fail**

Run:
`uv run --python 3.11 --extra dev --extra qiskit pytest tests/test_cli_exec.py tests/test_cli_export.py tests/test_cli_bench.py tests/test_cli_inspect.py -q`

Expected:
- `FAIL` because replay trust is not yet surfaced consistently across host-facing JSON outputs.

**Step 3: Write minimal implementation**

Implement:
- replay-integrity payload in inspect JSON
- structured import failure propagation for report-backed exec/export/bench
- degraded inspect status when replay trust is weakened but not invalid

**Step 4: Run tests to verify they pass**

Run:
`uv run --python 3.11 --extra dev --extra qiskit pytest tests/test_cli_exec.py tests/test_cli_export.py tests/test_cli_bench.py tests/test_cli_inspect.py -q`

Expected:
- `PASS`

**Step 5: Commit**

```bash
git add src/quantum_runtime/runtime/inspect.py src/quantum_runtime/runtime/executor.py src/quantum_runtime/runtime/export.py src/quantum_runtime/runtime/benchmark.py tests/test_cli_exec.py tests/test_cli_export.py tests/test_cli_bench.py tests/test_cli_inspect.py
git commit -m "feat: expose replay integrity trust"
```

### Task 4: Document the replay-integrity contract and run the release gate

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Test: `tests/test_release_docs.py`

**Step 1: Update docs**

Document:
- the replay-integrity contract
- what legacy reports do and do not guarantee
- which commands fail hard versus degrade

**Step 2: Run doc verification**

Run:
`uv run --python 3.11 --extra dev pytest tests/test_release_docs.py -q`

Expected:
- `PASS`

**Step 3: Run full verification**

Run:
- `uv run --python 3.11 --extra dev ruff check src tests`
- `uv run --python 3.11 --extra dev mypy src`
- `uv run --python 3.11 --extra dev --extra qiskit pytest -q`

Expected:
- all commands succeed

**Step 4: Commit**

```bash
git add README.md CHANGELOG.md tests/test_release_docs.py docs/plans/2026-04-03-replay-integrity-guardrails.md
git commit -m "docs: define replay integrity contract"
```
