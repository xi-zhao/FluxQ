# Coding Conventions

**Analysis Date:** 2026-04-18

## Naming Patterns

**Files:**
- Use `snake_case.py` module names under `src/quantum_runtime/`, for example `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/run_manifest.py`, `src/quantum_runtime/qspec/validation.py`, and `src/quantum_runtime/workspace/manager.py`.
- Use package `__init__.py` files as stable barrels, especially `src/quantum_runtime/runtime/__init__.py`, `src/quantum_runtime/qspec/__init__.py`, `src/quantum_runtime/workspace/__init__.py`, and `src/quantum_runtime/reporters/__init__.py`.
- Name tests `tests/test_<area>.py`, for example `tests/test_cli_exec.py`, `tests/test_runtime_imports.py`, `tests/test_workspace_manager.py`, and `tests/test_packaging_release.py`.
- Keep checked-in snapshots and golden artifacts in `tests/golden/`, for example `tests/golden/qiskit_ghz_main.py`, `tests/golden/qspec_ghz.json`, and `tests/golden/report_summary_ghz.txt`.

**Functions:**
- Use `snake_case` for public functions across runtime and tests, for example `execute_intent()` in `src/quantum_runtime/runtime/executor.py`, `resolve_report_file()` in `src/quantum_runtime/runtime/imports.py`, `remediation_for_error()` in `src/quantum_runtime/runtime/contracts.py`, and `test_qrun_exec_json_generates_workspace_artifacts_and_report()` in `tests/test_cli_exec.py`.
- Prefix file-local helpers with `_`, for example `_json_error()` and `_handle_workspace_safety_error()` in `src/quantum_runtime/cli.py`, `_seed_bootstrap_file()` in `src/quantum_runtime/workspace/manager.py`, `_backend_capabilities_fixture()` in `tests/test_cli_backend_list.py`, and `_write_current_pack_shape()` in `tests/test_pack_bundle.py`.
- Name Typer command handlers with a `_command` suffix inside `src/quantum_runtime/cli.py`, including `init_command()`, `exec_command()`, `compare_command()`, `doctor_command()`, and `backend_list_command()`.
- Prefer verb-oriented helper prefixes that describe the runtime action: `resolve_*`, `load_*`, `write_*`, `build_*`, `compare_*`, `execute_*`, `persist_*`, and `validate_*`.

**Variables:**
- Use `snake_case` for locals and parameters, with descriptive suffixes like `*_path`, `*_payload`, `*_result`, `*_resolution`, and `*_root`; examples include `workspace_root`, `report_path`, `baseline_resolution`, `event_sink`, and `artifact_names` in `src/quantum_runtime/runtime/` and `tests/`.
- Use `UPPER_SNAKE_CASE` for module constants and test globals, for example `SCHEMA_VERSION` in `src/quantum_runtime/runtime/contracts.py` and `src/quantum_runtime/workspace/trace.py`, `DEFAULT_QRUN_TOML` in `src/quantum_runtime/workspace/manager.py`, and `PROJECT_ROOT` plus `RUNNER` in many CLI tests such as `tests/test_cli_exec.py`.
- Keep workspace and revision identifiers explicit as `workspace`, `workspace_root`, `revision`, and `current_revision` rather than abbreviated aliases.

**Types:**
- Use `PascalCase` for Pydantic models, dataclasses, and exceptions, for example `ExecResult` in `src/quantum_runtime/runtime/executor.py`, `ImportResolution` in `src/quantum_runtime/runtime/imports.py`, `BackendCapabilityDescriptor` in `src/quantum_runtime/runtime/backend_registry.py`, `WorkspaceHandle` in `src/quantum_runtime/workspace/manager.py`, and `WorkspaceRecoveryRequiredError` in `src/quantum_runtime/errors.py`.
- Suffix machine-facing models with domain nouns such as `Result`, `Report`, `Payload`, `Manifest`, `Resolution`, or `Descriptor`, as seen in `ErrorPayload`, `WorkspaceConflictErrorPayload`, `PackInspectionResult`, `DoctorReport`, and `WorkspaceBaselineResolution`.
- Use `Literal[...]` for constrained domain values in models, such as `status` fields in `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/runtime/contracts.py`, and `src/quantum_runtime/workspace/trace.py`.

## Code Style

**Formatting:**
- Start source and test files with `from __future__ import annotations`; this is consistent in `src/quantum_runtime/cli.py`, `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/qspec/model.py`, `tests/test_cli_exec.py`, and `tests/test_runtime_imports.py`.
- Keep modules docstring-first in `src/`. Representative examples include `src/quantum_runtime/cli.py`, `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/workspace/trace.py`, and `src/quantum_runtime/runtime/backend_registry.py`.
- Follow Black-like manual formatting even though no formatter is configured in `pyproject.toml`: 4-space indentation, hanging indents, trailing commas in multiline calls, and blank lines between top-level declarations. This is visible in `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/runtime/contracts.py`, and `tests/test_cli_observability.py`.
- Prefer deterministic JSON serialization via `model_dump_json(indent=2)` or `json.dumps(..., indent=2, ensure_ascii=True)` over ad hoc string assembly. See `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/runtime/run_manifest.py`, `src/quantum_runtime/runtime/compare.py`, `src/quantum_runtime/reporters/writer.py`, and tests such as `tests/test_cli_exec.py` and `tests/test_runtime_imports.py`.
- Use `pathlib.Path` for filesystem work instead of raw string paths, for example throughout `src/quantum_runtime/runtime/pack.py`, `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/workspace/manager.py`, and nearly every test file under `tests/`.
- Keep public functions and many tests fully type-annotated. Examples include `execute_intent(*, workspace_root: Path, intent_file: Path, ...) -> ExecResult` in `src/quantum_runtime/runtime/executor.py`, `workspace_recovery_required_error_payload(...) -> WorkspaceRecoveryRequiredErrorPayload` in `src/quantum_runtime/runtime/contracts.py`, and test signatures like `test_resolve_workspace_current_returns_structured_provenance(tmp_path: Path) -> None` in `tests/test_runtime_imports.py`.

**Linting:**
- Ruff is the only configured linter in `pyproject.toml`.
- The active Ruff rule set is intentionally narrow: `E4`, `E7`, `E9`, and `F` under `[tool.ruff.lint]`.
- Ruff runs against both `src` and `tests`, but `pyproject.toml` excludes `tests/golden/` and `tests/test_qspec_validation.py`.
- There is no configured import sorter, formatter, quote-style rule, or docstring linter. Import order and formatting are maintained by convention, not by automated enforcement.
- MyPy is configured separately in `mypy.ini` and only checks `src`. It uses `ignore_missing_imports = true` and carries targeted relaxations for `quantum_runtime.intent.planner`, `quantum_runtime.runtime.executor`, `quantum_runtime.reporters.summary`, and `quantum_runtime.diagnostics.transpile_validate`.

## Import Organization

**Order:**
1. Standard library imports first, such as `json`, `hashlib`, `pathlib.Path`, `typing`, `threading`, and `tomllib`.
2. Third-party imports second, such as `typer`, `pydantic`, `pytest`, `numpy`, and `qiskit`.
3. Internal `quantum_runtime...` imports last, or relative imports inside a package such as `from .manifest import WorkspaceManifest` in `src/quantum_runtime/workspace/manager.py`.

**Path Aliases:**
- Not detected. Imports are either absolute package imports like `from quantum_runtime.runtime import ...` in `src/quantum_runtime/cli.py` or relative imports within a subpackage like `from .trace import TraceWriter` in `src/quantum_runtime/workspace/manager.py`.
- Prefer importing through package barrels when crossing subsystem boundaries. `src/quantum_runtime/cli.py` imports most runtime and workspace APIs from `quantum_runtime.runtime` and `quantum_runtime.workspace` instead of leaf modules.
- Import leaf modules directly when the caller needs one concrete implementation or when tests target internals, for example `tests/test_qiskit_emitter.py`, `tests/test_runtime_imports.py`, and `tests/test_cli_backend_list.py`.

## Error Handling

**Patterns:**
- Prefer domain-specific exceptions that carry stable reason codes or structured details. Primary examples are `StructuredQuantumRuntimeError`, `WorkspaceConflictError`, and `WorkspaceRecoveryRequiredError` in `src/quantum_runtime/errors.py`, `QSpecValidationError` in `src/quantum_runtime/qspec/validation.py`, and `ImportSourceError` in `src/quantum_runtime/runtime/imports.py`.
- Preserve a machine-readable `details` payload on structured failures. `src/quantum_runtime/errors.py` normalizes `Path` and mapping values through `_coerce_details()` before exposing them.
- Re-raise low-level parsing, validation, and filesystem failures as runtime-domain errors close to the boundary. This is the dominant pattern in `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/export.py`, `src/quantum_runtime/runtime/pack.py`, `src/quantum_runtime/runtime/executor.py`, and `src/quantum_runtime/runtime/ibm_access.py`.
- Translate exceptions into schema-versioned JSON payloads in the CLI layer instead of leaking raw exceptions. `src/quantum_runtime/cli.py` routes failures through `_json_error()`, `_json_import_source_error()`, `_workspace_safety_payload()`, and `_emit_json_payload()`, all backed by models in `src/quantum_runtime/runtime/contracts.py`.
- Use remediation text consistently through `remediation_for_error()` in `src/quantum_runtime/runtime/contracts.py` rather than embedding ad hoc user guidance in each command.
- Use plain `ValueError` or narrow custom runtime exceptions only where a full structured hierarchy is unnecessary inside the runtime, such as `ReportImportError` in `src/quantum_runtime/runtime/executor.py`, `RunManifestIntegrityError` in `src/quantum_runtime/runtime/run_manifest.py`, and `ArtifactProvenanceMismatch` in `src/quantum_runtime/artifact_provenance.py`.
- Use `assert` only for internal invariants after branching or loader setup, not for user-facing validation. Representative cases are `assert resolution is not None` in `src/quantum_runtime/cli.py`, `assert manifest is not None` in `src/quantum_runtime/runtime/doctor.py`, and loader assertions in `tests/test_qiskit_emitter.py`.

## Logging

**Framework:** `typer.echo` for CLI output plus JSONL/NDJSON trace writers in the workspace layer. The standard `logging` module is not used in `src/quantum_runtime/`.

**Patterns:**
- Emit human and machine CLI output through `typer.echo` in `src/quantum_runtime/cli.py`; JSON is always routed through `dump_schema_payload()` or `event.model_dump_json()`.
- Persist runtime events with `TraceWriter`, `append_trace_log()`, and `write_trace_snapshot()` in `src/quantum_runtime/workspace/trace.py`.
- Keep workspace event output machine-readable and append-only in `.quantum/events.jsonl` and `.quantum/trace/events.ndjson`; event schemas are backed by `TraceEvent` in `src/quantum_runtime/workspace/trace.py` and `JsonlEvent` in `src/quantum_runtime/runtime/observability.py`.
- Use `ensure_ascii=True` when manually serializing JSON to persisted artifacts, for example in `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/runtime/compare.py`, `src/quantum_runtime/runtime/pack.py`, `src/quantum_runtime/reporters/writer.py`, and `src/quantum_runtime/diagnostics/benchmark.py`.
- Avoid `print()` in runtime modules. Tests may execute generated scripts that print JSON, as seen in `tests/test_qiskit_emitter.py`, but the main application surface does not use `print()`.

## Comments

**When to Comment:**
- Prefer concise module, class, and function docstrings instead of inline comments. This is the default style in `src/quantum_runtime/cli.py`, `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/runtime/backend_registry.py`, `src/quantum_runtime/runtime/imports.py`, and `src/quantum_runtime/workspace/trace.py`.
- Use descriptive helper names and structured payload models to explain intent rather than dense comment blocks. The larger orchestration modules rely on naming and helper extraction more than on inline explanation.
- Inline comments are rare. The clearest repeated inline-comment pattern is targeted coverage suppression, for example `# pragma: no cover` in `tests/test_runtime_workspace_safety.py`.

**JSDoc/TSDoc:**
- Not applicable. Use Python docstrings instead.

## Function Design

**Size:**
- Large orchestration modules are normal in the current codebase: `src/quantum_runtime/cli.py` is 1864 lines, `src/quantum_runtime/runtime/imports.py` is 1197 lines, `src/quantum_runtime/runtime/pack.py` is 1158 lines, `src/quantum_runtime/runtime/compare.py` is 904 lines, and `src/quantum_runtime/runtime/executor.py` is 757 lines.
- Supporting modules stay smaller and more focused, for example `src/quantum_runtime/workspace/manager.py`, `src/quantum_runtime/runtime/backend_registry.py`, `src/quantum_runtime/errors.py`, and `src/quantum_runtime/reporters/__init__.py`.
- When adding behavior to large orchestration modules, follow the existing style of extracting private helpers instead of growing command bodies inline.

**Parameters:**
- Prefer keyword-only parameters for orchestration flows and payload builders, for example `execute_intent(*, workspace_root: Path, intent_file: Path, ...)` in `src/quantum_runtime/runtime/executor.py`, `resolve_report_file(report_file: Path, *, workspace_root: Path | None = None)` in `src/quantum_runtime/runtime/imports.py`, and `workspace_conflict_error_payload(*, ...)` in `src/quantum_runtime/runtime/contracts.py`.
- Use `Path` for filesystem inputs and outputs.
- Use `dict[str, Any]`, `list[str]`, and `Literal[...]` in helper boundaries where a full model would be overkill.

**Return Values:**
- Return Pydantic models for machine-facing flows, including `ExecResult`, `ImportResolution`, `WorkspaceBaselineResolution`, `BackendCapabilityDescriptor`, `WorkspaceConflictErrorPayload`, and `WorkspaceRecoveryRequiredErrorPayload`.
- Return JSON-serializable dictionaries for small helper payloads and event sinks, such as the observability payloads assembled in `src/quantum_runtime/cli.py` and `src/quantum_runtime/runtime/observability.py`.
- CLI command handlers in `src/quantum_runtime/cli.py` return `None` and surface results by echoing JSON or text plus `typer.Exit`.

## Module Design

**Exports:**
- Use barrel modules to define the supported import surface. `src/quantum_runtime/runtime/__init__.py`, `src/quantum_runtime/qspec/__init__.py`, `src/quantum_runtime/workspace/__init__.py`, and `src/quantum_runtime/reporters/__init__.py` all declare explicit `__all__` lists.
- Keep package-facing exports narrow and typed. The barrel modules mostly expose result models, top-level commands, and helper constructors rather than every internal helper.

**Barrel Files:**
- Prefer barrel imports for cross-package use, especially in command wiring code like `src/quantum_runtime/cli.py`.
- Import leaf modules directly when tests need to patch or verify a concrete implementation, for example `tests/test_runtime_workspace_safety.py` importing `quantum_runtime.runtime.executor as executor_module`, `tests/test_qiskit_emitter.py` importing `quantum_runtime.lowering.qiskit_emitter`, and `tests/test_cli_backend_list.py` importing `quantum_runtime.runtime.backend_registry`.
- Treat generated metadata under `src/quantum_runtime.egg-info/` as packaging output, not as a hand-edited source pattern.

---

*Convention analysis: 2026-04-18*
