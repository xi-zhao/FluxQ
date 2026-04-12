# Phase 1: Canonical Ingress Resolution - Research

**Researched:** 2026-04-12  
**Domain:** Canonical ingress parsing, normalization, and semantic identity for FluxQ runtime inputs  
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- No phase-specific `*-CONTEXT.md` file exists for Phase 1. [VERIFIED: `.planning/phases/01-canonical-ingress-resolution` directory scan 2026-04-12]

### Claude's Discretion
- Research within the repo-wide constraints from `AGENTS.md`; no extra discuss-phase constraints were found. [VERIFIED: AGENTS.md; `.planning/phases/01-canonical-ingress-resolution` directory scan 2026-04-12]

### Deferred Ideas (OUT OF SCOPE)
- None recorded for Phase 1 because no phase context file exists. [VERIFIED: `.planning/phases/01-canonical-ingress-resolution` directory scan 2026-04-12]
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| `INGR-01` | Agent can submit prompt text and receive a normalized machine-readable intent without mutating workspace state. [VERIFIED: `.planning/REQUIREMENTS.md`] | Keep `prompt` on `intent_resolution_from_prompt()`, keep `resolve`/`plan` pure, and add explicit no-mutation tests for prompt/resolve/plan. [VERIFIED: `src/quantum_runtime/runtime/resolve.py`; `src/quantum_runtime/cli.py`; local CLI probe 2026-04-12] |
| `INGR-02` | Agent can resolve prompt, markdown intent, and structured JSON intent into a canonical `QSpec` plus execution plan. [VERIFIED: `.planning/REQUIREMENTS.md`] | Reuse `resolve_runtime_input()` for all executable ingress types and `build_execution_plan_from_resolved()` for dry-run planning; add prompt-path parity tests. [VERIFIED: `src/quantum_runtime/runtime/resolve.py`; `src/quantum_runtime/runtime/control_plane.py`; `tests/test_cli_runtime_gap.py`] |
| `INGR-03` | Semantically equivalent ingress inputs resolve to the same workload identity and semantic hash. [VERIFIED: `.planning/REQUIREMENTS.md`] | Treat normalized `QSpec` semantics as the identity surface, not raw prompt text; add an equivalence matrix that locks both positive and negative cases. [VERIFIED: `src/quantum_runtime/qspec/semantics.py`; `tests/test_cli_runtime_gap.py`; local CLI probe 2026-04-12] |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- Use Python 3.11, `uv`, and local CLI packaging. [VERIFIED: AGENTS.md]
- Keep `QSpec` as the compatible canonical truth layer; do not plan a breaking IR rewrite. [VERIFIED: AGENTS.md]
- Preserve Qiskit-first local execution and OpenQASM 3 as the exchange layer. [VERIFIED: AGENTS.md]
- Keep machine-readable output schema-versioned, stable, and agent-friendly. [VERIFIED: AGENTS.md]
- Prioritize local runtime maturity, replay trust, policy gating, and delivery bundles before broader remote-submit scope. [VERIFIED: AGENTS.md]

## Summary

Phase 1 should be planned as boundary-hardening around an existing ingress pipeline, not as a net-new subsystem. The repo already has a side-effect-free pre-exec path: `prompt` normalizes prompt text into `IntentResolution`, `resolve` turns one ingress selector into a canonical `QSpec` plus plan, and `plan` reuses the same resolved object to emit a dry-run execution plan. [VERIFIED: `src/quantum_runtime/cli.py`; `src/quantum_runtime/runtime/resolve.py`; `src/quantum_runtime/runtime/control_plane.py`]

The first mutating boundary is still `exec`, which initializes a workspace, reserves a revision, writes `intent` and `plan` runtime objects, and only then proceeds into artifact generation and diagnostics. Targeted CLI probes and existing tests show that `prompt`, `resolve`, and `plan` leave the workspace absent, while ingress-related tests in `tests/test_intent_parser.py`, `tests/test_planner.py`, `tests/test_qspec_validation.py`, `tests/test_cli_control_plane.py`, and `tests/test_cli_runtime_gap.py` are currently green. [VERIFIED: `src/quantum_runtime/runtime/executor.py`; `tests/test_cli_control_plane.py`; `tests/test_cli_runtime_gap.py`; targeted pytest run 2026-04-12; local CLI probe 2026-04-12]

The main planning risk is INGR-03 semantics. `workload_id` and `workload_hash` are derived from workload-shape fields, while `semantic_hash` aliases the broader execution hash that also includes normalized constraints and backend/export metadata. In a local probe, markdown and structured JSON produced the same `semantic_hash`, while a prompt produced the same hash only when the markdown omitted extra front matter constraints. [VERIFIED: `src/quantum_runtime/qspec/semantics.py`; local CLI probe 2026-04-12]

**Primary recommendation:** Plan Phase 1 around the existing `resolve_runtime_input()` -> validated `QSpec` -> `build_execution_plan_from_resolved()` pipeline, and spend the new work on explicit equivalence rules and tests rather than on new ingress architecture. [VERIFIED: `src/quantum_runtime/runtime/resolve.py`; `src/quantum_runtime/runtime/control_plane.py`]

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `quantum_runtime.runtime.resolve` | repo `0.3.1` [VERIFIED: `pyproject.toml`] | Produce a single `ResolvedRuntimeInput` from one ingress selector. [VERIFIED: `src/quantum_runtime/runtime/resolve.py`] | `resolve`, `plan`, and `exec` already depend on this boundary, so Phase 1 should extend it instead of creating command-specific resolver branches. [VERIFIED: `src/quantum_runtime/runtime/control_plane.py`; `src/quantum_runtime/runtime/executor.py`] |
| `quantum_runtime.qspec` | repo `0.3.1` [VERIFIED: `pyproject.toml`] | Normalize, validate, and semantically summarize the canonical runtime object. [VERIFIED: `src/quantum_runtime/qspec/model.py`; `src/quantum_runtime/qspec/validation.py`; `src/quantum_runtime/qspec/semantics.py`] | Project constraints already lock `QSpec` as the truth layer, and identity/provenance logic downstream depends on it. [VERIFIED: AGENTS.md; `src/quantum_runtime/qspec/model.py`; `src/quantum_runtime/runtime/compare.py`] |
| `pydantic` | `2.12.5` in repo [VERIFIED: `uv.lock`; local import probe 2026-04-12] | Typed machine-readable contracts for `IntentModel`, `ResolvedRuntimeInput`, `QSpec`, and control-plane payloads. [VERIFIED: `src/quantum_runtime/intent/structured.py`; `src/quantum_runtime/runtime/resolve.py`; `src/quantum_runtime/runtime/contracts.py`] | The repo already uses Pydantic for every ingress and runtime boundary, which keeps parsing and serialization consistent. [VERIFIED: codebase grep 2026-04-12; CITED: https://docs.pydantic.dev/latest/why/] |
| `typer` | `0.24.1` in repo [VERIFIED: `uv.lock`; local import probe 2026-04-12] | Stable CLI command and option surface for `prompt`, `resolve`, `plan`, and `exec`. [VERIFIED: `src/quantum_runtime/cli.py`] | Phase 1 is about preserving one control-plane surface, and the existing CLI already models that surface cleanly through Typer commands and options. [VERIFIED: `src/quantum_runtime/cli.py`; CITED: https://typer.tiangolo.com/tutorial/commands/; CITED: https://typer.tiangolo.com/tutorial/options/] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `PyYAML` | `6.0.3` in repo [VERIFIED: `uv.lock`; local import probe 2026-04-12] | Parse YAML front matter in markdown intent files through `yaml.safe_load()`. [VERIFIED: `src/quantum_runtime/intent/markdown.py`] | Use only at the markdown ingress boundary; do not duplicate YAML parsing elsewhere. [VERIFIED: `src/quantum_runtime/intent/parser.py`; `src/quantum_runtime/intent/markdown.py`] |
| `pytest` | `9.0.2` in repo [VERIFIED: `uv.lock`; `.venv` pytest version 2026-04-12] | Regression coverage for parser, planner, CLI, and semantic equivalence. [VERIFIED: `pyproject.toml`; `tests/`] | Use parametrized equivalence matrices and CLI integration tests for Phase 1. [VERIFIED: `tests/test_planner.py`; `tests/test_cli_runtime_gap.py`; CITED: https://docs.pytest.org/en/stable/how-to/parametrize.html] |
| `qiskit` + `qiskit-aer` | `2.3.1` / `0.17.2` in repo [VERIFIED: `uv.lock`; local import probe 2026-04-12] | Downstream `qiskit-local` capability detection that appears in dry-run plans. [VERIFIED: `src/quantum_runtime/runtime/backend_registry.py`; `src/quantum_runtime/runtime/control_plane.py`] | Keep them as downstream execution dependencies; Phase 1 should not add new Qiskit-specific ingress behavior. [VERIFIED: `src/quantum_runtime/runtime/control_plane.py`; AGENTS.md] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Per-command ingress parsing in `cli.py` | One shared resolver boundary in `resolve_runtime_input()` | The shared resolver already eliminates drift between `resolve`, `plan`, and `exec`; moving logic back into the CLI would duplicate validation and identity handling. [VERIFIED: `src/quantum_runtime/runtime/resolve.py`; `src/quantum_runtime/cli.py`; `src/quantum_runtime/runtime/control_plane.py`] |
| `IntentModel` as the downstream truth layer | `QSpec` as the canonical runtime object | `IntentModel` is intentionally sparse and ingress-shaped, while `QSpec` carries normalized registers, constraints, parameters, observables, runtime metadata, and semantic hashes. [VERIFIED: `src/quantum_runtime/intent/structured.py`; `src/quantum_runtime/qspec/model.py`; AGENTS.md] |
| Raw prompt or markdown text hashing | `summarize_qspec_semantics()` over normalized `QSpec` | Text hashing would treat formatting and source-form differences as identity changes; the current semantic summary separates workload identity from broader execution identity. [VERIFIED: `src/quantum_runtime/qspec/semantics.py`; local CLI probe 2026-04-12] |

Use the repo’s existing bootstrap path; no new dependency installation is required for Phase 1. [VERIFIED: `scripts/dev-bootstrap.sh`; `.github/workflows/ci.yml`]

```bash
./scripts/dev-bootstrap.sh install
```

Repo pins relevant to Phase 1 are `pydantic 2.12.5`, `typer 0.24.1`, `qiskit 2.3.1`, `qiskit-aer 0.17.2`, `PyYAML 6.0.3`, `pytest 9.0.2`, `ruff 0.15.8`, and `mypy 1.20.0`. [VERIFIED: `uv.lock`]

## Architecture Patterns

### Recommended Project Structure
```text
src/quantum_runtime/
├── intent/          # prompt, markdown, and structured JSON parsing into IntentModel
├── runtime/         # canonical resolve/plan surfaces and machine-readable contracts
├── qspec/           # canonical IR, normalization, validation, semantic hashing
└── workspace/       # mutation boundary used only after ingress is resolved
tests/
├── test_intent_parser.py
├── test_planner.py
├── test_qspec_validation.py
├── test_cli_control_plane.py
└── test_cli_runtime_gap.py
```
This is already the effective Phase 1 structure in the repo and should remain the planning backbone. [VERIFIED: codebase grep 2026-04-12]

### Pattern 1: Intent-Only Prompt Normalization
**What:** Keep prompt-only normalization as a pure `IntentResolution` surface that stops before planning or workspace access. [VERIFIED: `src/quantum_runtime/runtime/resolve.py`; `src/quantum_runtime/cli.py`]  
**When to use:** Use this for `INGR-01` and any agent preflight that only needs a normalized machine intent. [VERIFIED: `.planning/REQUIREMENTS.md`; `src/quantum_runtime/cli.py`]  
**Example:**
```python
result = intent_resolution_from_prompt(text)
return IntentResolution(
    source_kind="prompt_text",
    source="<inline>",
    intent=_intent_payload(intent=intent, source_kind="prompt_text", source="<inline>"),
)
```
Source: `src/quantum_runtime/runtime/resolve.py` [VERIFIED: `src/quantum_runtime/runtime/resolve.py`]

### Pattern 2: One Resolver For All Executable Ingress
**What:** Feed markdown, structured JSON, inline prompt text, and later import-backed inputs through `resolve_runtime_input()` so the rest of the runtime only sees `ResolvedRuntimeInput`. [VERIFIED: `src/quantum_runtime/runtime/resolve.py`]  
**When to use:** Use this for `resolve`, `plan`, and `exec`; do not add ingress-specific planning branches in the CLI. [VERIFIED: `src/quantum_runtime/cli.py`; `src/quantum_runtime/runtime/control_plane.py`; `src/quantum_runtime/runtime/executor.py`]  
**Example:**
```python
resolved = resolve_runtime_input(
    workspace_root=workspace_root,
    intent_file=intent_file,
    intent_json_file=intent_json_file,
    qspec_file=qspec_file,
    report_file=report_file,
    revision=revision,
    intent_text=intent_text,
)
plan = build_execution_plan_from_resolved(workspace_root=workspace_root, resolved=resolved)
```
Source: `src/quantum_runtime/runtime/control_plane.py` [VERIFIED: `src/quantum_runtime/runtime/control_plane.py`]

### Pattern 3: Identity Comes From Normalized QSpec Semantics
**What:** Compute `workload_id`, `workload_hash`, and `semantic_hash` from the normalized `QSpec`, not from ingress text. [VERIFIED: `src/quantum_runtime/qspec/semantics.py`]  
**When to use:** Use this whenever the planner needs to reason about INGR-03 or compare whether two ingress forms describe the same runtime object. [VERIFIED: `.planning/REQUIREMENTS.md`; `src/quantum_runtime/qspec/semantics.py`]  
**Example:**
```python
semantics = summarize_qspec_semantics(resolved.qspec)
semantic_hash = semantics["semantic_hash"]
workload_id = semantics["workload_id"]
```
Source: `src/quantum_runtime/runtime/control_plane.py` and `src/quantum_runtime/qspec/semantics.py` [VERIFIED: `src/quantum_runtime/runtime/control_plane.py`; `src/quantum_runtime/qspec/semantics.py`]

### Anti-Patterns to Avoid
- **Workspace mutation during preflight:** `prompt`, `resolve`, and `plan` are currently side-effect-free; do not let Phase 1 move workspace initialization or artifact writes ahead of `exec`. [VERIFIED: `src/quantum_runtime/runtime/executor.py`; `tests/test_cli_control_plane.py`; local CLI probe 2026-04-12]
- **Hashing raw ingress text:** raw prompt or markdown equality is not FluxQ’s identity rule; the canonical object is the normalized `QSpec`. [VERIFIED: AGENTS.md; `src/quantum_runtime/qspec/semantics.py`]
- **Ingress-specific semantic rules in the CLI:** keep parser, planner, and validation logic under `intent/`, `runtime/resolve.py`, and `qspec/`; `cli.py` should stay a thin boundary layer. [VERIFIED: AGENTS.md; `src/quantum_runtime/cli.py`; `.planning/codebase/ARCHITECTURE.md`]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| One-of-many input selection | Custom selector logic per command | The existing exact-one-input guard in `resolve_runtime_input()` | The resolver already enforces a single ingress selector and raises stable errors when callers pass zero or multiple inputs. [VERIFIED: `src/quantum_runtime/runtime/resolve.py`; `src/quantum_runtime/runtime/contracts.py`] |
| Intent schema parsing | Ad hoc dict extraction and string munging | `IntentModel` plus `parse_intent_text()`, `parse_intent_file()`, and `parse_intent_json_file()` | The current parser stack already normalizes defaults for exports, backend preferences, constraints, and shots. [VERIFIED: `src/quantum_runtime/intent/structured.py`; `src/quantum_runtime/intent/parser.py`] |
| YAML front matter parsing | Regex-based YAML splitting | `split_front_matter()` + `yaml.safe_load()` | The repo already isolates markdown front matter parsing in one helper, which is simpler and safer than re-parsing YAML in multiple ingress paths. [VERIFIED: `src/quantum_runtime/intent/markdown.py`] |
| Semantic identity | Text hash or serialized-intent hash | `normalize_qspec()`, `validate_qspec()`, and `summarize_qspec_semantics()` | Identity needs canonical circuit/runtime semantics, not source-form specifics. [VERIFIED: `src/quantum_runtime/qspec/validation.py`; `src/quantum_runtime/qspec/semantics.py`] |

**Key insight:** Phase 1 does not need new libraries; it needs one locked normalization contract and tests that prevent future drift between prompt, markdown, and structured JSON ingress. [VERIFIED: `src/quantum_runtime/runtime/resolve.py`; `tests/test_cli_runtime_gap.py`]

## Common Pitfalls

### Pitfall 1: Treating Workload Identity And Semantic Identity As The Same Thing
**What goes wrong:** Two ingress forms can share the same `workload_id` but still produce different `semantic_hash` values when one form carries extra constraints or backend or export metadata. [VERIFIED: `src/quantum_runtime/qspec/semantics.py`; local CLI probe 2026-04-12]  
**Why it happens:** `workload_hash` is built from subject-shape fields, while `semantic_hash` aliases the broader execution hash over the full semantic summary. [VERIFIED: `src/quantum_runtime/qspec/semantics.py`]  
**How to avoid:** Lock INGR-03 to “same normalized `QSpec` semantics” and add both positive and negative parity tests. [VERIFIED: `.planning/REQUIREMENTS.md`; `tests/test_cli_runtime_gap.py`]  
**Warning signs:** Equal `workload_id` with unequal `semantic_hash`, or prompt-vs-markdown parity failures when markdown front matter adds explicit constraints. [VERIFIED: local CLI probe 2026-04-12]

### Pitfall 2: Letting Dry-Run Commands Cross The Mutation Boundary
**What goes wrong:** A resolver or planner that touches `WorkspaceManager.load_or_init()` would create workspace state before execution begins. [VERIFIED: `src/quantum_runtime/runtime/executor.py`; `src/quantum_runtime/workspace/manager.py`]  
**Why it happens:** The executor already owns workspace initialization, revision reservation, and runtime-object persistence, so copying its behavior into `resolve` or `plan` is an easy refactor mistake. [VERIFIED: `src/quantum_runtime/runtime/executor.py`]  
**How to avoid:** Keep `prompt`, `resolve`, and `plan` on pure control-plane functions and add explicit filesystem assertions in CLI tests. [VERIFIED: `src/quantum_runtime/cli.py`; `tests/test_cli_control_plane.py`; local CLI probe 2026-04-12]  
**Warning signs:** A `.quantum` directory appears after `prompt`, `resolve`, or `plan`, or preflight commands begin reserving revisions. [VERIFIED: local CLI probe 2026-04-12]

### Pitfall 3: Duplicating Ingress Normalization In The CLI
**What goes wrong:** `prompt`, `resolve`, `plan`, and `exec` drift in defaults, error handling, or semantic hashing because each command implements its own parsing path. [VERIFIED: `src/quantum_runtime/cli.py`; `src/quantum_runtime/runtime/resolve.py`]  
**Why it happens:** `cli.py` is large, and it is tempting to solve a new ingress case by branching locally instead of extending `ResolvedRuntimeInput`. [VERIFIED: AGENTS.md; `.planning/codebase/CONCERNS.md`]  
**How to avoid:** Treat `ResolvedRuntimeInput` as the only executable ingress contract and keep CLI changes limited to option wiring and output formatting. [VERIFIED: `src/quantum_runtime/runtime/resolve.py`; `src/quantum_runtime/cli.py`]  
**Warning signs:** A new CLI option requires bespoke planning logic instead of calling `resolve_runtime_input()`. [VERIFIED: `src/quantum_runtime/cli.py`]

### Pitfall 4: Ignoring Backend Capability Effects In Dry-Run Results
**What goes wrong:** Plan and resolve tests assume `status=\"ok\"` in environments where optional or required backends are unavailable. [VERIFIED: `src/quantum_runtime/runtime/control_plane.py`; `src/quantum_runtime/runtime/backend_registry.py`]  
**Why it happens:** `build_execution_plan_from_resolved()` already merges backend capability findings into `blockers` and `advisories`. [VERIFIED: `src/quantum_runtime/runtime/control_plane.py`]  
**How to avoid:** Keep Phase 1 equivalence tests focused on intent, `QSpec`, and identity fields, and assert backend advisories separately. [VERIFIED: `src/quantum_runtime/runtime/control_plane.py`; `tests/test_cli_control_plane.py`]  
**Warning signs:** Optional-backend advisories, such as missing `classiq`, unexpectedly flip resolve or plan payload status in new tests. [VERIFIED: local CLI probe 2026-04-12; local import probe 2026-04-12]

## Code Examples

Verified patterns from the current codebase:

### Normalize Prompt Text Without Planning
```python
result = intent_resolution_from_prompt("Build a 4-qubit GHZ circuit and measure all qubits.")
assert result.source_kind == "prompt_text"
assert result.intent["backend_preferences"] == ["qiskit-local"]
```
Source: `src/quantum_runtime/runtime/resolve.py` and `tests/test_cli_runtime_gap.py` [VERIFIED: `src/quantum_runtime/runtime/resolve.py`; `tests/test_cli_runtime_gap.py`]

### Resolve Markdown Or Structured JSON Through The Same Control-Plane Surface
```python
result = resolve_runtime_object(
    workspace_root=workspace,
    intent_file=intent_file,
)
assert result.qspec["semantic_hash"].startswith("sha256:")
assert result.plan["execution"]["selected_backends"] == ["qiskit-local"]
```
Source: `src/quantum_runtime/runtime/control_plane.py` and `tests/test_cli_runtime_gap.py` [VERIFIED: `src/quantum_runtime/runtime/control_plane.py`; `tests/test_cli_runtime_gap.py`]

### Lock Positive Semantic Parity In Tests
```python
assert json_payload["qspec"]["semantic_hash"] == markdown_payload["qspec"]["semantic_hash"]
assert json_payload["qspec"]["workload_id"] == markdown_payload["qspec"]["workload_id"]
```
Source: `tests/test_cli_runtime_gap.py` [VERIFIED: `tests/test_cli_runtime_gap.py`]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw ingress text as the effective subject identity | Normalized `QSpec` semantics with separate `workload_hash` and `semantic_hash` [VERIFIED: `src/quantum_runtime/qspec/semantics.py`] | Current repo state on 2026-04-12 [VERIFIED: codebase grep 2026-04-12] | Lets downstream compare and replay logic reason about canonical runtime objects instead of source-form noise. [VERIFIED: `src/quantum_runtime/runtime/compare.py`; `src/quantum_runtime/runtime/imports.py`] |
| Parse-and-execute as one indistinguishable step | Split `prompt`, `resolve`, `plan`, and `exec` surfaces with `exec` as the first mutating boundary [VERIFIED: `src/quantum_runtime/cli.py`; `src/quantum_runtime/runtime/executor.py`] | Current repo state on 2026-04-12 [VERIFIED: codebase grep 2026-04-12] | Phase 1 can be planned as ingress-boundary hardening instead of executor redesign. [VERIFIED: `src/quantum_runtime/runtime/control_plane.py`; `src/quantum_runtime/runtime/executor.py`] |

**Deprecated/outdated:**
- Using raw prompt or markdown text as the identity surface is outdated for FluxQ; the repo-standard identity surface is `summarize_qspec_semantics()` over normalized `QSpec`. [VERIFIED: AGENTS.md; `src/quantum_runtime/qspec/semantics.py`]
- Adding new ingress behavior directly inside `cli.py` is outdated for this repo; extend `resolve_runtime_input()` and downstream typed payloads instead. [VERIFIED: `.planning/codebase/ARCHITECTURE.md`; `src/quantum_runtime/runtime/resolve.py`]

## Assumptions Log

All claims in this research were verified or cited in this session; no additional user confirmation is required before planning. [VERIFIED: this research session 2026-04-12]

## Open Questions

1. **What exactly counts as “semantically equivalent” across prompt, markdown, and structured JSON?**
   - What we know: The current implementation computes identity from normalized `QSpec` semantics, and prompt-vs-markdown parity only holds when the normalized semantics match. [VERIFIED: `src/quantum_runtime/qspec/semantics.py`; local CLI probe 2026-04-12]
   - What's unclear: Whether Phase 1 should infer richer constraints from free text or define equivalence strictly as equality after explicit normalization. [VERIFIED: `src/quantum_runtime/intent/parser.py`; `src/quantum_runtime/intent/planner.py`]
   - Recommendation: Lock this definition in the Phase 1 plan and add one positive parity test plus one intentional mismatch test. [VERIFIED: `.planning/REQUIREMENTS.md`; `tests/test_cli_runtime_gap.py`]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 virtualenv | Repo runtime and tests | ✓ [VERIFIED: `.venv` Python probe 2026-04-12] | `3.11.15` [VERIFIED: `.venv` Python probe 2026-04-12] | — |
| System `uv` | Repo-standard developer workflow | ✓ [VERIFIED: `uv --version` 2026-04-12] | `0.11.1` [VERIFIED: `uv --version` 2026-04-12] | `./scripts/dev-bootstrap.sh install` uses `venv` and `pip`. [VERIFIED: `scripts/dev-bootstrap.sh`] |
| `pytest` in `.venv` | Phase 1 regression suite | ✓ [VERIFIED: `.venv` pytest probe 2026-04-12] | `9.0.2` [VERIFIED: `.venv` pytest probe 2026-04-12] | — |
| `qiskit` / `qiskit-aer` in `.venv` | `qiskit-local` capability checks seen in dry-run plans | ✓ [VERIFIED: local import probe 2026-04-12] | `2.3.1` / `0.17.2` [VERIFIED: local import probe 2026-04-12] | — |
| `classiq` in `.venv` | Optional backend advisory path | ✗ [VERIFIED: local import probe 2026-04-12] | — | Treat as optional advisory only; do not make Phase 1 depend on it. [VERIFIED: `src/quantum_runtime/runtime/backend_registry.py`; `src/quantum_runtime/runtime/control_plane.py`] |

**Missing dependencies with no fallback:**
- None for Phase 1. [VERIFIED: local environment probes 2026-04-12]

**Missing dependencies with fallback:**
- `classiq` is absent, but Phase 1 can proceed because the backend is optional and dry-run payloads already model it as an advisory unless requested explicitly. [VERIFIED: `src/quantum_runtime/runtime/backend_registry.py`; `src/quantum_runtime/runtime/control_plane.py`]

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest 9.0.2` [VERIFIED: `.venv` pytest probe 2026-04-12] |
| Config file | `pyproject.toml` [VERIFIED: `pyproject.toml`] |
| Quick run command | `PYTHONPATH=src ./.venv/bin/python -m pytest -q tests/test_intent_parser.py tests/test_planner.py tests/test_qspec_validation.py tests/test_cli_control_plane.py tests/test_cli_runtime_gap.py` [VERIFIED: targeted pytest run 2026-04-12] |
| Full suite command | `./scripts/dev-bootstrap.sh verify` [VERIFIED: `scripts/dev-bootstrap.sh`] |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| `INGR-01` | Prompt text returns normalized machine intent without side effects. [VERIFIED: `.planning/REQUIREMENTS.md`] | CLI integration | `PYTHONPATH=src ./.venv/bin/python -m pytest -q tests/test_cli_runtime_gap.py::test_qrun_prompt_json_returns_normalized_intent_payload` [VERIFIED: `tests/test_cli_runtime_gap.py`] | ✅ [VERIFIED: `tests/test_cli_runtime_gap.py`] |
| `INGR-02` | Prompt, markdown, and JSON resolve through one canonical `QSpec` plus plan surface. [VERIFIED: `.planning/REQUIREMENTS.md`] | CLI integration | `PYTHONPATH=src ./.venv/bin/python -m pytest -q tests/test_cli_runtime_gap.py::test_qrun_resolve_json_normalizes_structured_intent_and_returns_plan tests/test_cli_control_plane.py::test_qrun_plan_json_is_dry_run_and_returns_machine_plan` [VERIFIED: `tests/test_cli_runtime_gap.py`; `tests/test_cli_control_plane.py`] | ✅ [VERIFIED: `tests/test_cli_runtime_gap.py`; `tests/test_cli_control_plane.py`] |
| `INGR-03` | Semantically equivalent ingress forms share `workload_id` and `semantic_hash`. [VERIFIED: `.planning/REQUIREMENTS.md`] | CLI integration | `PYTHONPATH=src ./.venv/bin/python -m pytest -q tests/test_cli_runtime_gap.py::test_qrun_resolve_json_normalizes_structured_intent_and_returns_plan` [VERIFIED: `tests/test_cli_runtime_gap.py`] | ✅ partial [VERIFIED: `tests/test_cli_runtime_gap.py`] |

### Sampling Rate
- **Per task commit:** Run the quick Phase 1 subset above. [VERIFIED: targeted pytest run 2026-04-12]
- **Per wave merge:** Run `./scripts/dev-bootstrap.sh verify`, then capture and triage any existing non-phase `mypy` failures explicitly. [VERIFIED: `scripts/dev-bootstrap.sh`; local `mypy src` run 2026-04-12]
- **Phase gate:** Require the targeted Phase 1 pytest subset green plus explicit sign-off on the current unrelated `mypy` debt until that debt is fixed. [VERIFIED: local `mypy src` run 2026-04-12; `.planning/codebase/CONCERNS.md`]

### Wave 0 Gaps
- [ ] `tests/test_cli_runtime_gap.py` — add explicit assertions that `resolve` leaves the workspace absent, not just `plan`. [VERIFIED: `tests/test_cli_control_plane.py`; local CLI probe 2026-04-12]
- [ ] `tests/test_cli_runtime_gap.py` or `tests/test_runtime_resolve.py` — add prompt-vs-markdown-vs-JSON parity coverage for a case with identical normalized semantics. [VERIFIED: `tests/test_cli_runtime_gap.py`; local CLI probe 2026-04-12]
- [ ] `tests/test_cli_runtime_gap.py` or `tests/test_runtime_resolve.py` — add a negative parity case that intentionally changes constraints and proves `semantic_hash` diverges even when `workload_id` matches. [VERIFIED: `src/quantum_runtime/qspec/semantics.py`; local CLI probe 2026-04-12]
- [ ] `tests/test_runtime_resolve.py` — add direct unit coverage for `expected_exactly_one_input`, `manual_qspec_required`, and `ResolvedRuntimeInput` contents without going through the CLI. [VERIFIED: `src/quantum_runtime/runtime/resolve.py`]
- [ ] Full verification remains red because `mypy src` currently fails in unrelated runtime files. [VERIFIED: local `mypy src` run 2026-04-12; `.planning/codebase/CONCERNS.md`]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no [VERIFIED: `.planning/codebase/ARCHITECTURE.md`] | No authentication layer exists in the core Python runtime. [VERIFIED: `.planning/codebase/ARCHITECTURE.md`] |
| V3 Session Management | no [VERIFIED: `.planning/codebase/ARCHITECTURE.md`] | Local CLI ingress has no session layer. [VERIFIED: `.planning/codebase/ARCHITECTURE.md`] |
| V4 Access Control | no [VERIFIED: `.planning/codebase/ARCHITECTURE.md`] | Phase 1 is local single-process ingress parsing, not multi-user authorization. [VERIFIED: `.planning/codebase/ARCHITECTURE.md`] |
| V5 Input Validation | yes [VERIFIED: `src/quantum_runtime/intent/structured.py`; `src/quantum_runtime/qspec/validation.py`] | Use `IntentModel`, `QSpec`, `normalize_qspec()`, and `validate_qspec()`; never trust raw prompt, markdown, or JSON directly. [VERIFIED: `src/quantum_runtime/intent/parser.py`; `src/quantum_runtime/qspec/validation.py`] |
| V6 Cryptography | yes [VERIFIED: `src/quantum_runtime/qspec/semantics.py`] | Use the existing `hashlib.sha256`-based semantic and workload digests for integrity signaling; do not invent a second hash scheme in Phase 1. [VERIFIED: `src/quantum_runtime/qspec/semantics.py`] |

### Known Threat Patterns for FluxQ ingress

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed JSON, YAML, or markdown input | Tampering | Parse into typed models and raise stable `ImportSourceError` or `QSpecValidationError` codes instead of continuing with partial state. [VERIFIED: `src/quantum_runtime/intent/parser.py`; `src/quantum_runtime/runtime/resolve.py`; `src/quantum_runtime/qspec/validation.py`] |
| Ambiguous multi-input selection | Tampering | Keep the exact-one-input guard in `resolve_runtime_input()` and surface `expected_exactly_one_input`. [VERIFIED: `src/quantum_runtime/runtime/resolve.py`; `src/quantum_runtime/runtime/contracts.py`] |
| Semantic identity spoofing via non-canonical source text | Spoofing | Compare normalized `QSpec` semantics, not prompt text, markdown formatting, or JSON field order. [VERIFIED: `src/quantum_runtime/qspec/semantics.py`; `src/quantum_runtime/qspec/validation.py`] |
| Workspace side effects during preflight | Tampering | Keep workspace mutation inside executor paths only and add no-write tests for preflight commands. [VERIFIED: `src/quantum_runtime/runtime/executor.py`; local CLI probe 2026-04-12] |

## Sources

### Primary (HIGH confidence)
- `AGENTS.md` - product constraints, stack constraints, and architecture rules. [VERIFIED: AGENTS.md]
- `pyproject.toml`, `uv.lock`, `.github/workflows/ci.yml`, `scripts/dev-bootstrap.sh` - package pins, test tooling, and bootstrap or verification commands. [VERIFIED: `pyproject.toml`; `uv.lock`; `.github/workflows/ci.yml`; `scripts/dev-bootstrap.sh`]
- `src/quantum_runtime/runtime/resolve.py` - canonical ingress normalization and prompt-only intent resolution. [VERIFIED: `src/quantum_runtime/runtime/resolve.py`]
- `src/quantum_runtime/runtime/control_plane.py` - dry-run resolve and plan surfaces plus semantic-plan payload shape. [VERIFIED: `src/quantum_runtime/runtime/control_plane.py`]
- `src/quantum_runtime/qspec/model.py`, `src/quantum_runtime/qspec/validation.py`, `src/quantum_runtime/qspec/semantics.py` - canonical runtime object, normalization, validation, and identity hashing. [VERIFIED: `src/quantum_runtime/qspec/model.py`; `src/quantum_runtime/qspec/validation.py`; `src/quantum_runtime/qspec/semantics.py`]
- `src/quantum_runtime/runtime/executor.py` - first mutation boundary and runtime-object persistence. [VERIFIED: `src/quantum_runtime/runtime/executor.py`]
- `tests/test_intent_parser.py`, `tests/test_planner.py`, `tests/test_qspec_validation.py`, `tests/test_cli_control_plane.py`, `tests/test_cli_runtime_gap.py` - current Phase 1 behavior coverage. [VERIFIED: `tests/`]
- Typer docs - command and option structure. [CITED: https://typer.tiangolo.com/tutorial/commands/; CITED: https://typer.tiangolo.com/tutorial/options/]
- Pydantic docs - typed validation and serialization model rationale. [CITED: https://docs.pydantic.dev/latest/why/]
- pytest docs - parametrized test patterns for equivalence matrices. [CITED: https://docs.pytest.org/en/stable/how-to/parametrize.html]

### Secondary (MEDIUM confidence)
- PyPI project pages for repo-pinned verification tools and published release metadata. [CITED: https://pypi.org/project/pytest/9.0.2/; CITED: https://pypi.org/project/ruff/0.15.8/; CITED: https://pypi.org/project/qiskit-aer/0.17.2/]

### Tertiary (LOW confidence)
- None. [VERIFIED: this research session 2026-04-12]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - the phase can reuse the existing repo stack without new libraries, and the relevant pins and commands are verified locally. [VERIFIED: `uv.lock`; `scripts/dev-bootstrap.sh`; local import probe 2026-04-12]
- Architecture: HIGH - the canonical resolver, control-plane, and executor boundaries are already explicit in code and tests. [VERIFIED: `src/quantum_runtime/runtime/resolve.py`; `src/quantum_runtime/runtime/control_plane.py`; `src/quantum_runtime/runtime/executor.py`]
- Pitfalls: HIGH - the biggest risks are directly observable in current hashing behavior, dry-run boundaries, and verification gaps. [VERIFIED: `src/quantum_runtime/qspec/semantics.py`; local CLI probe 2026-04-12; local `mypy src` run 2026-04-12]

**Research date:** 2026-04-12 [VERIFIED: this research session 2026-04-12]  
**Valid until:** 2026-05-12 for repo-state facts; re-check sooner if dependency pins or ingress behavior change. [VERIFIED: repo state 2026-04-12]
