# Requirements: FluxQ

**Defined:** 2026-04-12
**Core Value:** An agent or team can trust a FluxQ run as a durable runtime object that is reproducible, comparable, and deliverable, rather than as a one-off generated code snippet.

## v1 Requirements

Requirements for the next milestone of FluxQ’s runtime-first product surface.

### Ingress

- [ ] **INGR-01**: Agent can submit prompt text and receive a normalized machine-readable intent without mutating workspace state
- [ ] **INGR-02**: Agent can resolve prompt, markdown intent, and structured JSON intent into a canonical `QSpec` plus execution plan
- [ ] **INGR-03**: Semantically equivalent ingress inputs resolve to the same workload identity and semantic hash

### Runtime Workspace

- [ ] **RUNT-01**: Each executed revision persists `intent`, `plan`, `qspec`, `report`, `manifest`, and revision-scoped events as stable runtime artifacts
- [x] **RUNT-02**: Workspace writes are safe under concurrent agent or CI activity instead of assuming a single writer
- [ ] **RUNT-03**: Replay and import paths fail closed when provenance or integrity no longer matches the expected revision

### Policy And Comparison

- [x] **POLC-01**: Agent can compare current state against baseline and fail on specific drift classes without external wrapper logic
- [x] **POLC-02**: Agent can use benchmark results as policy evidence, including compare-to-baseline workflows
- [x] **POLC-03**: Agent can use doctor results in CI-oriented mode with clear blocking versus advisory outputs

### Delivery

- [ ] **DELV-01**: Agent can package one revision into a portable delivery bundle that includes the core runtime objects and export outputs
- [ ] **DELV-02**: Agent can inspect and verify a delivery bundle outside the original workspace
- [ ] **DELV-03**: Agent can unpack or re-import a verified delivery bundle into downstream workflows

### Integrations And Product Surface

- [ ] **SURF-01**: Public docs and examples consistently describe FluxQ as an agent-first quantum runtime CLI
- [ ] **SURF-02**: Repository includes concrete CI or agent integration examples that show end-to-end runtime workflows
- [ ] **SURF-03**: Release/versioning artifacts clearly describe what runtime contracts are stable and what is still evolving

## v2 Requirements

Deferred until the local runtime contract is stronger.

### Remote Execution

- **REMT-01**: User can submit a canonical run to remote quantum providers
- **REMT-02**: User can track remote job lifecycle through the same control-plane abstractions

### Advanced Optimization

- **OPTM-01**: User can run optimizer-driven parameter search beyond bounded local bindings and sweeps
- **OPTM-02**: User can use gradient or hybrid-loop workflows as first-class runtime operations

### Expanded Ecosystem

- **ECOS-01**: User can target a broader provider matrix with first-party parity guarantees
- **ECOS-02**: User can use richer import/export interchange profiles across external platforms

## Out of Scope

| Feature | Reason |
|---------|--------|
| New quantum language / DSL | FluxQ should orchestrate runtime objects, not become a competing language surface |
| General chat assistant UX | Prompt text is ingress only; the durable runtime object is the product center |
| Broad provider expansion now | Local runtime maturity and trust surfaces have higher leverage |
| Full optimizer platform in current milestone | It expands scope before delivery and policy surfaces are complete |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INGR-01 | Phase 1 | Complete |
| INGR-02 | Phase 1 | Complete |
| INGR-03 | Phase 1 | Complete |
| RUNT-01 | Phase 2 | Complete |
| RUNT-02 | Phase 3 | Complete |
| RUNT-03 | Phase 2 | Complete |
| POLC-01 | Phase 4 | Complete |
| POLC-02 | Phase 4 | Complete |
| POLC-03 | Phase 4 | Complete |
| DELV-01 | Phase 5 | Pending |
| DELV-02 | Phase 5 | Pending |
| DELV-03 | Phase 5 | Pending |
| SURF-01 | Phase 6 | Pending |
| SURF-02 | Phase 6 | Pending |
| SURF-03 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-12*
*Last updated: 2026-04-12 after Phase 3 completion*
