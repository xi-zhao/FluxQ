# Product Roadmap

## Thesis

Quantum Runtime CLI should become a `workspace-native quantum workflow runtime`, not a thin remote execution wrapper.

The product wins when an agent or developer can reliably move through this loop:

`intent -> qspec -> artifacts -> diagnostics -> report -> re-import -> continue`

That loop is the core product surface. More backends or remote execution only matter after the loop is reproducible, inspectable, and trusted.

## Product Goal

Build an agent-friendly quantum runtime CLI that is:

- reproducible enough for CI and autonomous agents
- trustworthy enough for benchmark and diagnostic consumption
- flexible enough to resume from workspace state instead of manual glue code

## Primary Users

1. Agent-hosted coding workflows
   Agents that need stable file-based orchestration instead of custom RPC integrations.

2. Quantum application prototyping
   Developers who want a deterministic path from high-level intent to executable artifacts and diagnostics.

3. Benchmark and backend comparison workflows
   Teams that need structured, replayable benchmark/report data instead of ad hoc notebooks.

## What Makes This Product Impactful

- It is easy to embed in an agent workflow.
- Its outputs are machine-readable and stable.
- Every run can be replayed or continued from workspace state.
- Benchmark numbers carry provenance and can be trusted.

## Strategic Principles

1. Reproducibility before expansion
   New execution surfaces are less valuable than making existing runs replayable from their own workspace artifacts.

2. Trust surfaces must be explicit
   Exit codes, report schema, backend capability descriptors, and benchmark provenance are part of the product, not internal implementation detail.

3. Pattern coverage should follow real workflow value
   Add circuit families that exercise planning, lowering, diagnostics, and benchmarking in meaningful ways.

4. Remote execution is a second-order capability
   It should arrive only after local runtime semantics are boringly reliable.

## Current State

The `0.1.x` foundation is mostly in place:

- deterministic workspace and revision tracking
- intent parsing and `QSpec` planning for the current core patterns
- Qiskit, OpenQASM 3, and Classiq emission
- local simulation, transpile validation, diagrams, and structural benchmarks
- hardened `inspect` / `doctor`
- unified backend capability registry
- report-based import paths for `exec`, `export`, and `bench`

This means the next phase should focus on product leverage, not raw feature count.

## Priority Order

### Priority 1: Complete The Import/Load Contract

Finish turning the workspace into the canonical runtime state surface.

Scope:

- support workspace/history/artifact references as first-class inputs
- standardize provenance in reports so any downstream step can explain what it loaded
- make replay and continuation deterministic across `exec`, `export`, `bench`, and `inspect`
- preserve structured, machine-readable failures for broken imports

Why first:

- this directly improves agent usability
- it compounds across every existing command
- it turns reports from passive outputs into active runtime state

### Priority 2: Expand High-Value Pattern Coverage

Deepen coverage where users will actually feel it.

Current priority set:

- `ghz`
- `bell`
- `qft`
- `hardware_efficient_ansatz`
- `qaoa_ansatz`

Next pattern work should only land if it strengthens:

- planner quality
- emitter quality
- diagnostics relevance
- benchmark/report usefulness

Why second:

- broader pattern support improves product reach
- but it only matters once the runtime loop around those patterns is dependable

### Priority 3: Standardize Trust Surfaces

Treat schemas and provenance as released product APIs.

Scope:

- report schema stability and schema versioning discipline
- explicit benchmark provenance and fallback markers
- backend capability descriptors with stable fields
- replay metadata that explains where a run came from

Why third:

- this is what lets CI, agent hosts, and future integrations trust the product without source-level knowledge

### Priority 4: Prepare Remote Submit, Do Not Ship It Prematurely

Remote hardware submission belongs to `0.3.x`, but only after the local runtime product is mature enough to support it.

Preparation work may include:

- job model design
- result persistence shape
- submission/status/fetch contract
- failure and retry semantics

But implementation should wait until the earlier priorities are complete.

## What Not To Do Yet

- do not add more backend providers just to widen the matrix
- do not build remote submit ahead of replay/import completeness
- do not chase benchmark sophistication that cannot be replayed from workspace state
- do not broaden the CLI with low-leverage commands that add surface area without workflow value

## Execution Sequence

### PR-A: Import/Load Completion

Goal:

- finish the replay and continuation contract

Candidate slices:

- artifact-reference imports
- workspace-reference imports
- history-based imports such as latest or named revision
- explicit provenance blocks in report JSON

### PR-B: Pattern Depth

Goal:

- strengthen the supported core patterns rather than adding long-tail novelty

Candidate slices:

- richer `qaoa_ansatz` arguments and validation
- stronger parameter handling and diagnostics
- additional goldens for high-value patterns

### PR-C: Trust Surface Stabilization

Goal:

- normalize the parts of the runtime that downstream automation consumes

Candidate slices:

- report provenance normalization
- stricter schema tests
- compatibility notes and schema guardrails in docs

### PR-D: Remote Submit Design Doc

Goal:

- write the contract before writing the integration

Candidate slices:

- job lifecycle
- persistence model
- backend adapter boundaries
- security and retry semantics

## Exit Criteria

### `0.2.x`

Ready when:

- workspace state is replayable across the main command surface
- the supported core patterns are stable and well-tested
- report and benchmark provenance are explicit and trustworthy

### `0.3.x`

Ready to start when:

- replay/import semantics are complete
- trust surfaces are stable enough for remote job orchestration
- at least one backend adapter can be designed without bending the local runtime model

## Product Risks

### If We Prioritize Wrong

- early remote submit turns the product into a brittle integration layer
- excessive backend expansion multiplies maintenance before the core runtime loop is complete
- benchmark improvements without provenance create impressive but low-trust output

### If We Prioritize Right

- the CLI becomes a credible runtime substrate for agents
- local workflow quality compounds into future remote execution support
- every new backend or integration has a stable substrate to sit on

## Decision Rule

When choosing the next feature, prefer the one that most improves:

1. replayability
2. trustworthiness
3. agent workflow leverage

If a feature improves none of those, it is probably not the right next step.
