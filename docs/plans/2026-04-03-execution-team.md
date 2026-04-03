# FluxQ Execution Team

## Mission

Build FluxQ into a decision-grade quantum runtime, not a thin quantum code generator.

The current execution plan follows `docs/plans/2026-04-03-post-v0.2-feature-roadmap.md`.

## Leadership

### CEO Reviewer

- Agent: `Lovelace`
- Role: product sequencing, wedge protection, non-goals, release positioning
- Authority:
  - decides what not to build yet
  - reviews whether each batch strengthens FluxQ's product moat
  - blocks roadmap drift toward low-leverage feature sprawl

### Quantum Master Reviewer

- Agent: `Plato`
- Role: quantum workflow value, technical credibility, benchmark honesty, semantic rigor
- Authority:
  - reviews quantum-facing semantics before and after implementation
  - blocks misleading benchmark or workflow claims
  - keeps pattern and observable work aligned with real quantum developer needs

## Core Implementation Team

### Runtime Lead

- Agent: `Lorentz`
- Ownership:
  - `src/quantum_runtime/cli.py`
  - `src/quantum_runtime/runtime/*`
  - report/import/compare/inspect orchestration
  - exit-code semantics
- Sprint 1 focus:
  - Batch A baseline workflows

### Quantum Systems Lead

- Agent: `Ptolemy`
- Ownership:
  - `src/quantum_runtime/qspec/*`
  - `src/quantum_runtime/intent/*`
  - quantum semantic validation
  - parameterized workflows and observables
- Sprint 1 focus:
  - design support for Batch A
  - lead Batch C afterward

### Benchmark and Backend Lead

- Agent: `Ohm`
- Ownership:
  - `src/quantum_runtime/diagnostics/*`
  - `src/quantum_runtime/backends/*`
  - backend capability metadata
  - target-aware benchmark parity
- Sprint 1 focus:
  - prepare Batch B interfaces while Batch A lands

### Release and Quality Lead

- Agent: `Banach`
- Ownership:
  - release docs
  - packaging and CI release gates
  - schema and regression guardrails
  - docs and test surfaces touched by each batch
- Sprint 1 focus:
  - keep baseline workflow rollout testable and releasable

## Operating Model

1. CEO reviewer and Quantum Master reviewer set the guardrails before major batch work begins.
2. One implementation lead owns each batch.
3. No batch is considered complete until:
   - owner verifies local behavior
   - Quantum Master signs off on technical credibility when relevant
   - CEO reviewer signs off on product leverage and non-goal discipline
   - Release and Quality Lead confirms docs/tests/release surfaces are aligned

## Batch Ownership

### Batch A: Baseline Workflows

- Primary owner: `Lorentz`
- Supporting reviewers: `Lovelace`, `Plato`, `Banach`
- Goal:
  - make FluxQ a CI and agent decision layer via baseline-aware compare and policy verdicts

### Batch B: Target-Aware Benchmarks

- Primary owner: `Ohm`
- Supporting reviewers: `Plato`, `Lovelace`, `Banach`
- Goal:
  - make backend comparison more target-aware and trustworthy

### Batch C: Parameterized Expectation-Value Workflows

- Primary owner: `Ptolemy`
- Supporting reviewers: `Plato`, `Lovelace`, `Banach`
- Goal:
  - move FluxQ from static circuit snapshots toward iterative quantum workflow usefulness

## Non-Goals The Team Must Defend

- no remote submit in this phase
- no backend matrix expansion for its own sake
- no long-tail pattern catalog expansion ahead of deeper workflow semantics
- no benchmark claims that blur structural, transpiled, and synthesis-backed modes

## Immediate Next Move

Start with `0.2.1` / Batch A:

- baseline references
- policy-driven compare verdicts
- baseline-aware inspect/report surfaces
- examples and tests that make the CI story obvious
