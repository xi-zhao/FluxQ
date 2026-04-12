# Coding Conventions

**Analysis Date:** 2026-04-12

## Naming Patterns

**Files:**
- Use `snake_case.py` for implementation modules under `src/quantum_runtime/`, for example `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/qspec/model.py`, and `src/quantum_runtime/workspace/manager.py`.
- Use package `__init__.py` files as barrels that re-export stable APIs, for example `src/quantum_runtime/runtime/__init__.py`, `src/quantum_runtime/qspec/__init__.py`, and `src/quantum_runtime/workspace/__init__.py`.
- Use `tests/test_<area>.py` for tests, for example `tests/test_cli_exec.py`, `tests/test_workspace_manager.py`, and `tests/test_release_docs.py`.
- Keep golden snapshots under `tests/golden/`, for example `tests/golden/qiskit_ghz_main.py`, `tests/golden/qspec_ghz.json`, and `tests/golden/report_summary_ghz.txt`.

**Functions:**
- Use `snake_case` for public functions, for example `parse_intent_text()` in `src/quantum_runtime/intent/parser.py`, `resolve_import_reference()` in `src/quantum_runtime/runtime/imports.py`, and `run_doctor()` in `src/quantum_runtime/runtime/doctor.py`.
- Prefix file-local helpers with `_`, for example `_json_error()` and `_resolve_runtime_input()` in `src/quantum_runtime/cli.py`, `_make_qspec()` in `tests/test_qspec_validation.py`, and `_seed_workspace()` in `tests/test_runtime_imports.py`.
- Name CLI command handlers with a `_command` suffix inside `src/quantum_runtime/cli.py`, for example `init_command()` and `version_command()`.

**Variables:**
- Use `snake_case` for locals and parameters, for example `workspace_root`, `report_payload`, and `required_backends` in `src/quantum_runtime/runtime/imports.py` and `src/quantum_runtime/runtime/doctor.py`.
- Use `UPPER_SNAKE_CASE` for module constants, for example `SCHEMA_VERSION` in `src/quantum_runtime/workspace/trace.py`, `DEFAULT_QRUN_TOML` in `src/quantum_runtime/workspace/manager.py`, and `PROJECT_ROOT` plus `RUNNER` in `tests/test_cli_exec.py`.

**Types:**
- Use `PascalCase` for Pydantic models, dataclasses, and exceptions, for example `QSpec` in `src/quantum_runtime/qspec/model.py`, `ExecResult` in `src/quantum_runtime/runtime/executor.py`, `WorkspaceHandle` in `src/quantum_runtime/workspace/manager.py`, and `ImportSourceError` in `src/quantum_runtime/runtime/imports.py`.
- Suffix structured payload models with domain-specific nouns such as `Result`, `Report`, `Manifest`, `Paths`, or `Resolution`, for example `DoctorReport`, `CompareResult`, `WorkspaceManifest`, `WorkspacePaths`, and `ImportResolution`.

## Code Style

**Formatting:**
- Start nearly every Python file with `from __future__ import annotations`, including `src/quantum_runtime/cli.py`, `src/quantum_runtime/runtime/backend_registry.py`, `tests/test_cli_exec.py`, and `tests/test_release_docs.py`.
- Keep modules docstring-first. Module, class, and public function docstrings are standard in `src/quantum_runtime/cli.py`, `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/runtime/imports.py`, and `src/quantum_runtime/workspace/trace.py`.
- Follow Black-like formatting manually: trailing commas in multi-line literals and calls, hanging indents, and blank lines between top-level declarations. This style is visible in `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/runtime/doctor.py`, and `tests/test_cli_control_plane.py`.
- Prefer explicit JSON serialization over ad hoc string building, using `model_dump_json(indent=2)` or `json.dumps(..., indent=2)`, as shown in `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/reporters/writer.py`, and many tests such as `tests/test_cli_exec.py` and `tests/test_pack_bundle.py`.
- No dedicated formatter config is detected in `pyproject.toml`. There is no `[tool.black]`, `ruff format`, or import-sorting configuration.

**Linting:**
- Run Ruff against `src` and `tests` from `pyproject.toml`, `CONTRIBUTING.md`, and `.github/workflows/ci.yml`.
- Current Ruff selection in `pyproject.toml` is intentionally narrow: `E4`, `E7`, `E9`, and `F`.
- Do not rely on Ruff to enforce import sorting, quote style, or docstring rules. The repository style is maintained by convention rather than by a strict formatter.
- Run MyPy only on `src` according to `mypy.ini`, with `ignore_missing_imports = true` plus targeted module overrides for packages such as `quantum_runtime.intent.planner` and `quantum_runtime.runtime.executor`.

## Import Organization

**Order:**
1. `from __future__ import annotations`
2. Standard library imports such as `json`, `subprocess`, `Path`, `Literal`, or `Any`
3. Third-party imports such as `typer`, `pytest`, `pydantic`, `numpy`, or `qiskit`
4. First-party imports using absolute `quantum_runtime...` paths or relative package imports

**Observed pattern:**
```python
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.cli import app
```

This pattern appears in `tests/test_cli_control_plane.py`. Relative imports are used within tightly scoped packages, for example `src/quantum_runtime/workspace/manager.py` and `src/quantum_runtime/qspec/__init__.py`.

**Path Aliases:**
- No alias system is configured. Imports use absolute package paths such as `from quantum_runtime.runtime import ...` in `src/quantum_runtime/cli.py` or relative imports such as `from .manifest import WorkspaceManifest` in `src/quantum_runtime/workspace/manager.py`.

## Error Handling

**Patterns:**
- Prefer domain-specific exceptions carrying stable error codes over raw exceptions. Examples:
  - `StructuredQuantumRuntimeError` with `.code` in `src/quantum_runtime/errors.py`
  - `ImportSourceError` with `code`, `source`, and `details` in `src/quantum_runtime/runtime/imports.py`
  - `ReportImportError` with `reason` in `src/quantum_runtime/runtime/executor.py`
- Translate low-level failures into machine-readable reasons close to the boundary. `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/control_plane.py`, and `src/quantum_runtime/runtime/executor.py` all catch broad parsing or filesystem failures and re-raise typed errors with stable codes.
- Keep CLI failure output schema-driven. `_json_error()` in `src/quantum_runtime/cli.py` emits an `ErrorPayload` through `dump_schema_payload()` and exits with `typer.Exit(code=3)`.
- Use `assert` only for internal invariants that should already hold, for example the `assert resolution is not None` check in `src/quantum_runtime/cli.py`, `assert manifest is not None` in `src/quantum_runtime/runtime/doctor.py`, and importlib loader assertions in `tests/test_qiskit_emitter.py`.

## Logging

**Framework:** `typer.echo` plus structured NDJSON event logging. Standard library `logging` is not used in `src/quantum_runtime/`.

**Patterns:**
- CLI text and JSON output goes through `typer.echo` in `src/quantum_runtime/cli.py`.
- Runtime event logging is implemented with `TraceWriter` and `TraceEvent` in `src/quantum_runtime/workspace/trace.py`, which append JSON lines to workspace files such as `trace/events.ndjson` and `events.jsonl`.
- Machine-facing payloads are usually serialized with Pydantic or `json.dumps(..., ensure_ascii=True)`, for example `src/quantum_runtime/runtime/compare.py`, `src/quantum_runtime/runtime/executor.py`, and `src/quantum_runtime/qspec/semantics.py`.

## Comments

**When to Comment:**
- Prefer docstrings over inline comments. Public-facing modules and models are documented with concise docstrings in `src/quantum_runtime/cli.py`, `src/quantum_runtime/qspec/model.py`, `src/quantum_runtime/runtime/imports.py`, and `src/quantum_runtime/workspace/trace.py`.
- Inline comments are rare. The codebase relies more on descriptive names and structured result models than on comment-heavy logic.

**JSDoc/TSDoc:**
- Not applicable. This is a Python codebase.
- Use Python docstrings instead of block comments for API explanation.

## Function Design

**Size:** Public entrypoints are often thin wrappers over private helpers, but some orchestration modules are intentionally large:
- `src/quantum_runtime/cli.py` is the main command surface and is 1409 lines.
- `src/quantum_runtime/runtime/executor.py` centralizes execution flow and is 540 lines.
- Smaller supporting modules such as `src/quantum_runtime/workspace/manager.py` and `src/quantum_runtime/errors.py` stay compact.

**Parameters:**
- Type-annotate public functions consistently, including tests. Examples include `parse_intent_file(path: Path) -> IntentModel` in `src/quantum_runtime/intent/parser.py` and `test_qrun_exec_json_generates_workspace_artifacts_and_report(tmp_path: Path) -> None` in `tests/test_cli_exec.py`.
- Prefer keyword-only parameters for orchestration functions with many inputs, for example `execute_intent(*, workspace_root: Path, intent_file: Path, ...)` in `src/quantum_runtime/runtime/executor.py` and `run_doctor(*, workspace_root: Path, fix: bool = False, ...)` in `src/quantum_runtime/runtime/doctor.py`.
- Use Pydantic `BaseModel` containers when a function returns or passes around structured runtime state, for example `ExecResult`, `DoctorReport`, `ImportResolution`, and `WorkspaceManifest`.

**Return Values:**
- Return structured models for machine-facing flows, for example `ExecResult` from `src/quantum_runtime/runtime/executor.py`, `DoctorReport` from `src/quantum_runtime/runtime/doctor.py`, and `ImportResolution` from `src/quantum_runtime/runtime/imports.py`.
- CLI commands return `None` and emit output via `typer.echo` in `src/quantum_runtime/cli.py`.
- Tests typically assert full JSON payload shape rather than a single field, as shown in `tests/test_cli_control_plane.py`, `tests/test_cli_exec.py`, and `tests/test_cli_observability.py`.

## Module Design

**Exports:** Use package-level barrel files with explicit `__all__` declarations.
- `src/quantum_runtime/runtime/__init__.py` re-exports the runtime surface.
- `src/quantum_runtime/workspace/__init__.py` re-exports workspace helpers.
- `src/quantum_runtime/qspec/__init__.py` re-exports models plus validation helpers.
- `src/quantum_runtime/reporters/__init__.py` re-exports `summarize_report` and `write_report`.

**Barrel Files:** Common and intentional.
- Use the barrel when importing across package boundaries, for example `from quantum_runtime.runtime import ...` in `src/quantum_runtime/cli.py`.
- Import directly from leaf modules when a test is focused on one implementation detail, for example `from quantum_runtime.runtime.executor import ExecResult` in `tests/test_cli_exec.py` and `from quantum_runtime.backends.classiq_backend import run_classiq_backend` in `tests/test_classiq_backend.py`.

---

*Convention analysis: 2026-04-12*
