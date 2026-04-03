# Compare Replay Trust Guardrails Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `qrun compare` expose replay-trust differences explicitly and let CI or agent hosts fail when the right-hand input regresses from a trustworthy replay baseline.

**Architecture:** Extend the existing compare pipeline instead of inventing a parallel trust command. Import resolution already computes `replay_integrity`; this slice should carry that state into compare-side payloads, compute a replay-integrity delta, and add a dedicated compare policy flag for trust regressions. Keep report drift and replay trust separate so hosts can distinguish “different outputs” from “less trustworthy replay evidence.”

**Tech Stack:** Python 3.11, Typer CLI, Pydantic, pytest, pathlib

### Task 1: Define replay-trust compare signals in the runtime layer

**Files:**
- Modify: `src/quantum_runtime/runtime/compare.py`
- Test: `tests/test_runtime_compare.py`

**Step 1: Write the failing tests**

Add tests that prove:
- compare results include side-level replay-integrity payloads
- compare results include a replay-integrity delta with status and warning changes
- compare results classify a left=`ok` to right=`legacy` or `degraded` transition as a replay-integrity regression
- compare highlights explain replay-trust changes in plain language

**Step 2: Run tests to verify they fail**

Run:
`uv run --python 3.11 --extra dev --extra qiskit pytest tests/test_runtime_compare.py -q`

Expected:
- `FAIL` because compare results currently ignore `ImportResolution.replay_integrity`.

**Step 3: Write minimal implementation**

Implement:
- replay-integrity payload on each compare side
- compare-level replay-integrity delta
- replay-integrity regression detection from left to right
- highlight text for trust degradation and legacy replay inputs

**Step 4: Run tests to verify they pass**

Run:
`uv run --python 3.11 --extra dev --extra qiskit pytest tests/test_runtime_compare.py -q`

Expected:
- `PASS`

**Step 5: Commit**

```bash
git add src/quantum_runtime/runtime/compare.py tests/test_runtime_compare.py
git commit -m "feat: surface replay trust in compare"
```

### Task 2: Add compare policy guardrails for replay-trust regressions

**Files:**
- Modify: `src/quantum_runtime/runtime/compare.py`
- Modify: `src/quantum_runtime/runtime/exit_codes.py`
- Modify: `src/quantum_runtime/cli.py`
- Test: `tests/test_cli_compare.py`
- Test: `tests/test_runtime_compare.py`

**Step 1: Write the failing tests**

Add tests that prove:
- `ComparePolicy` accepts a replay-trust regression guardrail
- compare verdicts fail when the right side regresses in replay integrity and the guardrail is enabled
- `qrun compare --forbid-replay-integrity-regressions --json` returns degraded exit code with a structured failed check
- plaintext compare output still surfaces the first highlight cleanly

**Step 2: Run tests to verify they fail**

Run:
`uv run --python 3.11 --extra dev --extra qiskit pytest tests/test_runtime_compare.py tests/test_cli_compare.py -q`

Expected:
- `FAIL` because the CLI and policy model do not yet understand replay-trust guardrails.

**Step 3: Write minimal implementation**

Implement:
- `ComparePolicy.forbid_replay_integrity_regressions`
- verdict evaluation for replay-integrity regressions
- compare JSON fields for the new delta and regression list
- CLI wiring for `--forbid-replay-integrity-regressions`

**Step 4: Run tests to verify they pass**

Run:
`uv run --python 3.11 --extra dev --extra qiskit pytest tests/test_runtime_compare.py tests/test_cli_compare.py -q`

Expected:
- `PASS`

**Step 5: Commit**

```bash
git add src/quantum_runtime/runtime/compare.py src/quantum_runtime/runtime/exit_codes.py src/quantum_runtime/cli.py tests/test_runtime_compare.py tests/test_cli_compare.py
git commit -m "feat: guard compare against replay trust regressions"
```

### Task 3: Document the replay-trust compare contract

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Test: `tests/test_release_docs.py`

**Step 1: Write the failing test**

Add a doc test that proves release docs mention replay-trust compare guardrails.

**Step 2: Run tests to verify they fail**

Run:
`uv run --python 3.11 --extra dev pytest tests/test_release_docs.py -q`

Expected:
- `FAIL` because docs do not yet describe replay-trust compare policy.

**Step 3: Write minimal implementation**

Document:
- what replay-integrity means in compare output
- the difference between report drift and replay-trust regression
- the new `--forbid-replay-integrity-regressions` flag

**Step 4: Run tests to verify they pass**

Run:
`uv run --python 3.11 --extra dev pytest tests/test_release_docs.py -q`

Expected:
- `PASS`

**Step 5: Commit**

```bash
git add README.md CHANGELOG.md tests/test_release_docs.py docs/plans/2026-04-03-compare-replay-trust.md
git commit -m "docs: describe compare replay trust guardrails"
```

### Task 4: Run the release gate for the full slice

**Files:**
- Modify: `src/quantum_runtime/cli.py`
- Modify: `src/quantum_runtime/runtime/compare.py`
- Modify: `src/quantum_runtime/runtime/exit_codes.py`
- Modify: `tests/test_cli_compare.py`
- Modify: `tests/test_runtime_compare.py`
- Modify: `tests/test_release_docs.py`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Step 1: Run static checks**

Run:
`uv run --python 3.11 --extra dev ruff check src tests`

Expected:
- `All checks passed`

**Step 2: Run type checks**

Run:
`uv run --python 3.11 --extra dev mypy src`

Expected:
- `Success: no issues found`

**Step 3: Run the full test suite**

Run:
`uv run --python 3.11 --extra dev --extra qiskit pytest -q`

Expected:
- `PASS`

**Step 4: Commit the product slice**

```bash
git add README.md CHANGELOG.md src/quantum_runtime/cli.py src/quantum_runtime/runtime/compare.py src/quantum_runtime/runtime/exit_codes.py tests/test_cli_compare.py tests/test_runtime_compare.py tests/test_release_docs.py docs/plans/2026-04-03-compare-replay-trust.md
git commit -m "feat: add compare replay trust guardrails"
```
