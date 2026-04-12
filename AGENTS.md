<!-- GSD:project-start source:PROJECT.md -->
## Project

**FluxQ**

FluxQ is an agent-first quantum runtime CLI for coding agents, CI pipelines, and quantum developers. It turns prompt text, markdown or JSON intents, canonical `QSpec`, and replayable reports into executable, revisioned, auditable quantum run objects that can be compared, exported, packaged, and trusted over time.

The product is not a chat assistant with quantum flavoring. Its product core is the runtime control plane: canonical normalization, immutable revision history, policy-grade comparison, reproducible delivery artifacts, and machine-readable observability around each run.

**Core Value:** An agent or team can trust a FluxQ run as a durable runtime object that is reproducible, comparable, and deliverable, rather than as a one-off generated code snippet.

### Constraints

- **Tech Stack**: Python 3.11 + `uv` + local CLI packaging — the repository and CI are already standardized around this stack
- **Execution Model**: Qiskit-first local execution with OpenQASM 3 as the exchange layer — this matches the validated current product surface
- **Compatibility**: Evolve the current `QSpec` and CLI compatibly instead of introducing a breaking IR rewrite — existing control-plane consumers already exist
- **Observability**: Machine-readable output must remain schema-versioned, stable, and agent-friendly — this is part of the product contract, not implementation detail
- **Product Scope**: Local runtime maturity, replay trust, policy gating, and delivery bundles come before remote-submit breadth — this is the current strategic wedge
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.11 - Main CLI/runtime package in `pyproject.toml`, `src/quantum_runtime/`, and `tests/`
- JSON/TOML/YAML/Markdown - Runtime contracts and workspace/config formats in `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/workspace/manager.py`, and `src/quantum_runtime/intent/markdown.py`
- Rust edition 2024 - Adjacent agent CLI sidecar in `aionrs/Cargo.toml` and `aionrs/src/`; root `.gitignore` excludes `/aionrs/`, so it is not part of the Python package build in `pyproject.toml`
## Runtime
- CPython 3.11 - Required by `pyproject.toml` (`requires-python = ">=3.11,<3.12"`), `mypy.ini`, `.github/workflows/ci.yml`, and `scripts/dev-bootstrap.sh`
- `uv` - Developer install/test flow in `README.md`, `CONTRIBUTING.md`, and `uv.lock`
- `pip` - CI/bootstrap install path in `.github/workflows/ci.yml` and `scripts/dev-bootstrap.sh`
- `cargo` - Only for the adjacent `aionrs/` crate in `aionrs/Cargo.toml`
- Lockfile: present in `uv.lock`
## Frameworks
- Typer `0.24.1` - CLI command surface in `src/quantum_runtime/cli.py`; declared in `pyproject.toml`, locked in `uv.lock`
- Pydantic `2.12.5` - Schema and result models across `src/quantum_runtime/runtime/`, `src/quantum_runtime/qspec/`, and `src/quantum_runtime/diagnostics/`
- Qiskit `2.3.1` - Circuit construction, transpilation, and OpenQASM export in `src/quantum_runtime/lowering/qiskit_emitter.py`, `src/quantum_runtime/diagnostics/transpile_validate.py`, and `src/quantum_runtime/lowering/qasm3_emitter.py`
- Qiskit Aer `0.17.2` - Local execution backend in `src/quantum_runtime/diagnostics/simulate.py`
- Classiq `1.7.0` - Optional synthesis/export backend in `src/quantum_runtime/backends/classiq_backend.py` and `src/quantum_runtime/lowering/classiq_emitter.py`
- pytest `9.0.2` - Test runner configured in `pyproject.toml` and used throughout `tests/`
- setuptools `>=69` + `wheel` - Build backend in `pyproject.toml`
- build `1.3.0` - Release artifact builder used by `.github/workflows/ci.yml`
- Ruff `0.15.8` - Linting configured in `pyproject.toml`
- MyPy `1.20.0` - Static checking configured in `mypy.ini`
## Key Dependencies
- `qiskit` `2.3.1` - In-memory circuit generation and backend-facing export logic in `src/quantum_runtime/lowering/qiskit_emitter.py`
- `qiskit-aer` `0.17.2` - Local simulator used by `src/quantum_runtime/diagnostics/simulate.py`
- `pydantic` `2.12.5` - Stable machine-readable payloads in `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/runtime/observability.py`, and `src/quantum_runtime/reporters/writer.py`
- `typer` `0.24.1` - User-facing `qrun` CLI in `src/quantum_runtime/cli.py`
- `pyyaml` `6.0.3` - YAML front matter parsing for markdown intents in `src/quantum_runtime/intent/markdown.py`
- `matplotlib` `3.10.8` - PNG circuit rendering in `src/quantum_runtime/diagnostics/diagrams.py`
- `pytest` `9.0.2` - Release and behavior checks in `tests/test_packaging_release.py`, `tests/test_open_source_release.py`, and the broader `tests/` suite
- `ruff` `0.15.8` - Lint gate in `.github/workflows/ci.yml`
- `mypy` `1.20.0` - Type gate in `.github/workflows/ci.yml` and `mypy.ini`
- `classiq` `1.7.0` - Optional extra only; enabled via `.[classiq]` in `.github/workflows/classiq.yml`
## Configuration
- Runtime workspace config is file-based, not env-driven: `qrun init` creates `qrun.toml`, `workspace.json`, `events.jsonl`, and `trace/events.ndjson` via `src/quantum_runtime/workspace/manager.py` and `src/quantum_runtime/workspace/paths.py`
- Main Python runtime does not declare required runtime secrets or API-key env vars in `src/quantum_runtime/`
- Developer bootstrap honors `PYTHON_BIN`, `PIP_TIMEOUT`, and `PIP_INDEX_URL` in `scripts/dev-bootstrap.sh`
- Optional sidecar provider config lives outside the package in `aionrs/src/config.rs` and `aionrs/src/auth.rs`
- Package metadata and tool configuration live in `pyproject.toml`
- Type-check configuration lives in `mypy.ini`
- CI/build automation lives in `.github/workflows/ci.yml` and `.github/workflows/classiq.yml`
- Release artifacts are built into `dist/` and validated by `tests/test_packaging_release.py`
## Platform Requirements
- Python 3.11 with virtualenv support is required by `pyproject.toml` and `scripts/dev-bootstrap.sh`
- Local Qiskit workflows need base dependencies from `pyproject.toml`
- Classiq work needs the optional extra and dedicated workflow path from `.github/workflows/classiq.yml`
- Rust/Cargo is only required when working inside the adjacent `aionrs/` tree described by `aionrs/Cargo.toml`
- Deployment target is a local CLI/package, not a long-running service; entrypoint is `qrun = "quantum_runtime.cli:main"` in `pyproject.toml`
- Distribution model is wheel/sdist packaging built by `python -m build` in `.github/workflows/ci.yml` and stored in `dist/`
- Runtime persistence target is the local workspace directory managed by `src/quantum_runtime/workspace/paths.py`
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Use `snake_case.py` for implementation modules under `src/quantum_runtime/`, for example `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/qspec/model.py`, and `src/quantum_runtime/workspace/manager.py`.
- Use package `__init__.py` files as barrels that re-export stable APIs, for example `src/quantum_runtime/runtime/__init__.py`, `src/quantum_runtime/qspec/__init__.py`, and `src/quantum_runtime/workspace/__init__.py`.
- Use `tests/test_<area>.py` for tests, for example `tests/test_cli_exec.py`, `tests/test_workspace_manager.py`, and `tests/test_release_docs.py`.
- Keep golden snapshots under `tests/golden/`, for example `tests/golden/qiskit_ghz_main.py`, `tests/golden/qspec_ghz.json`, and `tests/golden/report_summary_ghz.txt`.
- Use `snake_case` for public functions, for example `parse_intent_text()` in `src/quantum_runtime/intent/parser.py`, `resolve_import_reference()` in `src/quantum_runtime/runtime/imports.py`, and `run_doctor()` in `src/quantum_runtime/runtime/doctor.py`.
- Prefix file-local helpers with `_`, for example `_json_error()` and `_resolve_runtime_input()` in `src/quantum_runtime/cli.py`, `_make_qspec()` in `tests/test_qspec_validation.py`, and `_seed_workspace()` in `tests/test_runtime_imports.py`.
- Name CLI command handlers with a `_command` suffix inside `src/quantum_runtime/cli.py`, for example `init_command()` and `version_command()`.
- Use `snake_case` for locals and parameters, for example `workspace_root`, `report_payload`, and `required_backends` in `src/quantum_runtime/runtime/imports.py` and `src/quantum_runtime/runtime/doctor.py`.
- Use `UPPER_SNAKE_CASE` for module constants, for example `SCHEMA_VERSION` in `src/quantum_runtime/workspace/trace.py`, `DEFAULT_QRUN_TOML` in `src/quantum_runtime/workspace/manager.py`, and `PROJECT_ROOT` plus `RUNNER` in `tests/test_cli_exec.py`.
- Use `PascalCase` for Pydantic models, dataclasses, and exceptions, for example `QSpec` in `src/quantum_runtime/qspec/model.py`, `ExecResult` in `src/quantum_runtime/runtime/executor.py`, `WorkspaceHandle` in `src/quantum_runtime/workspace/manager.py`, and `ImportSourceError` in `src/quantum_runtime/runtime/imports.py`.
- Suffix structured payload models with domain-specific nouns such as `Result`, `Report`, `Manifest`, `Paths`, or `Resolution`, for example `DoctorReport`, `CompareResult`, `WorkspaceManifest`, `WorkspacePaths`, and `ImportResolution`.
## Code Style
- Start nearly every Python file with `from __future__ import annotations`, including `src/quantum_runtime/cli.py`, `src/quantum_runtime/runtime/backend_registry.py`, `tests/test_cli_exec.py`, and `tests/test_release_docs.py`.
- Keep modules docstring-first. Module, class, and public function docstrings are standard in `src/quantum_runtime/cli.py`, `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/runtime/imports.py`, and `src/quantum_runtime/workspace/trace.py`.
- Follow Black-like formatting manually: trailing commas in multi-line literals and calls, hanging indents, and blank lines between top-level declarations. This style is visible in `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/runtime/doctor.py`, and `tests/test_cli_control_plane.py`.
- Prefer explicit JSON serialization over ad hoc string building, using `model_dump_json(indent=2)` or `json.dumps(..., indent=2)`, as shown in `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/reporters/writer.py`, and many tests such as `tests/test_cli_exec.py` and `tests/test_pack_bundle.py`.
- No dedicated formatter config is detected in `pyproject.toml`. There is no `[tool.black]`, `ruff format`, or import-sorting configuration.
- Run Ruff against `src` and `tests` from `pyproject.toml`, `CONTRIBUTING.md`, and `.github/workflows/ci.yml`.
- Current Ruff selection in `pyproject.toml` is intentionally narrow: `E4`, `E7`, `E9`, and `F`.
- Do not rely on Ruff to enforce import sorting, quote style, or docstring rules. The repository style is maintained by convention rather than by a strict formatter.
- Run MyPy only on `src` according to `mypy.ini`, with `ignore_missing_imports = true` plus targeted module overrides for packages such as `quantum_runtime.intent.planner` and `quantum_runtime.runtime.executor`.
## Import Organization
- No alias system is configured. Imports use absolute package paths such as `from quantum_runtime.runtime import ...` in `src/quantum_runtime/cli.py` or relative imports such as `from .manifest import WorkspaceManifest` in `src/quantum_runtime/workspace/manager.py`.
## Error Handling
- Prefer domain-specific exceptions carrying stable error codes over raw exceptions. Examples:
- Translate low-level failures into machine-readable reasons close to the boundary. `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/control_plane.py`, and `src/quantum_runtime/runtime/executor.py` all catch broad parsing or filesystem failures and re-raise typed errors with stable codes.
- Keep CLI failure output schema-driven. `_json_error()` in `src/quantum_runtime/cli.py` emits an `ErrorPayload` through `dump_schema_payload()` and exits with `typer.Exit(code=3)`.
- Use `assert` only for internal invariants that should already hold, for example the `assert resolution is not None` check in `src/quantum_runtime/cli.py`, `assert manifest is not None` in `src/quantum_runtime/runtime/doctor.py`, and importlib loader assertions in `tests/test_qiskit_emitter.py`.
## Logging
- CLI text and JSON output goes through `typer.echo` in `src/quantum_runtime/cli.py`.
- Runtime event logging is implemented with `TraceWriter` and `TraceEvent` in `src/quantum_runtime/workspace/trace.py`, which append JSON lines to workspace files such as `trace/events.ndjson` and `events.jsonl`.
- Machine-facing payloads are usually serialized with Pydantic or `json.dumps(..., ensure_ascii=True)`, for example `src/quantum_runtime/runtime/compare.py`, `src/quantum_runtime/runtime/executor.py`, and `src/quantum_runtime/qspec/semantics.py`.
## Comments
- Prefer docstrings over inline comments. Public-facing modules and models are documented with concise docstrings in `src/quantum_runtime/cli.py`, `src/quantum_runtime/qspec/model.py`, `src/quantum_runtime/runtime/imports.py`, and `src/quantum_runtime/workspace/trace.py`.
- Inline comments are rare. The codebase relies more on descriptive names and structured result models than on comment-heavy logic.
- Not applicable. This is a Python codebase.
- Use Python docstrings instead of block comments for API explanation.
## Function Design
- `src/quantum_runtime/cli.py` is the main command surface and is 1409 lines.
- `src/quantum_runtime/runtime/executor.py` centralizes execution flow and is 540 lines.
- Smaller supporting modules such as `src/quantum_runtime/workspace/manager.py` and `src/quantum_runtime/errors.py` stay compact.
- Type-annotate public functions consistently, including tests. Examples include `parse_intent_file(path: Path) -> IntentModel` in `src/quantum_runtime/intent/parser.py` and `test_qrun_exec_json_generates_workspace_artifacts_and_report(tmp_path: Path) -> None` in `tests/test_cli_exec.py`.
- Prefer keyword-only parameters for orchestration functions with many inputs, for example `execute_intent(*, workspace_root: Path, intent_file: Path, ...)` in `src/quantum_runtime/runtime/executor.py` and `run_doctor(*, workspace_root: Path, fix: bool = False, ...)` in `src/quantum_runtime/runtime/doctor.py`.
- Use Pydantic `BaseModel` containers when a function returns or passes around structured runtime state, for example `ExecResult`, `DoctorReport`, `ImportResolution`, and `WorkspaceManifest`.
- Return structured models for machine-facing flows, for example `ExecResult` from `src/quantum_runtime/runtime/executor.py`, `DoctorReport` from `src/quantum_runtime/runtime/doctor.py`, and `ImportResolution` from `src/quantum_runtime/runtime/imports.py`.
- CLI commands return `None` and emit output via `typer.echo` in `src/quantum_runtime/cli.py`.
- Tests typically assert full JSON payload shape rather than a single field, as shown in `tests/test_cli_control_plane.py`, `tests/test_cli_exec.py`, and `tests/test_cli_observability.py`.
## Module Design
- `src/quantum_runtime/runtime/__init__.py` re-exports the runtime surface.
- `src/quantum_runtime/workspace/__init__.py` re-exports workspace helpers.
- `src/quantum_runtime/qspec/__init__.py` re-exports models plus validation helpers.
- `src/quantum_runtime/reporters/__init__.py` re-exports `summarize_report` and `write_report`.
- Use the barrel when importing across package boundaries, for example `from quantum_runtime.runtime import ...` in `src/quantum_runtime/cli.py`.
- Import directly from leaf modules when a test is focused on one implementation detail, for example `from quantum_runtime.runtime.executor import ExecResult` in `tests/test_cli_exec.py` and `from quantum_runtime.backends.classiq_backend import run_classiq_backend` in `tests/test_classiq_backend.py`.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Keep CLI parsing in `src/quantum_runtime/cli.py`; keep orchestration and machine contracts in `src/quantum_runtime/runtime/`.
- Normalize every ingress path through `src/quantum_runtime/runtime/resolve.py` into a `ResolvedRuntimeInput`, then treat `src/quantum_runtime/qspec/model.py` `QSpec` as the truth layer.
- Persist mutable aliases plus immutable history through `src/quantum_runtime/workspace/manager.py`, `src/quantum_runtime/workspace/paths.py`, `src/quantum_runtime/reporters/writer.py`, and `src/quantum_runtime/runtime/run_manifest.py`.
## Layers
- Purpose: Parse flags, enforce output-mode rules, and translate failures into stable JSON payloads and exit codes.
- Location: `src/quantum_runtime/cli.py`
- Contains: Typer `app`, `backend_app`, `baseline_app`, JSON and JSONL emitters, and command handlers for `init`, `resolve`, `plan`, `status`, `show`, `schema`, `baseline`, `bench`, `export`, `pack`, `exec`, `inspect`, `compare`, `doctor`, and `backend list`.
- Depends on: `src/quantum_runtime/runtime/__init__.py`, `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/runtime/exit_codes.py`, `src/quantum_runtime/workspace/__init__.py`
- Used by: Console script `qrun` declared in `pyproject.toml`
- Purpose: Provide CLI-independent runtime operations and machine-readable contracts.
- Location: `src/quantum_runtime/runtime/`
- Contains: `control_plane.py`, `executor.py`, `resolve.py`, `imports.py`, `compare.py`, `inspect.py`, `doctor.py`, `export.py`, `pack.py`, `backend_list.py`, `backend_registry.py`, `observability.py`, `contracts.py`, `run_manifest.py`
- Depends on: `src/quantum_runtime/intent/`, `src/quantum_runtime/qspec/`, `src/quantum_runtime/lowering/`, `src/quantum_runtime/diagnostics/`, `src/quantum_runtime/reporters/`, `src/quantum_runtime/workspace/`
- Used by: `src/quantum_runtime/cli.py` and tests such as `tests/test_cli_control_plane.py`, `tests/test_runtime_compare.py`, and `tests/test_runtime_imports.py`
- Purpose: Turn prompt text, markdown, or structured JSON into a normalized `IntentModel` and then into `QSpec`.
- Location: `src/quantum_runtime/intent/` and `src/quantum_runtime/runtime/resolve.py`
- Contains: front-matter and section parsing in `src/quantum_runtime/intent/markdown.py`, schema in `src/quantum_runtime/intent/structured.py`, parser entrypoints in `src/quantum_runtime/intent/parser.py`, and rule-based lowering in `src/quantum_runtime/intent/planner.py`
- Depends on: `src/quantum_runtime/qspec/` and `src/quantum_runtime/errors.py`
- Used by: `src/quantum_runtime/runtime/resolve.py`, `src/quantum_runtime/cli.py`, `tests/test_intent_parser.py`, `tests/test_planner.py`
- Purpose: Define the runtime truth layer for planning, export, benchmark, compare, and replay.
- Location: `src/quantum_runtime/qspec/`
- Contains: IR models in `src/quantum_runtime/qspec/model.py`, semantic hashing in `src/quantum_runtime/qspec/semantics.py`, validation in `src/quantum_runtime/qspec/validation.py`, parameter workflow helpers in `src/quantum_runtime/qspec/parameter_workflow.py`, and observable normalization in `src/quantum_runtime/qspec/observables.py`
- Depends on: Pydantic and internal helpers only
- Used by: planner, runtime orchestration, diagnostics, lowering, reporters, and tests such as `tests/test_qspec_validation.py`
- Purpose: Lower `QSpec` into runnable and replayable artifacts, plus optional backend-specific outputs.
- Location: `src/quantum_runtime/lowering/` and `src/quantum_runtime/backends/`
- Contains: `src/quantum_runtime/lowering/qiskit_emitter.py`, `src/quantum_runtime/lowering/qasm3_emitter.py`, `src/quantum_runtime/lowering/classiq_emitter.py`, and `src/quantum_runtime/backends/classiq_backend.py`
- Depends on: `src/quantum_runtime/qspec/`, Qiskit libraries, and optional `classiq`
- Used by: `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/diagnostics/benchmark.py`, `tests/test_qiskit_emitter.py`, `tests/test_qasm_export.py`, `tests/test_classiq_backend.py`
- Purpose: Produce execution evidence around the generated workload rather than raw source alone.
- Location: `src/quantum_runtime/diagnostics/` and `src/quantum_runtime/reporters/`
- Contains: local simulation, transpile validation, resource estimation, diagrams, benchmarking, report writing, and summary compression
- Depends on: `src/quantum_runtime/qspec/`, `src/quantum_runtime/lowering/`, `src/quantum_runtime/backends/`, `src/quantum_runtime/workspace/`
- Used by: `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/runtime/doctor.py`, `src/quantum_runtime/runtime/inspect.py`
- Purpose: Manage revision numbering, canonical paths, baseline state, and append-only event logs.
- Location: `src/quantum_runtime/workspace/`
- Contains: `src/quantum_runtime/workspace/manager.py`, `src/quantum_runtime/workspace/paths.py`, `src/quantum_runtime/workspace/manifest.py`, `src/quantum_runtime/workspace/baseline.py`, `src/quantum_runtime/workspace/trace.py`
- Depends on: Filesystem and Pydantic only
- Used by: Every mutating runtime flow, especially `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/doctor.py`, and `src/quantum_runtime/runtime/pack.py`
## Data Flow
- Use `src/quantum_runtime/workspace/manifest.py` as the mutable pointer to `current_revision`, `active_spec`, and `active_report`.
- Keep immutable history copies under the workspace subdirectories defined in `src/quantum_runtime/workspace/paths.py`, especially `specs/history/`, `reports/history/`, `manifests/history/`, `artifacts/history/`, `benchmarks/history/`, `doctor/history/`, and `packs/`.
- Treat `.quantum/events.jsonl` and `.quantum/trace/events.ndjson` as append-only event streams; JSON command payloads are projections of workspace state, not the source of record.
## Key Abstractions
- Purpose: Represent one normalized execution input regardless of whether it came from prompt text, markdown intent, JSON intent, `QSpec`, report file, or historical revision.
- Examples: `src/quantum_runtime/runtime/resolve.py`
- Pattern: Pydantic internal contract carrying parsed intent, canonical `QSpec`, source metadata, and requested exports.
- Purpose: Act as the canonical runtime IR that every downstream stage consumes.
- Examples: `src/quantum_runtime/qspec/model.py`, `tests/golden/qspec_ghz.json`, `tests/golden/qspec_qaoa_maxcut.json`
- Pattern: Pydantic schema plus semantic normalization and validation in `src/quantum_runtime/qspec/validation.py` and hash summarization in `src/quantum_runtime/qspec/semantics.py`.
- Purpose: Centralize where runtime state lives and how revisions are allocated.
- Examples: `src/quantum_runtime/workspace/manager.py`, `src/quantum_runtime/workspace/paths.py`
- Pattern: Lightweight filesystem service object; mutating runtime code should ask it for paths instead of constructing ad hoc strings.
- Purpose: Treat current workspace state, historical revisions, detached report files, and baselines with one comparison-ready shape.
- Examples: `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/workspace/baseline.py`
- Pattern: Pydantic resolution objects carrying hashes, provenance, replay-integrity, and source kind for compare, export, inspect, and baseline flows.
- Purpose: Separate execution evidence from integrity-checked join metadata.
- Examples: `src/quantum_runtime/reporters/writer.py`, `src/quantum_runtime/runtime/run_manifest.py`
- Pattern: Revisioned JSON artifacts written in lockstep after execution; compare and import code trusts these files instead of recomputing context from prompts.
- Purpose: Give agents and CI stable, low-friction signals without reading raw workspace files directly.
- Examples: `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/runtime/observability.py`, `src/quantum_runtime/workspace/trace.py`
- Pattern: Schema-versioned JSON payloads, reason codes, decision blocks, gate blocks, and NDJSON events.
## Entry Points
- Location: `pyproject.toml`, `src/quantum_runtime/cli.py`
- Triggers: `qrun ...` shell invocations
- Responsibilities: Parse command arguments, choose output mode, call runtime functions, and map exceptions to exit codes or JSON payloads.
- Location: `.quantum/workspace.json`, `.quantum/qrun.toml`, `.quantum/specs/current.json`, `.quantum/reports/latest.json`
- Triggers: `qrun exec`, `qrun inspect`, `qrun compare`, `qrun pack`, and baseline commands
- Responsibilities: Persist the current selected run plus immutable history that later commands reopen.
- Location: `scripts/dev-bootstrap.sh`, `.github/workflows/ci.yml`, `.github/workflows/classiq.yml`
- Triggers: Local setup, repository CI, and optional Classiq-only test runs
- Responsibilities: Install dependencies, run Ruff and MyPy, execute pytest, and build release artifacts.
## Error Handling
- Raise domain-specific exceptions such as `ImportSourceError`, `ReportImportError`, `QSpecValidationError`, and `ArtifactProvenanceMismatch` from lower layers in `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/qspec/validation.py`, and `src/quantum_runtime/artifact_provenance.py`.
- Translate failures into schema-versioned JSON payloads and deterministic exit behavior through `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/runtime/exit_codes.py`, and helper functions in `src/quantum_runtime/cli.py`.
- Use reason codes, decision blocks, and gate blocks from `src/quantum_runtime/runtime/observability.py` so agent-facing flows stay machine actionable even when degraded.
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
