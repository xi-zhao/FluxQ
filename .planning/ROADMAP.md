# Roadmap: FluxQ

## Milestones

- ✅ **v1.0 Runtime Foundation** — Phases 1-8, 29 plans, shipped 2026-04-18. Archive: `.planning/milestones/v1.0-ROADMAP.md`
- 🚧 **v1.1 Remote Execution** — Phases 9-13, active planning for IBM Quantum Platform job-mode remote trust

## Current Status

- Active milestone: **v1.1 Remote Execution**
- Active focus: roadmap created, ready to plan **Phase 9**
- Scope guard: IBM Quantum Platform only, job mode only, trust-first remote execution
- Next step: `/gsd-plan-phase 9`

## Phases

<details>
<summary>✅ v1.0 Runtime Foundation (Phases 1-8) — SHIPPED 2026-04-18</summary>

- [x] Phase 1: Canonical Ingress Resolution (3/3 plans) — completed 2026-04-12
- [x] Phase 2: Trusted Revision Artifacts (4/4 plans) — completed 2026-04-12
- [x] Phase 3: Concurrent Workspace Safety (4/4 plans) — completed 2026-04-12
- [x] Phase 4: Policy Acceptance Gates (4/4 plans) — completed 2026-04-16
- [x] Phase 5: Verified Delivery Bundles (3/3 plans) — completed 2026-04-14
- [x] Phase 6: Runtime Adoption Surface (3/3 plans) — completed 2026-04-15
- [x] Phase 7: Compare Trust Closure (3/3 plans) — completed 2026-04-15
- [x] Phase 8: Verification And Bookkeeping Closure (5/5 plans) — completed 2026-04-18

</details>

### 🚧 v1.1 Remote Execution (Active)

**Milestone Goal:** Extend FluxQ from a trustworthy local control plane to a trustworthy remote execution control plane through IBM Quantum Platform job mode without weakening canonical artifacts, offline trust, or fail-closed machine output.

- [ ] **Phase 9: IBM Access & Backend Readiness** - Configure non-interactive IBM access and validate explicit backend readiness before any remote submission.
- [ ] **Phase 10: Canonical Remote Submit & Attempt Records** - Submit existing FluxQ runtime objects remotely and persist a first-class remote attempt immediately.
- [ ] **Phase 11: Remote Lifecycle Control** - Reopen, poll, and cancel remote jobs without resubmitting compute.
- [ ] **Phase 12: Terminal Result Materialization** - Finalize terminal remote jobs into immutable local artifacts that remain usable offline.
- [ ] **Phase 13: Fail-Closed Remote Observability** - Expose schema-versioned remote JSON and JSONL contracts for submit, lifecycle, finalization, and recovery.

## Phase Details

### Phase 9: IBM Access & Backend Readiness
**Goal**: Users can establish explicit IBM Quantum Platform access and validate remote backend readiness before FluxQ submits any canonical run.
**Depends on**: Phase 8
**Requirements**: AUTH-01, BACK-01
**Success Criteria** (what must be TRUE):
  1. User can configure IBM Quantum Platform credentials and instance selection non-interactively for local agents and CI.
  2. User can list compatible IBM remote backends before submission.
  3. Backend discovery shows readiness details that let the user decide whether a pinned backend is usable.
**Plans**: 3 plans

Plans:
- [x] 09-01-PLAN.md — IBM optional extra, non-secret profile contract, and `qrun ibm configure`
- [x] 09-02-PLAN.md — IBM `doctor --ci` auth/profile gate plus JSONL observability
- [ ] 09-03-PLAN.md — IBM `backend list` inventory and target readiness surface

### Phase 10: Canonical Remote Submit & Attempt Records
**Goal**: Users can submit canonical FluxQ runtime objects to IBM Quantum Platform and immediately receive a durable local remote attempt record.
**Depends on**: Phase 9
**Requirements**: REMT-01, REMT-02
**Success Criteria** (what must be TRUE):
  1. User can submit a remote run from the same prompt, markdown, structured JSON, `QSpec`, or trusted report-backed ingress surface used locally.
  2. Successful submission immediately yields a persisted FluxQ remote attempt record with provider job handle, backend, instance, and submit-time provenance.
  3. The submission path preserves the existing canonical `QSpec` surface instead of introducing a separate remote-only input format.
**Plans**: TBD

### Phase 11: Remote Lifecycle Control
**Goal**: Users can manage an existing remote job lifecycle without changing run identity or resubmitting compute.
**Depends on**: Phase 10
**Requirements**: REMT-03
**Success Criteria** (what must be TRUE):
  1. User can reopen a previously submitted remote job without creating a second submission.
  2. User can poll remote status and distinguish provider lifecycle state from local terminal finalization state.
  3. User can cancel an eligible remote job and see that cancellation reflected in FluxQ lifecycle state without rerunning compute.
**Plans**: TBD

### Phase 12: Terminal Result Materialization
**Goal**: Users can turn a terminal remote job into immutable local FluxQ artifacts that stay inspectable, comparable, and packable offline.
**Depends on**: Phase 11
**Requirements**: REMT-04
**Success Criteria** (what must be TRUE):
  1. User can finalize a terminal remote job into immutable local revision artifacts after FluxQ retrieves and normalizes the provider outcome.
  2. Finalized remote revisions remain inspectable and comparable after provider access is unavailable.
  3. Finalized remote revisions can be packed and moved offline without losing the remote execution evidence needed for trust.
**Plans**: TBD

### Phase 13: Fail-Closed Remote Observability
**Goal**: Agents and CI can consume stable, fail-closed remote control-plane output across submit, lifecycle, finalization, and recovery flows.
**Depends on**: Phase 12
**Requirements**: OBSV-01
**Success Criteria** (what must be TRUE):
  1. Agent or CI can consume schema-versioned JSON output for remote submit, lifecycle, finalization, and recovery commands.
  2. Agent or CI can consume JSONL lifecycle events that distinguish submission, provider refresh, finalization, and recovery states.
  3. Remote failures surface fail-closed machine-readable reasons instead of silent retry, silent resubmission, or ambiguous partial success.
  4. Recovery states tell the caller whether a remote attempt can be reopened, finalized, or requires explicit remediation.
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-8 Runtime Foundation | v1.0 | 29/29 | Complete | 2026-04-18 |
| 9. IBM Access & Backend Readiness | v1.1 | 0/3 | Not started | - |
| 10. Canonical Remote Submit & Attempt Records | v1.1 | 0/TBD | Not started | - |
| 11. Remote Lifecycle Control | v1.1 | 0/TBD | Not started | - |
| 12. Terminal Result Materialization | v1.1 | 0/TBD | Not started | - |
| 13. Fail-Closed Remote Observability | v1.1 | 0/TBD | Not started | - |
