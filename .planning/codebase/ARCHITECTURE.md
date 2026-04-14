# Architecture

**Analysis Date:** 2026-04-14

## Pattern Overview

**Overall:** CLI-driven filesystem control plane around a canonical `QSpec` IR.

**Key Characteristics:**
- `src/quantum_runtime/cli.py` is the only shipped command entrypoint; it delegates nearly all behavior to `src/quantum_runtime/runtime/`.
- Every ingress path is normalized through `src/quantum_runtime/runtime/resolve.py` into `ResolvedRuntimeInput` and a validated `QSpec` from `src/quantum_runtime/qspec/model.py`.
- Workspace state lives on disk under a `WorkspacePaths` layout from `src/quantum_runtime/workspace/paths.py`, with mutable aliases such as `reports/latest.json` and immutable history under `reports/history/`, `specs/history/`, `manifests/history/`, `artifacts/history/`, `events/history/`, and `trace/history/`.
- Read-only commands such as `status`, `show`, `inspect`, `compare`, `export`, and `pack` reopen persisted runtime objects through `src/quantum_runtime/runtime/imports.py` instead of reparsing prompts.
- Policy and agent-facing UX are machine-first: schema payloads in `src/quantum_runtime/runtime/contracts.py`, JSONL/NDJSON events in `src/quantum_runtime/runtime/observability.py` and `src/quantum_runtime/workspace/trace.py`, and acceptance gates in `src/quantum_runtime/runtime/policy.py`.

## Layers

**CLI Command Layer:**
- Purpose: Parse shell flags, enforce `--json` and `--jsonl` rules, fan out to runtime services, and translate failures into exit codes.
- Location: `src/quantum_runtime/cli.py`
- Contains: Typer `app`, `baseline_app`, `backend_app`, plus handlers for `init`, `prompt`, `resolve`, `plan`, `status`, `show`, `schema`, `baseline`, `bench`, `export`, `pack`, `pack-inspect`, `exec`, `inspect`, `compare`, `doctor`, and `backend list`.
- Depends on: `src/quantum_runtime/runtime/__init__.py`, `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/runtime/exit_codes.py`, `src/quantum_runtime/runtime/observability.py`, `src/quantum_runtime/workspace/__init__.py`
- Used by: `qrun` console script in `pyproject.toml`; CLI tests such as `tests/test_cli_exec.py`, `tests/test_cli_control_plane.py`, and `tests/test_cli_compare.py`

**Read-only Control Plane Layer:**
- Purpose: Produce plan, resolve, status, show, and schema payloads without mutating workspace state.
- Location: `src/quantum_runtime/runtime/control_plane.py`
- Contains: `PlanResult`, `ResolveResult`, `StatusResult`, `ShowResult`, `SchemaResult`, plus `build_execution_plan()`, `resolve_runtime_object()`, `workspace_status()`, `show_run()`, and `schema_contract()`
- Depends on: `src/quantum_runtime/runtime/resolve.py`, `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/observability.py`, `src/quantum_runtime/runtime/run_manifest.py`, `src/quantum_runtime/workspace/paths.py`
- Used by: `src/quantum_runtime/cli.py` and tests such as `tests/test_cli_control_plane.py` and `tests/test_cli_observability.py`

**Ingress Normalization Layer:**
- Purpose: Accept prompt text, markdown intent, JSON intent, `QSpec`, report file, or revision reference and normalize it into one internal shape.
- Location: `src/quantum_runtime/intent/` and `src/quantum_runtime/runtime/resolve.py`
- Contains: Markdown front matter parsing in `src/quantum_runtime/intent/markdown.py`, text/file parsing in `src/quantum_runtime/intent/parser.py`, `IntentModel` in `src/quantum_runtime/intent/structured.py`, rule-based lowering in `src/quantum_runtime/intent/planner.py`, and `ResolvedRuntimeInput` in `src/quantum_runtime/runtime/resolve.py`
- Depends on: `src/quantum_runtime/qspec/`, `src/quantum_runtime/errors.py`, and `src/quantum_runtime/runtime/imports.py`
- Used by: Control-plane planning, execution in `src/quantum_runtime/runtime/executor.py`, and ingress tests such as `tests/test_intent_parser.py`, `tests/test_planner.py`, `tests/test_cli_ingress_resolution.py`, and `tests/test_runtime_ingress_resolution.py`

**Canonical IR Layer:**
- Purpose: Hold the single canonical runtime object that downstream code compares, exports, validates, and executes.
- Location: `src/quantum_runtime/qspec/`
- Contains: `QSpec`, `Constraints`, `PatternNode`, `MeasureNode`, and runtime metadata in `src/quantum_runtime/qspec/model.py`; normalization and validation in `src/quantum_runtime/qspec/validation.py`; semantic hashing in `src/quantum_runtime/qspec/semantics.py`; parameter workflow and observable helpers in `src/quantum_runtime/qspec/parameter_workflow.py` and `src/quantum_runtime/qspec/observables.py`
- Depends on: Pydantic plus internal helpers only
- Used by: Ingress planning, emitters, diagnostics, report writing, import resolution, and tests such as `tests/test_qspec_semantics.py` and `tests/test_qspec_validation.py`

**Execution and Artifact Generation Layer:**
- Purpose: Turn one normalized `QSpec` into revisioned artifacts, diagnostics, backend reports, report JSON, and immutable run manifests.
- Location: `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/lowering/`, `src/quantum_runtime/diagnostics/`, `src/quantum_runtime/backends/`, and `src/quantum_runtime/reporters/`
- Contains: Execution orchestration in `src/quantum_runtime/runtime/executor.py`; Qiskit, OpenQASM 3, and Classiq emitters in `src/quantum_runtime/lowering/`; simulation, diagrams, resource estimates, transpile validation, and benchmarking in `src/quantum_runtime/diagnostics/`; optional synthesis in `src/quantum_runtime/backends/classiq_backend.py`; report writing in `src/quantum_runtime/reporters/writer.py`
- Depends on: `src/quantum_runtime/runtime/resolve.py`, `src/quantum_runtime/qspec/`, `src/quantum_runtime/workspace/`, and external Qiskit and Classiq packages
- Used by: `qrun exec`, `qrun bench`, `qrun doctor`, and tests such as `tests/test_cli_exec.py`, `tests/test_diagnostics.py`, `tests/test_qiskit_emitter.py`, and `tests/test_report_writer.py`

**Import, Replay, and Comparison Layer:**
- Purpose: Reopen persisted runs as trusted runtime inputs, enforce replay integrity, and compute compare, inspect, export, baseline, and pack views.
- Location: `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/compare.py`, `src/quantum_runtime/runtime/inspect.py`, `src/quantum_runtime/runtime/export.py`, `src/quantum_runtime/runtime/pack.py`, `src/quantum_runtime/runtime/policy.py`
- Contains: `ImportReference`, `ImportResolution`, `WorkspaceBaselineResolution`, replay-integrity checks, compare deltas and verdicts, inspect summaries, artifact re-export, revision bundles, and benchmark or doctor policy gates
- Depends on: `src/quantum_runtime/runtime/run_manifest.py`, `src/quantum_runtime/artifact_provenance.py`, `src/quantum_runtime/workspace/`, `src/quantum_runtime/qspec/`, and emitters or diagnostics where needed
- Used by: CLI commands `compare`, `inspect`, `export`, `pack`, `baseline`, `show`, and `status`, plus tests such as `tests/test_runtime_imports.py`, `tests/test_runtime_compare.py`, `tests/test_cli_export.py`, `tests/test_pack_bundle.py`, and `tests/test_workspace_baseline.py`

**Workspace Persistence Layer:**
- Purpose: Define the on-disk source of truth, allocate revisions, coordinate writers, and keep append-only history coherent.
- Location: `src/quantum_runtime/workspace/` plus `src/quantum_runtime/runtime/run_manifest.py`
- Contains: Workspace init and load in `src/quantum_runtime/workspace/manager.py`, path helpers in `src/quantum_runtime/workspace/paths.py`, revision manifest and atomic file helpers in `src/quantum_runtime/workspace/manifest.py`, baseline storage in `src/quantum_runtime/workspace/baseline.py`, lock lease management in `src/quantum_runtime/workspace/locking.py`, trace or event logging in `src/quantum_runtime/workspace/trace.py`, immutable per-run manifests in `src/quantum_runtime/runtime/run_manifest.py`
- Depends on: Filesystem, Pydantic, and runtime contracts only
- Used by: Every mutating command and every replay or import flow

## Data Flow

**Resolve And Plan Flow:**

1. `src/quantum_runtime/cli.py` accepts exactly one runtime input for `qrun prompt`, `qrun resolve`, or `qrun plan`.
2. `src/quantum_runtime/runtime/resolve.py` parses the source through `src/quantum_runtime/intent/parser.py` or `src/quantum_runtime/runtime/imports.py` and returns `ResolvedRuntimeInput`.
3. `src/quantum_runtime/intent/planner.py` lowers parsed intent into `QSpec`, or `src/quantum_runtime/runtime/resolve.py` validates an existing `QSpec` or report-derived one.
4. `src/quantum_runtime/runtime/control_plane.py` builds `ResolveResult` or `PlanResult`, including backend advisories from `src/quantum_runtime/runtime/doctor.py`.

**State Management:**
- This path is read-only. It does not reserve a revision or update `.quantum/`; it only projects what execution would do.

**Execution And Revision Commit Flow:**

1. `exec_command()` in `src/quantum_runtime/cli.py` calls one of `execute_intent()`, `execute_intent_text()`, `execute_intent_json()`, `execute_qspec()`, or `execute_report()` in `src/quantum_runtime/runtime/executor.py`.
2. `src/quantum_runtime/workspace/manager.py` loads or creates the workspace, then `src/quantum_runtime/workspace/locking.py` acquires `.workspace.lock`.
3. `WorkspaceHandle.reserve_revision()` bumps `workspace.json`, then `src/quantum_runtime/runtime/executor.py` writes `intents/history/`, `plans/history/`, `specs/history/`, and optional `intents/history/<revision>.md`.
4. Emitters and diagnostics write revision-scoped artifacts under `artifacts/history/<revision>/` and `figures/`; `src/quantum_runtime/reporters/writer.py` serializes the report and replay-integrity digests.
5. `src/quantum_runtime/runtime/run_manifest.py` writes `manifests/history/<revision>.json`, event snapshots are copied into `events/history/` and `trace/history/`, and alias files such as `specs/current.json`, `reports/latest.json`, `artifacts/qiskit/main.py`, and `manifests/latest.json` are promoted.

**State Management:**
- History files are revision-stable. Alias files are mutable pointers to the currently selected revision described by `workspace.json`.

**Replay, Baseline, And Compare Flow:**

1. `src/quantum_runtime/runtime/imports.py` resolves current workspace state, a report file, or a historical revision into `ImportResolution`.
2. That resolution re-derives report and `QSpec` hashes, canonical artifact provenance via `src/quantum_runtime/artifact_provenance.py`, run-manifest linkage, and replay-integrity status.
3. `src/quantum_runtime/workspace/baseline.py` stores approved left-hand state in `baselines/current.json`; `src/quantum_runtime/runtime/compare.py` compares baseline vs current or any two resolutions.
4. `src/quantum_runtime/runtime/inspect.py`, `src/quantum_runtime/runtime/export.py`, and `src/quantum_runtime/runtime/pack.py` reuse the same resolved runtime object instead of parsing prompts again.

**State Management:**
- `baselines/current.json`, `compare/latest.json`, `benchmarks/latest.json`, `doctor/latest.json`, and `packs/<revision>/` are derived projections. The replayable source of record remains the report, `QSpec`, manifests history, and artifact snapshots.

## Key Abstractions

**ResolvedRuntimeInput:**
- Purpose: Carry one normalized execution request regardless of whether it came from prompt text, markdown, JSON intent, a `QSpec` file, a report file, or a revision reference.
- Examples: `src/quantum_runtime/runtime/resolve.py`
- Pattern: Internal Pydantic container with `intent_model`, `intent_resolution`, validated `qspec`, `input_data`, and `requested_exports`.

**QSpec:**
- Purpose: Represent the canonical workload and runtime metadata that every downstream stage consumes.
- Examples: `src/quantum_runtime/qspec/model.py`, `tests/golden/qspec_ghz.json`, `tests/golden/qspec_qaoa_maxcut.json`
- Pattern: Pydantic IR plus semantic normalization and hashing in `src/quantum_runtime/qspec/validation.py` and `src/quantum_runtime/qspec/semantics.py`.

**WorkspaceHandle / WorkspacePaths / WorkspaceManifest:**
- Purpose: Centralize where mutable aliases, immutable history, and revision counters live.
- Examples: `src/quantum_runtime/workspace/manager.py`, `src/quantum_runtime/workspace/paths.py`, `src/quantum_runtime/workspace/manifest.py`
- Pattern: Small filesystem service objects; runtime code asks them for canonical locations instead of building raw strings.

**ImportResolution:**
- Purpose: Reopen persisted runtime state with provenance, semantic summaries, replay-integrity verdicts, and artifact locations.
- Examples: `src/quantum_runtime/runtime/imports.py`
- Pattern: Structured Pydantic read model used by compare, inspect, export, baseline, and pack flows.

**RunManifestArtifact / RunReportArtifact:**
- Purpose: Separate execution evidence from the immutable join record that ties one revision’s `QSpec`, report, intent, plan, and events together.
- Examples: `src/quantum_runtime/runtime/run_manifest.py`, `src/quantum_runtime/reporters/writer.py`
- Pattern: Schema-versioned persisted JSON contracts written per revision and later reopened by import and control-plane logic.

**JsonlEvent / TraceEvent:**
- Purpose: Give agents incremental, machine-readable progress without scraping human logs.
- Examples: `src/quantum_runtime/runtime/observability.py`, `src/quantum_runtime/workspace/trace.py`
- Pattern: JSONL or NDJSON envelopes with stable `phase`, `status`, `error_code`, and `payload` fields.

## Entry Points

**CLI Binary:**
- Location: `pyproject.toml`, `src/quantum_runtime/cli.py`
- Triggers: `qrun ...` shell invocations
- Responsibilities: Parse command arguments, select output mode, map runtime exceptions to structured payloads and exit codes, and emit JSON or JSONL envelopes.

**Workspace Initialization:**
- Location: `src/quantum_runtime/workspace/manager.py`, `src/quantum_runtime/workspace/paths.py`
- Triggers: `qrun init`, any mutating command that calls `WorkspaceManager.load_or_init()`
- Responsibilities: Create the `.quantum/` directory skeleton, seed `workspace.json`, `qrun.toml`, `events.jsonl`, and `trace/events.ndjson`, and return a `WorkspaceHandle`.

**Runtime Control Plane API:**
- Location: `src/quantum_runtime/runtime/__init__.py`
- Triggers: Imports from `src/quantum_runtime/cli.py` and direct unit tests
- Responsibilities: Re-export the stable runtime surface so commands depend on one barrel instead of leaf modules.

**Pack And Replay Inputs:**
- Location: `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/pack.py`
- Triggers: `qrun exec --report-file`, `qrun show --revision`, `qrun compare`, `qrun export`, `qrun inspect`, `qrun pack`
- Responsibilities: Resolve existing runtime objects from disk, validate integrity, and optionally package them into `packs/<revision>/`.

**Automation And CI:**
- Location: `scripts/dev-bootstrap.sh`, `.github/workflows/ci.yml`, `.github/workflows/classiq.yml`
- Triggers: Local bootstrap or verification, GitHub Actions
- Responsibilities: Create `.venv`, install editable dependencies, run Ruff, MyPy, and pytest, and build release artifacts or Classiq-only test coverage.

## Error Handling

**Strategy:** Raise typed domain errors in lower layers, then convert them into schema-versioned payloads or deterministic exit codes at the CLI boundary.

**Patterns:**
- `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/run_manifest.py`, and `src/quantum_runtime/qspec/validation.py` convert parse, provenance, and integrity problems into stable error codes such as `artifact_provenance_invalid`, `run_manifest_integrity_invalid`, and `manual_qspec_required`.
- `src/quantum_runtime/workspace/locking.py`, `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/runtime/export.py`, `src/quantum_runtime/runtime/compare.py`, and `src/quantum_runtime/workspace/baseline.py` wrap lock conflicts and interrupted atomic writes as `WorkspaceConflictError` or `WorkspaceRecoveryRequiredError`.
- `src/quantum_runtime/runtime/contracts.py` plus `src/quantum_runtime/runtime/exit_codes.py` keep CLI failures machine-readable and deterministic.
- Read-only payloads prefer degraded or error result objects with `reason_codes`, `next_actions`, `decision`, and `gate` blocks over uncaught exceptions.

## Cross-Cutting Concerns

**Logging:** `src/quantum_runtime/cli.py` emits user-facing JSON or JSONL; `src/quantum_runtime/workspace/trace.py` appends NDJSON snapshots to both `events.jsonl` and `trace/events.ndjson`; `src/quantum_runtime/runtime/observability.py` standardizes event and gate envelopes.

**Validation:** `src/quantum_runtime/intent/parser.py` validates ingress shape, `src/quantum_runtime/qspec/validation.py` canonicalizes and validates IR, `src/quantum_runtime/runtime/imports.py` validates report and replay integrity, and `src/quantum_runtime/runtime/run_manifest.py` validates immutable manifest consistency.

**Concurrency And Recovery:** `src/quantum_runtime/workspace/locking.py` provides one workspace-wide writer lease, while `src/quantum_runtime/workspace/manifest.py` and related callers use same-directory temp files plus `os.replace()` to make commits atomic; `pending_atomic_write_files()` is used across exec, export, baseline, pack, and doctor flows to fail closed on interrupted writes.

**Provenance And Replay Trust:** `src/quantum_runtime/artifact_provenance.py` canonicalizes artifact paths, `src/quantum_runtime/reporters/writer.py` stores digest-backed replay metadata, and `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/inspect.py`, and `src/quantum_runtime/runtime/compare.py` refuse or degrade inputs when replay trust weakens.

**Policy Gates:** `src/quantum_runtime/runtime/policy.py`, `src/quantum_runtime/runtime/compare.py`, and `src/quantum_runtime/runtime/doctor.py` turn runtime findings into pass, fail, or advisory gates for CI and agents.

**Authentication:** Not detected in the shipped Python runtime under `src/quantum_runtime/`. Optional host integration examples live under `integrations/aionrs/`, and the adjacent Rust crate under `aionrs/` has its own provider auth model.

---

*Architecture analysis: 2026-04-14*
