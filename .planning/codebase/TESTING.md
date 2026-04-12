# Testing Patterns

**Analysis Date:** 2026-04-12

## Test Framework

**Runner:**
- `pytest` is the test runner. The dev extra in `pyproject.toml` declares `pytest>=8.0`.
- Config lives in `pyproject.toml` under `[tool.pytest.ini_options]` with `testpaths = ["tests"]`.

**Assertion Library:**
- Built-in `pytest` assertions and `pytest.raises(...)` are used throughout `tests/test_workspace_manager.py`, `tests/test_qspec_validation.py`, `tests/test_runtime_imports.py`, and `tests/test_cli_control_plane.py`.

**Run Commands:**
```bash
uv run --python 3.11 --extra dev --extra qiskit pytest -q
pytest -q tests/test_cli_exec.py
# No dedicated watch-mode or coverage command is configured in `pyproject.toml`,
# `README.md`, `CONTRIBUTING.md`, or `.github/workflows/ci.yml`.
```

The canonical local gate comes from `CONTRIBUTING.md`. CI runs `pytest -q --ignore tests/test_classiq_backend.py --ignore tests/test_classiq_emitter.py --ignore tests/test_qspec_validation.py` in `.github/workflows/ci.yml`, while `.github/workflows/classiq.yml` separately runs `tests/test_classiq_backend.py` and `tests/test_classiq_emitter.py`.

## Test File Organization

**Location:**
- Tests are stored in a separate top-level `tests/` directory, not co-located with source.
- The suite currently contains 33 top-level `tests/test_*.py` modules.
- Snapshot and golden artifacts live under `tests/golden/`.
- There is no `tests/conftest.py` and no shared fixture package.

**Naming:**
- Use `tests/test_<feature>.py`, for example `tests/test_cli_exec.py`, `tests/test_runtime_compare.py`, `tests/test_pack_bundle.py`, and `tests/test_release_docs.py`.
- Use `tests/golden/<artifact>` for literal expected outputs, for example `tests/golden/qiskit_ghz_main.py`, `tests/golden/qasm_ghz_main.qasm`, `tests/golden/qspec_qaoa_maxcut.json`, and `tests/golden/report_summary_ghz.txt`.

**Structure:**
```text
tests/
├── test_cli_*.py              # Typer command and machine-output integration tests
├── test_runtime_*.py          # Runtime import/compare contract tests
├── test_qspec_validation.py   # Validation and normalization edge cases
├── test_qiskit_emitter.py     # Generated-code and golden snapshot tests
├── test_classiq_backend.py    # Optional backend behavior with monkeypatch fakes
├── test_release_docs.py       # Documentation and release contract checks
└── golden/                    # Snapshot fixtures and golden expected outputs
```

## Test Structure

**Suite Organization:**
```python
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.cli import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()


def test_qrun_init_json_creates_manifest_layout_and_schema_version(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    result = RUNNER.invoke(app, ["init", "--workspace", str(workspace), "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
```

This pattern is taken directly from `tests/test_cli_control_plane.py`.

**Patterns:**
- Prefer file-local setup over shared fixtures. Most tests construct their own workspace root with `tmp_path / ".quantum"` and call `WorkspaceManager.load_or_init(...)`, as in `tests/test_workspace_manager.py`, `tests/test_report_writer.py`, and `tests/test_cli_bench.py`.
- Use module constants for shared paths and runners, such as `PROJECT_ROOT` and `RUNNER` in `tests/test_cli_exec.py`, `tests/test_cli_doctor.py`, and `tests/test_qiskit_emitter.py`.
- Parse CLI output as JSON and assert a mix of exit code, payload schema, and filesystem side effects. This is the dominant style in `tests/test_cli_exec.py`, `tests/test_cli_compare.py`, `tests/test_cli_export.py`, and `tests/test_cli_observability.py`.
- Teardown is implicit through `tmp_path`; no explicit cleanup hooks are used.
- Parametrization exists but is limited. `tests/test_planner.py` uses `@pytest.mark.parametrize(...)` to cover multiple supported pattern families.

## Mocking

**Framework:** `pytest` built-ins, primarily `monkeypatch`

**Patterns:**
```python
def test_run_classiq_backend_returns_dependency_missing_when_sdk_unavailable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "quantum_runtime.backends.classiq_backend._load_classiq_module",
        raise_missing,
    )
```

This is the standard mocking shape in `tests/test_classiq_backend.py`. Similar `monkeypatch.setattr(...)` usage appears in `tests/test_cli_doctor.py`, `tests/test_cli_backend_list.py`, and `tests/test_runtime_imports.py`. `monkeypatch.chdir(...)` is used when a test needs relative-path behavior, for example in `tests/test_runtime_imports.py`.

**What to Mock:**
- Optional dependency loaders and environment-sensitive integration points, especially Classiq-related code in `tests/test_classiq_backend.py` and backend capability discovery in `tests/test_cli_doctor.py` or `tests/test_cli_backend_list.py`.
- Current working directory changes when path resolution is under test, as in `tests/test_runtime_imports.py`.

**What NOT to Mock:**
- Core JSON payloads and filesystem artifacts. Most integration tests write real files and then inspect `workspace.json`, `reports/latest.json`, `manifests/latest.json`, or trace logs directly.
- Generated code paths. `tests/test_qiskit_emitter.py` imports emitted Python from disk and executes it instead of stubbing the emitter output.
- CLI behavior. Most command tests use `CliRunner.invoke(...)` against the real Typer app in `src/quantum_runtime/cli.py`.

## Fixtures and Factories

**Test Data:**
```python
def _make_qspec() -> QSpec:
    return QSpec(
        program_id="  prog_ghz_4  ",
        goal="  Generate a 4-qubit GHZ circuit and measure all qubits.  ",
        ...
    )
```

This local helper style is used in `tests/test_qspec_validation.py`. Other examples include `_binding_only_qaoa_qspec()` in `tests/test_cli_exec.py`, `_seed_workspace()` in `tests/test_runtime_imports.py`, `_load_pack_module()` in `tests/test_pack_bundle.py`, and `_write_current_pack_shape()` in `tests/test_pack_bundle.py`.

**Location:**
- Helpers live inside the test module that uses them.
- Example input files under `examples/` are reused directly by tests such as `tests/test_cli_exec.py`, `tests/test_qiskit_emitter.py`, and `tests/test_classiq_backend.py`.
- Golden fixtures live under `tests/golden/`.
- No shared fixture registry is detected because there is no `tests/conftest.py`.

## Coverage

**Requirements:** No coverage threshold or coverage collection command is enforced.
- No `coverage` or `pytest-cov` dependency is declared in `pyproject.toml`.
- No coverage report command is documented in `README.md`, `CONTRIBUTING.md`, or `.github/workflows/ci.yml`.
- CI focuses on pass/fail behavior rather than measured coverage percentage.

**View Coverage:**
```bash
# Not configured. Add a local `pytest --cov ...` invocation manually if you need coverage data.
```

**Coverage Shape:**
- The suite is broad in behavior coverage, especially around CLI commands and workspace-state transitions.
- `tests/test_cli_exec.py`, `tests/test_cli_compare.py`, `tests/test_cli_export.py`, `tests/test_cli_control_plane.py`, and `tests/test_cli_observability.py` cover most of the command surface in `src/quantum_runtime/cli.py`.
- `tests/test_runtime_imports.py`, `tests/test_runtime_compare.py`, `tests/test_workspace_manager.py`, and `tests/test_workspace_baseline.py` cover the workspace and runtime state model.
- `tests/test_release_docs.py` and `tests/test_packaging_release.py` treat docs and packaging metadata as testable release contracts.
- Optional backend coverage is split out: `.github/workflows/classiq.yml` runs `tests/test_classiq_backend.py` and `tests/test_classiq_emitter.py` separately from the default CI job.

## Test Types

**Unit Tests:**
- Model parsing, validation, and normalization in `tests/test_intent_parser.py`, `tests/test_planner.py`, and `tests/test_qspec_validation.py`.
- Workspace and helper modules in `tests/test_workspace_manager.py`, `tests/test_workspace_baseline.py`, `tests/test_artifact_provenance.py`, and `tests/test_pack_bundle.py`.
- Lowering and diagnostics modules in `tests/test_qiskit_emitter.py`, `tests/test_classiq_emitter.py`, `tests/test_diagnostics.py`, and `tests/test_benchmark.py`.

**Integration Tests:**
- Typer command tests with real filesystem effects in `tests/test_cli_exec.py`, `tests/test_cli_compare.py`, `tests/test_cli_doctor.py`, `tests/test_cli_export.py`, and `tests/test_cli_inspect.py`.
- Runtime import and replay-integrity tests in `tests/test_runtime_imports.py` and `tests/test_runtime_compare.py`.
- Release and packaging contract checks in `tests/test_release_docs.py`, `tests/test_open_source_release.py`, and `tests/test_packaging_release.py`.

**E2E Tests:**
- No dedicated E2E framework is used.
- The closest E2E-style coverage is the CLI flow exercised through `CliRunner` plus subprocess-based smoke tests in `tests/test_cli_init.py` and `tests/test_qiskit_emitter.py`.

## Common Patterns

**Async Testing:**
```python
# Not used. No `async def` tests, `pytest-asyncio`, or event-loop fixtures were detected.
```

**Error Testing:**
```python
with pytest.raises(QSpecValidationError) as exc:
    validate_qspec(invalid)

assert exc.value.code == "invalid_qspec"
```

This is the standard error assertion pattern in `tests/test_qspec_validation.py`. CLI error tests follow the same shape at the process boundary by checking exit codes plus JSON reason fields, for example in `tests/test_cli_control_plane.py`, `tests/test_cli_compare.py`, and `tests/test_cli_export.py`.

**Golden and Generated Artifact Testing:**
```python
source = emit_qiskit_source(qspec)
golden = (PROJECT_ROOT / "tests" / "golden" / "qiskit_ghz_main.py").read_text()

assert source == golden
```

This snapshot style appears in `tests/test_qiskit_emitter.py`, `tests/test_classiq_emitter.py`, `tests/test_planner.py`, and `tests/test_report_writer.py`.

**Generated Code Execution:**
```python
spec = importlib.util.spec_from_file_location("generated_qiskit_program", output_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
```

`tests/test_qiskit_emitter.py` and `tests/test_pack_bundle.py` load generated modules from disk instead of mocking import-time behavior.

**CLI Subprocess Smoke Testing:**
```python
def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_ROOT)
    return subprocess.run([sys.executable, "-m", "quantum_runtime.cli", *args], ...)
```

`tests/test_cli_init.py` uses this pattern to validate the package entrypoint outside `CliRunner`.

---

*Testing analysis: 2026-04-12*
