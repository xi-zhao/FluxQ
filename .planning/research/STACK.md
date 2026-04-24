# Technology Stack

**Project:** FluxQ v1.1 Remote Execution
**Researched:** 2026-04-18
**Scope:** Only stack additions or changes needed for one trustworthy remote execution provider path. The existing Python 3.11 + `uv` + Typer + Pydantic + Qiskit-first local control plane stays intact.
**Overall confidence:** HIGH

## Recommendation

FluxQ v1.1 should add exactly one remote provider path: **IBM Quantum Platform through `qiskit-ibm-runtime` in Qiskit Runtime job mode**.

This is the narrowest credible extension of the current architecture. It preserves the existing `QSpec` truth layer, keeps Qiskit as the execution-language spine, uses the provider's official Python client instead of a hand-rolled REST integration, and exposes stable primitives for submission, job lookup, status polling, result retrieval, and usage metrics. It also fits FluxQ's trust model: persist immutable local artifacts while reopening remote jobs by provider `job_id`.

The key design choice is to standardize on **`channel="ibm_quantum_platform"`**, **explicit `instance` selection**, and **job mode first**. Job mode avoids the plan-dependent complexity of session scheduling and TTL management while still allowing FluxQ to prove remote submission, remote lifecycle tracking, and fail-closed machine output.

## Unchanged Foundation

Do not change these for v1.1:

| Technology | Current Version | Keep? | Why |
|------------|-----------------|-------|-----|
| Python | 3.11 | Yes | `qiskit-ibm-runtime` supports Python 3.11 and does not force a runtime upgrade. |
| Typer | 0.24.1 | Yes | Current CLI surface already maps cleanly to remote submit/status/show flows. |
| Pydantic | 2.12.5 | Yes | Existing schema-versioned contracts remain the right mechanism for remote machine output. |
| Qiskit | 2.3.1 | Yes | IBM's current docs use Qiskit 2.3.x and Qiskit Runtime primitives build directly on the Qiskit primitives interface. |
| Qiskit Aer | 0.17.2 | Yes | Local simulation stays the baseline and fallback trust path. |

## Recommended Stack Additions / Changes

### Core Remote Provider

| Technology | Version | Purpose | Why | Integration Points |
|------------|---------|---------|-----|--------------------|
| `qiskit-ibm-runtime` | `~=0.46` | Official IBM Quantum Platform client for auth, backend discovery, primitive submission, job lifecycle, and result retrieval | Current PyPI latest is `0.46.1` (published 2026-03-23). IBM docs and release notes show this is the supported path on the post-Classic platform. | Add as an **optional extra** in `pyproject.toml`; register in `src/quantum_runtime/runtime/backend_registry.py`; consume from `src/quantum_runtime/runtime/executor.py`; validate from `src/quantum_runtime/runtime/doctor.py`; persist metadata through `src/quantum_runtime/reporters/writer.py` and `src/quantum_runtime/runtime/run_manifest.py`. |

### Service Dependencies

| Dependency | Version | Purpose | Why | Integration Points |
|------------|---------|---------|-----|--------------------|
| IBM Quantum Platform account | Current platform service | Required provider account | Remote execution needs an IBM Quantum Platform identity, not a local-only Python dependency. | Document and validate externally; do not treat as workspace state. |
| IBM Cloud API key | N/A | Runtime authentication credential | `QiskitRuntimeService` authenticates with the IBM Cloud API key. | Resolve from env or provider-saved account; never persist the secret in `.quantum/`. |
| IBM Quantum instance CRN or instance name | N/A | Target service instance selection | IBM docs say `instance` is optional but recommend providing it; that reduces ambiguity and extra instance-selection calls. | Reuse existing constraint/config surfaces; persist only the non-secret CRN/name reference. |

### Required Provider APIs

| API / Class | Comes From | Purpose | When to Use |
|-------------|------------|---------|-------------|
| `QiskitRuntimeService` | `qiskit_ibm_runtime` | Authentication, backend lookup, job lookup, service-scoped operations | Always. This should be the single entry point for FluxQ's IBM adapter. |
| `SamplerV2` | `qiskit_ibm_runtime` | Remote shot-based execution returning sampled results | Default remote path for GHZ/Bell/QFT-style runs and any run whose durable output is sampling-based. |
| `EstimatorV2` | `qiskit_ibm_runtime` | Remote expectation-value execution | Only when the existing `QSpec.observables` / objective surface requires expectation values, especially for QAOA-style workloads. |
| `RuntimeJobV2` | `qiskit_ibm_runtime` | `job_id()`, `status()`, `result()`, `cancel()`, `metrics()`, `wait_for_final_state()` | Always for lifecycle tracking and restart-safe reopen. FluxQ should persist `job_id`, provider, instance, backend, primitive kind, and latest status. |
| `RuntimeEncoder` / `RuntimeDecoder` | `qiskit_ibm_runtime` | Provider-supported JSON serialization for raw job results | Use when storing the provider-native result snapshot alongside FluxQ's normalized report. Avoid custom JSON encoding for IBM result objects. |
| `SamplerOptions` / `EstimatorOptions` | `qiskit_ibm_runtime.options` | Bounded remote execution controls | v1.1 should expose only a small allowlist: `default_shots`, `default_precision`, and `max_execution_time`; keep mitigation knobs mostly out of the public CLI for now. |

## Opinionated Stack Shape

### Packaging

Add IBM support as an optional extra, not as a base dependency.

Reason:
- FluxQ's shipped wedge is still local-runtime trust.
- Local installs and CI should not require cloud-provider dependencies.
- `doctor` and `backend list` already model optional backends well.

Recommended shape:

```toml
[project.optional-dependencies]
ibm = [
  "qiskit-ibm-runtime~=0.46",
]
```

### Authentication Model

Use **provider-managed credentials or explicit env injection**, not FluxQ-managed secret storage.

Reason:
- IBM documents `QiskitRuntimeService.save_account()` for trusted environments and stores saved credentials under `$HOME/.qiskit/qiskit-ibm.json`.
- FluxQ's workspace is a revisioned artifact store, not a secrets vault.
- Persisting API keys inside `.quantum/` would weaken the trust boundary.

Recommended v1.1 behavior:
- Allow explicit credentials at runtime through environment or process injection.
- Allow a named saved account/profile for trusted developer machines.
- Persist only non-secret references in FluxQ artifacts, such as `provider`, `channel`, `instance`, `backend`, `job_id`, and `auth_source_kind`.

### Execution Mode

Use **job mode only** in v1.1.

Reason:
- IBM documents three execution modes, but job mode is the simplest trustworthy path for a single durable runtime object.
- Session mode is unavailable to Open Plan users.
- Batch/session add TTL, queue-reactivation, and cost-surface complexity that does not help FluxQ prove the first remote trust path.

Recommended v1.1 mapping:
- `SamplerV2(mode=backend)` or `EstimatorV2(mode=backend)` only.
- Defer `Session` and `Batch` to a later milestone after single-job reopen and policy gating are solid.

## Integration With Existing FluxQ Architecture

### `src/quantum_runtime/qspec/model.py`

Do not introduce a new IR.

Reuse existing fields:
- `backend_preferences`: add one new backend key, such as `ibm-runtime`
- `constraints.backend_provider`: map to IBM provider identity
- `constraints.backend_name`: carry the explicit target backend name
- `observables`: decide whether the adapter chooses `SamplerV2` or `EstimatorV2`

### `src/quantum_runtime/runtime/backend_registry.py`

Add a third backend descriptor for IBM Runtime.

Expected capability additions:
- `remote_submit: True`
- `remote_job_status: True`
- `remote_result_reopen: True`
- `estimator: True`
- `sampler: True`

The dependency record should resolve `qiskit_ibm_runtime` / `qiskit-ibm-runtime` exactly the same way the registry already resolves Qiskit Aer and Classiq.

### `src/quantum_runtime/runtime/executor.py`

Keep the local executor spine, but branch to a provider adapter after canonical `QSpec` resolution.

Remote adapter responsibilities:
- Choose `SamplerV2` vs `EstimatorV2`
- Build provider PUBs from the current canonicalized Qiskit circuit output
- Submit the job and capture `job_id`
- Optionally wait for completion when the caller asks for synchronous execution
- Normalize provider status, metrics, and result summary into `backend_reports`

The local workspace remains the source of record for FluxQ's trust surface. IBM remains the source of truth only for remote job state and raw provider results.

### `src/quantum_runtime/reporters/writer.py` and `src/quantum_runtime/runtime/run_manifest.py`

Extend existing report/manifest payloads additively.

Persist:
- provider name
- channel
- instance CRN or instance name
- backend name
- primitive kind (`sampler_v2` or `estimator_v2`)
- provider `job_id`
- remote status
- retrieved-at timestamp
- job metrics / usage summary
- digest and path for any provider-native result snapshot written locally

Do not replace the current report model with provider-native payloads.

### `src/quantum_runtime/runtime/doctor.py`

Add IBM Runtime validation as an optional backend health check.

Doctor should verify:
- `qiskit-ibm-runtime` importability
- selected backend key is known
- auth source is present when IBM remote execution is requested
- named account / explicit instance configuration is coherent

Doctor should not:
- require IBM credentials for purely local workspaces
- attempt to provision cloud instances

## What NOT To Add In v1.1

| Do Not Add | Why Not | What To Do Instead |
|------------|---------|--------------------|
| `qiskit-ibm-provider` | The repository was archived on 2024-07-24, and IBM's migration guidance says `backend.run` / `qiskit-ibm-provider` are no longer supported for Runtime. | Use `qiskit-ibm-runtime` primitives only. |
| Remote `backend.run` as FluxQ's IBM path | IBM's migration guide says the supported remote path is V2 primitives, not the old backend-run hardware flow. | Use `SamplerV2` and `EstimatorV2`. |
| Raw Qiskit Runtime REST client as the primary v1.1 integration | It duplicates auth, polling, status handling, and serialization logic already present in the official Python client. | Use `qiskit-ibm-runtime`; keep REST only as a future escape hatch for non-Python tooling. |
| IBM Cloud Resource Controller / provisioning SDKs | FluxQ v1.1 needs to consume an existing runtime instance, not manage tenant provisioning. | Require a pre-existing instance CRN or saved profile. |
| `qiskit[all]` | IBM examples use it for convenience, but FluxQ already has the required core Qiskit pieces and should keep install surface narrow. | Keep existing `qiskit` + `qiskit-aer`; add only `qiskit-ibm-runtime`. |
| First-class `Session` / `Batch` CLI support | Sessions are unavailable on Open Plan and both modes add TTL/cost semantics that complicate v1.1 trust guarantees. | Standardize on job mode first. |
| Additional provider SDKs (`amazon-braket-sdk`, Azure Quantum, etc.) | That would force a multi-provider auth, capability, and artifact matrix before the first remote path is proven. | Ship one IBM provider path only. |
| New database, queue, or remote state service | FluxQ already has a filesystem-backed revision/control-plane model. Extra infrastructure would be stack creep. | Persist remote metadata in the existing workspace artifacts and reopen by provider job ID. |
| Workspace secret persistence or custom keyring integration | FluxQ should not become a credential manager. | Use env injection or provider-managed saved accounts. |
| Error-mitigation add-ons / functions platform / optimizer frameworks | These widen the product from trusted remote execution into a higher-level optimization platform too early. | Expose only a minimal options allowlist on top of Runtime primitives. |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Provider client | `qiskit-ibm-runtime` | Raw Qiskit Runtime REST API | More code, more auth surface, no control-plane benefit for a Python CLI. |
| IBM access model | `QiskitRuntimeService(channel=\"ibm_quantum_platform\", token=..., instance=...)` or named saved account | Workspace-owned secrets | Violates FluxQ's artifact trust boundary. |
| Primitive choice | `SamplerV2` default, `EstimatorV2` when observables require it | Force everything through one primitive | Would either lose sampling parity or lose expectation-value capability already implied by current `QSpec`. |
| Execution mode | Job mode | Session / Batch | Too much lifecycle and cost complexity for the first remote milestone. |
| Packaging | Optional `ibm` extra | Base dependency | Makes local-only installs heavier for no immediate benefit. |

## Installation

```bash
# Add IBM Runtime support as an optional extra
uv add --optional ibm qiskit-ibm-runtime~=0.46

# For development or CI jobs that exercise the remote path
uv sync --extra dev --extra ibm
```

## Sources

- IBM Quantum Docs: Initialize your Qiskit Runtime service account
  - https://quantum.cloud.ibm.com/docs/en/guides/initialize-account
  - Used for: `ibm_quantum_platform` default channel, explicit `instance` recommendation, account initialization model
  - Confidence: HIGH

- IBM Quantum Docs: Save your login credentials
  - https://quantum.cloud.ibm.com/docs/en/guides/save-credentials
  - Used for: saved-account workflow, credential file location, trusted-environment guidance
  - Confidence: HIGH

- IBM Quantum Docs: QiskitRuntimeService API
  - https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service
  - Used for: service constructor surface, `instance`, `proxies`, `verify`, `private_endpoint`
  - Confidence: HIGH

- IBM Quantum Docs: SamplerV2 API
  - https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/sampler-v2
  - Used for: job-mode primitive interface and `RuntimeJobV2` return type
  - Confidence: HIGH

- IBM Quantum Docs: EstimatorV2 API
  - https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/estimator-v2
  - Used for: observable-driven execution path and `RuntimeJobV2` return type
  - Confidence: HIGH

- IBM Quantum Docs: Introduction to Qiskit Runtime execution modes
  - https://quantum.cloud.ibm.com/docs/en/guides/execution-modes
  - Used for: job vs batch vs session tradeoffs and Open Plan session restriction
  - Confidence: HIGH

- IBM Quantum Docs: Maximum execution time for Qiskit Runtime workloads
  - https://quantum.cloud.ibm.com/docs/en/guides/max-execution-time
  - Used for: `max_execution_time`, metrics/usage, TTL/cost implications, 50 MB input limit
  - Confidence: HIGH

- IBM Quantum Docs: Specify options
  - https://quantum.cloud.ibm.com/docs/en/guides/specify-runtime-options
  - Used for: minimal options allowlist, precedence, current version examples (`qiskit-ibm-runtime~=0.45.1`, `qiskit[all]~=2.3.1`)
  - Confidence: HIGH

- IBM Quantum Docs: Retrieve and save job results
  - https://quantum.cloud.ibm.com/docs/en/guides/save-jobs
  - Used for: `service.jobs()`, `service.job()`, durable job retrieval, `RuntimeEncoder` / `RuntimeDecoder`
  - Confidence: HIGH

- IBM Quantum Docs: Qiskit Runtime client release notes
  - https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/release-notes
  - Used for: removal of `ibm_quantum`, `ibm_quantum_platform` default direction, instance/job behavior on the new platform
  - Confidence: HIGH

- PyPI: `qiskit-ibm-runtime`
  - https://pypi.org/project/qiskit-ibm-runtime/
  - Used for: current release `0.46.1` on 2026-03-23 and Python version support
  - Confidence: HIGH

- GitHub: `Qiskit/qiskit-ibm-provider` archive status
  - https://github.com/Qiskit/qiskit-ibm-provider
  - Used for: explicit non-recommendation of the archived legacy provider package
  - Confidence: HIGH
