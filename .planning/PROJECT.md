# FluxQ

## What This Is

FluxQ is an agent-first quantum runtime CLI for coding agents, CI pipelines, and quantum developers. It turns prompt text, markdown or JSON intents, canonical `QSpec`, and replayable reports into executable, revisioned, auditable quantum run objects that can be compared, exported, packaged, and trusted over time.

The product is not a chat assistant with quantum flavoring. Its product core is the runtime control plane: canonical normalization, immutable revision history, policy-grade comparison, reproducible delivery artifacts, and machine-readable observability around each run.

## Core Value

An agent or team can trust a FluxQ run as a durable runtime object that is reproducible, comparable, and deliverable, rather than as a one-off generated code snippet.

## Current Milestone: v1.1 Remote Execution

**Goal:** Extend FluxQ from a trustworthy local runtime control plane to a trustworthy remote execution control plane.

**Target features:**
- Submit canonical runs to one remote provider through the existing runtime object surface
- Track remote job lifecycle through the same control-plane abstractions used locally
- Preserve schema-versioned, fail-closed, agent-friendly machine output across local and remote flows

## Current State

- v1.0 Runtime Foundation shipped on 2026-04-18.
- FluxQ now has a complete local control-plane baseline across canonical ingress, trusted revision artifacts, shared-workspace safety, CI-ready policy gates, verified delivery bundles, and runtime-first adoption guidance.
- The v1.0 closeout repaired the surviving exec alias-promotion recovery hole and re-established a truthful verification and bookkeeping proof chain.
- v1.1 now focuses on carrying that same trust model into remote submission and remote lifecycle management without weakening the local contract.

## Requirements

### Validated

- ✓ Agent or CI can initialize a revisioned local workspace and execute supported workloads from markdown intents, prompt text, structured JSON intents, `QSpec`, or replayable report inputs — v1.0
- ✓ Agent or CI can consume schema-versioned JSON and JSONL control-plane output for `plan`, `status`, `show`, `compare`, `export`, `bench`, `doctor`, and related commands — v1.0
- ✓ FluxQ persists canonical `qspec`, `report`, `manifest`, artifact provenance, replay-integrity metadata, and revision history for completed runs — v1.0
- ✓ FluxQ supports local parameterized workflows for `ghz`, `qaoa_ansatz`, and `hardware_efficient_ansatz`, including representative export points and target-aware diagnostics where available — v1.0
- ✓ Agent can use `prompt`, `resolve`, and `plan` as side-effect-free ingress surfaces with canonical identity parity locked down by regression coverage — Phase 1
- ✓ Agent can reopen trusted revisions from immutable history artifacts, and replay/import now fail closed on trusted drift while preserving explicit legacy-compatible reopen flows — Phase 2
- ✓ Agent or CI can target one workspace from exec, compare, benchmark, doctor, baseline, export, and pack flows without silent current/history corruption, and blocked writes now surface structured conflict or recovery-required signals — Phase 3
- ✓ Policy surfaces now support CI-ready acceptance decisions across compare, benchmark, and doctor flows without custom wrapper logic — Phases 4 and 7
- ✓ Trusted delivery bundles can be packed, verified outside the source workspace, and re-imported into downstream workspaces without losing bundle-local trust signals — Phase 5
- ✓ Public docs, integration assets, and release/versioning surfaces now describe FluxQ consistently as a runtime/control-plane product, with an end-to-end adoption workflow and explicit stable/evolving/optional contract guidance — Phase 6

### Active

- [ ] `REMT-01`: Submit canonical runs to one remote provider through the same control-plane abstractions
- [ ] `REMT-02`: Track remote job lifecycle through the same runtime object surfaces and observability contracts
- [ ] `REMT-03`: Preserve schema-versioned, fail-closed machine output across local and remote execution flows

### Out of Scope

- A new quantum programming language or DSL — FluxQ should orchestrate canonical runtime objects, not replace the ecosystem language layer
- General-purpose conversational assistant or IDE behavior — natural language is ingress, not the product center
- Broad provider expansion in v1.1 — the first remote milestone should prove one trustworthy provider path before widening the matrix
- Full optimizer platform in v1.1 — remote execution and lifecycle trust come first
- Rich external interchange expansion in v1.1 — provider lifecycle parity is higher priority than wider ecosystem coverage

## Context

- This is a brownfield Python 3.11 CLI project built around `Typer`, `Pydantic`, `Qiskit`, optional `Classiq`, and a filesystem-backed workspace under `.quantum/`.
- The shipped v1.0 runtime spine now covers `init -> prompt/resolve/plan -> exec -> baseline -> compare -> export -> bench -> doctor -> pack -> pack-inspect -> pack-import`.
- `.planning/codebase/` contains a fresh codebase map, so architecture, conventions, tests, and concerns are already documented for the next milestone.
- The adjacent `aionrs/` tree remains a separate Rust-sidecar integration surface; the shipped product core is still the Python runtime package in `pyproject.toml`.

## Constraints

- **Tech Stack**: Python 3.11 + `uv` + local CLI packaging — the repository and CI are already standardized around this stack
- **Execution Model**: Qiskit-first local execution with OpenQASM 3 as the exchange layer — this matches the validated current product surface
- **Compatibility**: Evolve the current `QSpec` and CLI compatibly instead of introducing a breaking IR rewrite — existing control-plane consumers already exist
- **Observability**: Machine-readable output must remain schema-versioned, stable, and agent-friendly — this is part of the product contract, not implementation detail
- **Product Scope**: Local runtime maturity, replay trust, policy gating, and delivery bundles come before remote-submit breadth — this remains the strategic wedge

## Next Milestone Goals

- Extend FluxQ from a trustworthy local runtime control plane to a trustworthy remote execution control plane.
- Add remote submission and remote lifecycle tracking without weakening the durable runtime-object model.
- Preserve fail-closed and agent-friendly machine-output contracts while adding one clear remote provider path.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Position FluxQ as an agent-first quantum runtime CLI | The strongest differentiation is reproducible runtime state, not “chatty” generation | ✓ Validated in v1.0 |
| Treat prompt text as ingress, not source of truth | Agents need a canonical object to compare, re-run, and export | ✓ Validated in v1.0 |
| Keep `QSpec` as the canonical truth layer and evolve it compatibly | Existing runtime code, tests, and artifacts already depend on it | ✓ Validated in v1.0 |
| Stay Qiskit-first with OpenQASM 3 as the exchange layer | This keeps the current delivery story strong without widening the provider matrix too early | ✓ Validated in v1.0 |
| Use revisioned filesystem artifacts as the primary control plane | This keeps FluxQ easy for agents, CI, and teams to consume and audit | ✓ Validated in v1.0 |
| Split alias-mismatch recovery from interrupted-temp-file recovery in machine output | Agents need truthful remediation instead of one generic “doctor --fix” suggestion | ✓ Established in Phase 08 |
| Re-close bookkeeping only after the corrected proof chain is green | Milestone archives must describe what is true, not what was previously assumed | ✓ Established in Phase 08 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition**:
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone**:
1. Review the shipped product position against the actual codebase
2. Re-check the core value
3. Refresh Active / Out of Scope for the next milestone
4. Update Current State and Next Milestone Goals

---
*Last updated: 2026-04-18 for v1.1 Remote Execution kickoff*
