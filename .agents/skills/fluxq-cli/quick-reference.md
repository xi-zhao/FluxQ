# FluxQ CLI Quick Reference / FluxQ CLI 快速速查

This file complements `SKILL.md`. Commands are grouped by workflow instead of by subcommand name.

这份文件配合 `SKILL.md` 使用，重点是高频工作流，不是完整参数手册。

## Fast Path From One Sentence / 一句话快通道

```bash
qrun prompt "Build a 4-qubit GHZ circuit and measure all qubits." --json
qrun plan --workspace .quantum --intent-text "Build a 4-qubit GHZ circuit and measure all qubits." --json
qrun exec --workspace .quantum --intent-text "Build a 4-qubit GHZ circuit and measure all qubits." --json
```

Use this path when the user starts from one short prompt.

适合从一句自然语言直接进入 FluxQ。

## Intent-File Path / Intent 文件闭环

```bash
qrun init --workspace .quantum --json
qrun resolve --workspace .quantum --intent-file examples/intent-qaoa-maxcut-sweep.md --json
qrun plan --workspace .quantum --intent-file examples/intent-qaoa-maxcut-sweep.md --json
qrun exec --workspace .quantum --intent-file examples/intent-qaoa-maxcut-sweep.md --json
```

Use this path when the experiment has explicit constraints, exports, or parameter sweeps.

参数扫描、导出要求、约束较多时，优先走 intent 文件。

## Trust Loop / 信任闭环

```bash
qrun baseline set --workspace .quantum --revision rev_000001 --json
qrun status --workspace .quantum --json
qrun show --workspace .quantum --json
qrun inspect --workspace .quantum --json
qrun compare --workspace .quantum --baseline --json
```

Use this path when the user wants to approve, inspect, or compare trusted workspace state.

当你要“批准一个版本”或判断“现在和批准版本有没有漂移”时，用这一组。

## Delivery Loop / 交付闭环

```bash
qrun doctor --workspace .quantum --json --ci
qrun bench --workspace .quantum --json
qrun pack --workspace .quantum --revision rev_000001 --json
qrun pack-inspect --pack-root .quantum/packs/rev_000001 --json
qrun pack-import --pack-root .quantum/packs/rev_000001 --workspace downstream/.quantum --json
```

Run `pack-inspect` before `pack-import`.

一定先 `pack-inspect`，再 `pack-import`。

## IBM Readiness / IBM 就绪性

```bash
qrun ibm configure --workspace .quantum --credential-mode env --token-env QISKIT_IBM_TOKEN --instance "<instance-crn>" --json
qrun backend list --workspace .quantum --json
qrun doctor --workspace .quantum --json --ci
```

This is a readiness surface only. Do not present it as remote job submission.

这里现在只覆盖就绪性检查，不要把它说成远程任务提交。

## Structured Output / 结构化输出

```bash
qrun exec --workspace .quantum --intent-file examples/intent-ghz.md --jsonl
qrun compare --workspace .quantum --baseline --json
qrun doctor --workspace .quantum --json --ci
```

Prefer `--json` or `--jsonl` when another agent, script, or CI job will consume the result.

只要后面还有 agent、脚本或 CI 消费结果，优先走结构化输出。
