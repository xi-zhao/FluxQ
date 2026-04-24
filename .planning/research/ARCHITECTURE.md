# Architecture Research: FluxQ v1.1 Remote Execution

**Domain:** Remote execution integration for FluxQ's existing local control plane  
**Researched:** 2026-04-18  
**Confidence:** HIGH for provider capabilities, MEDIUM-HIGH for the recommended internal shape

## Recommendation

FluxQ should integrate remote execution as a control-plane extension, not as a second runtime model. `QSpec` remains the canonical workload truth. Remote provider state is additional execution evidence layered on top of that truth.

The key architectural rule is this: **remote lifecycle polling must never mutate an existing immutable revision artifact**. A remote run should be modeled as:

1. **Submission revision**: immutable record of what FluxQ canonicalized and sent.
2. **Append-only remote lifecycle store**: provider receipts and status snapshots keyed by a stable FluxQ attempt id.
3. **Materialized terminal revision**: a second immutable revision created only when FluxQ has fetched a terminal remote outcome and normalized it into the existing report/manifest trust model.

This is the best fit for FluxQ's current architecture because it preserves the same source-of-record distinction it already uses locally:

- `QSpec`, report history, manifest history, and artifact snapshots remain the durable truth.
- `workspace.json` and `latest` aliases remain mutable pointers only.
- status polling stays operational and append-only until a terminal result is materialized.
- compare/export/pack continue to trust persisted artifacts, not live provider APIs.

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│ CLI / Control Plane                                                │
│ qrun exec / status / show / inspect / compare / pack / doctor      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Canonical Ingress                                                  │
│ resolve.py -> ResolvedRuntimeInput -> validated QSpec              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Execution Router                                                   │
│ local path                     remote path                         │
│ executor.py                    remote/service.py                   │
└───────────────┬───────────────────────────────┬─────────────────────┘
                │                               │
                ▼                               ▼
┌────────────────────────────┐   ┌────────────────────────────────────┐
│ Local evidence pipeline    │   │ Remote provider adapter            │
│ simulate / transpile /     │   │ qiskit-ibm-runtime client          │
│ diagrams / report          │   │ submit / poll / cancel / fetch     │
└───────────────┬────────────┘   └────────────────┬───────────────────┘
                │                                 │
                ▼                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Workspace truth + evidence                                          │
│ specs/history/ reports/history/ manifests/history/ artifacts/history │
│ remote/attempts/<attempt_id>/ submission.json status.ndjson result   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Read models                                                         │
│ imports.py / inspect.py / compare.py / export.py / pack.py          │
│ trust only persisted artifacts; treat remote API as refresh source  │
└─────────────────────────────────────────────────────────────────────┘
```

## Core Architectural Decision

### Separate attempt identity from revision identity

FluxQ currently treats a revision as the immutable identity of a completed local run. Remote execution breaks that assumption because a provider job progresses over time.

Recommended inference from the current codebase: add a stable **`attempt_id`** for remote lifecycle tracking, and let one attempt produce multiple immutable revisions.

- `attempt_id`: stable FluxQ identifier for one remote provider job lifecycle.
- `submission_revision`: immutable revision created when submission succeeds.
- `terminal_revision`: immutable revision created when the provider reaches `DONE`, `ERROR`, or `CANCELLED` and FluxQ materializes the outcome.

Do **not** overload `revision` to mean both "lifecycle in progress" and "finalized evidence".

## New Components

### Recommended new runtime package

```text
src/quantum_runtime/runtime/remote/
├── __init__.py          # Barrel for remote control-plane surface
├── models.py            # Attempt, receipt, status snapshot, terminal result, lineage
├── service.py           # submit, sync, materialize, cancel orchestration
├── store.py             # append-only workspace remote evidence store
├── provider.py          # provider protocol / adapter contract
└── ibm_runtime.py       # IBM Qiskit Runtime adapter
```

### Recommended new workspace layout

```text
.quantum/
└── remote/
    ├── active.json                      # mutable projection of active attempts
    └── attempts/
        └── <attempt_id>/
            ├── submission.json          # normalized request + safe provider receipt
            ├── status.ndjson            # append-only normalized poll snapshots
            ├── provider/
            │   ├── submission.raw.json  # optional sanitized provider payload
            │   ├── status.raw.ndjson    # optional sanitized raw status payloads
            │   └── result.raw.json      # terminal raw result when fetched
            └── result.normalized.json   # FluxQ-normalized terminal result evidence
```

### New component responsibilities

| New Component | Responsibility | Why It Exists |
|---|---|---|
| `runtime/remote/models.py` | Provider-agnostic Pydantic contracts for attempt ids, status snapshots, receipts, terminal results, and lineage | Keeps provider details out of CLI and workspace plumbing |
| `runtime/remote/provider.py` | Minimal protocol for `submit()`, `get_status()`, `get_result()`, `cancel()`, `capabilities()` | Prevents IBM-specific behavior from leaking into control-plane code |
| `runtime/remote/ibm_runtime.py` | IBM adapter using `qiskit-ibm-runtime` | Matches the current Qiskit-first constraint while avoiding direct REST coupling |
| `runtime/remote/store.py` | Atomic writes for submission receipts, append-only status logs, and active-attempt projections | Makes remote polling evidence durable without mutating revision history |
| `runtime/remote/service.py` | Remote orchestration for submit, sync, finalize, and cancel | Keeps async lifecycle logic out of the already-large `executor.py` |

## Modified Seams

| Existing Module | Change | Why |
|---|---|---|
| `src/quantum_runtime/runtime/executor.py` | Split into routing + shared revision commit helpers; local path stays intact | Remote async state does not belong inline in the current monolithic local executor |
| `src/quantum_runtime/runtime/resolve.py` | Resolve remote target selection from compatible `QSpec` fields and CLI flags; do not resolve provider job state here | Keeps ingress canonical and side-effect free |
| `src/quantum_runtime/qspec/model.py` | Only add optional remote-target metadata if it affects execution semantics; never store job ids, tokens, CRNs, or poll state | Preserves `QSpec` as canonical workload truth rather than operational state |
| `src/quantum_runtime/runtime/control_plane.py` | Extend `status`, `show`, and plan payloads to surface remote attempt summaries and terminal-state readiness | Remote lifecycle should show up through existing control-plane read models |
| `src/quantum_runtime/lowering/qasm3_emitter.py` | Keep canonical OpenQASM 3 export as persisted exchange evidence even if the provider adapter submits through the SDK | Preserves FluxQ's OpenQASM 3 exchange layer for audit and packaging |
| `src/quantum_runtime/diagnostics/transpile_validate.py` | Add remote preflight against provider backend targets and persist target assumptions used at submit time | IBM Runtime requires ISA-compatible circuits for backend execution |
| `src/quantum_runtime/reporters/writer.py` | Add an `execution` block with `mode`, `state`, `terminal`, `attempt_id`, target details, and lineage | Existing report contract needs explicit remote lifecycle semantics |
| `src/quantum_runtime/runtime/run_manifest.py` | Add remote evidence pointers and lineage links; keep hashes over persisted local artifacts | Manifests must prove which remote evidence files belong to which revision |
| `src/quantum_runtime/runtime/imports.py` | Reopen submission revisions and terminal revisions distinctly; reject or degrade on non-terminal remote revisions for compare/export flows | Existing read models assume final evidence exists |
| `src/quantum_runtime/runtime/inspect.py` | Surface remote lifecycle state, attempt id, provider job id, and terminal materialization lineage | `inspect` becomes the main trust view for remote state |
| `src/quantum_runtime/runtime/compare.py` | Compare only terminal revisions by default; do not treat provider queue state as report drift | Keeps policy-grade comparison meaningful |
| `src/quantum_runtime/runtime/export.py` | Export canonical `QSpec` plus remote normalized evidence only for terminal revisions | Prevents exporting incomplete runtime objects as final |
| `src/quantum_runtime/runtime/pack.py` | Include remote evidence files in bundles and verify their digests | Remote trust must survive relocation like local trust already does |
| `src/quantum_runtime/runtime/observability.py` | Add remote event types and stable state mapping | JSONL/NDJSON contracts must stay agent-friendly |
| `src/quantum_runtime/runtime/backend_registry.py` | Add a remote backend/provider descriptor such as `qiskit-runtime` with `remote_submit`, `remote_status`, `remote_cancel`, and auth capability flags | Doctor and backend list need explicit remote capability reporting |
| `src/quantum_runtime/runtime/doctor.py` | Check optional `qiskit-ibm-runtime` install plus presence of a configured account reference, but never persist secrets | Remote readiness must be machine-checkable without weakening secret boundaries |
| `src/quantum_runtime/workspace/paths.py` | Add canonical `remote/` directories and path helpers | Remote lifecycle needs first-class workspace paths |
| `src/quantum_runtime/workspace/manager.py` | Seed new remote directories during init | Remote state should be as deterministic as current workspace layout |

## Data Flow Changes

### 1. Submit Flow

```text
qrun exec --remote
  -> resolve.py produces ResolvedRuntimeInput + QSpec
  -> remote preflight compiles local provider-ready artifacts
  -> remote service submits through provider adapter
  -> reserve submission revision
  -> persist:
       specs/history/<submission_revision>.json
       intents/history/<submission_revision>.json
       plans/history/<submission_revision>.json
       reports/history/<submission_revision>.json
       manifests/history/<submission_revision>.json
       remote/attempts/<attempt_id>/submission.json
       remote/attempts/<attempt_id>/status.ndjson   (first snapshot)
  -> promote aliases to the submission revision
```

Recommended behavior:

- The submission revision is a real revision and becomes visible through `status`, `show`, and `inspect`.
- Its report is **not** a final replayable execution result. It is a canonical submission record with `execution.terminal = false`.
- Submission should persist provider-ready evidence, such as target backend selection and the exact provider-safe payload FluxQ derived, but not secrets.

### 2. Poll / Sync Flow

```text
qrun remote sync / qrun status
  -> remote store resolves active attempts
  -> provider adapter polls RuntimeJobV2 or equivalent
  -> normalized snapshot appended to status.ndjson
  -> active.json projection updated
  -> no new revision while state is non-terminal
```

This is where FluxQ should track provider lifecycle through the same control-plane abstractions without corrupting immutability.

- Poll snapshots are append-only evidence.
- They are operational state, not canonical truth for compare/export.
- `status` and `inspect` can safely project them.

### 3. Materialize Terminal Result Flow

```text
remote status becomes DONE / ERROR / CANCELLED
  -> fetch terminal result and usage metrics
  -> normalize into FluxQ remote result evidence
  -> reserve terminal revision
  -> persist a new report + manifest + history artifacts
  -> link back to submission_revision and attempt_id
  -> update aliases to terminal revision
  -> mark attempt inactive in active.json
```

This is the most important trust-preserving step. FluxQ should **create a new immutable terminal revision**, not rewrite the submission revision.

Recommended lineage fields in report/manifest:

- `execution.mode`: `remote`
- `execution.state`: `submitted|queued|running|completed|failed|cancelled`
- `execution.terminal`: `true|false`
- `execution.attempt_id`
- `execution.provider.name`
- `execution.provider.job_id`
- `execution.lineage.submission_revision`
- `execution.lineage.materialized_from_attempt`

### 4. Reopen / Compare / Pack Flow

`imports.py` should treat remote revisions in two classes:

- **Submission revisions**: canonical and inspectable, but not valid for compare/export/baseline unless the command explicitly accepts non-terminal objects.
- **Terminal revisions**: fully valid runtime objects once replay/provenance checks pass.

`pack.py` should bundle:

- the normal revision artifacts already required today
- the normalized remote submission receipt
- append-only status evidence
- terminal raw and normalized remote result evidence for terminal revisions

## Trust Boundaries To Preserve

### Keep canonical identity local and deterministic

Do not put any of the following into `QSpec` semantic identity:

- provider job ids
- session ids
- account names
- CRNs
- access tokens
- poll timestamps
- queue position

Those are operational details, not workload truth.

### Keep provider auth outside the workspace truth layer

Based on current IBM docs, `QiskitRuntimeService` can load saved accounts from `~/.qiskit/qiskit-ibm.json`. FluxQ should only store a non-secret reference such as an account name, channel, or explicit target selection in config or CLI flags. Secrets stay outside the workspace and outside bundles.

### Keep remote API reads out of replay trust

`imports.py`, `compare.py`, and `pack.py` should trust persisted workspace evidence only. The provider API is a refresh source for `sync`, not a read-time dependency for replay trust.

### Keep submission evidence and terminal evidence distinct

If FluxQ submits successfully but later fails to fetch or materialize the result, the submission revision must remain valid as a submission record. The terminal revision simply does not exist yet.

## Patterns To Follow

### Pattern: Immutable submission, immutable finalization

**What:** Create one revision at submit time and another at terminal materialization time.  
**Why:** This preserves the existing immutable-history model.  
**Trade-off:** One remote attempt can span two revisions, so lineage must be explicit.

### Pattern: Provider adapter behind a normalized state machine

**What:** Map provider states into FluxQ states such as `submitted`, `queued`, `running`, `completed`, `failed`, `cancelled`.  
**Why:** IBM Runtime exposes `INITIALIZING`, `QUEUED`, `RUNNING`, `DONE`, `CANCELLED`, and `ERROR`; FluxQ should normalize those into one stable schema.  
**Trade-off:** Some provider-specific nuance moves into provider-specific details blocks.

### Pattern: Local preflight before remote submit

**What:** Fetch backend metadata, compile or validate provider-ready artifacts locally, and persist them before submission.  
**Why:** IBM Runtime requires ISA-compatible circuits for backend execution, and FluxQ's trust model depends on preserving what it intended to send.  
**Trade-off:** Submission path does more work up front, but that is the right trade for auditability.

## Anti-Patterns To Avoid

### Anti-Pattern: Mutating `reports/history/<revision>.json` when status changes

**Why bad:** It breaks FluxQ's immutable revision contract and invalidates current compare/import assumptions.  
**Do instead:** Append status snapshots under `remote/attempts/<attempt_id>/status.ndjson`, then create a new terminal revision when final.

### Anti-Pattern: Storing provider secrets or raw auth material in workspace artifacts

**Why bad:** It weakens delivery-bundle safety and breaks the current local trust boundary.  
**Do instead:** Store only non-secret account references and safe provider receipts.

### Anti-Pattern: Letting compare/export read directly from the provider API

**Why bad:** A run object becomes dependent on mutable remote state instead of persisted evidence.  
**Do instead:** Materialize terminal revisions first, then compare/export from local persisted artifacts.

### Anti-Pattern: Stuffing all remote logic into `executor.py`

**Why bad:** The current executor already owns local revision commit complexity. Async remote lifecycle will make it too fragile.  
**Do instead:** Extract shared commit helpers and put remote orchestration in a dedicated `runtime/remote/` package.

## Suggested Build Order

1. **Extract a shared revision commit seam from `executor.py`.**  
   Move revision reservation, history writes, alias promotion, and manifest/report commit helpers behind small internal APIs. No remote behavior yet.

2. **Add provider-agnostic remote contracts and workspace paths.**  
   Introduce `attempt_id`, remote models, `remote/` workspace paths, and append-only remote evidence storage. No provider integration yet.

3. **Add IBM Runtime adapter behind a narrow protocol.**  
   Use `qiskit-ibm-runtime`, not direct REST, for v1.1. Extend backend registry and doctor so remote readiness is machine-visible.

4. **Implement remote submit only.**  
   Create submission revisions plus remote attempt receipts. Make `status` and `inspect` understand non-terminal remote revisions. Do not implement compare/export/pack changes yet.

5. **Implement polling and append-only lifecycle sync.**  
   Add `sync` behavior and JSONL events. Keep sync side effects confined to remote evidence files and active-attempt projections.

6. **Implement terminal materialization.**  
   When a job becomes terminal, create a new immutable terminal revision with normalized remote result evidence, updated report/manifest contracts, and lineage.

7. **Upgrade read models.**  
   Teach `imports`, `inspect`, `compare`, `export`, and baseline flows to distinguish submission revisions from terminal revisions and fail closed where required.

8. **Upgrade pack/import and provenance verification.**  
   Extend `artifact_provenance.py`, `run_manifest.py`, and `pack.py` so remote evidence survives relocation and remains verifiable.

9. **Only then add ergonomic CLI features.**  
   Optional `--wait`, `remote cancel`, richer `status`, and provider-specific inspection should come after the trust path is correct.

## Why This Build Order Fits FluxQ

- It respects the current trust boundary that only persisted history artifacts are authoritative.
- It avoids rewriting `imports.py` and `compare.py` before terminal remote evidence exists.
- It keeps remote submit useful early while protecting compare/export from half-built semantics.
- It forces lineage and schema changes to be explicit before the bundle and policy surfaces depend on them.

## Confidence Assessment

| Area | Confidence | Notes |
|---|---|---|
| Existing FluxQ seam analysis | HIGH | Based on direct codebase reads of `executor`, `imports`, `run_manifest`, `writer`, `workspace`, and backend registry |
| IBM Runtime lifecycle capabilities | HIGH | Based on current official IBM docs for `QiskitRuntimeService`, `RuntimeJobV2`, job retrieval, and REST/session flows |
| Recommended two-revision remote model | MEDIUM-HIGH | Architectural recommendation inferred from FluxQ's existing immutability and provenance rules |
| Remote QSpec evolution guidance | MEDIUM | Recommendation depends on how much remote execution configuration FluxQ wants to encode canonically in v1.1 |

## Sources

- FluxQ project context and architecture:
  - `/Users/xizhao/my_projects/Fluxq/Qcli/.planning/PROJECT.md`
  - `/Users/xizhao/my_projects/Fluxq/Qcli/.planning/codebase/ARCHITECTURE.md`
  - `src/quantum_runtime/runtime/executor.py`
  - `src/quantum_runtime/runtime/imports.py`
  - `src/quantum_runtime/runtime/run_manifest.py`
  - `src/quantum_runtime/reporters/writer.py`
  - `src/quantum_runtime/workspace/paths.py`
  - `src/quantum_runtime/runtime/backend_registry.py`
- IBM official documentation, accessed 2026-04-18:
  - Qiskit Runtime service API: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service
  - RuntimeJobV2 API: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/dev/runtime-job-v2
  - Retrieve and save job results: https://quantum.cloud.ibm.com/docs/en/guides/save-jobs
  - Qiskit Runtime REST API: https://quantum.cloud.ibm.com/docs/en/api/qiskit-runtime-rest
  - Latest updates: https://docs.quantum.ibm.com/guides/latest-updates
  - Introduction to transpilation: https://quantum.cloud.ibm.com/docs/guides/transpile
  - Compare transpiler settings / ISA requirement: https://quantum.cloud.ibm.com/docs/guides/circuit-transpilation-settings

---
*Architecture research for FluxQ v1.1 remote execution integration*
