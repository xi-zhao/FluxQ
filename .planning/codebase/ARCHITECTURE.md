# Architecture

**Analysis Date:** 2026-04-12

## Pattern Overview

**Overall:** Layered CLI control plane around a canonical intermediate representation and a revisioned filesystem workspace.

**Key Characteristics:**
- Keep CLI parsing in `src/quantum_runtime/cli.py`; keep orchestration and machine contracts in `src/quantum_runtime/runtime/`.
- Normalize every ingress path through `src/quantum_runtime/runtime/resolve.py` into a `ResolvedRuntimeInput`, then treat `src/quantum_runtime/qspec/model.py` `QSpec` as the truth layer.
- Persist mutable aliases plus immutable history through `src/quantum_runtime/workspace/manager.py`, `src/quantum_runtime/workspace/paths.py`, `src/quantum_runtime/reporters/writer.py`, and `src/quantum_runtime/runtime/run_manifest.py`.

## Layers

**CLI Surface:**
- Purpose: Parse flags, enforce output-mode rules, and translate failures into stable JSON payloads and exit codes.
- Location: `src/quantum_runtime/cli.py`
- Contains: Typer `app`, `backend_app`, `baseline_app`, JSON and JSONL emitters, and command handlers for `init`, `resolve`, `plan`, `status`, `show`, `schema`, `baseline`, `bench`, `export`, `pack`, `exec`, `inspect`, `compare`, `doctor`, and `backend list`.
- Depends on: `src/quantum_runtime/runtime/__init__.py`, `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/runtime/exit_codes.py`, `src/quantum_runtime/workspace/__init__.py`
- Used by: Console script `qrun` declared in `pyproject.toml`

**Control Plane / Runtime Orchestration:**
- Purpose: Provide CLI-independent runtime operations and machine-readable contracts.
- Location: `src/quantum_runtime/runtime/`
- Contains: `control_plane.py`, `executor.py`, `resolve.py`, `imports.py`, `compare.py`, `inspect.py`, `doctor.py`, `export.py`, `pack.py`, `backend_list.py`, `backend_registry.py`, `observability.py`, `contracts.py`, `run_manifest.py`
- Depends on: `src/quantum_runtime/intent/`, `src/quantum_runtime/qspec/`, `src/quantum_runtime/lowering/`, `src/quantum_runtime/diagnostics/`, `src/quantum_runtime/reporters/`, `src/quantum_runtime/workspace/`
- Used by: `src/quantum_runtime/cli.py` and tests such as `tests/test_cli_control_plane.py`, `tests/test_runtime_compare.py`, and `tests/test_runtime_imports.py`

**Intent Ingress and Planning:**
- Purpose: Turn prompt text, markdown, or structured JSON into a normalized `IntentModel` and then into `QSpec`.
- Location: `src/quantum_runtime/intent/` and `src/quantum_runtime/runtime/resolve.py`
- Contains: front-matter and section parsing in `src/quantum_runtime/intent/markdown.py`, schema in `src/quantum_runtime/intent/structured.py`, parser entrypoints in `src/quantum_runtime/intent/parser.py`, and rule-based lowering in `src/quantum_runtime/intent/planner.py`
- Depends on: `src/quantum_runtime/qspec/` and `src/quantum_runtime/errors.py`
- Used by: `src/quantum_runtime/runtime/resolve.py`, `src/quantum_runtime/cli.py`, `tests/test_intent_parser.py`, `tests/test_planner.py`

**Canonical IR / Semantic Validation:**
- Purpose: Define the runtime truth layer for planning, export, benchmark, compare, and replay.
- Location: `src/quantum_runtime/qspec/`
- Contains: IR models in `src/quantum_runtime/qspec/model.py`, semantic hashing in `src/quantum_runtime/qspec/semantics.py`, validation in `src/quantum_runtime/qspec/validation.py`, parameter workflow helpers in `src/quantum_runtime/qspec/parameter_workflow.py`, and observable normalization in `src/quantum_runtime/qspec/observables.py`
- Depends on: Pydantic and internal helpers only
- Used by: planner, runtime orchestration, diagnostics, lowering, reporters, and tests such as `tests/test_qspec_validation.py`

**Artifact Generation and Optional Backends:**
- Purpose: Lower `QSpec` into runnable and replayable artifacts, plus optional backend-specific outputs.
- Location: `src/quantum_runtime/lowering/` and `src/quantum_runtime/backends/`
- Contains: `src/quantum_runtime/lowering/qiskit_emitter.py`, `src/quantum_runtime/lowering/qasm3_emitter.py`, `src/quantum_runtime/lowering/classiq_emitter.py`, and `src/quantum_runtime/backends/classiq_backend.py`
- Depends on: `src/quantum_runtime/qspec/`, Qiskit libraries, and optional `classiq`
- Used by: `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/diagnostics/benchmark.py`, `tests/test_qiskit_emitter.py`, `tests/test_qasm_export.py`, `tests/test_classiq_backend.py`

**Diagnostics and Reporting:**
- Purpose: Produce execution evidence around the generated workload rather than raw source alone.
- Location: `src/quantum_runtime/diagnostics/` and `src/quantum_runtime/reporters/`
- Contains: local simulation, transpile validation, resource estimation, diagrams, benchmarking, report writing, and summary compression
- Depends on: `src/quantum_runtime/qspec/`, `src/quantum_runtime/lowering/`, `src/quantum_runtime/backends/`, `src/quantum_runtime/workspace/`
- Used by: `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/runtime/doctor.py`, `src/quantum_runtime/runtime/inspect.py`

**Workspace Persistence:**
- Purpose: Manage revision numbering, canonical paths, baseline state, and append-only event logs.
- Location: `src/quantum_runtime/workspace/`
- Contains: `src/quantum_runtime/workspace/manager.py`, `src/quantum_runtime/workspace/paths.py`, `src/quantum_runtime/workspace/manifest.py`, `src/quantum_runtime/workspace/baseline.py`, `src/quantum_runtime/workspace/trace.py`
- Depends on: Filesystem and Pydantic only
- Used by: Every mutating runtime flow, especially `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/doctor.py`, and `src/quantum_runtime/runtime/pack.py`

## Data Flow

**Execution Flow:**

1. `pyproject.toml` maps `qrun` to `src/quantum_runtime/cli.py:main`, and a command handler selects one ingress source.
2. `src/quantum_runtime/runtime/resolve.py` enforces exactly one input, parses it through `src/quantum_runtime/intent/parser.py` or `src/quantum_runtime/runtime/imports.py`, and builds a `ResolvedRuntimeInput`.
3. `src/quantum_runtime/intent/planner.py` lowers plannable intent into `QSpec`; `src/quantum_runtime/qspec/validation.py` normalizes and validates that IR before side effects begin.
4. `src/quantum_runtime/runtime/executor.py` opens a `WorkspaceHandle` from `src/quantum_runtime/workspace/manager.py`, reserves a revision, and persists `intents/latest.json` plus `plans/latest.json` and their history copies through `WorkspacePaths`.
5. The executor writes `specs/current.json` and `specs/history/<revision>.json`, then calls emitters in `src/quantum_runtime/lowering/` plus diagnostics in `src/quantum_runtime/diagnostics/`.
6. `src/quantum_runtime/reporters/writer.py` derives semantics, provenance, replay-integrity digests, and report status, then writes `reports/latest.json` and `reports/history/<revision>.json`.
7. `src/quantum_runtime/runtime/run_manifest.py` synthesizes `manifests/latest.json` and `manifests/history/<revision>.json`, while `src/quantum_runtime/workspace/trace.py` and `src/quantum_runtime/runtime/observability.py` emit NDJSON events for the same revision.

**Replay / Compare Flow:**

1. `src/quantum_runtime/runtime/imports.py` resolves `workspace_current`, `report_file`, or `report_revision` into an `ImportResolution` with source metadata, hashes, provenance, and replay-integrity state.
2. `src/quantum_runtime/runtime/compare.py` compares workload identity, raw `QSpec` hashes, report drift, backend deltas, and replay-integrity regressions, then persists the result to `compare/latest.json`.
3. `src/quantum_runtime/runtime/inspect.py`, `src/quantum_runtime/runtime/control_plane.py`, and `src/quantum_runtime/runtime/doctor.py` reopen the same workspace files to expose thin agent-facing status, decision, gate, and health blocks.

**State Management:**
- Use `src/quantum_runtime/workspace/manifest.py` as the mutable pointer to `current_revision`, `active_spec`, and `active_report`.
- Keep immutable history copies under the workspace subdirectories defined in `src/quantum_runtime/workspace/paths.py`, especially `specs/history/`, `reports/history/`, `manifests/history/`, `artifacts/history/`, `benchmarks/history/`, `doctor/history/`, and `packs/`.
- Treat `.quantum/events.jsonl` and `.quantum/trace/events.ndjson` as append-only event streams; JSON command payloads are projections of workspace state, not the source of record.

## Key Abstractions

**`ResolvedRuntimeInput`:**
- Purpose: Represent one normalized execution input regardless of whether it came from prompt text, markdown intent, JSON intent, `QSpec`, report file, or historical revision.
- Examples: `src/quantum_runtime/runtime/resolve.py`
- Pattern: Pydantic internal contract carrying parsed intent, canonical `QSpec`, source metadata, and requested exports.

**`QSpec`:**
- Purpose: Act as the canonical runtime IR that every downstream stage consumes.
- Examples: `src/quantum_runtime/qspec/model.py`, `tests/golden/qspec_ghz.json`, `tests/golden/qspec_qaoa_maxcut.json`
- Pattern: Pydantic schema plus semantic normalization and validation in `src/quantum_runtime/qspec/validation.py` and hash summarization in `src/quantum_runtime/qspec/semantics.py`.

**`WorkspaceHandle` / `WorkspacePaths`:**
- Purpose: Centralize where runtime state lives and how revisions are allocated.
- Examples: `src/quantum_runtime/workspace/manager.py`, `src/quantum_runtime/workspace/paths.py`
- Pattern: Lightweight filesystem service object; mutating runtime code should ask it for paths instead of constructing ad hoc strings.

**`ImportResolution` / `WorkspaceBaselineResolution`:**
- Purpose: Treat current workspace state, historical revisions, detached report files, and baselines with one comparison-ready shape.
- Examples: `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/workspace/baseline.py`
- Pattern: Pydantic resolution objects carrying hashes, provenance, replay-integrity, and source kind for compare, export, inspect, and baseline flows.

**Run Report + Manifest Artifacts:**
- Purpose: Separate execution evidence from integrity-checked join metadata.
- Examples: `src/quantum_runtime/reporters/writer.py`, `src/quantum_runtime/runtime/run_manifest.py`
- Pattern: Revisioned JSON artifacts written in lockstep after execution; compare and import code trusts these files instead of recomputing context from prompts.

**Machine Observability Contracts:**
- Purpose: Give agents and CI stable, low-friction signals without reading raw workspace files directly.
- Examples: `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/runtime/observability.py`, `src/quantum_runtime/workspace/trace.py`
- Pattern: Schema-versioned JSON payloads, reason codes, decision blocks, gate blocks, and NDJSON events.

## Entry Points

**Console CLI:**
- Location: `pyproject.toml`, `src/quantum_runtime/cli.py`
- Triggers: `qrun ...` shell invocations
- Responsibilities: Parse command arguments, choose output mode, call runtime functions, and map exceptions to exit codes or JSON payloads.

**Runtime Workspace Files:**
- Location: `.quantum/workspace.json`, `.quantum/qrun.toml`, `.quantum/specs/current.json`, `.quantum/reports/latest.json`
- Triggers: `qrun exec`, `qrun inspect`, `qrun compare`, `qrun pack`, and baseline commands
- Responsibilities: Persist the current selected run plus immutable history that later commands reopen.

**Developer Bootstrap and CI:**
- Location: `scripts/dev-bootstrap.sh`, `.github/workflows/ci.yml`, `.github/workflows/classiq.yml`
- Triggers: Local setup, repository CI, and optional Classiq-only test runs
- Responsibilities: Install dependencies, run Ruff and MyPy, execute pytest, and build release artifacts.

## Error Handling

**Strategy:** Fail fast on invalid ingress or invalid workspace integrity, but use explicit `"degraded"` versus `"error"` machine statuses when a command can still return useful guidance.

**Patterns:**
- Raise domain-specific exceptions such as `ImportSourceError`, `ReportImportError`, `QSpecValidationError`, and `ArtifactProvenanceMismatch` from lower layers in `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/qspec/validation.py`, and `src/quantum_runtime/artifact_provenance.py`.
- Translate failures into schema-versioned JSON payloads and deterministic exit behavior through `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/runtime/exit_codes.py`, and helper functions in `src/quantum_runtime/cli.py`.
- Use reason codes, decision blocks, and gate blocks from `src/quantum_runtime/runtime/observability.py` so agent-facing flows stay machine actionable even when degraded.

## Cross-Cutting Concerns

**Logging:** Append workspace events through `src/quantum_runtime/workspace/trace.py` and stream command-level JSONL events through `src/quantum_runtime/runtime/observability.py`.

**Validation:** Validate at boundaries: intent parsing in `src/quantum_runtime/intent/parser.py`, canonical `QSpec` checks in `src/quantum_runtime/qspec/validation.py`, provenance and replay integrity in `src/quantum_runtime/artifact_provenance.py` and `src/quantum_runtime/runtime/imports.py`.

**Authentication:** Not detected in the core Python runtime under `src/quantum_runtime/`. Optional `classiq` support in `src/quantum_runtime/backends/classiq_backend.py` assumes SDK-level authentication or configuration outside this repo and does not add an internal auth layer.

---

*Architecture analysis: 2026-04-12*
