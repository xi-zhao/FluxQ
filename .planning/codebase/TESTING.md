# Testing Patterns

**Analysis Date:** 2026-04-18

## Test Framework

**Runner:**
- `pytest >=8.0` is declared in the `dev` extra in `pyproject.toml`.
- Config: `pyproject.toml` under `[tool.pytest.ini_options]` with `testpaths = ["tests"]`.

**Assertion Library:**
- Pytest built-in assertion rewriting plus `pytest.raises`, used throughout `tests/test_cli_*.py`, `tests/test_runtime_*.py`, and `tests/test_qspec_validation.py`.

**Run Commands:**
```bash
uv run --python 3.11 --extra dev --extra qiskit pytest -q                                                                 # Full contributor smoke from `CONTRIBUTING.md`
pytest -q --ignore tests/test_classiq_backend.py --ignore tests/test_classiq_emitter.py --ignore tests/test_qspec_validation.py  # CI suite in `.github/workflows/ci.yml`
./scripts/dev-bootstrap.sh verify                                                                                         # Repo-local smoke wrapper
```

- Watch mode: Not detected.
- Coverage command: Not detected.

## Test File Organization

**Location:**
- Tests live in the top-level `tests/` directory selected by `pyproject.toml`; they are not co-located with `src/quantum_runtime/`.
- No `conftest.py` is present under `tests/`. Shared setup is intentionally light, and helper builders stay inside each test module.
- Checked-in snapshots and golden artifacts live under `tests/golden/`.

**Naming:**
- Use `tests/test_<domain>.py` names across the suite, for example `tests/test_cli_exec.py`, `tests/test_runtime_imports.py`, `tests/test_workspace_locking.py`, `tests/test_qiskit_emitter.py`, and `tests/test_release_docs.py`.
- CLI contract suites cluster under `tests/test_cli_*.py`.
- Runtime and workspace internals cluster under `tests/test_runtime_*.py` and `tests/test_workspace_*.py`.
- Private helpers inside tests use `_` prefixes, such as `_write_intent()`, `_seed_workspace()`, `_parse_jsonl()`, and `_backend_capabilities_fixture()`.

**Structure:**
```text
tests/
├── test_cli_*.py
├── test_runtime_*.py
├── test_workspace_*.py
├── test_qspec_*.py
├── test_*release*.py
└── golden/
```

- Current breadth signal: `338` `def test_...` functions across `tests/test_*.py`.

## Test Structure

**Suite Organization:**
```python
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()

def _write_intent(path: Path, *, title: str, goal: str) -> Path:
    ...

def test_qrun_exec_json_generates_workspace_artifacts_and_report(tmp_path: Path) -> None:
    result = RUNNER.invoke(app, ["exec", "--workspace", str(tmp_path / ".quantum"), ...])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
```

**Patterns:**
- Set up scenarios with file-local helpers plus `tmp_path` instead of shared fixtures. Representative suites: `tests/test_cli_exec.py`, `tests/test_runtime_imports.py`, `tests/test_pack_bundle.py`, and `tests/test_runtime_workspace_safety.py`.
- Use `PROJECT_ROOT = Path(__file__).resolve().parents[1]` to read checked-in examples, docs, or golden files, as seen in `tests/test_cli_exec.py`, `tests/test_qiskit_emitter.py`, `tests/test_packaging_release.py`, and `tests/test_release_docs.py`.
- For CLI tests, assert exit code first, then parse JSON, then assert the contract shape, file existence, path suffixes, and persisted workspace state. This is the dominant style in `tests/test_cli_exec.py`, `tests/test_cli_compare.py`, `tests/test_cli_control_plane.py`, `tests/test_cli_observability.py`, and `tests/test_cli_doctor.py`.
- For direct runtime tests, use `pytest.raises` for failures and inspect stable reason codes or typed exception fields, for example in `tests/test_runtime_imports.py`, `tests/test_runtime_workspace_safety.py`, `tests/test_qspec_validation.py`, and `tests/test_artifact_provenance.py`.
- Teardown is usually implicit. Tests rely on pytest temporary directories and only clean up explicitly when the scenario requires it, such as `shutil.rmtree()` in `tests/test_runtime_imports.py`.
- Parametrization is used sparingly rather than as the default style. Current uses are concentrated in `tests/test_cli_ibm_config.py`, `tests/test_cli_workspace_safety.py`, `tests/test_runtime_revision_artifacts.py`, `tests/test_planner.py`, and `tests/test_workspace_locking.py`.

## Mocking

**Framework:** `pytest` `monkeypatch` plus inline fake functions and fake classes. A repo-wide `unittest.mock` pattern is not detected.

**Patterns:**
```python
def _fake_list_backends(*, workspace_root: Path) -> dict[str, object]:
    return {"backends": {}, "remote": {...}}

monkeypatch.setattr("quantum_runtime.cli.list_backends", _fake_list_backends)
```

```python
monkeypatch.setattr(executor_module, "run_local_simulation", _blocking_run_local_simulation)
monkeypatch.setattr(executor_module, "write_diagrams", _thread_safe_write_diagrams)
monkeypatch.setenv("QISKIT_IBM_TOKEN", "super-secret-token")
monkeypatch.chdir(tmp_path)
```

**What to Mock:**
- Optional or external boundaries, such as backend discovery and IBM readiness helpers in `tests/test_cli_backend_list.py`, `tests/test_cli_ibm_config.py`, and `tests/test_cli_observability.py`.
- Failure points and race windows inside runtime orchestration, such as `run_local_simulation`, `write_diagrams`, and `write_run_manifest` in `tests/test_runtime_workspace_safety.py`.
- Environment variables and current working directory for path and credential resolution in `tests/test_runtime_imports.py`, `tests/test_cli_observability.py`, and `tests/test_cli_ibm_config.py`.

**What NOT to Mock:**
- The workspace filesystem shape under `tmp_path`. Most tests intentionally write a real `.quantum` directory and inspect the resulting files.
- CLI dispatch itself. `tests/test_cli_*.py` generally invoke the real Typer app through `CliRunner()` instead of unit-testing handlers in isolation.
- Golden-file outputs when the point of the test is exact emission fidelity, such as `tests/test_qiskit_emitter.py`, `tests/test_qasm_export.py`, and `tests/test_report_writer.py`.
- Repo documentation and packaging metadata. `tests/test_release_docs.py`, `tests/test_packaging_release.py`, `tests/test_open_source_release.py`, and `tests/test_runtime_adoption_workflow.py` read committed files directly.

## Fixtures and Factories

**Test Data:**
```python
def _write_intent(path: Path, *, title: str, goal: str) -> Path:
    path.write_text(f"---\ntitle: {title}\n---\n\n{goal}\n")
    return path
```

- File-local helper builders are the normal pattern:
- `_write_intent()` appears in `tests/test_cli_exec.py` and `tests/test_runtime_workspace_safety.py`.
- `_seed_workspace()` and `_seed_two_revision_workspace()` live in `tests/test_runtime_imports.py`.
- `_backend_capabilities_fixture()` lives in `tests/test_cli_backend_list.py`.
- `_write_current_pack_shape()` and `_write_bundle_manifest()` live in `tests/test_pack_bundle.py`.
- Many tests derive QSpec payloads from real checked-in examples via `parse_intent_file()` and `plan_to_qspec()`, for example in `tests/test_cli_exec.py`, `tests/test_qiskit_emitter.py`, `tests/test_qspec_semantics.py`, and `tests/test_runtime_imports.py`.
- Snapshot data is stored under `tests/golden/`, including `tests/golden/qiskit_ghz_main.py`, `tests/golden/qasm_ghz_main.qasm`, `tests/golden/qspec_ghz.json`, `tests/golden/qspec_qaoa_maxcut.json`, and `tests/golden/report_summary_ghz.txt`.

**Location:**
- Helper factories stay in the same file as the tests that use them.
- Example intent and runtime input files come from `examples/`.
- Docs and release contract tests read committed files in `README.md`, `CHANGELOG.md`, `ARCHITECTURE.md`, `docs/releases/`, `docs/versioning.md`, and other repo docs.

## Coverage

**Requirements:** None enforced.
- No `pytest-cov`, coverage percentage threshold, or coverage report command is configured in `pyproject.toml`, `.github/workflows/ci.yml`, `README.md`, or `CONTRIBUTING.md`.
- One targeted coverage suppression comment is present in `tests/test_runtime_workspace_safety.py`, but the repository does not publish a formal percentage.
- CI runs a reduced suite in `.github/workflows/ci.yml` and explicitly ignores `tests/test_classiq_backend.py`, `tests/test_classiq_emitter.py`, and `tests/test_qspec_validation.py`.
- Contributor guidance in `CONTRIBUTING.md` is broader than CI and expects `uv run --python 3.11 --extra dev --extra qiskit pytest -q`.

**View Coverage:**
```bash
# Not configured in this repository.
```

## Test Types

**Unit Tests:**
- Pure model and validation checks live in `tests/test_qspec_validation.py`, `tests/test_qspec_semantics.py`, `tests/test_target_validation.py`, `tests/test_artifact_provenance.py`, `tests/test_workspace_locking.py`, and `tests/test_workspace_manager.py`.
- Lowering and artifact emission tests live in `tests/test_qiskit_emitter.py`, `tests/test_qasm_export.py`, `tests/test_report_writer.py`, and `tests/test_diagnostics.py`.

**Integration Tests:**
- The dominant suite style is CLI-plus-workspace integration through `CliRunner` and a real temporary `.quantum` directory. Representative files: `tests/test_cli_exec.py`, `tests/test_cli_compare.py`, `tests/test_cli_control_plane.py`, `tests/test_cli_inspect.py`, `tests/test_cli_doctor.py`, `tests/test_cli_observability.py`, and `tests/test_cli_backend_list.py`.
- Runtime filesystem and revision workflows are tested directly in `tests/test_runtime_imports.py`, `tests/test_runtime_compare.py`, `tests/test_runtime_workspace_safety.py`, `tests/test_runtime_revision_artifacts.py`, and `tests/test_pack_bundle.py`.
- Repo contract tests treat documentation and packaging as part of the runtime surface in `tests/test_release_docs.py`, `tests/test_packaging_release.py`, `tests/test_open_source_release.py`, and `tests/test_runtime_adoption_workflow.py`.

**E2E Tests:**
- Browser or remote-service E2E tests are not used.
- The closest local end-to-end checks are real CLI runs through `CliRunner()` and executing generated Python via `subprocess.run()` in `tests/test_qiskit_emitter.py`.
- Optional backend surfaces exist, but IBM and Classiq behaviors are largely validated through local fakes, environment patching, or dedicated optional suites rather than through live external systems.

## Common Patterns

**Async Testing:**
```python
first_thread = threading.Thread(target=_run_exec, args=(workspace, ghz_intent, first_outcome))
second_thread = threading.Thread(target=_run_exec, args=(workspace, bell_intent, second_outcome))
```

- Native async tests are not used. No `pytest-asyncio` or `async def test_...` patterns are detected.
- Concurrency coverage is thread-based instead, primarily in `tests/test_runtime_workspace_safety.py`.

**Error Testing:**
```python
with pytest.raises(ImportSourceError) as excinfo:
    resolve_report_file(tmp_path / "missing-report.json")
assert excinfo.value.code == "report_file_missing"
```

- Direct runtime tests assert stable exception codes or typed fields, as in `tests/test_runtime_imports.py`, `tests/test_qspec_validation.py`, and `tests/test_artifact_provenance.py`.
- CLI failure tests assert structured exit codes and parse the emitted JSON payload, then verify `reason`, `error_code`, `details`, and remediation semantics. This pattern is widespread in `tests/test_cli_control_plane.py`, `tests/test_cli_workspace_safety.py`, `tests/test_cli_compare.py`, `tests/test_cli_export.py`, `tests/test_cli_doctor.py`, and `tests/test_cli_baseline.py`.

---

*Testing analysis: 2026-04-18*
