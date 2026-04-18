# Requirements: FluxQ

**Defined:** 2026-04-18
**Core Value:** An agent or team can trust a FluxQ run as a durable runtime object that is reproducible, comparable, and deliverable, rather than as a one-off generated code snippet.

## v1.1 Requirements

Requirements for the v1.1 Remote Execution milestone.

### Remote Access

- [x] **AUTH-01**: User can configure IBM Quantum Platform credentials and instance selection non-interactively for local agents and CI
- [ ] **BACK-01**: User can list compatible remote backends and see readiness details before remote submission

### Remote Execution

- [ ] **REMT-01**: User can submit a canonical run to IBM Quantum Platform through the same ingress and `QSpec` surface used locally
- [ ] **REMT-02**: User receives a persisted FluxQ remote attempt record with provider job handle, backend, instance, and submit-time provenance immediately after successful submission

### Remote Lifecycle

- [ ] **REMT-03**: User can reopen, poll, and cancel a remote job without resubmitting compute
- [ ] **REMT-04**: User can materialize a terminal remote job into immutable local revision artifacts that remain inspectable, comparable, and packable offline

### Remote Observability

- [ ] **OBSV-01**: Agent or CI can consume fail-closed schema-versioned JSON and JSONL output for remote submit, lifecycle, finalization, and recovery states

## v2 Requirements

Deferred until the first remote provider path is trustworthy.

### Remote Execution

- **REMT-05**: User can use session or batch execution modes as first-class remote lifecycle options

### Expanded Ecosystem

- **ECOS-01**: User can target a broader provider matrix with first-party parity guarantees
- **ECOS-02**: User can use richer import/export interchange profiles across external platforms

### Advanced Optimization

- **OPTM-01**: User can run optimizer-driven parameter search beyond bounded local bindings and sweeps
- **OPTM-02**: User can use gradient or hybrid-loop workflows as first-class runtime operations

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-provider support in v1.1 | First prove one trustworthy remote provider path before widening the matrix |
| Session or batch execution as the default v1.1 UX | Job mode is the narrowest trustworthy first remote slice |
| Automatic backend selection by default | Canonical remote runs should stay reproducible and environment-explicit |
| Automatic retry or silent resubmission | Retries can duplicate spend and blur run identity |
| Provider-private or destructive remote mutation flows | FluxQ should not weaken replayability or auditability before retention semantics are explicit |
| Full optimizer platform in v1.1 | Remote submission and lifecycle trust come first |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 9 | Complete |
| BACK-01 | Phase 9 | Pending |
| REMT-01 | Phase 10 | Pending |
| REMT-02 | Phase 10 | Pending |
| REMT-03 | Phase 11 | Pending |
| REMT-04 | Phase 12 | Pending |
| OBSV-01 | Phase 13 | Pending |

**Coverage:**
- v1.1 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-18*
*Last updated: 2026-04-18 after v1.1 roadmap creation*
