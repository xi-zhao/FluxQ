# Product Strategy

## Category Definition

FluxQ is a `decision-grade quantum workflow runtime`.

That means it is built to help a team decide whether a quantum workflow is reproducible, comparable, trustworthy, and safe to continue in an agent or CI loop. It is not just another quantum CLI.

## Thesis

FluxQ should become the `workspace-native quantum workflow runtime` for AI-native quantum engineering.

The product is not a thin circuit generator, notebook replacement, or backend router. It wins when a team can move through:

`prompt / resolve -> qspec -> artifacts -> diagnostics -> report -> compare -> pack -> continue`

with stable workspace state, replayable history, trustworthy machine-readable outputs, and a canonical runtime object that agents can consume directly.

## Why Customers Need This

Quantum teams already know how to generate a circuit. Their harder problems are:

- generated quantum work is hard to replay a week later
- notebooks, scripts, Qiskit outputs, OpenQASM files, and optional backend outputs drift apart
- agent-generated changes are difficult to inspect, compare, and approve safely
- benchmark numbers are easy to overread because target assumptions and fallback paths are often implicit
- CI systems can lint code, but they usually cannot guard a quantum workflow with revision-aware semantics

FluxQ solves those workflow problems by treating the quantum run as a durable runtime object rather than a one-off file emission.

That runtime object now starts with prompt or structured intent ingress, normalizes through resolve, and persists revisioned `intent`, `plan`, `qspec`, `report`, `manifest`, and `events.jsonl` artifacts for later comparison, export, or packaging.

## Status Quo And Switching Trigger

Today, many target customers stitch together:

- notebooks
- ad hoc Python scripts
- Qiskit or backend-specific outputs
- custom CI glue
- agent prompts with little durable state

They switch when those workflows start to break under iteration:

- reruns stop being trustworthy
- agent-generated changes become hard to review
- revisions cannot be compared semantically
- benchmark numbers lose meaning because assumptions drift
- team workflows become dependent on individual memory instead of runtime state

## Product Promise

FluxQ gives customers:

- a deterministic workspace for quantum runs
- replayable reports and revision history
- semantic workload comparison instead of raw file diff alone
- explicit trust signals for replay integrity, benchmark provenance, and backend capability
- a CLI and JSON control plane that coding agents and CI systems can orchestrate directly

## Primary Customer Profiles

### 1. AI-Native Quantum R&D Teams

This is the beachhead market.

These teams:

- use coding agents to generate, revise, and compare quantum workflows
- need CI-grade reproducibility instead of notebook-only experimentation
- care about whether a workload changed semantically, not just whether a file changed
- need an auditable path from intent or QSpec to artifacts and diagnostics

This customer most directly values FluxQ's current strengths: workspace state, replay, compare, baseline guardrails, and benchmark honesty.

The daily user is usually an engineer or researcher.

The internal champion or buyer is usually the person who needs:

- reviewability across a team
- CI guardrails around agent-generated changes
- reproducible workflow state instead of notebook folklore

### 2. Quantum Platform And Internal Tooling Teams

These teams build internal developer platforms, agent hosts, or orchestration layers.

They need:

- stable file-based contracts
- machine-readable JSON output
- reliable exit codes
- trustworthy import, replay, and compare flows

For them, FluxQ is a runtime substrate, not just a CLI.

### 3. Applied Quantum Prototype And Consulting Teams

These teams repeatedly show progress to customers, internal stakeholders, or research partners.

They need to answer:

- what changed since the last revision
- whether benchmark differences are real or just assumption drift
- how to regenerate the same outputs without rebuilding context manually

FluxQ helps them keep prototypes explainable and presentable over time.

## Beachhead Market

The first market to optimize for is:

`teams using AI agents plus CI to iterate on quantum prototypes`

This wedge is attractive because:

- the pain is immediate and concrete
- the workflow is already file-based and automation-heavy
- trust, replay, and compare matter more than remote hardware breadth
- FluxQ already has the right product surface for this customer class

## Adoption Ladder

FluxQ should expand through a clear adoption path:

1. local CLI use for deterministic workspace output
2. saved reports and revision history for replay
3. baseline compare in CI for approval guardrails
4. target-aware benchmark decisions with explicit provenance
5. parameterized workflow iteration for repeated optimization loops

This matters because the product becomes more valuable as a runtime standard, not because it adds the most commands.

## Anti-ICP

FluxQ should not optimize first for:

- pure education users who only need a notebook demo
- one-off local experiments that never need replay or comparison
- customers whose primary need is immediate hardware submission across many vendors
- users who only want a code snippet generator

Those users may still benefit from FluxQ, but they should not drive roadmap priority.

## Jobs To Be Done

Customers hire FluxQ to:

1. turn a prompt or quantum task into a revisioned, replayable workspace instead of an ephemeral script
2. let agents and CI continue a workflow from trusted state without rebuilding context by hand
3. compare quantum revisions semantically and operationally
4. benchmark responsibly, with explicit target assumptions and fallback reasons
5. export the same workload into multiple representations without losing provenance
6. package one approved revision into a portable delivery boundary for downstream agents or CI

## Why FluxQ Wins

FluxQ should win on workflow quality, not backend count.

Its differentiation story is:

- revisioned workspace instead of scattered files
- replayable reports instead of one-time outputs
- semantic compare instead of raw diff alone
- prompt ingress and resolve normalization instead of prompt-text drift
- canonical `qspec` and revisioned runtime objects instead of ad hoc execution state
- policy and baseline guardrails instead of manual review only
- benchmark honesty instead of ambiguous performance theater

## Strategic Principles

1. Reproducibility before expansion  
New surfaces are less important than making existing runs replayable and trustworthy.

2. Trust surfaces are part of the product  
Exit codes, report schema, benchmark provenance, and backend capability descriptors are customer-facing APIs.

3. Optimize for decision-grade workflows  
FluxQ should help customers decide whether to continue, compare, approve, or reject a run.

4. Pattern depth beats pattern count  
Support the circuit families that exercise real planning, diagnostics, benchmarking, and agent orchestration value.

5. Remote execution is downstream of runtime maturity  
Do not chase hardware breadth before the local runtime model is boringly reliable.

## Trust Contract And Anti-Overclaim

FluxQ should be explicit about what it will not claim:

- it does not treat transpile metrics and synthesis metrics as equivalent by default
- it does not promise remote hardware execution as the near-term core product
- it does not claim that every benchmark result is hardware-comparable
- it does not market itself as a notebook replacement for all exploratory quantum work
- it does not optimize first for provider breadth

This is part of the brand, not just technical caution.

## What FluxQ Must Be Known For

If FluxQ earns a reputation, it should be for these things:

- replayable quantum workflow state
- reliable agent and CI integration
- semantic compare and baseline guardrails
- benchmark honesty instead of benchmark theater

## Near-Term Direction

The next product steps should keep reinforcing the beachhead use case:

- baseline-driven compare and approval workflows
- benchmark provenance and comparability clarity
- parameterized expectation-value workflows for `qaoa_ansatz` and `hardware_efficient_ansatz`
- stronger schema and trust-surface stability
- portable revision packaging and canonical workspace events for agent consumption

Remote submit belongs later, after these surfaces are stable enough to carry job orchestration safely.

## Proof Of Value

FluxQ should earn adoption by producing operational outcomes customers can feel:

- fewer unverifiable workflow changes landing through agents or CI
- faster approval decisions because baseline compare and replay trust are explicit
- clearer backend and benchmark interpretation because assumptions and fallback paths are visible

Those are better success measures than raw command count or backend count.

## Non-Goals

Reject work that mainly:

- widens the backend matrix without improving trust or replay
- pushes remote submit ahead of local runtime maturity
- increases benchmark ambiguity while sounding more impressive in demos
- optimizes for education/demo usage at the expense of the beachhead engineering workflow

## Decision Rule

When choosing the next feature, prefer the one that most improves:

1. replayability
2. trustworthiness
3. agent and CI leverage for quantum workflows

If a feature mostly increases backend count, novelty, or demo value without improving those three, it is probably not the right next step.
