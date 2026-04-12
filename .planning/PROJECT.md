# FluxQ

## What This Is

FluxQ is an agent-first quantum runtime CLI for coding agents, CI pipelines, and quantum developers. It turns prompt text, markdown or JSON intents, canonical `QSpec`, and replayable reports into executable, revisioned, auditable quantum run objects that can be compared, exported, packaged, and trusted over time.

The product is not a chat assistant with quantum flavoring. Its product core is the runtime control plane: canonical normalization, immutable revision history, policy-grade comparison, reproducible delivery artifacts, and machine-readable observability around each run.

## Core Value

An agent or team can trust a FluxQ run as a durable runtime object that is reproducible, comparable, and deliverable, rather than as a one-off generated code snippet.

## Requirements

### Validated

- ✓ Agent or CI can initialize a revisioned local workspace and execute supported workloads from markdown intents, prompt text, structured JSON intents, `QSpec`, or replayable report inputs — existing
- ✓ Agent or CI can consume schema-versioned JSON and JSONL control-plane output for `plan`, `status`, `show`, `compare`, `export`, `bench`, `doctor`, and related commands — existing
- ✓ FluxQ persists canonical `qspec`, `report`, `manifest`, artifact provenance, replay-integrity metadata, and revision history for completed runs — existing
- ✓ FluxQ supports local parameterized workflows for `ghz`, `qaoa_ansatz`, and `hardware_efficient_ansatz`, including representative export points and target-aware diagnostics where available — existing
- ✓ Agent can use `prompt`, `resolve`, and `plan` as side-effect-free ingress surfaces with canonical identity parity locked down by regression coverage — Phase 1
- ✓ Agent can reopen trusted revisions from immutable history artifacts, and replay/import now fail closed on trusted drift while preserving explicit legacy-compatible reopen flows — Phase 2

### Active

- [ ] Delivery bundles can be verified, unpacked, and reused outside the original workspace without losing provenance or trust signals
- [ ] Policy surfaces support CI-ready acceptance decisions across compare, benchmark, and doctor flows without custom wrapper logic
- [ ] Workspace mutation is safe for multi-agent and CI concurrency instead of assuming a single writer
- [ ] Runtime documentation, release notes, and integration examples consistently describe FluxQ as a runtime/control-plane product rather than a generator demo

### Out of Scope

- Broad remote hardware submission and provider-matrix expansion before the local runtime contract is boringly reliable — this would dilute the core runtime wedge
- A new quantum programming language or DSL — FluxQ should orchestrate canonical runtime objects, not replace the ecosystem language layer
- General-purpose conversational assistant or IDE behavior — natural language is ingress, not the product center
- Full optimizer, gradient, or remote job-orchestration platform in the near term — current focus is deterministic local runtime quality and delivery

## Context

- This is a brownfield Python 3.11 CLI project built around `Typer`, `Pydantic`, `Qiskit`, optional `Classiq`, and a filesystem-backed workspace under `.quantum/`
- Existing code already implements the runtime spine: `init -> resolve/plan -> exec -> baseline -> compare -> export -> bench -> doctor -> pack`
- A fresh codebase map exists in `.planning/codebase/`, so the current architecture, conventions, testing strategy, and known concerns are already documented
- Recent work has already shifted the product toward the target position by adding `qrun prompt`, `qrun resolve`, persisted `intent.json` and `plan.json`, canonical runtime metadata on `QSpec`, delivery packing, and revision-scoped benchmark/doctor/compare artifacts
- The adjacent `aionrs/` tree is a separate Rust-sidecar integration surface, but the project’s core runtime remains the Python package declared in `pyproject.toml`

## Constraints

- **Tech Stack**: Python 3.11 + `uv` + local CLI packaging — the repository and CI are already standardized around this stack
- **Execution Model**: Qiskit-first local execution with OpenQASM 3 as the exchange layer — this matches the validated current product surface
- **Compatibility**: Evolve the current `QSpec` and CLI compatibly instead of introducing a breaking IR rewrite — existing control-plane consumers already exist
- **Observability**: Machine-readable output must remain schema-versioned, stable, and agent-friendly — this is part of the product contract, not implementation detail
- **Product Scope**: Local runtime maturity, replay trust, policy gating, and delivery bundles come before remote-submit breadth — this is the current strategic wedge

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Position FluxQ as an agent-first quantum runtime CLI | The strongest differentiation is reproducible runtime state, not “chatty” generation | — Pending |
| Treat prompt text as ingress, not source of truth | Agents need a canonical object to compare, re-run, and export | — Pending |
| Keep `QSpec` as the canonical truth layer and evolve it compatibly | Existing runtime code, tests, and artifacts already depend on it | — Pending |
| Stay Qiskit-first with OpenQASM 3 as the exchange layer | This keeps the current delivery story strong without widening the provider matrix too early | — Pending |
| Use revisioned filesystem artifacts as the primary control plane | This keeps FluxQ easy for agents, CI, and teams to consume and audit | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-12 after Phase 2 completion*
