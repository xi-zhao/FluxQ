# Phase 10: Canonical Remote Submit & Attempt Records - Research

**Researched:** 2026-04-18  
**Domain:** Canonical IBM submit flow and durable remote attempt persistence  
**Confidence:** MEDIUM-HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

No `*-CONTEXT.md` exists in `.planning/phases/10-canonical-remote-submit-attempt-records/`, so there are no discuss-phase decisions to copy verbatim. [VERIFIED: phase init `node "/Users/xizhao/.codex/get-shit-done/bin/gsd-tools.cjs" init phase-op "10"`; phase-dir scan]

### Locked Decisions

- IBM Quantum Platform only, job mode only, trust-first remote execution. [VERIFIED: local file `.planning/STATE.md`; local file `.planning/ROADMAP.md`; local file `.planning/REQUIREMENTS.md`]
- Remote attempt identity must remain separate from immutable terminal revision identity. [VERIFIED: local file `.planning/STATE.md`]
- Remote submission must require explicit instance and backend selection; no implicit auto-selection or silent retry. [VERIFIED: local file `.planning/STATE.md`; local file `.planning/REQUIREMENTS.md`]
- Secrets must stay outside `.quantum`; FluxQ persists references and provenance, not credentials. [VERIFIED: local file `.planning/STATE.md`; local file `src/quantum_runtime/runtime/ibm_access.py`]
- Canonical ingress must stay compatible with the current prompt, markdown, JSON intent, `QSpec`, and trusted report-backed surfaces; no remote-only IR rewrite. [VERIFIED: local file `AGENTS.md`; local file `.planning/ROADMAP.md`; local file `.planning/REQUIREMENTS.md`; local file `src/quantum_runtime/runtime/resolve.py`]

### Claude's Discretion

- Phase 10 still has freedom on CLI shape and module split because only Phase 09 IBM readiness surfaces are shipped today. [VERIFIED: local file `.agents/skills/fluxq-cli/SKILL.md`; local file `src/quantum_runtime/cli.py`]
- Phase 10 can choose whether to create only a durable attempt store now or also create a non-terminal submission revision now; the repo has not locked that choice yet. [VERIFIED: local file `.planning/ROADMAP.md`; local file `.planning/STATE.md`] [ASSUMED]
- Phase 10 can choose the narrowest provider adapter seam as long as it reuses `resolve_ibm_access()` and `build_ibm_service()`. [VERIFIED: local file `.planning/phases/09-ibm-access-backend-readiness/09-01-PLAN.md`; local file `src/quantum_runtime/runtime/ibm_access.py`; local file `tests/test_cli_ibm_config.py`]

### Deferred Ideas (OUT OF SCOPE)

- Reopen, poll, and cancel remote jobs without resubmission; that is Phase 11. [VERIFIED: local file `.planning/ROADMAP.md`; local file `.planning/REQUIREMENTS.md`]
- Terminal result materialization into immutable local revision artifacts; that is Phase 12. [VERIFIED: local file `.planning/ROADMAP.md`; local file `.planning/REQUIREMENTS.md`]
- Full fail-closed remote JSONL lifecycle/recovery contract; that is Phase 13. [VERIFIED: local file `.planning/ROADMAP.md`; local file `.planning/REQUIREMENTS.md`]
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REMT-01 | User can submit a canonical run to IBM Quantum Platform through the same ingress and `QSpec` surface used locally | Reuse `resolve_runtime_input()` and the existing one-input invariant, then route the resolved `QSpec` into a new IBM submit adapter rather than inventing a remote-only parser. [VERIFIED: local file `src/quantum_runtime/runtime/resolve.py`; local file `src/quantum_runtime/runtime/executor.py`; local file `tests/test_cli_exec.py`] |
| REMT-02 | User receives a persisted FluxQ remote attempt record with provider job handle, backend, instance, and submit-time provenance immediately after successful submission | Add a dedicated remote-attempt store under `.quantum/remote/attempts/` with atomic writes, Pydantic models, and canonical `QSpec` snapshot files; keep it separate from report/revision history. [VERIFIED: local file `.planning/STATE.md`; local file `src/quantum_runtime/workspace/manifest.py`; local file `src/quantum_runtime/workspace/paths.py`; local file `src/quantum_runtime/runtime/run_manifest.py`] [ASSUMED] |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Repository root `./CLAUDE.md` does not exist, so there are no additional CLAUDE-level project directives to enforce. [VERIFIED: repo-root file check]

## Summary

Phase 10 should stay narrow: reuse the current canonical ingress path, submit through the existing IBM access seam, and persist a durable non-terminal remote attempt record without changing FluxQ's immutable revision/report contract yet. [VERIFIED: local file `.planning/ROADMAP.md`; local file `.planning/REQUIREMENTS.md`; local file `src/quantum_runtime/runtime/resolve.py`; local file `src/quantum_runtime/runtime/ibm_access.py`] [ASSUMED]

The strongest repo-first fit is to add a provider-specific `qrun ibm submit` flow that mirrors the existing mutually-exclusive input selectors used by `qrun exec`, calls `resolve_runtime_input()`, performs IBM-target preflight, submits through a new IBM adapter layered on `build_ibm_service()`, and then writes an attempt record under `.quantum/remote/attempts/<attempt_id>/`. [VERIFIED: local file `src/quantum_runtime/cli.py`; local file `src/quantum_runtime/runtime/resolve.py`; local file `src/quantum_runtime/runtime/ibm_access.py`; local file `tests/test_cli_ibm_config.py`] [ASSUMED]

Phase 10 should not mutate `workspace.json.current_revision`, `reports/history/`, or `manifests/history/` on submit. Those artifacts are the current trust boundary for completed local runs, while the roadmap assigns terminal remote artifact creation to Phase 12. [VERIFIED: local file `.planning/STATE.md`; local file `.planning/ROADMAP.md`; local file `src/quantum_runtime/workspace/manifest.py`; local file `src/quantum_runtime/runtime/run_manifest.py`; local file `src/quantum_runtime/reporters/writer.py`] [ASSUMED]

**Primary recommendation:** Implement `qrun ibm submit` as an additive CLI command that reuses `resolve_runtime_input()`, submits through a new IBM primitive adapter built on `build_ibm_service()`, and persists an attempt-only record plane under `.quantum/remote/attempts/` without creating a non-terminal revision yet. [VERIFIED: local file `src/quantum_runtime/cli.py`; local file `src/quantum_runtime/runtime/resolve.py`; local file `src/quantum_runtime/runtime/ibm_access.py`; local file `.planning/ROADMAP.md`] [ASSUMED]

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `qiskit-ibm-runtime` | repo pin `~=0.46`; latest `0.46.1` via registry lookup. [VERIFIED: local file `pyproject.toml`; VERIFIED: `python3 -m pip index versions qiskit-ibm-runtime`] | Official IBM submit and job-handle client already implied by Phase 09's `build_ibm_service()` seam. [VERIFIED: local file `src/quantum_runtime/runtime/ibm_access.py`] | Phase 09 already standardized IBM access on this SDK, so Phase 10 should extend that seam instead of introducing REST or a second client. [VERIFIED: local file `.planning/phases/09-ibm-access-backend-readiness/09-01-PLAN.md`; local file `src/quantum_runtime/runtime/ibm_access.py`] |
| `qiskit` | repo env `2.3.1`; latest `2.4.0` via registry lookup. [VERIFIED: `uv run python -c 'import qiskit; print(qiskit.__version__)'`; VERIFIED: `python3 -m pip index versions qiskit`] | Canonical circuit construction still flows through `build_qiskit_circuit()`. [VERIFIED: local file `src/quantum_runtime/lowering/qiskit_emitter.py`; local file `src/quantum_runtime/diagnostics/transpile_validate.py`] | Remote submit should stay Qiskit-first because current `QSpec` lowering and diagnostics already depend on Qiskit circuits. [VERIFIED: local file `AGENTS.md`; local file `src/quantum_runtime/lowering/qiskit_emitter.py`; local file `src/quantum_runtime/runtime/executor.py`] |
| `Typer` | repo env `0.24.1`; latest `0.24.1` via registry lookup. [VERIFIED: `uv run python -c 'import typer; print(typer.__version__)'`; VERIFIED: `python3 -m pip index versions typer`] | Existing command routing, JSON output, and provider-specific subcommands all live in `cli.py`. [VERIFIED: local file `src/quantum_runtime/cli.py`] | The narrowest additive surface is a new IBM subcommand, not a new CLI framework. [VERIFIED: local file `src/quantum_runtime/cli.py`] [ASSUMED] |
| `Pydantic` | repo env `2.12.5`; latest `2.13.2` via registry lookup. [VERIFIED: `uv run python -c 'import pydantic; print(pydantic.__version__)'`; VERIFIED: `python3 -m pip index versions pydantic`] | Current machine contracts, manifest payloads, and IBM access models are all Pydantic-first. [VERIFIED: local file `src/quantum_runtime/runtime/contracts.py`; local file `src/quantum_runtime/runtime/run_manifest.py`; local file `src/quantum_runtime/runtime/ibm_access.py`] | Attempt records should follow the same schema-versioned Pydantic style. [VERIFIED: local file `src/quantum_runtime/runtime/contracts.py`; local file `src/quantum_runtime/runtime/ibm_access.py`] [ASSUMED] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `qiskit-aer` | repo env `0.17.2`; latest `0.17.2` via registry lookup. [VERIFIED: `uv run python -c 'import qiskit_aer; print(qiskit_aer.__version__)'`; VERIFIED: `python3 -m pip index versions qiskit-aer`] | Local baseline simulation remains the parity reference for canonical ingress tests and provider-mock tests. [VERIFIED: local file `src/quantum_runtime/diagnostics/simulate.py`] | Keep local simulation in tests; do not make live IBM submit a required fast-path test. [VERIFIED: local file `tests/test_cli_exec.py`; local file `tests/test_diagnostics.py`] [ASSUMED] |
| `pytest` | repo env `9.0.2`; latest `9.0.3` via registry lookup. [VERIFIED: `uv run pytest --version`; VERIFIED: `python3 -m pip index versions pytest`] | Current CLI and runtime regression harness. [VERIFIED: local file `pyproject.toml`; local file `.github/workflows/ci.yml`] | Follow the existing `tests/test_cli_*.py` and `tests/test_runtime_*.py` pattern for submit and attempt-store coverage. [VERIFIED: local file `tests/test_cli_ibm_config.py`; local file `tests/test_cli_backend_list.py`; local file `tests/test_runtime_workspace_safety.py`] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `qrun exec --remote ...` | `qrun ibm submit ...` | `qrun ibm submit` is narrower and matches the existing provider-specific IBM namespace, while `exec --remote` would widen the already-large local executor too early. [VERIFIED: local file `src/quantum_runtime/cli.py`; local file `src/quantum_runtime/runtime/executor.py`; local file `.agents/skills/fluxq-cli/SKILL.md`] [ASSUMED] |
| Writing submit state into `reports/history/` and `manifests/history/` immediately | Writing a dedicated attempt store under `.quantum/remote/attempts/` | A separate attempt store keeps Phase 10 aligned with the roadmap, which reserves immutable local artifact creation for Phase 12. [VERIFIED: local file `.planning/ROADMAP.md`; local file `src/quantum_runtime/workspace/manifest.py`; local file `src/quantum_runtime/runtime/run_manifest.py`] [ASSUMED] |
| Reusing `validate_target_constraints()` as the exact IBM submit preflight | Adding a new IBM-target preflight helper | `validate_target_constraints()` only handles generic transpile kwargs and does not know about provider backends or observable layout projection. [VERIFIED: local file `src/quantum_runtime/diagnostics/transpile_validate.py`; local file `src/quantum_runtime/qspec/observables.py`] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/primitives-examples] |

**Installation:**
```bash
uv sync --extra dev --extra ibm
```

**Version verification:**  
- `qiskit-ibm-runtime`: repo pin `~=0.46`; latest `0.46.1`. [VERIFIED: local file `pyproject.toml`; VERIFIED: `python3 -m pip index versions qiskit-ibm-runtime`]  
- `qiskit`: repo env `2.3.1`; latest `2.4.0`. [VERIFIED: `uv run python -c 'import qiskit; print(qiskit.__version__)'`; VERIFIED: `python3 -m pip index versions qiskit`]  
- `qiskit-aer`: repo env and latest both `0.17.2`. [VERIFIED: `uv run python -c 'import qiskit_aer; print(qiskit_aer.__version__)'`; VERIFIED: `python3 -m pip index versions qiskit-aer`]  

## Architecture Patterns

### Recommended Project Structure

```text
src/
├── quantum_runtime/
│   ├── cli.py                        # add `qrun ibm submit` beside `qrun ibm configure`
│   ├── runtime/
│   │   ├── ibm_access.py            # keep auth/service construction seam unchanged
│   │   ├── ibm_submit.py            # new IBM submit adapter and preflight
│   │   └── remote_attempts.py       # attempt models + atomic persistence helpers
│   └── workspace/
│       └── paths.py                 # add `.quantum/remote/attempts/...` helpers
└── tests/
    ├── test_cli_ibm_submit.py       # canonical ingress reuse + submit JSON contract
    └── test_runtime_remote_attempts.py
```
[VERIFIED: local file `src/quantum_runtime/cli.py`; local file `src/quantum_runtime/runtime/ibm_access.py`; local file `src/quantum_runtime/workspace/paths.py`; local file `tests/test_cli_ibm_config.py`; local file `tests/test_cli_backend_list.py`] [ASSUMED]

### Pattern 1: Reuse Canonical Ingress Exactly Once

**What:** `qrun ibm submit` should accept the same mutually-exclusive inputs as `qrun exec` and call `resolve_runtime_input()` first, so remote submit consumes the same `ResolvedRuntimeInput` and canonical `QSpec`. [VERIFIED: local file `src/quantum_runtime/runtime/resolve.py`; local file `src/quantum_runtime/runtime/executor.py`; local file `tests/test_cli_exec.py`]

**When to use:** Always; Phase 10 should add a remote submit consumer, not a second ingress parser. [VERIFIED: local file `.planning/REQUIREMENTS.md`; local file `src/quantum_runtime/runtime/resolve.py`]

**Example:**
```python
# Source: src/quantum_runtime/runtime/resolve.py
resolved = resolve_runtime_input(
    workspace_root=workspace_root,
    intent_text=intent_text,
)
qspec = resolved.qspec
semantic_hash = summarize_qspec_semantics(qspec)["semantic_hash"]
```
[VERIFIED: local file `src/quantum_runtime/runtime/resolve.py`; local file `src/quantum_runtime/qspec/semantics.py`]

### Pattern 2: Keep IBM SDK Usage Behind One Submit Seam

**What:** CLI code should not import IBM primitives directly. A new `ibm_submit.py` helper should receive `ResolvedRuntimeInput`, call `resolve_ibm_access()` and `build_ibm_service()`, select `SamplerV2` or `EstimatorV2`, and return a sanitized submit receipt. [VERIFIED: local file `src/quantum_runtime/runtime/ibm_access.py`; local file `src/quantum_runtime/cli.py`] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/execution-modes] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/primitives-examples] [ASSUMED]

**When to use:** For submit only; keep backend inventory in `backend_list.py` and lifecycle reopen/poll/cancel out of this helper until Phase 11. [VERIFIED: local file `src/quantum_runtime/runtime/backend_list.py`; local file `.planning/ROADMAP.md`]

**Example:**
```python
# Recommended additive seam combining current repo seams.
resolution = resolve_ibm_access(workspace_root=workspace_root)
service = build_ibm_service(resolution=resolution)
backend = service.backend(backend_name)
job = submit_ibm_job(service=service, backend=backend, resolved=resolved)
job_id = job.job_id()
```
[VERIFIED: local file `src/quantum_runtime/runtime/ibm_access.py`] [ASSUMED]

### Pattern 3: Persist Attempt Records Outside Revision History

**What:** Persist one durable attempt directory after successful submit, with a stable `attempt_id`, canonical `QSpec` snapshot, sanitized provider receipt, and submit-time provenance; do not touch `workspace.json.current_revision` or `reports/latest.json` yet. [VERIFIED: local file `.planning/STATE.md`; local file `.planning/ROADMAP.md`; local file `src/quantum_runtime/workspace/manifest.py`; local file `src/quantum_runtime/reporters/writer.py`] [ASSUMED]

**When to use:** Immediately after submit succeeds and a provider job handle is available. [VERIFIED: local file `.planning/REQUIREMENTS.md`] [ASSUMED]

**Example:**
```text
.quantum/
└── remote/
    └── attempts/
        └── att_000001/
            ├── attempt.json
            ├── qspec.json
            ├── input.json
            └── provider_receipt.json
```
[VERIFIED: local file `src/quantum_runtime/workspace/paths.py`; local file `src/quantum_runtime/workspace/manifest.py`] [ASSUMED]

### Pattern 4: Add IBM Submit Preflight Instead of Reusing Benchmark Validation Blindly

**What:** Use a new helper that transpiles against the selected IBM backend target and, when using `EstimatorV2`, rewrites observables against the transpiled circuit layout. [VERIFIED: local file `src/quantum_runtime/diagnostics/transpile_validate.py`; local file `src/quantum_runtime/qspec/observables.py`] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/primitives-examples]

**When to use:** Before the network submit call; a preflight failure should return a stable CLI error and write no attempt record. [VERIFIED: local file `src/quantum_runtime/runtime/contracts.py`; local file `src/quantum_runtime/runtime/ibm_access.py`] [ASSUMED]

### Anti-Patterns to Avoid

- **Do not branch remote submit inside `executor.py`:** that file is still the synchronous local revision pipeline and already manages revision reservation, alias promotion, and diagnostics writes. [VERIFIED: local file `src/quantum_runtime/runtime/executor.py`]  
- **Do not flip `workspace.json.current_revision` on submit:** `workspace.json` currently tracks completed local revision aliases only, and the roadmap assigns terminal remote materialization to Phase 12. [VERIFIED: local file `src/quantum_runtime/workspace/manifest.py`; local file `.planning/ROADMAP.md`] [ASSUMED]  
- **Do not write tokens, saved-account secrets, or auth headers into attempt files:** Phase 09 explicitly kept secrets outside `.quantum`. [VERIFIED: local file `.planning/STATE.md`; local file `src/quantum_runtime/runtime/ibm_access.py`; local file `tests/test_cli_ibm_config.py`]  
- **Do not auto-select backends or silently retry submit:** this is a locked project decision, and retries can duplicate spend and blur attempt identity. [VERIFIED: local file `.planning/STATE.md`; local file `.planning/REQUIREMENTS.md`]  

## Plan Decomposition

### Recommended Plan Split

1. **Plan 10-01: Remote Attempt Models And Store**  
   Add Pydantic attempt models, workspace path helpers, atomic write helpers, and a narrow attempt directory schema; keep revision/report history untouched. [VERIFIED: local file `src/quantum_runtime/workspace/manifest.py`; local file `src/quantum_runtime/workspace/paths.py`; local file `.planning/ROADMAP.md`] [ASSUMED]

2. **Plan 10-02: IBM Submit Adapter And Preflight**  
   Add `ibm_submit.py` that reuses `build_ibm_service()`, performs backend-target preflight, chooses primitive kind, tags the job, and returns a sanitized submit receipt. [VERIFIED: local file `src/quantum_runtime/runtime/ibm_access.py`; local file `src/quantum_runtime/qspec/model.py`; local file `src/quantum_runtime/diagnostics/transpile_validate.py`] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/add-job-tags] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/execution-modes] [ASSUMED]

3. **Plan 10-03: `qrun ibm submit` CLI And Canonical Ingress Tests**  
   Add the provider-specific CLI command, mirror `qrun exec` input selectors, persist the attempt record on success, and cover prompt/markdown/JSON/QSpec/report-backed parity in CLI tests. [VERIFIED: local file `src/quantum_runtime/cli.py`; local file `src/quantum_runtime/runtime/resolve.py`; local file `tests/test_cli_exec.py`] [ASSUMED]

**Why this split:** It keeps Phase 10 inside submit + persistence, while leaving lifecycle refresh/cancel to Phase 11 and immutable finalization to Phase 12. [VERIFIED: local file `.planning/ROADMAP.md`; local file `.planning/REQUIREMENTS.md`]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| IBM auth and client construction | direct CLI imports of IBM SDK or raw REST auth | `resolve_ibm_access()` + `build_ibm_service()` [VERIFIED: local file `src/quantum_runtime/runtime/ibm_access.py`] | Phase 09 already locked this seam, and existing tests already monkeypatch it cleanly. [VERIFIED: local file `.planning/phases/09-ibm-access-backend-readiness/09-01-PLAN.md`; local file `tests/test_cli_ibm_config.py`] |
| Canonical remote input parsing | a second remote-only parser or provider-specific IR | `resolve_runtime_input()` + existing `QSpec` semantics [VERIFIED: local file `src/quantum_runtime/runtime/resolve.py`; local file `src/quantum_runtime/qspec/semantics.py`] | REMT-01 explicitly requires the same ingress and `QSpec` surface used locally. [VERIFIED: local file `.planning/REQUIREMENTS.md`] |
| Durable attempt persistence | ad hoc JSON writes scattered across CLI and runtime code | dedicated `remote_attempts.py` models + `atomic_write_text()` + `WorkspacePaths` helpers [VERIFIED: local file `src/quantum_runtime/workspace/manifest.py`; local file `src/quantum_runtime/workspace/paths.py`] | The repo already has a consistent atomic filesystem pattern for durable runtime state. [VERIFIED: local file `src/quantum_runtime/workspace/manifest.py`; local file `src/quantum_runtime/runtime/run_manifest.py`] |
| Duplicate-submit heuristics | silent retry after ambiguous submit failure | provider job tags + explicit failure surface + no auto-retry [VERIFIED: local file `.planning/STATE.md`; local file `.planning/REQUIREMENTS.md`] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/add-job-tags] [ASSUMED] | The project explicitly forbids silent retry, and tag-based correlation is the least invasive future-proof boundary. [VERIFIED: local file `.planning/STATE.md`] [ASSUMED] |

**Key insight:** Phase 10 should add exactly one new durable truth plane, the attempt store; it should not widen the existing revision/report truth plane until terminal results exist. [VERIFIED: local file `.planning/ROADMAP.md`; local file `src/quantum_runtime/workspace/manifest.py`; local file `src/quantum_runtime/runtime/run_manifest.py`] [ASSUMED]

## Common Pitfalls

### Pitfall 1: Conflating Remote Attempt State With Immutable Revision State

**What goes wrong:** Submit writes `reports/history/` or advances `current_revision` even though no terminal remote result exists yet. [VERIFIED: local file `src/quantum_runtime/workspace/manifest.py`; local file `src/quantum_runtime/reporters/writer.py`] [ASSUMED]

**Why it happens:** The current local executor reserves revisions as part of a synchronous, completed run pipeline. [VERIFIED: local file `src/quantum_runtime/runtime/executor.py`]

**How to avoid:** Keep submit receipts under `.quantum/remote/attempts/` and reserve immutable revisions only during Phase 12 finalization. [VERIFIED: local file `.planning/ROADMAP.md`; local file `.planning/STATE.md`] [ASSUMED]

**Warning signs:** new code writes `reports/latest.json`, `manifests/latest.json`, or `workspace.json.current_revision` during submit. [VERIFIED: local file `src/quantum_runtime/workspace/manifest.py`; local file `src/quantum_runtime/reporters/writer.py`; local file `src/quantum_runtime/runtime/run_manifest.py`] [ASSUMED]

### Pitfall 2: Reusing Local Target Validation As Exact IBM Submit Preflight

**What goes wrong:** Phase 10 assumes `validate_target_constraints()` is enough, even though it only understands generic transpile kwargs and has no provider-target or observable-layout logic. [VERIFIED: local file `src/quantum_runtime/diagnostics/transpile_validate.py`; local file `src/quantum_runtime/qspec/observables.py`]

**Why it happens:** The helper already looks like a transpile gate, but its current contract is benchmark validation, not provider submit preparation. [VERIFIED: local file `src/quantum_runtime/diagnostics/transpile_validate.py`]

**How to avoid:** Add a dedicated IBM preflight that uses the selected backend object and returns a sanitized submit-ready payload or stable error. [VERIFIED: local file `src/quantum_runtime/runtime/ibm_access.py`] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/primitives-examples] [ASSUMED]

**Warning signs:** code submits directly after `build_qiskit_circuit()` without backend-target transpile or observable layout handling. [VERIFIED: local file `src/quantum_runtime/lowering/qiskit_emitter.py`; local file `src/quantum_runtime/qspec/observables.py`] [ASSUMED]

### Pitfall 3: Secret Leakage Into Attempt Artifacts

**What goes wrong:** `attempt.json` or provider receipt files include environment values, raw tokens, saved-account internals, or auth headers. [VERIFIED: local file `src/quantum_runtime/runtime/ibm_access.py`; local file `tests/test_cli_ibm_config.py`] [ASSUMED]

**Why it happens:** Submit-time provenance is useful, but it is easy to serialize too much provider config when storing receipts. [VERIFIED: local file `src/quantum_runtime/runtime/ibm_access.py`] [ASSUMED]

**How to avoid:** Persist only non-secret references: provider, channel, instance, backend, primitive kind, job id, semantic hash, and submit options. [VERIFIED: local file `.planning/STATE.md`; local file `src/quantum_runtime/runtime/ibm_access.py`; local file `src/quantum_runtime/qspec/semantics.py`] [ASSUMED]

**Warning signs:** tests begin asserting on token values, or JSON payloads expose `Authorization`, `token`, or saved-account file contents. [VERIFIED: local file `tests/test_cli_ibm_config.py`] [ASSUMED]

### Pitfall 4: Duplicate Submit After Ambiguous Provider Failure

**What goes wrong:** a retry creates two IBM jobs for what FluxQ models as one submit action. [VERIFIED: local file `.planning/STATE.md`; local file `.planning/REQUIREMENTS.md`] [ASSUMED]

**Why it happens:** the project explicitly forbids silent retry, but submit-time code may still be tempted to retry transport errors. [VERIFIED: local file `.planning/STATE.md`; local file `.planning/REQUIREMENTS.md`]

**How to avoid:** no automatic retry in Phase 10; emit a fail-closed submit error when no durable job handle is known, and tag successful submissions with FluxQ correlation identifiers for future manual reconciliation. [VERIFIED: local file `.planning/STATE.md`; local file `.planning/REQUIREMENTS.md`] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/add-job-tags] [ASSUMED]

**Warning signs:** submit helper catches broad exceptions and replays the same provider call without a persisted local receipt or correlation tag. [ASSUMED]

## Code Examples

Verified and planner-relevant patterns:

### Canonical Ingress Reuse
```python
# Source: src/quantum_runtime/runtime/resolve.py
resolved = resolve_runtime_input(
    workspace_root=workspace_root,
    report_file=report_file,
)
qspec = resolved.qspec
source_kind = resolved.source_kind
requested_exports = resolved.requested_exports
```
[VERIFIED: local file `src/quantum_runtime/runtime/resolve.py`]

### Existing IBM Service Seam
```python
# Source: src/quantum_runtime/runtime/ibm_access.py
resolution = resolve_ibm_access(workspace_root=workspace_root)
service = build_ibm_service(resolution=resolution)
```
[VERIFIED: local file `src/quantum_runtime/runtime/ibm_access.py`]

### IBM Job-Mode Submit Shape To Mirror
```python
# Source: IBM Quantum docs, adapted to FluxQ naming.
backend = service.backend(backend_name)
sampler = SamplerV2(mode=backend)
job = sampler.run([isa_circuit], shots=shots)
job_id = job.job_id()
```
[CITED: https://quantum.cloud.ibm.com/docs/en/guides/execution-modes] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/local-testing-mode]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Repo currently advertises IBM as readiness-only with `remote_submit: false` in `backend_registry.py`. [VERIFIED: local file `src/quantum_runtime/runtime/backend_registry.py`] | Phase 10 should flip only submit capability to true while leaving lifecycle/finalization capabilities for later phases. [VERIFIED: local file `.planning/ROADMAP.md`; local file `.planning/REQUIREMENTS.md`] [ASSUMED] | Phase 10 | `backend list` stays truthful while submit becomes available. [VERIFIED: local file `tests/test_cli_backend_list.py`] [ASSUMED] |
| Current IBM seam stops at access + backend readiness. [VERIFIED: local file `src/quantum_runtime/runtime/ibm_access.py`; local file `src/quantum_runtime/runtime/backend_list.py`] | Phase 10 should add a separate submit adapter on top of that seam instead of widening the CLI or `backend_list.py` directly. [VERIFIED: local file `src/quantum_runtime/runtime/ibm_access.py`; local file `src/quantum_runtime/runtime/backend_list.py`] [ASSUMED] | Phase 10 | Keeps IBM SDK imports and submit policy out of `cli.py`. [VERIFIED: local file `src/quantum_runtime/cli.py`] [ASSUMED] |
| Current workspace truth is revision/report/manifest-centered. [VERIFIED: local file `src/quantum_runtime/workspace/manifest.py`; local file `src/quantum_runtime/runtime/run_manifest.py`; local file `src/quantum_runtime/reporters/writer.py`] | Phase 10 should add an attempt-only store, not a second report history path. [VERIFIED: local file `.planning/ROADMAP.md`; local file `.planning/STATE.md`] [ASSUMED] | Phase 10 | Keeps compare/export/pack untouched until terminal materialization exists. [VERIFIED: local file `.planning/ROADMAP.md`] [ASSUMED] |

**Deprecated/outdated:**
- The current `backend_registry.py` note that IBM is "readiness-only" becomes outdated once Phase 10 lands and must be updated in the same change set. [VERIFIED: local file `src/quantum_runtime/runtime/backend_registry.py`] [ASSUMED]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `qrun ibm submit` is the narrowest Phase 10 CLI surface and is preferable to `qrun exec --remote`. | Standard Stack / Architecture Patterns | Planner may pick the wrong command surface and widen `executor.py` unnecessarily. |
| A2 | Phase 10 should persist only attempt records and should not create a non-terminal submission revision. | Summary / Architecture Patterns | If the project wants submission revisions now, later Phase 11/12 tasks will need broader read-model changes than this research assumes. |
| A3 | One primitive kind per attempt (`sampler_v2` or `estimator_v2`) is sufficient for the first remote submit slice. | Architecture Patterns / Open Questions | If one canonical run must preserve both sampling and expectation outputs in one shot, Phase 10 scope is materially larger. |

## Open Questions

1. **Should Phase 10 create a submission revision or only an attempt record?**  
   What we know: the roadmap gives Phase 10 "attempt record" language and gives immutable remote artifact creation to Phase 12, while state says attempt identity must stay separate from terminal revision identity. [VERIFIED: local file `.planning/ROADMAP.md`; local file `.planning/STATE.md`]  
   What's unclear: whether the planner wants an inspectable non-terminal submission revision before lifecycle and finalization ship. [ASSUMED]  
   Recommendation: keep Phase 10 attempt-only unless the planner explicitly accepts broader status/show/inspect changes in this phase. [ASSUMED]

2. **How far should primitive selection go in Phase 10?**  
   What we know: `QSpec` already carries observables, local simulation computes expectation values, and IBM primitives split sampling from estimation. [VERIFIED: local file `src/quantum_runtime/qspec/model.py`; local file `src/quantum_runtime/diagnostics/simulate.py`] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/primitives]  
   What's unclear: whether Phase 10 needs both `SamplerV2` and `EstimatorV2` live paths immediately, or only the selector seam and one implemented primitive. [ASSUMED]  
   Recommendation: implement the selector seam now and make `primitive_kind` part of the attempt record even if the first plan only completes one primitive path. [ASSUMED]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | repo runtime and tests | ✓ | `3.11.15` via `python3.11` and `uv run python` [VERIFIED: `python3.11 --version`; VERIFIED: `uv run python --version`] | — |
| `uv` | install and test flow | ✓ | `0.11.1` [VERIFIED: `uv --version`] | — |
| `pytest` | phase regression tests | ✓ | `9.0.2` [VERIFIED: `uv run pytest --version`] | — |
| `ruff` | lint gate | ✓ | `0.15.8` [VERIFIED: `uv run ruff --version`] | — |
| `mypy` | static gate | ✓ with module invocation | `1.20.0` via `uv run python -m mypy --version` [VERIFIED: `uv run python -m mypy --version`] | Use `uv run python -m mypy src`; the checked-in `.venv/bin/mypy` launcher is stale. [VERIFIED: local file `.venv/bin/mypy`; VERIFIED: `uv run mypy --version`] |
| `qiskit-ibm-runtime` in repo `uv` environment | Phase 10 submit path | ✗ | missing from `uv run python` [VERIFIED: `uv run python -c 'import qiskit_ibm_runtime'`] | Install with `uv sync --extra ibm`; until then, tests should monkeypatch the submit seam. [VERIFIED: local file `pyproject.toml`; local file `tests/test_cli_ibm_config.py`] |
| IBM credentials/profile | live remote smoke | not audited | — | Use mocked service and job objects for fast tests; defer live smoke to explicit human/CI setup. [VERIFIED: local file `.planning/phases/09-ibm-access-backend-readiness/09-01-PLAN.md`; local file `.agents/skills/fluxq-cli/SKILL.md`] |

**Missing dependencies with no fallback:**
- None for repo-local implementation planning. [VERIFIED: local file `pyproject.toml`; local file `.github/workflows/ci.yml`] [ASSUMED]

**Missing dependencies with fallback:**
- `qiskit-ibm-runtime` is not installed in the current `uv run` environment; install the optional extra for live submit work, but keep fast tests seam-mocked. [VERIFIED: local file `pyproject.toml`; VERIFIED: `uv run python -c 'import qiskit_ibm_runtime'`; local file `tests/test_cli_ibm_config.py`]  
- `uv run mypy` uses a stale wrapper script in this workspace; use `uv run python -m mypy src` instead. [VERIFIED: local file `.venv/bin/mypy`; VERIFIED: `uv run mypy --version`; VERIFIED: `uv run python -m mypy --version`]  

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest 9.0.2` [VERIFIED: `uv run pytest --version`] |
| Config file | `pyproject.toml` [VERIFIED: local file `pyproject.toml`] |
| Quick run command | `uv run pytest tests/test_cli_ibm_submit.py -q --maxfail=1` [ASSUMED] |
| Full suite command | `uv run pytest -q --ignore tests/test_classiq_backend.py --ignore tests/test_classiq_emitter.py --ignore tests/test_qspec_validation.py` [VERIFIED: local file `.github/workflows/ci.yml`] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REMT-01 | `qrun ibm submit` accepts prompt, markdown, JSON intent, `QSpec`, and trusted report-backed inputs through one canonical resolver | CLI + unit | `uv run pytest tests/test_cli_ibm_submit.py::test_qrun_ibm_submit_reuses_all_supported_ingress_surfaces -q --maxfail=1` | ❌ Wave 0 |
| REMT-02 | Successful submit persists attempt metadata, canonical `QSpec` snapshot, backend, instance, primitive kind, and provider job handle without mutating `current_revision` | runtime + CLI | `uv run pytest tests/test_runtime_remote_attempts.py::test_submit_persists_attempt_record_and_leaves_revision_state_unchanged -q --maxfail=1` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_cli_ibm_submit.py tests/test_runtime_remote_attempts.py -q --maxfail=1` [ASSUMED]
- **Per wave merge:** `uv run pytest -q --ignore tests/test_classiq_backend.py --ignore tests/test_classiq_emitter.py --ignore tests/test_qspec_validation.py` [VERIFIED: local file `.github/workflows/ci.yml`]
- **Phase gate:** `uv run ruff check src tests`, `uv run python -m mypy src`, and the phase-specific pytest lane. [VERIFIED: local file `.github/workflows/ci.yml`; VERIFIED: `uv run ruff --version`; VERIFIED: `uv run python -m mypy --version`] [ASSUMED]

### Wave 0 Gaps

- [ ] `tests/test_cli_ibm_submit.py` — submit command parity across all ingress selectors; mirror the pattern used by `tests/test_cli_exec.py`. [VERIFIED: local file `tests/test_cli_exec.py`]  
- [ ] `tests/test_runtime_remote_attempts.py` — atomic attempt-store persistence, secret scrubbing, workspace conflict, and unchanged `current_revision`. [VERIFIED: local file `tests/test_runtime_workspace_safety.py`; local file `src/quantum_runtime/workspace/manifest.py`] [ASSUMED]  
- [ ] Optional live smoke lane — only after `uv sync --extra ibm` and explicit IBM credentials exist. [VERIFIED: local file `pyproject.toml`; local file `.planning/phases/09-ibm-access-backend-readiness/09-01-PLAN.md`]  

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Reuse `resolve_ibm_access()` and `build_ibm_service()`; keep credentials external to `.quantum`. [VERIFIED: local file `src/quantum_runtime/runtime/ibm_access.py`; local file `.planning/STATE.md`] |
| V3 Session Management | no | Phase 10 is job mode only; IBM sessions are out of scope. [VERIFIED: local file `.planning/ROADMAP.md`; local file `.planning/REQUIREMENTS.md`] |
| V4 Access Control | no | This phase is a local CLI/workspace control plane, not a multi-user service boundary. [VERIFIED: local file `AGENTS.md`; local file `src/quantum_runtime/cli.py`] |
| V5 Input Validation | yes | Keep Typer option validation plus Pydantic models and `resolve_runtime_input()` one-input enforcement. [VERIFIED: local file `src/quantum_runtime/cli.py`; local file `src/quantum_runtime/runtime/resolve.py`; local file `src/quantum_runtime/runtime/ibm_access.py`] |
| V6 Cryptography | no | Phase 10 should continue using existing local artifact-digest patterns where needed, but it does not introduce new cryptographic protocols. [VERIFIED: local file `src/quantum_runtime/reporters/writer.py`; local file `src/quantum_runtime/runtime/run_manifest.py`] |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Token or auth-header leakage into attempt JSON | Information Disclosure | Persist only non-secret references and add explicit redaction assertions in attempt-store tests. [VERIFIED: local file `src/quantum_runtime/runtime/ibm_access.py`; local file `tests/test_cli_ibm_config.py`] [ASSUMED] |
| Duplicate remote submit after ambiguous failure | Denial of Service | No silent retry; use explicit correlation tags and fail-closed submit errors. [VERIFIED: local file `.planning/STATE.md`; local file `.planning/REQUIREMENTS.md`] [CITED: https://quantum.cloud.ibm.com/docs/en/guides/add-job-tags] [ASSUMED] |
| Non-terminal submit treated as completed revision | Tampering | Separate attempt store from report/revision history until Phase 12. [VERIFIED: local file `.planning/ROADMAP.md`; local file `src/quantum_runtime/workspace/manifest.py`] [ASSUMED] |
| Implicit backend or instance drift | Tampering | Require explicit `--backend` and recorded `instance`; keep auto-selection out of submit. [VERIFIED: local file `.planning/STATE.md`; local file `.planning/REQUIREMENTS.md`] |

## Sources

### Primary (HIGH confidence)

- [local file `src/quantum_runtime/runtime/resolve.py`] - canonical ingress reuse and `ResolvedRuntimeInput`
- [local file `src/quantum_runtime/runtime/executor.py`] - current local synchronous revision pipeline
- [local file `src/quantum_runtime/runtime/ibm_access.py`] - Phase 09 IBM access/service seam
- [local file `src/quantum_runtime/runtime/backend_list.py`] - current IBM readiness-only projection
- [local file `src/quantum_runtime/runtime/backend_registry.py`] - current `remote_submit: false` descriptor
- [local file `src/quantum_runtime/workspace/manifest.py`] - authoritative mutable workspace manifest shape
- [local file `src/quantum_runtime/workspace/paths.py`] - current workspace directory helpers
- [local file `src/quantum_runtime/runtime/run_manifest.py`] - immutable manifest artifact pattern
- [local file `src/quantum_runtime/reporters/writer.py`] - immutable report artifact pattern
- [local file `src/quantum_runtime/diagnostics/transpile_validate.py`] - current transpile helper limits
- [local file `src/quantum_runtime/qspec/model.py`] - current `QSpec` fields including observables, backend provider/name, and shots
- [local file `src/quantum_runtime/qspec/semantics.py`] - semantic hash and canonical execution identity
- [local file `.planning/STATE.md`] - current locked decisions and phase boundary notes
- [local file `.planning/ROADMAP.md`] - Phase 10/11/12/13 success criteria and sequencing
- [local file `.planning/REQUIREMENTS.md`] - REMT-01 and REMT-02 definitions
- [local file `.planning/phases/09-ibm-access-backend-readiness/09-RESEARCH.md`] - Phase 09 IBM readiness constraints
- [local file `.planning/phases/09-ibm-access-backend-readiness/09-01-PLAN.md`] - IBM service seam decision
- [local file `.agents/skills/fluxq-cli/SKILL.md`] - current shipped IBM boundary
- [local file `tests/test_cli_ibm_config.py`] - existing IBM seam test style
- [local file `tests/test_cli_backend_list.py`] - current IBM readiness CLI contract
- [local file `tests/test_cli_exec.py`] - canonical ingress parity examples
- [local file `tests/test_runtime_workspace_safety.py`] - workspace safety and atomic-write test style

### Secondary (MEDIUM confidence)

- https://quantum.cloud.ibm.com/docs/en/guides/execution-modes - job mode primitive shape for submit
- https://quantum.cloud.ibm.com/docs/en/guides/primitives-examples - ISA transpile and observable layout patterns
- https://quantum.cloud.ibm.com/docs/en/guides/primitives - primitive split between sampling and expectation evaluation
- https://quantum.cloud.ibm.com/docs/en/guides/add-job-tags - provider job tags for correlation
- https://quantum.cloud.ibm.com/docs/en/guides/local-testing-mode - job object and primitive testing patterns

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - the repo already pins the IBM extra and Phase 09 already standardized the auth/service seam. [VERIFIED: local file `pyproject.toml`; local file `src/quantum_runtime/runtime/ibm_access.py`]
- Architecture: MEDIUM - the tight attempt-only store recommendation fits the roadmap and current workspace model, but the repo has not yet locked whether submit also creates a non-terminal revision. [VERIFIED: local file `.planning/ROADMAP.md`; local file `.planning/STATE.md`] [ASSUMED]
- Pitfalls: HIGH - the failure boundaries are directly visible from current workspace/revision code and explicit remote-execution decisions. [VERIFIED: local file `src/quantum_runtime/runtime/executor.py`; local file `src/quantum_runtime/workspace/manifest.py`; local file `.planning/STATE.md`]

**Research date:** 2026-04-18  
**Valid until:** 2026-05-18 for repo-local architecture assumptions; shorter if the roadmap or IBM submit scope changes.
