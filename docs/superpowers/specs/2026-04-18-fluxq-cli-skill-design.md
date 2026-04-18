# FluxQ CLI Skill Design

Date: `2026-04-18`  
Project: `FluxQ`  
Scope: repository-native project skill for FluxQ runtime workflows

## Goal

Create an in-repo FluxQ skill that ships with the repository, can be discovered by coding agents, and teaches the product as a runtime control-plane workflow rather than as a loose collection of commands.

The skill should help an agent recognize when FluxQ is the right tool, choose the correct command path, and stay within the product's current implementation boundaries.

## Constraints

- The skill must live in the repository and evolve with the CLI.
- The skill must be task-oriented, not a full command manual.
- The skill must be bilingual:
  - English should carry the discovery and trigger vocabulary.
  - Chinese should carry the operator guidance and explanation.
- The default mental model must be the full FluxQ lifecycle:
  - ingress
  - execution
  - trust loop
  - gates
  - delivery
- The skill should guide users interactively when an agent is helping them operate FluxQ.
- The skill must match the current product surface.
- The skill must not imply that remote IBM submission already exists.

## Deliverables

### 1. Canonical project skill

Path:

`./.agents/skills/fluxq-cli/SKILL.md`

Responsibilities:

- define when an agent should use FluxQ
- explain the default end-to-end FluxQ workflow
- route common task types to the right command family
- warn about common misuse patterns
- state current IBM boundaries clearly

### 2. Lightweight command reference

Path:

`./.agents/skills/fluxq-cli/quick-reference.md`

Responsibilities:

- provide concise, high-signal command snippets
- support the skill without turning `SKILL.md` into a manual
- group examples by workflow, not by alphabetized command name

## Options Considered

### Option A: single-file skill only

Put everything into one `SKILL.md`.

Pros:

- simplest layout
- low setup cost

Cons:

- likely to grow into a command manual
- harder to maintain as FluxQ evolves
- weak separation between discovery logic and command examples

### Option B: duplicate skill across multiple agent ecosystems

Create parallel copies under `.agents`, `.claude`, `.cursor`, and similar directories.

Pros:

- broad initial discoverability

Cons:

- high drift risk
- unnecessary duplication before the canonical project skill stabilizes

### Option C: canonical skill plus small reference file

Create one canonical repository skill under `.agents/skills/fluxq-cli/`, with a thin quick-reference file next to it.

Pros:

- keeps the skill task-oriented
- keeps examples maintainable
- makes future wrappers possible without copying core content
- best fit for a CLI that will keep growing

Cons:

- slightly more structure than a single file

Decision:

Choose **Option C**.

## Target User Experience

When an agent sees a task like:

- "turn this prompt into a revisioned quantum run"
- "compare current output with an approved baseline"
- "package this run for downstream delivery"
- "check whether IBM backend access is ready"

the skill should cause the agent to:

1. recognize FluxQ as the correct control-plane tool
2. choose the right workflow branch
3. avoid inventing unsupported capabilities
4. prefer the built-in trust and delivery loop over ad hoc scripting
5. guide the user toward the next correct command instead of dumping an unstructured command list

## Skill Structure

The skill should be organized like this:

### Frontmatter

- `name: fluxq-cli`
- description written in English for discovery
- description focused on *when to use* rather than *how the skill works*

Example shape:

> Use when working with FluxQ runtime workflows, including intent ingress, revision trust, compare or baseline decisions, delivery bundles, and IBM backend readiness checks.

### Sections in `SKILL.md`

1. `Overview`
   - FluxQ is a runtime control plane, not just a quantum code generator.
   - English + Chinese explanation.

2. `When to Use`
   - situations that should trigger FluxQ
   - situations where FluxQ is overkill

3. `Default Workflow`
   - the main closed loop:
     - prompt or intent ingress
     - resolve or plan
     - exec
     - baseline and compare
     - doctor and bench
     - pack, inspect, import

4. `Task Routing`
   - map common user intents to the right FluxQ entry point

5. `Quick Decisions`
   - natural language vs markdown intent
   - compare vs inspect vs show
   - when to use delivery commands

6. `IBM Readiness Boundary`
   - explain what exists today:
     - `qrun ibm configure`
     - `qrun backend list`
     - `qrun doctor --ci`
   - explain what does not exist yet:
     - remote submit and remote lifecycle commands

7. `Common Mistakes`
   - treating FluxQ like a chat generator
   - skipping baseline before trust-sensitive compare work
   - importing packs without inspection
   - implying IBM remote submit already exists

## Trigger Vocabulary

The English discovery language should cover terms that external agents are likely to search for:

- `intent`
- `prompt`
- `QSpec`
- `revision`
- `baseline`
- `compare`
- `replay`
- `doctor`
- `bench`
- `pack`
- `import`
- `IBM readiness`
- `backend readiness`
- `CI gate`
- `delivery bundle`

The Chinese explanatory language should cover the operator's mental model:

- 从自然语言或 intent 进入运行闭环
- 把一次运行固化成 revision
- 对比当前状态和批准版本
- 用 doctor 和 bench 做守门
- 把 revision 打成 bundle 并交付给下游

## Default Workflow Contract

The skill should bias agents toward this order:

1. `prompt` or `resolve` when the task starts from language or intent material
2. `plan` when the user needs a dry run or validation before execution
3. `exec` when a real revisioned runtime object should be produced
4. `baseline set` once a run becomes the approved reference
5. `compare` when checking workload, report, or trust drift
6. `doctor` and optional `bench` before continuing or shipping
7. `pack -> pack-inspect -> pack-import` for downstream delivery

This order matters because FluxQ's value is the trusted control-plane loop, not any single command in isolation.

## Interactive Guidance Contract

The skill should not behave like a static reference page when an agent is actively helping a user.

Instead, it should define a lightweight guidance style for live FluxQ usage:

1. identify the user's current stage first:
   - starting from natural language
   - starting from an intent file
   - checking trust or drift
   - preparing delivery
   - checking IBM readiness
2. if key context is missing, ask only one short question at a time
3. prefer giving one recommended next command, with brief alternatives only when they are materially different
4. explain why the next command is the right one now
5. tell the user what artifact, signal, or decision they should expect from that command
6. keep the user inside the FluxQ lifecycle instead of routing them into ad hoc scripting too early
7. for IBM-related tasks, stop at readiness guidance unless the product surface has actually added remote-submit features

In practice, the skill should encourage agent guidance like:

- "If you are starting from one sentence, begin with `qrun prompt` or `qrun exec --intent-text`."
- "If you want a dry run before producing a revision, use `qrun plan`."
- "If this revision is now approved, set a baseline before compare work."
- "Before shipping to another workspace, run `pack-inspect` before `pack-import`."

This keeps the skill useful during real operator interaction instead of only during offline task routing.

## Quick Reference Design

`quick-reference.md` should be intentionally compact and grouped by workflow:

### Fast path

- `qrun prompt`
- `qrun resolve --intent-text`
- `qrun plan --intent-text`
- `qrun exec --intent-text`

### Intent-file path

- `qrun init`
- `qrun resolve --intent-file`
- `qrun plan --intent-file`
- `qrun exec --intent-file`

### Trust loop

- `qrun baseline set`
- `qrun status`
- `qrun show`
- `qrun inspect`
- `qrun compare`

### Delivery loop

- `qrun doctor`
- `qrun bench`
- `qrun pack`
- `qrun pack-inspect`
- `qrun pack-import`

### IBM readiness

- `qrun ibm configure`
- `qrun backend list --workspace`
- `qrun doctor --ci`

The reference should explicitly say that IBM support is currently a readiness surface, not a submission surface.

## Validation Plan

The skill should be considered ready when it passes three checks:

### 1. Discovery check

The frontmatter and `When to Use` section make it obvious that this skill applies to:

- intent ingress tasks
- trusted revision and compare tasks
- delivery bundle tasks
- IBM readiness tasks

### 2. Routing check

Given representative requests, the skill guides the reader to the correct branch:

- "Run this natural language quantum request"
- "Compare current output to the approved version"
- "Package a revision for another workspace"
- "Check IBM backend readiness before remote work"

### 3. Boundary check

The skill never claims capabilities that belong to future phases:

- no remote job submission
- no remote lifecycle reopen or cancel
- no remote finalization workflow

### 4. Guidance check

Given live-user prompts, the skill should encourage a guided response instead of a command dump:

- "I have a prompt. What should I run first?"
- "I already executed once. How do I know if it still matches the approved version?"
- "I want to hand this run to another workspace safely."
- "Can I use IBM from this workspace yet?"

The expected behavior is:

- identify the stage
- recommend the next smallest useful command
- explain what it will tell the user
- avoid over-prescribing future commands before the current step is understood

## Future Evolution

The initial version should optimize for the current product surface.

When FluxQ adds future remote-submit capabilities, the preferred evolution path is:

1. update the canonical `.agents/skills/fluxq-cli/` skill
2. extend `quick-reference.md`
3. only then add thin wrappers for other agent ecosystems if needed

This keeps one source of truth inside the repository and lets the skill evolve with the CLI.

## Future Product Direction: CLI-Native Guidance

This skill can improve how agents guide users through FluxQ today, but it cannot by itself change the experience of users who run `qrun` directly in a shell without an agent.

That distinction should stay explicit:

- the skill owns agent-side guidance
- the CLI owns product-native guidance

If FluxQ later wants built-in operator guidance, that should be planned as a product feature, not hidden inside the skill. Candidate future surfaces include:

- `qrun guide`
- `qrun start`
- workflow-aware interactive help
- command-specific next-step hints in human-readable output

That future CLI work should reuse the same lifecycle model as the skill:

- ingress
- execution
- trust loop
- gates
- delivery

This gives the project a clean evolution path: the repository skill teaches agents now, and later product work can bring the same guidance into the CLI itself.
