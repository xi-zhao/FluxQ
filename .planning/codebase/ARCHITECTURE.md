# Architecture

**Analysis Date:** 2026-04-18

## Pattern Overview

**Overall:** CLI-first filesystem control plane around a canonical `QSpec` IR and revisioned runtime objects.

**Key Characteristics:**
- `src/quantum_runtime/cli.py` is the only shipped command entrypoint from `pyproject.toml`; it delegates almost all behavior to `src/quantum_runtime/runtime/`.
- Every supported ingress path is normalized through `src/quantum_runtime/runtime/resolve.py` into `ResolvedRuntimeInput` and a validated `QSpec` from `src/quantum_runtime/qspec/model.py`.
- Durable state is file-based under a workspace layout defined by `src/quantum_runtime/workspace/paths.py`, with mutable aliases such as `specs/current.json` and `reports/latest.json` plus immutable history under `specs/history/`, `reports/history/`, `manifests/history/`, `artifacts/history/`, `events/history/`, and `trace/history/`.
- Read-oriented commands such as `status`, `show`, `inspect`, `compare`, `export`, and `pack` reopen persisted runtime objects through `src/quantum_runtime/runtime/imports.py` and `src/quantum_runtime/runtime/run_manifest.py` instead of reparsing prompts.
- Agent-facing behavior is machine-first: schema payloads in `src/quantum_runtime/runtime/contracts.py`, JSONL events in `src/quantum_runtime/runtime/observability.py`, workspace NDJSON logs in `src/quantum_runtime/workspace/trace.py`, and policy gates in `src/quantum_runtime/runtime/policy.py`.

## Layers

**CLI Command Layer:**
- Purpose: Parse shell flags, enforce `--json` and `--jsonl` output rules, call runtime services, and map failures to deterministic exit codes.
- Location: `src/quantum_runtime/cli.py`
- Contains: Typer `app`, `backend_app`, `baseline_app`, `ibm_app`, and handlers for `init`, `version`, `prompt`, `resolve`, `plan`, `status`, `show`, `schema`, `baseline set/show/clear`, `ibm configure`, `bench`, `export`, `pack`, `pack-inspect`, `pack-import`, `exec`, `inspect`, `compare`, `doctor`, and `backend list`.
- Depends on: `src/quantum_runtime/runtime/__init__.py`, `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/runtime/exit_codes.py`, `src/quantum_runtime/runtime/observability.py`, `src/quantum_runtime/workspace/__init__.py`
- Used by: The `qrun` console script declared in `pyproject.toml` and CLI tests such as `tests/test_cli_exec.py`, `tests/test_cli_control_plane.py`, `tests/test_cli_compare.py`, `tests/test_cli_doctor.py`, and `tests/test_cli_ibm_config.py`

**Read-only Control Plane Layer:**
- Purpose: Build plan, resolve, status, show, and schema payloads without mutating workspace state.
- Location: `src/quantum_runtime/runtime/control_plane.py`
- Contains: `PlanResult`, `ResolveResult`, `StatusResult`, `ShowResult`, `SchemaResult`, plus `build_execution_plan()`, `build_execution_plan_from_resolved()`, `resolve_runtime_object()`, `workspace_status()`, `show_run()`, and `schema_contract()`
- Depends on: `src/quantum_runtime/runtime/resolve.py`, `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/compare.py`, `src/quantum_runtime/runtime/doctor.py`, `src/quantum_runtime/runtime/observability.py`, `src/quantum_runtime/runtime/run_manifest.py`, `src/quantum_runtime/workspace/paths.py`
- Used by: `src/quantum_runtime/cli.py` and tests such as `tests/test_cli_control_plane.py` and `tests/test_cli_observability.py`

**Ingress Normalization Layer:**
- Purpose: Accept prompt text, markdown intent, JSON intent, `QSpec`, report file, or revision reference and normalize it into one execution shape.
- Location: `src/quantum_runtime/intent/` and `src/quantum_runtime/runtime/resolve.py`
- Contains: Markdown front-matter parsing in `src/quantum_runtime/intent/markdown.py`, parsing entrypoints in `src/quantum_runtime/intent/parser.py`, `IntentModel` in `src/quantum_runtime/intent/structured.py`, rule-based lowering in `src/quantum_runtime/intent/planner.py`, and `ResolvedRuntimeInput` plus `IntentResolution` in `src/quantum_runtime/runtime/resolve.py`
- Depends on: `src/quantum_runtime/qspec/`, `src/quantum_runtime/errors.py`, and `src/quantum_runtime/runtime/imports.py`
- Used by: `src/quantum_runtime/runtime/control_plane.py`, `src/quantum_runtime/runtime/executor.py`, and ingress tests such as `tests/test_intent_parser.py`, `tests/test_planner.py`, `tests/test_cli_ingress_resolution.py`, and `tests/test_runtime_ingress_resolution.py`

**Canonical IR Layer:**
- Purpose: Hold the single canonical runtime object that every downstream stage compares, exports, validates, and executes.
- Location: `src/quantum_runtime/qspec/`
- Contains: `QSpec`, `Constraints`, `PatternNode`, `MeasureNode`, and runtime metadata in `src/quantum_runtime/qspec/model.py`; normalization and validation in `src/quantum_runtime/qspec/validation.py`; semantic hashing in `src/quantum_runtime/qspec/semantics.py`; parameter and observable helpers in `src/quantum_runtime/qspec/parameter_workflow.py` and `src/quantum_runtime/qspec/observables.py`
- Depends on: Pydantic plus internal helper modules only
- Used by: Ingress lowering, emitters, diagnostics, report writing, import resolution, and tests such as `tests/test_qspec_semantics.py`, `tests/test_qspec_validation.py`, and `tests/test_target_validation.py`

**Execution and Artifact Generation Layer:**
- Purpose: Turn one normalized `QSpec` into revisioned artifacts, diagnostics, backend reports, report JSON, and immutable run manifests.
- Location: `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/lowering/`, `src/quantum_runtime/diagnostics/`, `src/quantum_runtime/backends/`, and `src/quantum_runtime/reporters/`
- Contains: Execution orchestration in `src/quantum_runtime/runtime/executor.py`; Qiskit, OpenQASM 3, and Classiq emitters in `src/quantum_runtime/lowering/`; local simulation, resource estimation, diagrams, transpile validation, and benchmarks in `src/quantum_runtime/diagnostics/`; optional Classiq synthesis in `src/quantum_runtime/backends/classiq_backend.py`; report writing and summary generation in `src/quantum_runtime/reporters/writer.py` and `src/quantum_runtime/reporters/summary.py`
- Depends on: `src/quantum_runtime/runtime/resolve.py`, `src/quantum_runtime/qspec/`, `src/quantum_runtime/workspace/`, and external Qiskit or Classiq packages
- Used by: `qrun exec`, `qrun bench`, `qrun doctor`, and tests such as `tests/test_cli_exec.py`, `tests/test_diagnostics.py`, `tests/test_qiskit_emitter.py`, `tests/test_qasm_export.py`, `tests/test_classiq_backend.py`, and `tests/test_report_writer.py`

**Import, Replay, Comparison, and Delivery Layer:**
- Purpose: Reopen persisted runs as trusted runtime inputs, enforce replay integrity, and compute compare, inspect, export, baseline, and pack views.
- Location: `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/compare.py`, `src/quantum_runtime/runtime/inspect.py`, `src/quantum_runtime/runtime/export.py`, `src/quantum_runtime/runtime/pack.py`, `src/quantum_runtime/runtime/policy.py`, `src/quantum_runtime/artifact_provenance.py`
- Contains: `ImportReference`, `ImportResolution`, `WorkspaceBaselineResolution`, replay-integrity checks, compare deltas and verdicts, inspect summaries, artifact re-export, portable revision bundles, and policy gates
- Depends on: `src/quantum_runtime/runtime/run_manifest.py`, `src/quantum_runtime/workspace/`, `src/quantum_runtime/qspec/`, and emitters or diagnostics where needed
- Used by: CLI commands `compare`, `inspect`, `export`, `baseline`, `pack`, `pack-inspect`, `pack-import`, `show`, and `status`, plus tests such as `tests/test_runtime_imports.py`, `tests/test_runtime_compare.py`, `tests/test_cli_export.py`, `tests/test_cli_pack_import.py`, `tests/test_pack_bundle.py`, and `tests/test_workspace_baseline.py`

**Backend Capability and Remote Readiness Layer:**
- Purpose: Describe available runtime backends, persist non-secret IBM access references, and surface remote-readiness state without performing remote submit.
- Location: `src/quantum_runtime/runtime/backend_registry.py`, `src/quantum_runtime/runtime/backend_list.py`, `src/quantum_runtime/runtime/ibm_access.py`, `src/quantum_runtime/runtime/doctor.py`
- Contains: Backend dependency descriptors, `list_backends()`, IBM profile persistence and validation, `build_ibm_service()`, and doctor checks that merge dependency health with workspace state
- Depends on: `src/quantum_runtime/workspace/`, optional `qiskit-ibm-runtime`, and TOML parsing through `tomllib`
- Used by: `qrun backend list`, `qrun ibm configure`, `qrun doctor --ci`, and tests such as `tests/test_cli_backend_list.py`, `tests/test_cli_ibm_config.py`, and `tests/test_cli_doctor.py`

**Workspace Persistence Layer:**
- Purpose: Define the on-disk source of truth, allocate revisions, coordinate writers, and keep append-only history coherent.
- Location: `src/quantum_runtime/workspace/` plus `src/quantum_runtime/runtime/run_manifest.py`
- Contains: Workspace init and load in `src/quantum_runtime/workspace/manager.py`, path helpers in `src/quantum_runtime/workspace/paths.py`, revision manifest and atomic file helpers in `src/quantum_runtime/workspace/manifest.py`, baseline storage in `src/quantum_runtime/workspace/baseline.py`, writer lease management in `src/quantum_runtime/workspace/locking.py`, trace logging in `src/quantum_runtime/workspace/trace.py`, and immutable per-run manifests in `src/quantum_runtime/runtime/run_manifest.py`
- Depends on: Filesystem, Pydantic, and runtime contracts only
- Used by: Every mutating command and every replay or import flow

## Data Flow

**Resolve and Plan Flow:**

1. `src/quantum_runtime/cli.py` accepts exactly one input selector for `qrun prompt`, `qrun resolve`, or `qrun plan`.
2. `src/quantum_runtime/runtime/resolve.py` parses the source through `src/quantum_runtime/intent/parser.py` or reopens an existing run through `src/quantum_runtime/runtime/imports.py`.
3. `src/quantum_runtime/intent/planner.py` lowers parsed intent into `QSpec`, or `src/quantum_runtime/runtime/resolve.py` validates a `QSpec` or report-derived one directly.
4. `src/quantum_runtime/runtime/control_plane.py` builds `IntentResolution`, `ResolveResult`, or `PlanResult`, including backend advisories from `src/quantum_runtime/runtime/doctor.py`.

**State Management:**
- This path is read-only. It does not reserve a revision or promote aliases inside `.quantum/`.

**Execution and Revision Commit Flow:**

1. One `exec` handler in `src/quantum_runtime/cli.py` calls `execute_intent()`, `execute_intent_text()`, `execute_intent_json()`, `execute_qspec()`, or `execute_report()` in `src/quantum_runtime/runtime/executor.py`.
2. `src/quantum_runtime/workspace/manager.py` loads or creates the workspace, then `src/quantum_runtime/workspace/locking.py` acquires `.workspace.lock`.
3. `WorkspaceHandle.reserve_revision()` bumps `workspace.json`, then `src/quantum_runtime/runtime/executor.py` writes `intents/history/`, `plans/history/`, `specs/history/`, optional `intents/history/<revision>.md`, and staged event logs under `cache/`.
4. Emitters and diagnostics write revision-scoped artifacts under `artifacts/history/<revision>/`; `src/quantum_runtime/reporters/writer.py` writes the report with artifact provenance and replay-integrity digests.
5. `src/quantum_runtime/runtime/run_manifest.py` writes `manifests/history/<revision>.json`, event snapshots are copied into `events/history/` and `trace/history/`, and alias files such as `specs/current.json`, `reports/latest.json`, `manifests/latest.json`, `artifacts/qiskit/main.py`, `artifacts/qasm/main.qasm`, and `figures/circuit.png` are promoted.

**State Management:**
- History files are revision-stable. Alias files are mutable pointers to the currently selected revision described by `workspace.json`.

**Replay, Baseline, Compare, and Delivery Flow:**

1. `src/quantum_runtime/runtime/imports.py` resolves current workspace state, a report file, or a historical revision into `ImportResolution`.
2. That resolution re-derives report and `QSpec` hashes, canonical artifact provenance through `src/quantum_runtime/artifact_provenance.py`, run-manifest linkage through `src/quantum_runtime/runtime/run_manifest.py`, and replay-integrity state.
3. `src/quantum_runtime/workspace/baseline.py` stores approved state in `baselines/current.json`; `src/quantum_runtime/runtime/compare.py` compares baseline vs current or any two `ImportResolution` objects.
4. `src/quantum_runtime/runtime/inspect.py`, `src/quantum_runtime/runtime/export.py`, and `src/quantum_runtime/runtime/pack.py` reuse the same resolved runtime object instead of re-running planners.
5. Derived projections such as `compare/latest.json`, `benchmarks/latest.json`, `doctor/latest.json`, and `packs/<revision>/` are written after validation, but the replayable source of record remains the revision-scoped report, `QSpec`, run manifest, and artifact history.

**State Management:**
- Compare, doctor, benchmark, and pack outputs are projections. The durable runtime object is the revision set under `specs/history/`, `reports/history/`, `manifests/history/`, `artifacts/history/`, `events/history/`, and `trace/history/`.

**IBM Readiness Flow:**

1. `qrun ibm configure` writes a non-secret `[remote.ibm]` profile into `qrun.toml` through `src/quantum_runtime/runtime/ibm_access.py`.
2. `src/quantum_runtime/runtime/backend_list.py` combines static backend descriptors from `src/quantum_runtime/runtime/backend_registry.py` with resolved IBM access state.
3. `src/quantum_runtime/runtime/doctor.py` uses that same IBM access resolution to produce readiness findings and CI-facing reason codes.
4. `build_ibm_service()` in `src/quantum_runtime/runtime/ibm_access.py` constructs the runtime SDK client only after configuration is validated and the external token source is available.

**State Management:**
- IBM secrets are not stored under `.quantum/`; only non-secret references such as `credential_mode`, `instance`, `token_env`, or `saved_account_name` are persisted in `qrun.toml`.

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
- Purpose: Centralize where mutable aliases, immutable history, revision counters, and bootstrap files live.
- Examples: `src/quantum_runtime/workspace/manager.py`, `src/quantum_runtime/workspace/paths.py`, `src/quantum_runtime/workspace/manifest.py`
- Pattern: Small filesystem service objects; runtime code asks them for canonical locations instead of constructing raw strings.

**ImportResolution / WorkspaceBaselineResolution:**
- Purpose: Reopen persisted runtime state with provenance, semantic summaries, replay-integrity verdicts, and artifact locations.
- Examples: `src/quantum_runtime/runtime/imports.py`
- Pattern: Structured read models reused by compare, inspect, export, baseline, and pack flows.

**RunManifestArtifact / RunReportArtifact:**
- Purpose: Separate execution evidence from the immutable join record that ties one revision's `QSpec`, report, intent, plan, and events together.
- Examples: `src/quantum_runtime/runtime/run_manifest.py`, `src/quantum_runtime/reporters/writer.py`
- Pattern: Schema-versioned persisted JSON contracts written per revision and later reopened by import and control-plane logic.

**JsonlEvent / TraceEvent:**
- Purpose: Give agents incremental, machine-readable progress without scraping prose logs.
- Examples: `src/quantum_runtime/runtime/observability.py`, `src/quantum_runtime/workspace/trace.py`
- Pattern: JSONL or NDJSON envelopes with stable `phase`, `status`, `error_code`, and `payload` fields.

**IbmAccessProfile / IbmAccessResolution:**
- Purpose: Separate non-secret IBM workspace configuration from runtime-only credential material.
- Examples: `src/quantum_runtime/runtime/ibm_access.py`
- Pattern: Pydantic models persisted in `qrun.toml` and resolved into readiness or error states before remote SDK construction.

## Entry Points

**CLI Binary:**
- Location: `pyproject.toml`, `src/quantum_runtime/cli.py`
- Triggers: `qrun ...` shell invocations
- Responsibilities: Parse command arguments, select output mode, emit JSON or JSONL payloads, and translate runtime exceptions into structured failures and exit codes.

**Workspace Bootstrap:**
- Location: `src/quantum_runtime/workspace/manager.py`, `src/quantum_runtime/workspace/paths.py`
- Triggers: `qrun init` and any mutating command that calls `WorkspaceManager.load_or_init()`
- Responsibilities: Create the workspace directory skeleton, seed `workspace.json`, `qrun.toml`, `events.jsonl`, and `trace/events.ndjson`, and return a `WorkspaceHandle`.

**Runtime API Barrel:**
- Location: `src/quantum_runtime/runtime/__init__.py`
- Triggers: Imports from `src/quantum_runtime/cli.py` and direct unit tests
- Responsibilities: Re-export the stable runtime surface so the CLI depends on one barrel instead of many leaf imports.

**Pack and Replay Inputs:**
- Location: `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/pack.py`
- Triggers: `qrun exec --report-file`, `qrun show --revision`, `qrun compare`, `qrun export`, `qrun inspect`, `qrun pack`, `qrun pack-inspect`, `qrun pack-import`
- Responsibilities: Resolve existing runtime objects from disk, validate integrity, and optionally package them into `packs/<revision>/`.

**Developer Automation:**
- Location: `scripts/dev-bootstrap.sh`, `.github/workflows/ci.yml`, `.github/workflows/classiq.yml`
- Triggers: Local bootstrap or verification and GitHub Actions
- Responsibilities: Install dependencies, run Ruff, MyPy, and pytest, and build release artifacts or optional Classiq coverage.

## Error Handling

**Strategy:** Raise typed domain errors in lower layers, then convert them into schema-versioned payloads or deterministic exit codes at the CLI boundary.

**Patterns:**
- `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/run_manifest.py`, and `src/quantum_runtime/qspec/validation.py` convert parse, provenance, and integrity problems into stable error codes such as `invalid_qspec`, `manual_qspec_required`, `run_manifest_integrity_invalid`, and replay-integrity failures.
- `src/quantum_runtime/workspace/locking.py`, `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/runtime/export.py`, `src/quantum_runtime/runtime/compare.py`, and `src/quantum_runtime/workspace/baseline.py` wrap lock conflicts and interrupted atomic writes as `WorkspaceConflictError` or `WorkspaceRecoveryRequiredError`.
- `src/quantum_runtime/runtime/contracts.py` plus `src/quantum_runtime/runtime/exit_codes.py` keep CLI failures machine-readable and deterministic.
- Read-oriented payloads prefer degraded or error result objects with `reason_codes`, `next_actions`, `decision`, and `gate` blocks over uncaught exceptions.

## Cross-Cutting Concerns

**Logging:** `src/quantum_runtime/cli.py` emits user-facing JSON or JSONL, `src/quantum_runtime/runtime/observability.py` defines machine event envelopes, and `src/quantum_runtime/workspace/trace.py` persists command progress into both `events.jsonl` and `trace/events.ndjson`.

**Validation:** `src/quantum_runtime/intent/parser.py` validates ingress shape, `src/quantum_runtime/qspec/validation.py` canonicalizes and validates IR, `src/quantum_runtime/runtime/imports.py` validates report and replay integrity, and `src/quantum_runtime/runtime/run_manifest.py` validates immutable manifest consistency.

**Authentication:** `src/quantum_runtime/runtime/ibm_access.py` persists only non-secret IBM profile references in `qrun.toml` and requires secrets to remain external via environment variables or saved IBM accounts.

**Concurrency and Recovery:** `src/quantum_runtime/workspace/locking.py` provides one workspace-wide writer lease, while `src/quantum_runtime/workspace/manifest.py` and its callers use same-directory temp files plus `os.replace()` to make commits atomic; `pending_atomic_write_files()` is used across exec, export, baseline, compare, doctor, and pack flows to fail closed on interrupted writes.

**Provenance and Replay Trust:** `src/quantum_runtime/artifact_provenance.py` canonicalizes artifact paths, `src/quantum_runtime/reporters/writer.py` stores digest-backed replay metadata, and `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/inspect.py`, and `src/quantum_runtime/runtime/compare.py` degrade or reject inputs when replay trust weakens.

**Policy Gates:** `src/quantum_runtime/runtime/policy.py`, `src/quantum_runtime/runtime/compare.py`, and `src/quantum_runtime/runtime/doctor.py` turn runtime findings into pass, fail, or advisory gates for CI and agents.

---

*Architecture analysis: 2026-04-18*
