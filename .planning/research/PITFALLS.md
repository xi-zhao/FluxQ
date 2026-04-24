# Domain Pitfalls

**Domain:** Remote execution on top of FluxQ's local-first runtime control plane
**Researched:** 2026-04-18
**Assumption:** The first remote provider path is IBM Qiskit Runtime / IBM Quantum Platform. This is an inference from FluxQ's Qiskit-first constraint, not a stated requirement.
**Overall confidence:** HIGH for provider lifecycle, auth, and limit semantics; MEDIUM for exact phase mapping because the v1.1 roadmap is not yet written.

## Executive View

The biggest mistake would be to treat remote execution as "one more backend" inside the current synchronous `exec` path. FluxQ's shipped control plane assumes that one command produces one finished, locally durable, comparable run object under one short-lived authority boundary. Remote providers break that assumption: submission is asynchronous, results may arrive much later, provider states do not match FluxQ's current `ok/degraded/error` contract, and provider-side retention and auth rules can directly undermine FluxQ's replay and packaging guarantees.

The roadmap should therefore guard the milestone in four ordered steps: define the provider boundary and state model first, add submission and detached lifecycle persistence second, finalize remote runs into immutable local artifacts third, and only then widen into cancel/recovery/packaging/CI hardening. Sessions, batches, and multi-job orchestration should stay out of the first remote provider slice.

## Critical Pitfalls

### Pitfall 1: Treating remote submission as a thin branch inside the synchronous executor

**What goes wrong:** Remote submit, poll, and finalize logic gets added directly to `src/quantum_runtime/runtime/executor.py`, which currently reserves a revision and keeps the workspace writer model centered around one command producing one completed run.

**Why it happens:** The current local pipeline assumes one critical section, one revision reservation, one final report, and then alias promotion. Remote jobs are asynchronous and can outlive the CLI process by minutes or hours.

**Consequences:** FluxQ either holds the workspace lock across network waits, or it promotes `latest` aliases before the run is actually final. Both outcomes weaken the trust model.

**Warning signs:**
- `execute_intent()` starts calling provider SDK or REST APIs directly.
- `acquire_workspace_lock()` spans HTTP requests or `wait_for_final_state()`.
- `reports/latest.json` or `manifests/latest.json` represent `QUEUED` or `RUNNING` jobs.
- Remote polling is implemented by rerunning `exec` instead of a detached lifecycle command.

**Prevention:**
- Add a provider adapter layer outside the current local executor.
- Introduce a detached remote lifecycle store for submission and polling state.
- Reserve or promote authoritative revision artifacts only when FluxQ has locally persisted the final result snapshot, metrics, logs, and manifest.
- Keep submission, polling, and finalization as separate operations even if the CLI offers a convenience wrapper.

**Absorb in phases:** Phase 1 `Provider Boundary & State Model`; Phase 2 `Submission + Detached Lifecycle`; Phase 3 `Remote Finalization`.

### Pitfall 2: Collapsing provider lifecycle into FluxQ's existing `ok | degraded | error` contract too early

**What goes wrong:** Provider job states like `INITIALIZING`, `QUEUED`, `RUNNING`, `CANCELLED`, `DONE`, and `ERROR` get flattened into FluxQ's final run status before a final result exists.

**Why it happens:** FluxQ's current machine contracts are centered on completed local operations. Remote providers expose lifecycle state, final state, and result availability as separate concepts.

**Consequences:** Agents and CI will misread readiness. A queued remote job might look like a failed run, or a `DONE` job without a fetched result might look final when FluxQ still lacks durable evidence.

**Warning signs:**
- `status`, `inspect`, and `doctor` disagree about the same remote run.
- `report.status` is set from provider state instead of from FluxQ finalization outcome.
- `backend_registry.py` only flips `remote_submit` to `True` without adding capability distinctions for poll, cancel, final result, logs, and metrics.

**Prevention:**
- Define a canonical remote state mapping table before implementation.
- Separate `submission_state`, `provider_state`, and `finalization_state` from final report verdict.
- Only emit a normal FluxQ report verdict after the final result snapshot is locally durable.
- Extend JSON and JSONL contracts with raw provider state plus normalized readiness semantics.

**Absorb in phases:** Phase 1 `Provider Boundary & State Model`; Phase 3 `Remote Finalization + Observability`.

### Pitfall 3: Losing reproducibility through implicit instance and backend selection

**What goes wrong:** FluxQ allows remote runs to depend on automatic instance selection, `least_busy` backend discovery, or unstated region and plan filters, so the same input resolves to different provider targets over time.

**Why it happens:** IBM documents both saved-account automatic instance selection and explicit instance selection, but FluxQ's product core is durable run identity, not "best effort hardware access."

**Consequences:** Compare and baseline flows become noisy or misleading because drift comes from provider selection, not workload change.

**Warning signs:**
- Remote execution defaults to automatic instance selection or `least_busy`.
- Reports omit instance CRN, backend name, region, runtime image, calibration ID, or provider Qiskit version.
- Docs describe remote runs as "send to the best available backend" without recording the concrete choice.

**Prevention:**
- Require explicit provider profile plus concrete instance and backend for canonical remote execution.
- Allow discovery commands to recommend backends, but force canonical execution to record the chosen instance, backend, runtime image, calibration ID, and provider version in immutable artifacts.
- Keep `QSpec` subject identity separate from remote environment identity.

**Absorb in phases:** Phase 1 `Provider Config & Selection`; Phase 3 `Remote Finalization + Compare`.

### Pitfall 4: Leaking credentials into workspace artifacts, packs, or source-controlled config

**What goes wrong:** API keys, bearer tokens, CRNs, or auth headers end up in `qrun.toml`, reports, JSONL events, bundle packs, or example docs.

**Why it happens:** FluxQ is workspace-native and machine-readable by design, while IBM's auth model uses API keys, saved accounts, bearer tokens, and CRNs. Without a hard boundary, secrets will bleed into durable artifacts.

**Consequences:** Secret exposure in git, CI logs, exported bundles, and agent-visible machine output. This is a product trust failure, not just an implementation bug.

**Warning signs:**
- `qrun.toml` or workspace JSON gains `token`, `Authorization`, or raw bearer token fields.
- JSONL events include request headers or provider client config verbatim.
- Docs tell users to paste credentials into files that live under the workspace.

**Prevention:**
- Store credential references, not credentials, in FluxQ config.
- Resolve tokens from process environment, saved provider account state, or explicit runtime flags outside the workspace.
- Redact tokens, CRNs, and auth headers from reports, events, packs, and error payloads.
- Treat CI and untrusted environments as first-class cases from day one.

**Absorb in phases:** Phase 1 `Auth & Config Boundary`; Phase 4 `Packaging + CI Hardening`.

### Pitfall 5: Using provider-side privacy or deletion features in ways that destroy FluxQ replayability

**What goes wrong:** FluxQ enables provider features that remove or make remote data one-shot, then still behaves as if the run is durably replayable and importable.

**Why it happens:** IBM's REST API supports `private=true`, where inputs are omitted and results can only be read once, and it also supports deleting jobs in terminal states. Those features are valid for the provider, but they conflict with FluxQ's default trust contract unless FluxQ snapshots everything first.

**Consequences:** `compare`, `inspect`, `pack`, and `pack-import` become network-dependent, non-replayable, or permanently degraded for some remote runs.

**Warning signs:**
- A tracked remote revision stores only `job_id` and expects the provider to remain the source of truth.
- The roadmap includes `delete` or `private` controls before final result snapshotting exists.
- `pack` or `compare` requires live provider access to reconstruct a run.

**Prevention:**
- Keep provider retention as upstream convenience, not FluxQ's source of truth.
- Snapshot final result, logs, metrics, and environment metadata into immutable local artifacts before any provider-side destructive action is exposed.
- Default tracked revisions to provider settings compatible with durable local replay.
- If private or destructive modes are later added, mark them as explicitly reduced-trust workflows.

**Absorb in phases:** Phase 2 `Submission + Persistence`; Phase 3 `Remote Finalization`; Phase 4 `Pack/Import Hardening`.

### Pitfall 6: Shipping remote execution without provider-aware preflight for limits, cost, and rate controls

**What goes wrong:** FluxQ submits work that is structurally valid locally but rejected remotely due to request size, rate limits, plan restrictions, or provider time limits.

**Why it happens:** The local runtime today validates QSpec and local workspace health, but remote providers add payload size, request rate, quantum-time, and execution-mode constraints that are not visible from local-only checks.

**Consequences:** Remote execution looks flaky, expensive, and hard to automate. Retry loops can make things worse.

**Warning signs:**
- No plan-time estimate for payload size or remote execution mode.
- Retries happen immediately on provider failure with no backoff or attempt budgeting.
- v1.1 promises sessions or batches without plan-aware checks.

**Prevention:**
- Extend `plan` or add a remote preflight stage that estimates provider payload size and validates required remote config.
- Surface explicit remote limits and user-settable execution budgets in machine-readable output.
- Enforce provider-aware retry and backoff behavior.
- Ship job mode first; defer session and batch flows until FluxQ can model their TTL and quota semantics honestly.

**Absorb in phases:** Phase 1 `Remote Preflight`; Phase 2 `Submission Controls`.

## Moderate Pitfalls

### Pitfall 7: Breaking compare and baseline trust by mixing workload identity with remote environment drift

**What goes wrong:** Remote runs of the same `QSpec` on different backends, calibrations, or runtime options are compared as if they were simple local report drift.

**Why it happens:** The current compare surface already separates subject and backend deltas, but remote execution adds more environment-level variance that needs first-class modeling.

**Consequences:** Baselines become noisy and policy gates become harder to interpret.

**Warning signs:**
- Remote compare output only reports generic `backend_regression` or `report_drift`.
- Remote reports do not carry a distinct environment block for instance, backend, calibration, runtime image, and provider options.

**Prevention:**
- Preserve subject identity on canonical `QSpec` semantics.
- Add explicit remote environment deltas and policy switches for environment drift versus workload drift.
- Require like-for-like environment baselines by default.

**Absorb in phases:** Phase 3 `Compare + Inspect Remote Semantics`.

### Pitfall 8: Duplicate submission after ambiguous client or network failures

**What goes wrong:** FluxQ retries a failed submit call without knowing whether the provider already accepted the first attempt, producing duplicate remote jobs for what users think is one run.

**Why it happens:** Remote creation returns a provider job ID only after the request succeeds from the client's perspective. Ambiguous failures need FluxQ-side correlation and deduplication.

**Consequences:** Double cost, confusing lifecycle state, and one FluxQ revision mapping to multiple provider jobs.

**Warning signs:**
- Submit retries reuse no correlation identifier.
- Provider tags are not used to bind remote jobs to FluxQ revisions or submission attempts.
- The workspace records a single remote run but the provider shows multiple jobs with the same input.

**Prevention:**
- Persist a submission-attempt record before retrying.
- Tag provider jobs with FluxQ project, revision, and attempt identifiers.
- Make submit retry logic duplicate-aware and surface ambiguity explicitly when it cannot be resolved automatically.

**Absorb in phases:** Phase 2 `Submission + Detached Lifecycle`.

### Pitfall 9: Trusting local testing mode as proof that remote behavior is correct

**What goes wrong:** The team ships based on fake backend or Aer tests alone, then discovers that auth, execution mode, option handling, status transitions, metrics, and retention behavior differ remotely.

**Why it happens:** IBM's local testing mode is useful, but it ignores most runtime options on local simulators, and session syntax is supported but ignored locally.

**Consequences:** FluxQ gets strong local green signals and weak remote truth.

**Warning signs:**
- The only new tests use fake backends or Aer simulators.
- There are no tests for remote auth failures, missing results, cancel conflicts, or lifecycle resumption.
- CI treats local testing mode as a full substitute for remote contract testing.

**Prevention:**
- Use three layers of coverage: adapter unit tests, local testing mode for circuit and transpilation parity, and provider contract tests with mocked or live lifecycle transitions.
- Add at least one low-cost remote smoke lane outside the main fast test path.
- Keep provider-state fixtures close to compare/import/report code, not only CLI end-to-end tests.

**Absorb in phases:** Phase 2 `Provider Contract Tests`; Phase 4 `CI Hardening`.

### Pitfall 10: Scope creep into sessions, batches, and multi-job orchestration before single-job trust is closed

**What goes wrong:** v1.1 starts with sessions, batches, or grouped workloads because the provider offers them, even though FluxQ has not yet proven a trustworthy single remote run object.

**Why it happens:** Provider capabilities are tempting product breadth, but they carry extra semantics: batches can run out of order and have TTL behavior; sessions have dedicated-window semantics and are not supported for some plans.

**Consequences:** The milestone turns into scheduler design instead of trustworthy remote execution.

**Warning signs:**
- Early plans include session lifecycle, batch fan-out, or iterative algorithm orchestration.
- `backend list` starts advertising multiple remote execution modes before one remote round trip is replayable end to end.

**Prevention:**
- Keep v1.1 scoped to job mode for one provider.
- Defer session and batch support until after FluxQ can submit, resume, finalize, compare, pack, and recover one remote run safely.

**Absorb in phases:** Defer to post-v1.1 or a later v1.x phase after Phase 4 is complete.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Provider boundary and config | Credentials leak into workspace or provider auto-selection weakens reproducibility | Keep tokens outside FluxQ artifacts; require explicit instance/backend in canonical exec |
| Remote submission | Duplicate jobs or long-held workspace locks during submit/poll | Persist submission attempts and use provider tags; keep locks short and local-only |
| Lifecycle tracking | Provider states are mapped directly to final FluxQ verdicts | Add a separate remote lifecycle model and canonical state mapping table |
| Remote finalization | FluxQ stores only a job ID and depends on live provider state forever | Snapshot final result, logs, metrics, backend properties, and environment metadata locally |
| Compare and baseline | Subject drift and environment drift are conflated | Add explicit remote environment deltas and keep QSpec semantics as the subject identity |
| Pack/import | Remote revisions are not self-contained after export | Pack immutable local snapshots, not live provider references |
| Testing and CI | Fake-backend tests hide real remote failures | Layer unit, local testing, mocked lifecycle, and small live smoke coverage |
| Product scope | Sessions and batches arrive before single-job trust is proven | Hold v1.1 to one provider in job mode only |

## Roadmap Guardrails

Use these as milestone gates:

1. **Phase 1: Provider Boundary, Auth, and State Model**
   - Define the provider adapter seam, auth/config boundary, explicit instance/backend selection, and canonical remote state model.
   - Extend `plan` and `backend list` only with truthful remote capability and preflight semantics.

2. **Phase 2: Submission and Detached Lifecycle Persistence**
   - Submit in job mode only.
   - Persist submission attempts, provider job IDs, provider tags, and non-secret lifecycle state without promoting active aliases.
   - Keep workspace locks short and never hold them across network waits.

3. **Phase 3: Remote Finalization, Compare, and Observability**
   - Persist final result, logs, metrics, backend properties, calibration ID, runtime image, and provider version locally.
   - Finalize immutable reports and manifests only after FluxQ has durable evidence.
   - Add remote-aware compare, inspect, status, and baseline semantics.

4. **Phase 4: Recovery, Pack/Import, and CI Hardening**
   - Add cancel/recovery flows, pack/import coverage for remote revisions, secret scrubbing, and contract-focused CI.
   - Add one low-cost live remote smoke lane and keep the fast local lane separate.

5. **Deferred: Sessions, Batches, and Multi-Job Orchestration**
   - Do not enter this scope until the single-job remote path is replayable, compareable, packable, and recoverable.

## Sources

### Codebase sources

- `src/quantum_runtime/runtime/executor.py` - current synchronous exec, revision reservation, alias promotion, and workspace lock behavior. Confidence: HIGH.
- `src/quantum_runtime/runtime/imports.py` - current replay/import trust surface. Confidence: HIGH.
- `src/quantum_runtime/runtime/compare.py` - current subject/report/backend delta model. Confidence: HIGH.
- `src/quantum_runtime/runtime/control_plane.py`, `doctor.py`, `inspect.py` - current health/status surface split. Confidence: HIGH.
- `.planning/codebase/CONCERNS.md` - existing fault lines around oversized orchestration modules, duplicated health evaluation, long-lived exec lock, and log growth. Confidence: HIGH.
- `.planning/PROJECT.md` - v1.1 milestone goal and constraints. Confidence: HIGH.

### Official provider sources

- IBM Quantum REST API, Jobs: rate limit, `private` job behavior, delete/cancel semantics, metrics, and result retrieval. https://quantum.cloud.ibm.com/docs/en/api/qiskit-runtime-rest/tags/jobs Confidence: HIGH.
- IBM Quantum `RuntimeJobV2` API: job states, final states, `result()`, `logs()`, `metrics()`, and `wait_for_final_state()`. https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/dev/runtime-job-v2 Confidence: HIGH.
- IBM Quantum account initialization: explicit instance selection guidance and `qiskit_ibm_runtime` version caveats. https://quantum.cloud.ibm.com/docs/en/guides/initialize-account Confidence: HIGH.
- IBM Quantum untrusted-environment guidance: token handling, bearer token lifetime, and key revocation expectations. https://quantum.cloud.ibm.com/docs/en/guides/cloud-setup-untrusted Confidence: HIGH.
- IBM Quantum local testing mode: fake backend support, sessions ignored locally, and most options ignored on local simulators. https://quantum.cloud.ibm.com/docs/en/guides/local-testing-mode Confidence: HIGH.
- IBM Quantum execution modes: job/session/batch differences, session restrictions, and batch/session tradeoffs. https://quantum.cloud.ibm.com/docs/en/guides/execution-modes Confidence: HIGH.
- IBM Quantum maximum execution time guide: service-calculated timeout, quantum-time semantics, 50 MB input limit, session/batch TTL, and open-plan usage limits. https://quantum.cloud.ibm.com/docs/en/guides/max-execution-time Confidence: HIGH.
- IBM Quantum credential saving guide: saved credentials file location and automatic instance selection behavior. https://qiskit.qotlabs.org/docs/guides/save-credentials Confidence: MEDIUM because this is the IBM documentation mirror rather than the primary `quantum.cloud.ibm.com` domain, but it matches the current official guidance.
