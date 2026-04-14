# Testing Patterns

**Analysis Date:** 2026-04-14

## Test Framework

**Runner:**
- Use `pytest` as the test runner. The repository config is `[tool.pytest.ini_options]` in `pyproject.toml`, with `testpaths = ["tests"]`.
- Run the default CI pytest job from `.github/workflows/ci.yml` after installing `.[dev,qiskit]`.
- Run Classiq-only tests from `.github/workflows/classiq.yml` after installing `.[dev,classiq]`.

**Assertion Library:**
- Use plain `assert` statements plus `pytest.raises(...)` for exceptions. Representative files include `tests/test_cli_exec.py`, `tests/test_qspec_validation.py`, `tests/test_runtime_workspace_safety.py`, and `tests/test_target_validation.py`.

**Run Commands:**
```bash
uv run --python 3.11 --extra dev --extra qiskit pytest -q
./scripts/dev-bootstrap.sh verify
python -m pip install -e '.[dev,classiq]' && pytest -q tests/test_classiq_backend.py tests/test_classiq_emitter.py
```

Coverage command:
```bash
# Not configured in repo
```

## Test File Organization

**Location:**
- Keep tests in the top-level `tests/` directory rather than colocated with `src/`.
- Reuse checked-in example inputs from `examples/` and documentation files from the repo root or `docs/` when a test is about release or integration contracts.

**Naming:**
- Use `tests/test_<area>.py` for canonical test modules, for example `tests/test_cli_compare.py`, `tests/test_runtime_compare.py`, `tests/test_workspace_locking.py`, `tests/test_qasm_export.py`, and `tests/test_release_docs.py`.
- Keep golden files in `tests/golden/`, for example `tests/golden/qspec_ghz.json`, `tests/golden/qspec_qaoa_maxcut.json`, `tests/golden/qasm_ghz_main.qasm`, `tests/golden/qiskit_ghz_main.py`, and `tests/golden/report_summary_ghz.txt`.
- Do not copy the `-NSConflict-...` filenames in `tests/test_cli_bench-NSConflict-BlovedSwami-mac26.4.1.py` and `tests/test_runtime_imports-NSConflict-BlovedSwami-mac26.4.1.py`; those are conflict artifacts, not the suite pattern.

**Structure:**
```text
tests/
├── test_cli_*.py              # CLI commands and output contracts
├── test_runtime_*.py          # Runtime orchestration and comparison logic
├── test_workspace_*.py        # Workspace manifest, locking, and baseline behavior
├── test_*_release.py          # Packaging, docs, and release-contract checks
└── golden/                    # Snapshot fixtures for QSpec, source, and summaries
```

- The repository contains 43 canonical `tests/test_*.py` files and 318 `def test_...` functions.
- No `conftest.py` file is present under `tests/`.

## Test Structure

**Suite Organization:**
```python
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()

def _write_intent(path: Path, *, title: str, goal: str) -> Path:
    ...

def test_qrun_exec_json_generates_workspace_artifacts_and_report(tmp_path: Path) -> None:
    result = RUNNER.invoke(app, ["exec", "--workspace", str(workspace), "--json"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
```

**Patterns:**
- Keep setup helpers local to the test module. Examples include `_write_intent()` in `tests/test_cli_exec.py`, `_doctor_capabilities()` in `tests/test_cli_doctor.py`, `_load_pack_module()` in `tests/test_pack_bundle.py`, `_make_qspec()` in `tests/test_qspec_validation.py`, and `_history_paths()` in `tests/test_runtime_workspace_safety.py`.
- Use `tmp_path` as the default isolation mechanism for filesystem-heavy tests. This pattern is pervasive across `tests/test_cli_exec.py`, `tests/test_cli_compare.py`, `tests/test_runtime_imports.py`, `tests/test_workspace_manager.py`, and `tests/test_pack_bundle.py`.
- Use `CliRunner()` for CLI behavior unless a real process boundary matters. `tests/test_cli_exec.py`, `tests/test_cli_compare.py`, `tests/test_cli_observability.py`, and `tests/test_cli_doctor.py` use `CliRunner`; `tests/test_cli_init.py` uses `subprocess.run()` and `subprocess.Popen()` because it needs process-level lock behavior.
- Assert full JSON payload shape, exit code, and persisted files together. `tests/test_cli_control_plane.py`, `tests/test_cli_exec.py`, `tests/test_cli_compare.py`, and `tests/test_cli_observability.py` all read the workspace files back from disk after the command returns.
- Seed failure modes by mutating on-disk JSON or deleting authoritative files rather than by mocking everything. Examples appear in `tests/test_cli_control_plane.py`, `tests/test_cli_inspect.py`, `tests/test_workspace_baseline.py`, and `tests/test_runtime_imports.py`.
- Use `pytest.mark.parametrize(...)` sparingly for compact input matrices. The main example is `tests/test_planner.py`.

## Mocking

**Framework:** `pytest` `monkeypatch` with small inline fakes and lambdas. No dedicated mocking library is configured.

**Patterns:**
```python
monkeypatch.setattr(
    "quantum_runtime.backends.classiq_backend._load_classiq_module",
    raise_missing,
)

with pytest.raises(ImportSourceError) as excinfo:
    resolve_report_file(tmp_path / "missing-report.json")
```

```python
monkeypatch.setattr(
    "quantum_runtime.runtime.doctor.collect_backend_capabilities",
    lambda: _doctor_capabilities(classiq_available=False),
)
```

**What to Mock:**
- Optional dependency probes and backend capability discovery, for example in `tests/test_classiq_backend.py`, `tests/test_cli_backend_list.py`, and `tests/test_cli_doctor.py`.
- Expensive or concurrency-sensitive runtime boundaries, for example `run_local_simulation`, `write_diagrams`, and `write_run_manifest` in `tests/test_runtime_workspace_safety.py`.
- Backend synthesis and benchmark integration points, for example `run_classiq_backend` in `tests/test_benchmark.py` and `tests/test_cli_bench.py`.

**What NOT to Mock:**
- Workspace file writes and read-backs when the behavior under test is the workspace contract. `tests/test_cli_exec.py`, `tests/test_cli_compare.py`, `tests/test_runtime_imports.py`, `tests/test_runtime_revision_artifacts.py`, and `tests/test_workspace_manager.py` all prefer real files.
- Golden snapshot emitters when verifying canonical output. `tests/test_planner.py`, `tests/test_qasm_export.py`, `tests/test_qiskit_emitter.py`, `tests/test_classiq_emitter.py`, and `tests/test_report_writer.py` compare real generated outputs against checked-in fixtures.

## Fixtures and Factories

**Test Data:**
```python
def _make_qspec() -> QSpec:
    return QSpec(
        program_id="  prog_ghz_4  ",
        ...
        backend_preferences=[" qiskit-local ", "", "classiq", "qiskit-local"],
    )
```

```python
def _write_intent(path: Path, *, title: str, goal: str) -> Path:
    path.write_text(
        f"""---
title: {title}
---

{goal}
"""
    )
    return path
```

**Location:**
- Use module-local helpers rather than shared fixtures. No `@pytest.fixture` decorators are present in `tests/`.
- Reuse example input files such as `examples/intent-ghz.md` and `examples/intent-qaoa-maxcut.md` in parser, planner, CLI, benchmark, and export tests.
- Keep golden fixtures in `tests/golden/`:
  - `tests/golden/qspec_ghz.json` and `tests/golden/qspec_qaoa_maxcut.json` for planner output.
  - `tests/golden/qspec_hardware_efficient_ansatz.json` for parameterized HEA planning.
  - `tests/golden/qasm_ghz_main.qasm` and `tests/golden/qiskit_ghz_main.py` for source emitters.
  - `tests/golden/classiq_ghz_main.py` for Classiq source emission.
  - `tests/golden/report_summary_ghz.txt` for summary compression.

## Coverage

**Requirements:** No coverage target or coverage threshold is enforced. No `pytest-cov` dependency, `--cov` command, or coverage report config is present in `pyproject.toml`, `README.md`, `CONTRIBUTING.md`, or the GitHub workflows.

**View Coverage:**
```bash
# Not configured in repo
```

## Test Types

**Unit Tests:**
- Parser, planner, semantics, validation, lowering, and diagnostics logic are covered in focused modules such as `tests/test_intent_parser.py`, `tests/test_planner.py`, `tests/test_qspec_validation.py`, `tests/test_qasm_export.py`, `tests/test_qiskit_emitter.py`, `tests/test_classiq_emitter.py`, `tests/test_diagnostics.py`, and `tests/test_target_validation.py`.

**Integration Tests:**
- CLI and workspace contract coverage dominates the suite. Representative modules include `tests/test_cli_exec.py`, `tests/test_cli_compare.py`, `tests/test_cli_control_plane.py`, `tests/test_cli_observability.py`, `tests/test_cli_export.py`, `tests/test_cli_doctor.py`, `tests/test_runtime_imports.py`, `tests/test_runtime_workspace_safety.py`, and `tests/test_runtime_revision_artifacts.py`.
- Release and packaging contracts are also tested as integration surfaces through `tests/test_release_docs.py`, `tests/test_packaging_release.py`, and `tests/test_aionrs_assets.py`.

**E2E Tests:**
- No separate browser or service-level E2E framework is configured.
- The closest end-to-end tests are command-line flows that exercise real workspace state, subprocesses, or concurrency, especially `tests/test_cli_init.py`, `tests/test_cli_exec.py`, `tests/test_cli_compare.py`, and `tests/test_runtime_workspace_safety.py`.

## Known Gaps

**CI Scope:**
- The default PR pytest job in `.github/workflows/ci.yml` skips `tests/test_classiq_backend.py`, `tests/test_classiq_emitter.py`, and `tests/test_qspec_validation.py`.
- Classiq-only tests run only in `.github/workflows/classiq.yml`, and that workflow is gated behind manual `workflow_dispatch` input `run_classiq`.

**Coverage Tooling:**
- Coverage reporting is absent. The repository has no built-in way to answer line or branch coverage questions.

**Static Analysis Scope:**
- MyPy checks `src/` only. Tests in `tests/` are not type-checked.
- Ruff excludes `tests/golden/` and `tests/test_qspec_validation.py`, so those paths rely on manual review and execution rather than the main lint gate.

**Suite Structure:**
- No shared fixture layer exists. Setup duplication across CLI modules such as `tests/test_cli_exec.py`, `tests/test_cli_compare.py`, `tests/test_cli_observability.py`, and `tests/test_cli_doctor.py` increases drift risk when the workspace contract changes.
- Conflict-artifact files remain in the tree under `tests/`; do not extend them when adding new tests.

## Common Patterns

**Async Testing:**
```python
first_thread = threading.Thread(target=_run_exec, args=(workspace, ghz_intent, first_outcome))
second_thread = threading.Thread(target=_run_exec, args=(workspace, bell_intent, second_outcome))

first_thread.start()
assert first_simulation_started.wait(timeout=5)
second_thread.start()
```

- The suite does not use `asyncio` or async pytest plugins.
- Concurrency tests use `threading`, blocking events, subprocesses, and workspace locks in `tests/test_runtime_workspace_safety.py` and `tests/test_cli_init.py`.

**Error Testing:**
```python
with pytest.raises(QSpecValidationError) as exc:
    validate_qspec(invalid)

assert exc.value.code == "invalid_qspec"
```

```python
result = RUNNER.invoke(app, ["compare", "--workspace", str(workspace), "--json"])
assert result.exit_code == 2, result.stdout
payload = json.loads(result.stdout)
assert payload["gate"]["ready"] is False
```

- Error-path tests check both structured exception codes and CLI exit codes.
- Degraded runtime states are asserted through `reason_codes`, `next_actions`, `decision`, and `gate` blocks in `tests/test_cli_observability.py`, `tests/test_cli_control_plane.py`, `tests/test_cli_compare.py`, and `tests/test_cli_doctor.py`.

---

*Testing analysis: 2026-04-14*
