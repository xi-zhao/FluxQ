# Feature Landscape: v1.1 Remote Execution

**Domain:** Agent-first remote execution for FluxQ
**Researched:** 2026-04-18
**Overall confidence:** HIGH for provider capabilities, MEDIUM for milestone prioritization

## Milestone Framing

FluxQ v1.1 should behave as a trusted local control plane over remote compute, not as a second provider-specific CLI. That is an inference from two facts: FluxQ already has durable local run-object semantics, and IBM/Qiskit Runtime already exposes the raw remote primitives for accounts, backends, jobs, results, metrics, logs, and sessions.

For the first remote milestone, the right scope is **single-provider job-mode remote execution** with strong reopen, status, result, and policy behavior. Sessions, batches, multi-provider abstraction, and queue optimization add surface area faster than they add trust.

## Table Stakes

Features users will reasonably expect from a first remote milestone. Missing any of these makes remote execution feel incomplete.

| Feature | Why Expected | Complexity | Dependencies on Existing Local Surface |
|---------|--------------|------------|----------------------------------------|
| Non-interactive remote account/profile configuration | Agents and CI need token-based auth, explicit account selection, and deterministic instance or region choice without browser flows. | Medium | Extend `qrun init`/workspace config, `doctor`, stable JSON error payloads, and existing file-backed config patterns in `.quantum/`. |
| Canonical remote submit from existing ingress | A user should submit the same prompt, markdown intent, JSON intent, `QSpec`, or trusted report-backed run object remotely without a second DSL. | High | `prompt`/`resolve`/`plan`, `ResolvedRuntimeInput`, `QSpec`, current lowering flow, and `exec` orchestration. |
| Remote run handle persisted as a first-class revision | Submission must immediately create a durable local record that links FluxQ revision identity to provider job ID, backend, account/instance, and submit options. | High | Workspace manifest/history, `run_manifest.py`, `write_report()`, artifact provenance, and `TraceWriter`. |
| Remote status refresh and reopen by job ID | Agents need to resume after interruption, poll later, and reopen a remote run without re-submitting compute. | Medium | `status`, `show`, import/reopen patterns, `ImportResolution`, workspace alias/history handling. |
| Result hydration into the normal FluxQ report shape | Once a remote job completes, its result must materialize into the same inspectable/reportable object model used by local runs. | High | `ExecResult`, report writer, `inspect`, `compare`, `pack`, `pack-inspect`, and `pack-import`. |
| Remote cancel | Users expect to stop queued or running jobs when the provider still allows cancellation. | Medium | New remote lifecycle command(s), `status` surface, trace events, stable exit codes, and reason-code output. |
| Fail-closed remote error and state model | Unauthorized, quota, timeout, non-cancellable, failed, and drifted states must map to stable machine-readable reasons instead of raw provider text. | High | `contracts.py`, `observability.py`, `exit_codes.py`, policy/gate blocks, and current CLI JSON emitters. |
| Backend discovery and preflight target selection | Users need to see accessible backends, operational state, and pending load before submitting remote work. | Medium | Extend `backend list`, target-aware validation, `doctor`, and current backend capability reporting. |
| Remote metrics and logs retrieval | Agents need basic evidence after execution: usage/quantum time, provider timestamps, and provider logs where available. | Medium | Report schema versioning, `inspect`, trace/event writing, and machine-readable artifact persistence. |
| Submit-time guardrails for backend pinning and execution limits | Remote compute needs explicit backend targeting and execution limit knobs so runs stay reproducible and cost-aware. | Medium | `QSpec` compatibility layer, current exec options plumbing, backend validation, and policy surfaces. |

## Differentiators

These are the features that make FluxQ feel like an agent-first runtime control plane instead of a thin wrapper around the provider SDK.

| Feature | Value Proposition | Complexity | Dependencies on Existing Local Surface |
|---------|-------------------|------------|----------------------------------------|
| Compare-before-submit remote preview | Lets an agent see exactly what is about to run remotely and block on subject drift or policy failures before spending remote compute. | High | `baseline set`, `compare`, semantic hashing, policy gates, and current `show`/`status` summaries. |
| Reconcile-orphaned remote jobs without resubmission | If the CLI crashes after submit, FluxQ can reattach the existing provider job to workspace history instead of duplicating compute. | High | Trusted reopen/import flow, workspace revision manager, manifest integrity rules, and report-backed reopen behavior. |
| Provenance-grade remote manifest | A remote run should preserve semantic hash, provider job ID, backend identity, account/instance, timestamps, and result/metrics integrity in one auditable record. | High | `run_manifest.py`, artifact provenance, report writer, and immutable history directories. |
| Agent-optimized JSONL lifecycle watch | Remote execution should emit structured state transitions and next actions instead of spinner-only UX, so agents can branch automatically. | Medium | Existing `--jsonl` event-stream pattern, `TraceEvent`, `contracts.py`, and CLI output modes. |
| Policy-gated remote submit | Teams should be able to block remote submit on missing backend pin, disallowed region/instance, missing execution cap, or other trust rules. | High | Current policy/gate machinery, `doctor --ci`, backend inspection, and stable reason-code output. |
| Deferred hydration with local pack/compare continuity | FluxQ should allow "submit now, hydrate later" while keeping compare, inspect, and bundle workflows coherent once results land. | High | `inspect`, `compare`, `pack`, `pack-inspect`, `pack-import`, and trusted revision reopen paths. |

## Anti-Features

These should be explicit non-goals for the first remote milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Multi-provider support in v1.1 | Provider abstraction multiplies auth, lifecycle, and result-shape complexity before FluxQ proves one trustworthy remote path. | Ship one Qiskit/IBM Runtime path first and make provider boundaries explicit in manifests and contracts. |
| Session or batch orchestration as the default remote UX | IBM supports sessions, but they add extra lifecycle state, and Open Plan users cannot use session jobs. That is too much scope for the first remote milestone. | Start with plain job mode. Treat sessions as a later expansion once job-mode trust is solid. |
| Automatic backend selection as the default trusted behavior | The provider can auto-pick a backend, but FluxQ’s product value is reproducibility. Default auto-selection weakens auditability. | Require an explicit backend by default, or make `--backend auto` an explicit opt-in that records the chosen backend after submission. |
| Automatic retry or silent resubmission | Retries can duplicate spend, change execution context, and blur run identity. | Return explicit terminal state plus next actions; let the agent or CI decide whether to resubmit. |
| Interactive browser login or wizard-driven auth | It is hostile to CI and fragile for agents. | Support token-based configuration, saved provider credentials, and explicit workspace/profile references. |
| Rich real-time log streaming/websocket UI | It adds transport complexity without improving the core trust story. | Poll status, logs, and metrics with structured JSON or JSONL events. |
| Provider-native payloads that bypass `QSpec` | That would fracture FluxQ into "trusted local runs" and "opaque remote submissions." | Keep `QSpec` and report-backed inputs as the only submit surface. |
| Destructive remote-delete or post-submit metadata mutation as a normal workflow | The provider supports job deletion and tag replacement, but FluxQ’s product core is durable auditability. | Keep first-milestone remote history append-only on the FluxQ side; defer destructive/mutating provider operations until retention semantics are explicit. |
| Queue or cost optimization platform features | Useful later, but they are not the first proof of remote trust. | Limit v1.1 to submission, lifecycle, hydration, policy, and evidence capture. |

## Feature Dependencies

```text
Remote account/profile config + backend discovery
  -> canonical remote submit
  -> persisted remote run handle

Persisted remote run handle
  -> status refresh / reopen by job ID
  -> cancel
  -> result hydration

Result hydration
  -> inspect
  -> compare / baseline workflows
  -> pack / pack-inspect / pack-import

Policy-gated submit
  -> compare-before-submit
  -> fail-closed remote execution
```

## MVP Recommendation

Prioritize:

1. Non-interactive remote account/profile configuration plus backend discovery
2. Canonical remote submit that persists a local revision and provider job handle immediately
3. Remote status, reopen-by-job-ID, result hydration, and cancel
4. Fail-closed JSON/JSONL machine output with remote reason codes, metrics, and logs

One differentiator worth pulling into the first milestone:

1. Agent-optimized JSONL lifecycle watch

Defer:

- Sessions and batches
- Multi-provider support
- Automatic retry/resubmission
- Automatic backend selection as the default
- Destructive remote delete or metadata mutation

## Notes on Inference

- The recommendation to keep **job mode** as the only first-milestone execution mode is a product inference, not an IBM requirement. It follows from FluxQ’s trust-first scope and the extra lifecycle complexity that sessions introduce.
- The recommendation to require **explicit backend pinning by default** is also a product inference. IBM allows automatic backend selection in some paths, but FluxQ’s control-plane value is stronger when remote runs are reproducible by default.

## Sources

- IBM Quantum Docs, "Initialize your Qiskit Runtime service account" — account, instance, region, and plan selection. HIGH confidence. https://quantum.cloud.ibm.com/docs/en/guides/initialize-account
- IBM Quantum Docs, "Save your login credentials" — non-interactive credential saving, named accounts, and local credential storage behavior. HIGH confidence. https://quantum.cloud.ibm.com/docs/en/guides/save-credentials
- IBM Quantum Docs, "View backend details" — backend listing, backend status, and pending jobs. HIGH confidence. https://quantum.cloud.ibm.com/docs/en/guides/qpu-information
- IBM Quantum Docs, "Monitor or cancel a job" — job ID, status, result retrieval, cancellation, and execution-span metadata. HIGH confidence. https://quantum.cloud.ibm.com/docs/en/guides/monitor-job
- IBM Quantum Docs, "Retrieve and save job results" — reopen jobs later with `service.job()` or `service.jobs()`. HIGH confidence. https://quantum.cloud.ibm.com/docs/en/guides/save-jobs
- IBM Quantum Docs, "Maximum execution time for Qiskit Runtime workloads" — service timeouts, user-set execution caps, and metrics usage. HIGH confidence. https://quantum.cloud.ibm.com/docs/en/guides/max-execution-time
- IBM Quantum Docs, "Jobs" REST API — run/list/details/cancel/logs/metrics/results/delete/tags, job states, and submit rate limit. HIGH confidence. https://quantum.cloud.ibm.com/docs/en/api/qiskit-runtime-rest/tags/jobs
- IBM Quantum Docs, "Sessions" REST API and "Run jobs in a session" — session lifecycle, close semantics, and Open Plan limitations. HIGH confidence. https://quantum.cloud.ibm.com/docs/en/api/qiskit-runtime-rest/tags/sessions and https://quantum.cloud.ibm.com/docs/en/guides/run-jobs-session
