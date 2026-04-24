---
name: fluxq-cli
description: Use when working with FluxQ runtime workflows in this repository, especially intent ingress, revision baselines, compare or replay trust, doctor or bench gates, delivery bundles, or IBM backend readiness checks
---

# FluxQ CLI

## Overview / 概览

FluxQ is a runtime control plane for revisioned quantum runs.

FluxQ 不是“帮你随手生成一段量子代码”的聊天工具。它更适合把 prompt、Markdown intent、JSON intent、`QSpec`、历史 `report`，变成可执行、可比较、可交付的运行对象。

## When to Use / 何时使用

Use this skill when the user wants to:

- start from a prompt or intent and produce a revisioned run
- inspect or approve current workspace state
- set or compare against a baseline
- run `doctor` or `bench` gates before continuing
- package a revision and import it into another workspace
- check IBM backend readiness before future remote work

Do not use this skill when:

- the user only wants a quick handwritten Qiskit snippet with no workspace, baseline, or delivery concerns
- the task requires IBM remote submit, lifecycle polling, cancellation, or terminal finalization; those workflows are planned but not yet shipped

## Guidance Contract / 交互引导约定

When helping a user live:

1. Identify the stage first: ingress, trust loop, gates, delivery, or IBM readiness.
2. If context is missing, ask one short question only.
3. Recommend one next command first, with brief alternatives only when they are materially different.
4. Explain what the command will produce, validate, or decide.
5. Keep the user inside the FluxQ lifecycle instead of jumping to ad hoc scripting too early.

## Default Workflow / 默认闭环

1. Start from prompt or intent material with `qrun prompt`, `qrun resolve`, or `qrun plan`.
2. Produce a real revisioned runtime object with `qrun exec`.
3. Approve the reference revision with `qrun baseline set`.
4. Check drift or trust with `qrun compare`, `qrun show`, or `qrun inspect`.
5. Gate before continuing with `qrun doctor` and optional `qrun bench`.
6. Deliver downstream with `qrun pack -> qrun pack-inspect -> qrun pack-import`.

## Task Routing / 任务分流

| Situation | Prefer |
| --- | --- |
| One sentence and the user wants an immediate run | `qrun exec --intent-text "..." --json` |
| One sentence but the user wants a preview first | `qrun prompt "..." --json` then `qrun plan --intent-text "..." --json` |
| Complex experiment with sweeps, exports, or constraints | Markdown or JSON intent plus `qrun resolve/plan/exec` |
| "What is the current workspace state?" | `qrun status` or `qrun show` |
| "Has the approved run drifted?" | `qrun compare --baseline --json` |
| "Can I ship this revision?" | `qrun doctor`, optional `qrun bench`, then the pack flow |
| "Can I use IBM from this workspace yet?" | `qrun ibm configure`, `qrun backend list`, `qrun doctor --ci` |

## Quick Decisions / 快速判断

- Use `--intent-text` for a short prompt; use an intent file when parameters, sweeps, exports, or constraints should stay explicit and reviewable.
- Use `qrun show` for one selected run, `qrun inspect` for revision or artifact health, and `qrun compare` for drift or policy decisions.
- Treat `qrun pack-inspect` as mandatory before `qrun pack-import`.
- Prefer `--json` or `--jsonl` whenever another agent or CI job needs structured signals.

## IBM Boundary / IBM 边界

Available today:

- `qrun ibm configure`
- `qrun backend list --workspace`
- `qrun doctor --ci`

Not available yet:

- remote job submission
- remote lifecycle reopen, poll, or cancel
- remote finalization into local artifacts

## Quick Reference / 快速速查

See `quick-reference.md` for compact command examples grouped by workflow.

## Common Mistakes / 常见误区

- Treating FluxQ like a prompt-only code generator
- Skipping `qrun baseline set` and then expecting trust-aware compare decisions
- Importing a pack without `qrun pack-inspect`
- Describing IBM readiness as if remote execution were already implemented
