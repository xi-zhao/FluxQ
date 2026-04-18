# Project Research Summary

**Project:** FluxQ v1.1 Remote Execution  
**Domain:** Agent-first quantum runtime control plane with one trusted remote provider path  
**Researched:** 2026-04-18  
**Confidence:** HIGH

## Executive Summary

FluxQ v1.1 should extend the existing local trust model to exactly one remote execution path: IBM Quantum Platform via `qiskit-ibm-runtime` in Qiskit Runtime job mode. Keep the current Python 3.11 + `uv` + Typer + Pydantic + Qiskit 2.3.x foundation intact, and add `qiskit-ibm-runtime~=0.46` as an optional `ibm` extra. `QSpec` remains the canonical workload truth, and OpenQASM 3 plus persisted local artifacts remain the audit surface.

The decisive architecture choice is to avoid treating remote execution as a synchronous branch of the current executor. A remote run should have a stable `attempt_id`, an immutable submission revision, an append-only remote lifecycle store, and a later terminal revision that exists only after FluxQ has fetched and normalized the provider outcome. This keeps compare, export, pack, and replay trust anchored in local persisted evidence rather than live provider state.

The main risk is scope dilution. Sessions, multi-provider support, automatic backend selection, retries, and provider-native lifecycle shortcuts all weaken reproducibility before the first remote path is trustworthy. v1.1 should stay narrow: explicit provider profile, explicit instance and backend, submit/status-sync/cancel/finalize flows, fail-closed JSON and JSONL output, and durable remote evidence.

## Key Findings

Detailed research: [STACK.md](/Users/xizhao/my_projects/Fluxq/Qcli/.planning/research/STACK.md), [FEATURES.md](/Users/xizhao/my_projects/Fluxq/Qcli/.planning/research/FEATURES.md), [ARCHITECTURE.md](/Users/xizhao/my_projects/Fluxq/Qcli/.planning/research/ARCHITECTURE.md), [PITFALLS.md](/Users/xizhao/my_projects/Fluxq/Qcli/.planning/research/PITFALLS.md)

### Recommended Provider / Stack Additions

- `qiskit-ibm-runtime~=0.46` as an optional `ibm` extra, not a base dependency.
- `QiskitRuntimeService(channel="ibm_quantum_platform", instance=...)` as the only supported provider entry point.
- `SamplerV2` as the default remote primitive; `EstimatorV2` only when `QSpec.observables` requires expectation values.
- IBM Quantum Platform account, IBM Cloud API key, and instance reference resolved outside `.quantum/`; FluxQ stores only non-secret references.
- Keep Python 3.11, `uv`, Typer, Pydantic, Qiskit 2.3.1, and Qiskit Aer unchanged.

### Table Stakes for v1.1

- Non-interactive remote auth/profile configuration plus backend discovery and preflight validation.
- Canonical remote submit from the existing ingress surfaces: prompt, markdown intent, JSON intent, `QSpec`, and trusted report-backed inputs.
- Persist a first-class local remote handle immediately on submit: `attempt_id`, submission revision, provider, instance, backend, primitive, `job_id`, and submit options.
- Remote status refresh and reopen by `job_id` without resubmitting compute.
- Terminal result hydration into the normal FluxQ report and manifest shape.
- Remote cancel with stable reason codes and machine-readable lifecycle output.
- Fail-closed JSON and JSONL output for auth failures, quota issues, timeouts, non-terminal states, and provider errors.
- Provider metrics, logs, and execution-limit evidence persisted locally for later inspect, compare, and pack flows.

### Biggest Architecture Choice

Separate remote attempt identity from revision identity. The v1.1 model should be:

1. Submission revision: immutable record of what FluxQ canonicalized and submitted.
2. Remote lifecycle evidence: append-only status snapshots keyed by `attempt_id`.
3. Terminal revision: a second immutable revision created only after FluxQ has fetched and normalized the remote outcome.

This is the core choice because it preserves the current product promise: immutable artifacts are trusted, mutable pointers are only projections, and live provider APIs are refresh sources rather than the source of replay truth.

### Top Pitfalls to Avoid

1. Treating remote execution as a thin branch inside the synchronous executor. Use a separate remote service/store boundary and keep workspace locks short.
2. Flattening provider lifecycle states into FluxQ's final verdict too early. Model submission state, provider state, and finalization state separately.
3. Allowing implicit instance or backend selection. Require explicit instance and backend for canonical execution and record the environment in immutable artifacts.
4. Leaking credentials into `.quantum/`, packs, or JSONL output. Store references only; resolve secrets from env or provider-managed saved accounts.
5. Depending on live provider state for replay, compare, or pack. Snapshot results, logs, metrics, and environment metadata locally before treating a remote run as final.

## Recommended v1.1 Scope Cut

Ship one provider, one mode, one trustworthy loop.

- Include: IBM Runtime only, job mode only, explicit backend pinning, submit, sync/status, reopen, cancel, terminal hydration, fail-closed observability, and terminal-revision compatibility with inspect/compare/pack.
- Defer: sessions, batches, multi-provider support, automatic backend selection by default, automatic retry or silent resubmission, provider-private/delete modes, direct REST integration, and queue or cost-optimization features.

If scope pressure appears, cut breadth before cutting trust. Keep durable evidence, state modeling, and finalization semantics; drop convenience features first.

## Suggested Requirement Grouping for Next Step

### Group 1: Provider Boundary and Configuration

Define the IBM Runtime adapter seam, optional dependency, auth/reference model, explicit instance and backend selection, backend discovery, and remote preflight rules.

### Group 2: Submission and Attempt Persistence

Define canonical remote submit from existing ingress, `attempt_id`, submission revision semantics, provider tagging/correlation, and append-only remote workspace storage.

### Group 3: Lifecycle Sync, Cancel, and Terminal Materialization

Define polling, reopen by `job_id`, cancel semantics, status mapping, final result retrieval, metrics/log capture, and terminal revision creation.

### Group 4: Read Models, Policy, and User-Facing Contracts

Extend `status`, `show`, `inspect`, `compare`, `export`, `pack`, JSON output, JSONL events, reason codes, and policy gates so remote runs remain agent-friendly and fail closed.

### Group 5: Recovery, Packaging, and Verification

Cover duplicate-submit recovery, secret scrubbing, pack/import integrity for remote artifacts, adapter contract tests, mocked lifecycle tests, and one low-cost live remote smoke lane.

Recommended planning order: Group 1 -> Group 2 -> Group 3 -> Group 4 -> Group 5. This follows the real dependency chain and avoids building read surfaces before the remote state model is trustworthy.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | The research converges on official IBM Runtime docs and a narrow additive dependency change. |
| Features | HIGH | Table stakes are consistent with provider capabilities and FluxQ's control-plane positioning. |
| Architecture | MEDIUM-HIGH | The attempt-vs-revision split is an inference, but it is strongly supported by FluxQ's existing immutable artifact model. |
| Pitfalls | HIGH | The failure modes are concrete and tied to provider lifecycle, auth, retention, and FluxQ trust guarantees. |

**Overall confidence:** HIGH

### Gaps to Address

- Decide the exact CLI surface for remote sync and cancel: new `qrun remote ...` commands versus additive extensions to existing commands.
- Define the canonical state mapping table from IBM job states to FluxQ machine-readable reasons and readiness semantics.
- Decide the minimum remote environment block required for compare and baseline trust, especially backend properties, calibration identifiers, runtime image, and provider version.
- Confirm the smallest live-provider CI lane that is cheap enough to keep but strong enough to catch auth and lifecycle regressions.

## Sources

### Primary

- [PROJECT.md](/Users/xizhao/my_projects/Fluxq/Qcli/.planning/PROJECT.md) - v1.1 goal, scope, and product constraints
- [STACK.md](/Users/xizhao/my_projects/Fluxq/Qcli/.planning/research/STACK.md) - recommended IBM Runtime stack additions
- [FEATURES.md](/Users/xizhao/my_projects/Fluxq/Qcli/.planning/research/FEATURES.md) - table stakes, differentiators, anti-features
- [ARCHITECTURE.md](/Users/xizhao/my_projects/Fluxq/Qcli/.planning/research/ARCHITECTURE.md) - attempt/revision architecture and workspace shape
- [PITFALLS.md](/Users/xizhao/my_projects/Fluxq/Qcli/.planning/research/PITFALLS.md) - remote lifecycle and trust failure modes
- IBM Quantum docs cited throughout the research set - account init, saved credentials, execution modes, jobs, results, limits, and Runtime APIs

---
*Research completed: 2026-04-18*  
*Ready for roadmap: yes*
