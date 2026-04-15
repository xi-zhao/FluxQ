# Roadmap: FluxQ

## Overview

FluxQ's next milestone hardens the control plane from side-effect-free ingress through trusted revision artifacts, shared-workspace safety, CI-ready policy decisions, portable delivery bundles, and runtime-facing adoption materials so agents can treat runs as durable runtime objects end to end.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions after planning

- [x] **Phase 1: Canonical Ingress Resolution** - Normalize supported intent inputs into one side-effect-free runtime object surface.
- [x] **Phase 2: Trusted Revision Artifacts** - Persist replayable revision evidence and fail closed on integrity drift.
- [x] **Phase 3: Concurrent Workspace Safety** - Make shared workspace mutation safe for multiple agents and CI writers.
- [ ] **Phase 4: Policy Acceptance Gates** - Turn compare, benchmark, and doctor outputs into CI-ready accept or reject decisions.
- [x] **Phase 5: Verified Delivery Bundles** - Package, verify, and re-import trusted runtime bundles outside the source workspace.
- [x] **Phase 6: Runtime Adoption Surface** - Align docs, examples, and release notes around the runtime/control-plane contract.

## Phase Details

### Phase 1: Canonical Ingress Resolution
**Goal**: Agents can turn any supported ingress input into the same canonical runtime object before side effects begin.
**Depends on**: Nothing (first phase)
**Requirements**: INGR-01, INGR-02, INGR-03
**Success Criteria** (what must be TRUE):
  1. Agent can submit prompt text and receive a normalized machine-readable intent without creating or mutating workspace artifacts.
  2. Agent can resolve prompt, markdown, and structured JSON inputs into a canonical `QSpec` plus execution plan through the same control-plane surface.
  3. Semantically equivalent ingress inputs produce the same workload identity and semantic hash.
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Lock down CLI prompt, resolve, and plan no-write behavior plus cross-ingress parity
- [x] 01-02-PLAN.md — Lock down shared resolver canonicalization and semantic hash parity across equivalent ingress
- [x] 01-03-PLAN.md — Close the semantic-hash artifact gap in `tests/test_qspec_semantics.py`

### Phase 2: Trusted Revision Artifacts
**Goal**: Completed runs become trusted, replayable runtime revisions with stable artifact evidence.
**Depends on**: Phase 1
**Requirements**: RUNT-01, RUNT-03
**Success Criteria** (what must be TRUE):
  1. After execution, agent can reopen a revision and find its persisted `intent`, `plan`, `qspec`, `report`, `manifest`, and revision-scoped event records.
  2. Agent can replay or import a completed revision from persisted runtime artifacts without relying on the original ingress text.
  3. If provenance, revision identity, or integrity metadata no longer matches expectations, replay and import stop with a blocking failure instead of silently continuing.
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Persist self-describing revision artifacts and revision-scoped event snapshots
- [x] 02-02-PLAN.md — Fail closed on trusted replay/import drift while preserving legacy and baseline compatibility
- [x] 02-03-PLAN.md — Bind additive manifest trust blocks to canonical revision history and close the revision-artifact regression gap
- [x] 02-04-PLAN.md — Pin current-workspace replay to immutable history and align legacy fallback with replay-integrity evidence

### Phase 3: Concurrent Workspace Safety
**Goal**: Multiple agents or CI jobs can target one workspace without corrupting runtime state.
**Depends on**: Phase 2
**Requirements**: RUNT-02
**Success Criteria** (what must be TRUE):
  1. When concurrent writers target the same workspace, FluxQ serializes or rejects conflicting mutations instead of producing mixed `current` and `history` artifacts.
  2. If a write is interrupted mid-run, the workspace remains readable and the last valid revision stays intact.
  3. Agent or CI logs receive a clear machine-readable conflict or recovery signal when a write cannot be committed safely.
**Plans**: 4 plans

Plans:
- [x] 03-01-PLAN.md — Add the workspace lease and atomic alias-write primitives that preserve the current/history contract
- [x] 03-02-PLAN.md — Define stable machine-readable CLI conflict and recovery signals for shared-workspace failures
- [x] 03-03-PLAN.md — Guard the full exec mutation graph, including alias promotion, manifests, and event streams
- [x] 03-04-PLAN.md — Apply the workspace safety contract to compare, benchmark, doctor, baseline, export, and pack writers

### Phase 4: Policy Acceptance Gates
**Goal**: Agents and CI can accept or reject runtime revisions directly from FluxQ policy surfaces.
**Depends on**: Phase 3
**Requirements**: POLC-01, POLC-02, POLC-03
**Success Criteria** (what must be TRUE):
  1. Agent or CI can compare a revision against baseline state and fail on selected drift classes using FluxQ output and exit behavior alone.
  2. Agent or CI can use benchmark results as policy evidence, including compare-to-baseline flows, without custom wrapper logic.
  3. Agent or CI can run doctor in CI-oriented mode and receive explicit blocking versus advisory outcomes in machine-readable form.
**Plans**: 4 plans

Plans:
- [ ] 04-01-PLAN.md — Repair the local Phase 4 validation path so Ruff, MyPy, and the policy-gate pytest suite are executable from this workspace
- [ ] 04-02-PLAN.md — Lock baseline/current compare fail-on behavior and schema-versioned compare persistence for POLC-01
- [ ] 04-03-PLAN.md — Turn benchmark evidence plus saved baselines into a FluxQ-native accept/reject gate with provenance-safe history persistence
- [ ] 04-04-PLAN.md — Add `doctor --ci` with explicit blocking/advisory outputs and verdict-driven exit behavior

### Phase 5: Verified Delivery Bundles
**Goal**: Trusted runtime revisions can move between environments as portable bundles without losing provenance.
**Depends on**: Phase 4
**Requirements**: DELV-01, DELV-02, DELV-03
**Success Criteria** (what must be TRUE):
  1. Agent can package one revision into a portable bundle that contains the core runtime objects, selected export outputs, and trust metadata needed downstream.
  2. Outside the original workspace, agent can inspect a bundle and determine whether its provenance and integrity checks pass before using it.
  3. Agent can unpack or re-import a verified bundle into a downstream workflow and continue from the same revision evidence.
**Plans**: 3 plans

Plans:
- [x] 05-01-PLAN.md — Harden `qrun pack` into a path-safe, non-destructive bundle producer with bundle-local trust metadata
- [x] 05-02-PLAN.md — Verify copied bundles outside the source workspace with digest-backed `qrun pack-inspect`
- [x] 05-03-PLAN.md — Re-import a verified bundle into a downstream workspace and continue from the same revision evidence

### Phase 6: Runtime Adoption Surface
**Goal**: The repository explains FluxQ as a runtime/control-plane product and shows how agents or CI should adopt it.
**Depends on**: Phase 5
**Requirements**: SURF-01, SURF-02, SURF-03
**Success Criteria** (what must be TRUE):
  1. A new reader sees FluxQ described consistently as an agent-first quantum runtime CLI rather than a generator demo across the main docs and examples.
  2. Repository examples show an end-to-end agent or CI runtime workflow covering ingress, execution, policy evaluation, and delivery handoff.
  3. Release and versioning notes tell adopters which runtime contracts are stable, which are still evolving, and how to consume them safely.
**Plans**: 3 plans

Plans:
- [x] 06-01-PLAN.md — Align README and release-notes quickstart around one runtime-first adoption path
- [x] 06-02-PLAN.md — Document a canonical agent/CI adoption workflow across integration assets and case study
- [x] 06-03-PLAN.md — Clarify stable/evolving/optional runtime contracts and align package metadata

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Canonical Ingress Resolution | 3/3 | Complete | 2026-04-12 |
| 2. Trusted Revision Artifacts | 4/4 | Complete | 2026-04-12 |
| 3. Concurrent Workspace Safety | 4/4 | Complete | 2026-04-12 |
| 4. Policy Acceptance Gates | 0/4 | Not started | - |
| 5. Verified Delivery Bundles | 3/3 | Complete | 2026-04-14 |
| 6. Runtime Adoption Surface | 3/3 | Complete | 2026-04-15 |
