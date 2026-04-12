# Codebase Structure

**Analysis Date:** 2026-04-12

## Directory Layout

```text
Qcli/
├── src/quantum_runtime/    # Shipped Python package and runtime implementation
├── tests/                  # pytest coverage and golden fixtures
├── docs/                   # Release notes, plans, product docs, integration docs
├── examples/               # Sample intent markdown files
├── integrations/           # Host integration templates and examples
├── scripts/                # Developer bootstrap helpers
├── .github/workflows/      # CI and optional Classiq workflows
├── .planning/codebase/     # Generated codebase map documents
├── .quantum/               # Local generated runtime workspace (ignored)
├── aionrs/                 # Separate ignored Rust project with its own agent rules
├── pyproject.toml          # Packaging, tool config, and console script
└── ARCHITECTURE.md         # Human-written top-level architecture note
```

## Directory Purposes

**`src/quantum_runtime/`:**
- Purpose: Hold all shipped package code.
- Contains: CLI, runtime orchestration, canonical IR, diagnostics, lowerings, workspace helpers, reporters, and backend integrations.
- Key files: `src/quantum_runtime/cli.py`, `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/runtime/control_plane.py`, `src/quantum_runtime/qspec/model.py`

**`src/quantum_runtime/runtime/`:**
- Purpose: Own the public runtime control plane and orchestration seams behind the CLI.
- Contains: Resolution, execution, compare, inspect, export, doctor, pack, backend registry, observability, and contract modules.
- Key files: `src/quantum_runtime/runtime/resolve.py`, `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/compare.py`, `src/quantum_runtime/runtime/doctor.py`

**`src/quantum_runtime/intent/`:**
- Purpose: Handle ingress parsing and rule-based planning.
- Contains: Markdown parsing, structured intent schema, parser entrypoints, and intent-to-`QSpec` lowering.
- Key files: `src/quantum_runtime/intent/parser.py`, `src/quantum_runtime/intent/planner.py`, `src/quantum_runtime/intent/markdown.py`

**`src/quantum_runtime/qspec/`:**
- Purpose: Define and validate the canonical runtime IR.
- Contains: Pydantic models, semantic summaries, validation rules, parameter workflow helpers, and observables helpers.
- Key files: `src/quantum_runtime/qspec/model.py`, `src/quantum_runtime/qspec/validation.py`, `src/quantum_runtime/qspec/semantics.py`

**`src/quantum_runtime/workspace/`:**
- Purpose: Own workspace layout, manifest persistence, baselines, and trace logging.
- Contains: Revision management, path helpers, baseline records, and NDJSON trace support.
- Key files: `src/quantum_runtime/workspace/manager.py`, `src/quantum_runtime/workspace/paths.py`, `src/quantum_runtime/workspace/manifest.py`, `src/quantum_runtime/workspace/trace.py`

**`tests/`:**
- Purpose: Cover CLI contracts, runtime flows, emitters, diagnostics, workspace behavior, packaging, and docs.
- Contains: Mostly flat `test_*.py` modules plus golden artifacts in `tests/golden/`.
- Key files: `tests/test_cli_exec.py`, `tests/test_runtime_compare.py`, `tests/test_workspace_manager.py`, `tests/golden/qiskit_ghz_main.py`

**`docs/`:**
- Purpose: Store release, roadmap, integration, and product documentation.
- Contains: Release notes in `docs/releases/`, archived plans in `docs/plans/`, and product/integration documents.
- Key files: `docs/aionrs-integration.md`, `docs/versioning.md`, `docs/releases/v0.3.1.md`

**`examples/`:**
- Purpose: Provide sample ingress files for local runs and tests.
- Contains: Markdown intent examples for GHZ and QAOA workflows.
- Key files: `examples/intent-ghz.md`, `examples/intent-qaoa-maxcut.md`, `examples/intent-qaoa-maxcut-sweep.md`

**`integrations/`:**
- Purpose: Provide host integration templates rather than shipped runtime code.
- Contains: Example `CLAUDE.md` and hook configuration for `aionrs`.
- Key files: `integrations/aionrs/CLAUDE.md.example`, `integrations/aionrs/hooks.example.toml`

**`.planning/codebase/`:**
- Purpose: Hold generated codebase-reference documents consumed by later GSD workflows.
- Contains: `ARCHITECTURE.md`, `STRUCTURE.md`, and sibling analysis files when other focus areas are mapped.
- Key files: `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`

**`.quantum/`:**
- Purpose: Hold generated runtime workspace state used by local commands.
- Contains: `workspace.json`, `qrun.toml`, artifacts, reports, and event traces.
- Key files: `.quantum/workspace.json`, `.quantum/qrun.toml`, `.quantum/artifacts/qiskit/main.py`, `.quantum/trace/events.ndjson`

**`aionrs/`:**
- Purpose: Hold a separate Rust project and reference integration workspace, not FluxQ package code.
- Contains: Rust sources, its own docs, and its own scoped `AGENTS.md`.
- Key files: `aionrs/Cargo.toml`, `aionrs/src/main.rs`, `aionrs/AGENTS.md`

## Key File Locations

**Entry Points:**
- `pyproject.toml`: Defines package metadata, dependency groups, and the `qrun = "quantum_runtime.cli:main"` console script.
- `src/quantum_runtime/cli.py`: Registers the Typer command tree and handles CLI output modes.
- `scripts/dev-bootstrap.sh`: Boots a local `.venv`, installs dependencies, and runs verification commands.
- `.github/workflows/ci.yml`: Runs Ruff, MyPy, pytest, and release builds in GitHub Actions.
- `.github/workflows/classiq.yml`: Runs optional Classiq-only tests when manually requested.

**Configuration:**
- `pyproject.toml`: Central tool configuration for setuptools, pytest, and Ruff.
- `mypy.ini`: Static type-checker configuration.
- `.gitignore`: Ignores generated paths such as `.quantum/`, `dist/`, `build/`, `.venv/`, `.pytest_cache/`, and `/aionrs/`.
- `.quantum/qrun.toml`: Runtime workspace configuration created by `src/quantum_runtime/workspace/manager.py`.

**Core Logic:**
- `src/quantum_runtime/runtime/resolve.py`: Ingress normalization.
- `src/quantum_runtime/intent/planner.py`: Intent-to-`QSpec` lowering.
- `src/quantum_runtime/qspec/model.py`: Canonical IR definition.
- `src/quantum_runtime/runtime/executor.py`: End-to-end execution pipeline.
- `src/quantum_runtime/runtime/imports.py`: Replay and source resolution.
- `src/quantum_runtime/runtime/compare.py`: Semantic and artifact comparison.
- `src/quantum_runtime/workspace/manager.py`: Workspace lifecycle and revision management.

**Testing:**
- `tests/test_cli_*.py`: CLI contract coverage.
- `tests/test_runtime_*.py`: Runtime resolution and compare coverage.
- `tests/test_workspace_*.py`: Workspace and baseline behavior.
- `tests/golden/`: Golden generated outputs and fixture `QSpec` payloads.

## Naming Conventions

**Files:**
- Use snake_case Python module names under `src/quantum_runtime/`, such as `qiskit_emitter.py`, `backend_registry.py`, and `artifact_provenance.py`.
- Mirror major runtime surfaces in test filenames, such as `tests/test_cli_exec.py`, `tests/test_runtime_compare.py`, and `tests/test_workspace_manager.py`.

**Directories:**
- Use noun-based package folders for stable domains: `intent`, `qspec`, `runtime`, `workspace`, `diagnostics`, `lowering`, `reporters`, `backends`.
- Keep repo support directories explicit and single-purpose: `docs/`, `examples/`, `integrations/`, `scripts/`, `.planning/codebase/`.

## Where to Add New Code

**New Feature:**
- Primary code: Put command wiring in `src/quantum_runtime/cli.py` only when the public CLI changes; put the actual implementation in a focused module under `src/quantum_runtime/runtime/`.
- Tests: Add CLI coverage in `tests/test_cli_<feature>.py` and domain coverage in the nearest matching family such as `tests/test_runtime_<feature>.py` or `tests/test_<domain>.py`.

**New Component/Module:**
- Implementation: Place it beside the owning domain, not in a generic helpers bucket.
- New ingress or parser behavior belongs in `src/quantum_runtime/intent/`.
- New IR semantics or validation belongs in `src/quantum_runtime/qspec/`.
- New export target belongs in `src/quantum_runtime/lowering/`.
- New backend integration belongs in `src/quantum_runtime/backends/` and usually also requires updates in `src/quantum_runtime/runtime/backend_registry.py` and `src/quantum_runtime/runtime/backend_list.py`.
- New workspace artifact or persistence rule belongs in `src/quantum_runtime/workspace/` if it changes layout rules, or `src/quantum_runtime/runtime/` if it changes orchestration only.

**Utilities:**
- Shared helpers: Keep helpers close to the layer that owns them, such as `src/quantum_runtime/runtime/contracts.py` for machine payload utilities or `src/quantum_runtime/artifact_provenance.py` for provenance-only logic.
- Avoid adding a generic `utils.py`; the package already uses domain-specific modules instead.

## Special Directories

**`.quantum/`:**
- Purpose: Local runtime workspace generated by commands such as `qrun init` and `qrun exec`.
- Generated: Yes
- Committed: No

**`.planning/codebase/`:**
- Purpose: Generated codebase-reference documents for GSD planning and execution.
- Generated: Yes
- Committed: Yes

**`aionrs/`:**
- Purpose: Separate Rust project and integration reference checkout inside the repo root.
- Generated: No
- Committed: No

---

*Structure analysis: 2026-04-12*
