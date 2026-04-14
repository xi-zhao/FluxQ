# Coding Conventions

**Analysis Date:** 2026-04-14

## Naming Patterns

**Files:**
- Use `snake_case.py` for implementation modules under `src/quantum_runtime/`, for example `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/runtime/compare.py`, `src/quantum_runtime/intent/parser.py`, and `src/quantum_runtime/workspace/manager.py`.
- Use `tests/test_<area>.py` for canonical tests in the top-level `tests/` directory, for example `tests/test_cli_exec.py`, `tests/test_runtime_imports.py`, `tests/test_workspace_manager.py`, and `tests/test_release_docs.py`.
- Keep snapshot fixtures under `tests/golden/`, for example `tests/golden/qspec_ghz.json`, `tests/golden/qasm_ghz_main.qasm`, and `tests/golden/report_summary_ghz.txt`.
- Use package `__init__.py` files as barrel modules with explicit `__all__` lists, for example `src/quantum_runtime/runtime/__init__.py`, `src/quantum_runtime/qspec/__init__.py`, `src/quantum_runtime/workspace/__init__.py`, and `src/quantum_runtime/reporters/__init__.py`.
- Treat `src/quantum_runtime/reporters/writer-NSConflict-BlovedSwami-mac26.4.1.py`, `tests/test_cli_bench-NSConflict-BlovedSwami-mac26.4.1.py`, and `tests/test_runtime_imports-NSConflict-BlovedSwami-mac26.4.1.py` as conflict artifacts, not as naming patterns to extend.

**Functions:**
- Use `snake_case` for public functions and module-local helpers, for example `parse_intent_text()` in `src/quantum_runtime/intent/parser.py`, `execute_intent()` in `src/quantum_runtime/runtime/executor.py`, and `workspace_status()` in `src/quantum_runtime/runtime/control_plane.py`.
- Prefix file-local helpers with `_`, for example `_json_error()` and `_make_jsonl_emitter()` in `src/quantum_runtime/cli.py`, `_coerce_details()` in `src/quantum_runtime/errors.py`, and `_write_intent()` in `tests/test_cli_exec.py`.
- Name CLI command handlers with a `_command` suffix in `src/quantum_runtime/cli.py`, for example `init_command()`, `baseline_set_command()`, `pack_inspect_command()`, and `backend_list_command()`.

**Variables:**
- Use `snake_case` for locals and parameters, for example `workspace_root`, `event_sink`, `requested_exports`, `latest_manifest`, and `representative_bindings` across `src/quantum_runtime/runtime/` and `tests/`.
- Use `UPPER_SNAKE_CASE` for constants and reusable test module state, for example `SCHEMA_VERSION` in `src/quantum_runtime/runtime/contracts.py`, `DEFAULT_QRUN_TOML` in `src/quantum_runtime/workspace/manager.py`, `PROJECT_ROOT` in many test modules, and `RUNNER` in CLI test modules such as `tests/test_cli_exec.py`.

**Types:**
- Use `PascalCase` for Pydantic models, dataclasses, and structured error types, for example `ExecResult` in `src/quantum_runtime/runtime/executor.py`, `CompareResult` in `src/quantum_runtime/runtime/compare.py`, `WorkspaceHandle` in `src/quantum_runtime/workspace/manager.py`, and `WorkspaceConflictError` in `src/quantum_runtime/errors.py`.
- Use descriptive suffixes such as `Result`, `Report`, `Manifest`, `Resolution`, `Details`, `Policy`, and `Verdict`, for example `BenchmarkReport`, `WorkspaceManifest`, `ImportResolution`, `WorkspaceConflictDetails`, `ComparePolicy`, and `CompareVerdict`.

## Code Style

**Formatting:**
- Start modules with a module docstring and `from __future__ import annotations`, as shown in `src/quantum_runtime/cli.py`, `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/workspace/trace.py`, `tests/test_cli_exec.py`, and `tests/test_release_docs.py`.
- Group imports by standard library, third-party packages, and first-party packages with a blank line between groups. This is visible in `src/quantum_runtime/cli.py`, `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/intent/parser.py`, and `tests/test_classiq_backend.py`.
- Use manual Black-like wrapping: hanging indents, trailing commas in multiline literals and calls, and blank lines between top-level declarations. Representative files include `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/runtime/contracts.py`, and `tests/test_runtime_workspace_safety.py`.
- Serialize machine-facing JSON explicitly with `model_dump_json(indent=2)` or `json.dumps(..., indent=2, ensure_ascii=True)`, for example in `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/runtime/compare.py`, `src/quantum_runtime/reporters/writer.py`, `src/quantum_runtime/workspace/trace.py`, and many tests that seed or tamper workspace files.
- Keep type annotations on public functions and most tests. Examples include `parse_intent_file(path: Path) -> IntentModel` in `src/quantum_runtime/intent/parser.py`, `execute_intent(*, workspace_root: Path, intent_file: Path, ...) -> ExecResult` in `src/quantum_runtime/runtime/executor.py`, and `test_qrun_exec_json_generates_workspace_artifacts_and_report(tmp_path: Path) -> None` in `tests/test_cli_exec.py`.
- Prefer `Path` objects over raw path strings until the serialization boundary, for example in `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/workspace/manager.py`, `src/quantum_runtime/runtime/imports.py`, and `tests/test_cli_init.py`.

**Linting:**
- Lint with Ruff through `[tool.ruff]` in `pyproject.toml`, repository commands in `CONTRIBUTING.md`, and `.github/workflows/ci.yml`.
- Ruff scopes `src` and `tests` through `src = ["src", "tests"]` in `pyproject.toml`.
- Ruff excludes `tests/golden` and `tests/test_qspec_validation.py` through `extend-exclude = ["tests/golden", "tests/test_qspec_validation.py"]` in `pyproject.toml`.
- Ruff enforces only `E4`, `E7`, `E9`, and `F`. Import sorting, quote normalization, docstring style, and formatting are not tool-enforced.
- MyPy runs only on `src` through `files = src` in `mypy.ini` and through `mypy src` in `.github/workflows/ci.yml`, `CONTRIBUTING.md`, and `scripts/dev-bootstrap.sh`.
- MyPy is permissive around third-party packages and selected modules: `ignore_missing_imports = true`, plus module-specific exceptions for `quantum_runtime.intent.planner`, `quantum_runtime.runtime.executor`, and `quantum_runtime.diagnostics.transpile_validate` in `mypy.ini`.

## Import Organization

**Order:**
1. Standard library imports such as `json`, `hashlib`, `subprocess`, `threading`, `Path`, and `Any`.
2. Third-party imports such as `typer`, `pytest`, and `pydantic`.
3. First-party imports from `quantum_runtime...` or package-relative imports.

**Path Aliases:**
- Not detected. Imports use either absolute package paths such as `from quantum_runtime.runtime import ...` in `src/quantum_runtime/cli.py` and `tests/test_runtime_compare.py`, or relative imports such as `from .trace import TraceWriter` in `src/quantum_runtime/workspace/manager.py` and `from .model import QSpec` in `src/quantum_runtime/qspec/__init__.py`.

**Patterns:**
- Use absolute imports across package boundaries and in tests. Examples include `tests/test_cli_exec.py`, `tests/test_qasm_export.py`, and `src/quantum_runtime/cli.py`.
- Use relative imports inside a package when the module stays within one subsystem, for example `src/quantum_runtime/workspace/manager.py`, `src/quantum_runtime/intent/parser.py`, `src/quantum_runtime/qspec/validation.py`, and the package barrel modules.
- Favor barrel imports for broad orchestration surfaces. `src/quantum_runtime/cli.py` imports many runtime entrypoints from `src/quantum_runtime/runtime/__init__.py`, and `tests/test_runtime_compare.py` imports the public runtime API from the same barrel.
- Import leaf modules directly when testing one implementation detail, for example `tests/test_classiq_backend.py`, `tests/test_workspace_manager.py`, `tests/test_qasm_export.py`, and `tests/test_cli_backend_list.py`.

```python
from pathlib import Path

import typer

from quantum_runtime import __version__
from quantum_runtime.runtime import build_execution_plan, execute_intent
from quantum_runtime.workspace import WorkspaceManager
```

```python
from .locking import acquire_workspace_lock
from .manifest import WorkspaceManifest, atomic_write_text
from .paths import WorkspacePaths
```

## Error Handling

**Patterns:**
- Raise domain-specific exceptions that carry stable machine-readable codes and structured details. The base pattern is `StructuredQuantumRuntimeError` in `src/quantum_runtime/errors.py`, with concrete types such as `ManualQspecRequiredError`, `WorkspaceConflictError`, and `WorkspaceRecoveryRequiredError`.
- Use boundary-specific exceptions when a simple reason code is enough, for example `ImportSourceError` in `src/quantum_runtime/runtime/imports.py`, `ReportImportError` in `src/quantum_runtime/runtime/executor.py`, `ArtifactProvenanceMismatch` in `src/quantum_runtime/artifact_provenance.py`, and `RunManifestIntegrityError` in `src/quantum_runtime/runtime/run_manifest.py`.
- Convert failures into schema-versioned payloads at the CLI boundary through `_emit_json_payload()`, `_json_error()`, and `_handle_workspace_safety_error()` in `src/quantum_runtime/cli.py`.
- Keep remediations stable and explicit through `REMEDIATIONS`, `ensure_schema_payload()`, and `dump_schema_payload()` in `src/quantum_runtime/runtime/contracts.py`.
- Fail closed on provenance and integrity mismatches rather than silently discarding metadata. The explanatory inline comment in `src/quantum_runtime/runtime/export.py` and the guarded flows in `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/run_manifest.py`, and `src/quantum_runtime/runtime/inspect.py` follow this rule.
- Use `assert` only for invariants that should already hold after prior validation or branching, for example `assert resolution is not None` in `src/quantum_runtime/cli.py`, `assert manifest is not None` in `src/quantum_runtime/runtime/doctor.py`, and loader assertions in `tests/test_pack_bundle.py`.

```python
class StructuredQuantumRuntimeError(QuantumRuntimeError):
    code: str = "runtime_error"

    def __init__(self, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = _coerce_details(details or {})
```

## Logging

**Framework:** No `logging` module usage is present in `src/` or `tests/`.

**Patterns:**
- Human-facing CLI output uses `typer.echo(...)` in `src/quantum_runtime/cli.py`.
- Machine-facing command payloads use `dump_schema_payload()` and `ensure_schema_payload()` from `src/quantum_runtime/runtime/contracts.py`.
- Streaming command telemetry uses `JsonlEvent` in `src/quantum_runtime/runtime/observability.py` and `_make_jsonl_emitter()` in `src/quantum_runtime/cli.py`.
- Workspace event persistence uses `TraceWriter.append()` plus `append_trace_log()` and `write_trace_snapshot()` in `src/quantum_runtime/workspace/trace.py`.
- New runtime behavior should emit structured JSON payloads or NDJSON events instead of ad hoc print statements.

## Comments

**When to Comment:**
- Prefer module, class, and public function docstrings over inline comments. Examples appear throughout `src/quantum_runtime/cli.py`, `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/workspace/trace.py`, and `src/quantum_runtime/intent/parser.py`.
- Use inline comments sparingly for non-obvious constraints or fail-closed behavior. The notable example is the explanatory three-line comment in `src/quantum_runtime/runtime/export.py`.
- Tests rely more on descriptive helper names and explicit assertions than inline commentary. `tests/test_intent_parser.py` is the exception because its markdown fixture uses heading comments like `# Goal` and `# Notes` inside the sample input.

**JSDoc/TSDoc:**
- Not applicable. This repository uses Python docstrings rather than JS/TS comment conventions.

## Function Design

**Size:**
- Core orchestration modules are large: `src/quantum_runtime/cli.py` has 1667 lines, `src/quantum_runtime/runtime/imports.py` has 1191, `src/quantum_runtime/runtime/compare.py` has 904, `src/quantum_runtime/runtime/control_plane.py` has 739, and `src/quantum_runtime/runtime/executor.py` has 640.
- Supporting modules stay smaller and more focused, for example `src/quantum_runtime/workspace/manager.py`, `src/quantum_runtime/errors.py`, `src/quantum_runtime/intent/parser.py`, and `src/quantum_runtime/reporters/__init__.py`.
- Add new leaf helpers or subsystem modules before growing `src/quantum_runtime/cli.py` or `src/quantum_runtime/runtime/imports.py` further.

**Parameters:**
- Use keyword-only parameters for orchestration-heavy APIs, for example `execute_intent(*, workspace_root: Path, intent_file: Path, ...)`, `workspace_conflict_error_payload(*, ...)`, `_make_jsonl_emitter(*, workspace: Path)`, `append_trace_log(*, source_path: Path, destination_path: Path)`, and `run_doctor(*, workspace_root: Path, ...)`.
- Use structured inputs instead of long positional argument lists when data is cohesive, for example `ImportReference`, `ImportResolution`, `ComparePolicy`, and `WorkspaceHandle`.

**Return Values:**
- Return Pydantic models or structured dictionaries for machine-facing flows. Examples include `ExecResult`, `CompareResult`, `DoctorReport`, `ExportResult`, `InspectReport`, and schema payload dicts from `src/quantum_runtime/runtime/contracts.py`.
- CLI command handlers return `None` and communicate through `typer.echo(...)` plus `typer.Exit(...)` in `src/quantum_runtime/cli.py`.
- Use `Field(default_factory=...)` consistently for mutable defaults in Pydantic models, for example in `src/quantum_runtime/qspec/model.py`, `src/quantum_runtime/runtime/compare.py`, `src/quantum_runtime/runtime/contracts.py`, and `src/quantum_runtime/runtime/run_manifest.py`.

```python
def execute_intent(*, workspace_root: Path, intent_file: Path, event_sink: EventSink | None = None) -> ExecResult:
    resolved = resolve_runtime_input(workspace_root=workspace_root, intent_file=intent_file)
    ...
```

## Module Design

**Exports:**
- Publish stable public surfaces through barrel modules with explicit `__all__`, especially `src/quantum_runtime/runtime/__init__.py`, `src/quantum_runtime/qspec/__init__.py`, `src/quantum_runtime/workspace/__init__.py`, `src/quantum_runtime/lowering/__init__.py`, and `src/quantum_runtime/reporters/__init__.py`.
- Keep the CLI boundary dependent on barrel modules rather than on deep leaf imports. `src/quantum_runtime/cli.py` is the clearest example.

**Barrel Files:**
- Use barrel imports when a caller needs the stable cross-module contract. Examples: `src/quantum_runtime/cli.py`, `tests/test_runtime_compare.py`, and `tests/test_runtime_policy.py`.
- Use leaf-module imports when the test or module is validating a specific subsystem detail, for example `tests/test_workspace_manager.py`, `tests/test_qasm_export.py`, `tests/test_classiq_backend.py`, `tests/test_cli_backend_list.py`, and `src/quantum_runtime/reporters/writer.py`.

---

*Convention analysis: 2026-04-14*
