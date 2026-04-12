# Phase 4: Policy Acceptance Gates - Research

**Researched:** 2026-04-13 [VERIFIED: system date]
**Domain:** Policy-gated compare, benchmark, and doctor control-plane surfaces for FluxQ CI workflows. [VERIFIED: ROADMAP.md]
**Confidence:** MEDIUM [VERIFIED: codebase grep][ASSUMED]

## User Constraints

No phase-specific `CONTEXT.md` exists for Phase 4, so the constraints below are inherited from the repo planning docs and `AGENTS.md`. [VERIFIED: init phase-op 4][VERIFIED: PROJECT.md][VERIFIED: AGENTS.md]

### Locked Decisions

- Keep Python 3.11, `uv`, and local CLI packaging as the implementation stack. [VERIFIED: AGENTS.md]
- Keep Qiskit-first local execution with OpenQASM 3 as the exchange layer. [VERIFIED: AGENTS.md]
- Evolve the current `QSpec` and CLI compatibly instead of introducing a breaking IR rewrite. [VERIFIED: AGENTS.md]
- Keep machine-readable output schema-versioned, stable, and agent-friendly. [VERIFIED: AGENTS.md]
- Prioritize local runtime maturity, replay trust, policy gating, and delivery bundles before remote breadth. [VERIFIED: AGENTS.md][VERIFIED: PROJECT.md]

### Claude's Discretion

- Add shared policy-evaluation helpers and CLI options if they preserve the existing schema-versioned control-plane contract and brownfield Python/Typer/Pydantic stack. [VERIFIED: AGENTS.md][VERIFIED: pyproject.toml][ASSUMED]

### Deferred Ideas (OUT OF SCOPE)

- Remote execution and provider-matrix expansion are deferred to v2. [VERIFIED: REQUIREMENTS.md]
- A new quantum language or DSL is out of scope for this milestone. [VERIFIED: REQUIREMENTS.md]
- General chat-assistant UX is out of scope because prompt text is ingress, not product center. [VERIFIED: PROJECT.md]
- Full optimizer, gradient, or remote orchestration platforms are out of scope in the current milestone. [VERIFIED: PROJECT.md][VERIFIED: REQUIREMENTS.md]

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| POLC-01 | Agent can compare current state against baseline and fail on specific drift classes without external wrapper logic. [VERIFIED: REQUIREMENTS.md] | Reuse the existing `ComparePolicy`, baseline resolution, `verdict`, `reason_codes`, `next_actions`, and `gate` contract; keep policy rejection on FluxQ-owned exit behavior instead of shell wrappers. [VERIFIED: src/quantum_runtime/runtime/compare.py][VERIFIED: src/quantum_runtime/cli.py][VERIFIED: src/quantum_runtime/runtime/exit_codes.py] |
| POLC-02 | Agent can use benchmark results as policy evidence, including compare-to-baseline workflows. [VERIFIED: REQUIREMENTS.md] | Add a benchmark policy layer on top of the current `BenchmarkReport` evidence, but first fix revision labeling for imported benchmark history and require subject/comparability checks before metric thresholds. [VERIFIED: src/quantum_runtime/diagnostics/benchmark.py][VERIFIED: local reproduction][ASSUMED] |
| POLC-03 | Agent can use doctor results in CI-oriented mode with clear blocking versus advisory outputs. [VERIFIED: REQUIREMENTS.md] | Extend `DoctorReport` with explicit blocking/advisory classification and a compare-style gate envelope while preserving current `issues` and `advisories` for backward compatibility. [VERIFIED: src/quantum_runtime/runtime/doctor.py][VERIFIED: src/quantum_runtime/runtime/exit_codes.py][ASSUMED] |

## Summary

Compare is already the closest thing to the target Phase 4 contract: it supports baseline mode, `ComparePolicy`, explicit `verdict`, `reason_codes`, `next_actions`, and a `gate` block, and the CLI maps policy failure to exit code `2`. [VERIFIED: src/quantum_runtime/runtime/compare.py][VERIFIED: src/quantum_runtime/cli.py][VERIFIED: src/quantum_runtime/runtime/exit_codes.py]

Benchmark and doctor stop earlier. `BenchmarkReport` and `DoctorReport` expose evidence and generic status, but neither command emits a first-class policy verdict or a stable blocking-versus-advisory gate envelope comparable to `compare`. [VERIFIED: src/quantum_runtime/diagnostics/benchmark.py][VERIFIED: src/quantum_runtime/runtime/doctor.py]

Two implementation risks should be treated as Wave 0 work for Phase 4. Persisted compare artifacts are written from `CompareResult.model_dump()` and currently omit `schema_version`, even though CLI JSON responses add it through `ensure_schema_payload()`. [VERIFIED: src/quantum_runtime/runtime/compare.py][VERIFIED: src/quantum_runtime/runtime/contracts.py][VERIFIED: src/quantum_runtime/cli.py][VERIFIED: local reproduction] Benchmark persistence is also revision-ambiguous for imported history inputs: `qrun bench --revision rev_000001` writes benchmark history under `workspace.manifest.current_revision`, not the imported revision. [VERIFIED: src/quantum_runtime/diagnostics/benchmark.py][VERIFIED: local reproduction]

**Primary recommendation:** Introduce one shared runtime policy layer that consumes already-computed compare, benchmark, and doctor evidence; emits a common `policy` + `verdict` + `reason_codes` + `next_actions` + `gate` envelope; keeps policy rejection on exit code `2`; and fixes the compare/benchmark persistence gaps before adding new CI-facing flags. [ASSUMED]

## Standard Stack

No new external dependency is warranted for Phase 4; the work fits the existing brownfield Python, Typer, Pydantic, and internal runtime-module stack. [VERIFIED: AGENTS.md][VERIFIED: pyproject.toml][ASSUMED]

### Core

| Library / Module | Version | Purpose | Why Standard |
|------------------|---------|---------|--------------|
| `quantum_runtime.runtime.compare` [VERIFIED: codebase grep] | Repo `0.3.1`, compare payloads serialized under schema `0.3.0`. [VERIFIED: pyproject.toml][VERIFIED: src/quantum_runtime/runtime/contracts.py] | Canonical compare-side policy evaluation, baseline composition, and gate vocabulary. [VERIFIED: src/quantum_runtime/runtime/compare.py] | It already defines the only shipped FluxQ policy contract (`policy`, `verdict`, `reason_codes`, `next_actions`, `gate`). [VERIFIED: src/quantum_runtime/runtime/compare.py] |
| `typer` [VERIFIED: installed package] | `0.24.1` in the active `.venv`; PyPI also shows `0.24.1` released 2026-02-21. [VERIFIED: installed package][VERIFIED: pypi.org JSON] | CLI option parsing and deterministic exit handling. [VERIFIED: src/quantum_runtime/cli.py] | FluxQ already uses `typer.Exit(code=...)` across command surfaces, and Typer documents explicit exit-code control. [VERIFIED: src/quantum_runtime/cli.py][CITED: https://typer.tiangolo.com/tutorial/terminating/] |
| `pydantic` [VERIFIED: installed package] | `2.12.5` in the active `.venv`; PyPI shows `2.12.5` released 2025-11-26. [VERIFIED: installed package][CITED: https://pypi.org/project/pydantic/] | Stable machine-readable models and JSON serialization. [VERIFIED: src/quantum_runtime/runtime/contracts.py][VERIFIED: src/quantum_runtime/runtime/doctor.py][VERIFIED: src/quantum_runtime/diagnostics/benchmark.py] | FluxQ already standardizes on `BaseModel`, `model_dump(mode="json")`, and `model_dump_json(indent=2)`, which Pydantic documents directly. [VERIFIED: codebase grep][CITED: https://pydantic.dev/docs/validation/latest/concepts/serialization/] |
| `quantum_runtime.runtime.contracts` + `quantum_runtime.runtime.observability` [VERIFIED: codebase grep] | Schema `0.3.0`. [VERIFIED: src/quantum_runtime/runtime/contracts.py][VERIFIED: src/quantum_runtime/runtime/observability.py] | Shared schema payloads, workspace-safety envelopes, JSONL events, and gate summaries. [VERIFIED: src/quantum_runtime/runtime/contracts.py][VERIFIED: src/quantum_runtime/runtime/observability.py] | Phase 4 should extend these modules instead of inventing a second machine-output vocabulary. [VERIFIED: codebase grep][ASSUMED] |

### Supporting

| Library / Module | Version | Purpose | When to Use |
|------------------|---------|---------|-------------|
| `quantum_runtime.diagnostics.benchmark` [VERIFIED: codebase grep] | Schema `0.3.0`, Qiskit-backed evidence under repo `0.3.1`. [VERIFIED: src/quantum_runtime/diagnostics/benchmark.py][VERIFIED: pyproject.toml] | Structural benchmark evidence, per-backend comparability metadata, and history persistence. [VERIFIED: src/quantum_runtime/diagnostics/benchmark.py] | Use as the raw evidence source for POLC-02; do not add policy logic in the CLI first. [VERIFIED: src/quantum_runtime/diagnostics/benchmark.py][ASSUMED] |
| `quantum_runtime.runtime.doctor` [VERIFIED: codebase grep] | Schema `0.3.0`. [VERIFIED: src/quantum_runtime/runtime/doctor.py] | Workspace and dependency health evidence with current `issues` and `advisories` split. [VERIFIED: src/quantum_runtime/runtime/doctor.py] | Use as the raw evidence source for POLC-03, then layer explicit blocking/advisory classification on top. [VERIFIED: src/quantum_runtime/runtime/doctor.py][ASSUMED] |
| `pytest` [VERIFIED: installed package] | `9.0.2` in the active `.venv`; PyPI shows `9.0.3` released 2026-04-07. [VERIFIED: installed package][CITED: https://pypi.org/project/pytest/] | CLI and runtime regression coverage. [VERIFIED: pyproject.toml][VERIFIED: .github/workflows/ci.yml] | Use for all new policy-gate regressions; the existing targeted related suite already passes locally. [VERIFIED: local test run] |
| `qiskit` + `qiskit-aer` [VERIFIED: installed package] | `2.3.1` and `0.17.2` in the active `.venv`. [VERIFIED: installed package] | Provide current benchmark evidence and backend availability signals consumed by Phase 4. [VERIFIED: src/quantum_runtime/diagnostics/benchmark.py][VERIFIED: src/quantum_runtime/runtime/doctor.py] | Keep Phase 4 changes above the evidence layer; no Qiskit API redesign is required. [VERIFIED: AGENTS.md][ASSUMED] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Internal Pydantic policy models and existing CLI commands. [VERIFIED: codebase grep][ASSUMED] | A separate policy engine or new top-level `gate` command. [ASSUMED] | A new engine adds scope, migration surface, and a second output vocabulary without solving a demonstrated codebase limitation. [VERIFIED: AGENTS.md][ASSUMED] |
| Existing FluxQ exit-code family (`0`, `2`, `3`, `4`, `5`, `6`, `7`). [VERIFIED: src/quantum_runtime/runtime/exit_codes.py] | New policy-specific exit codes. [ASSUMED] | New codes would break or complicate current CI and agent consumers; non-zero already signals failure, and FluxQ already distinguishes degraded vs invalid input. [VERIFIED: src/quantum_runtime/runtime/exit_codes.py][CITED: https://click.palletsprojects.com/en/stable/exceptions/][ASSUMED] |

**Installation:** Reuse the current project environment; no new dependency is required for Phase 4. [VERIFIED: pyproject.toml][ASSUMED]

```bash
uv sync --extra dev --extra qiskit
```

**Version verification:** The active `.venv` reports Typer `0.24.1`, Pydantic `2.12.5`, pytest `9.0.2`, Qiskit `2.3.1`, and Qiskit Aer `0.17.2`. [VERIFIED: installed package] PyPI currently shows Typer `0.24.1` released 2026-02-21, Pydantic `2.12.5` released 2025-11-26, pytest `9.0.3` released 2026-04-07, and Ruff `0.15.10` released 2026-04-09. [VERIFIED: pypi.org JSON][CITED: https://pypi.org/project/pydantic/][CITED: https://pypi.org/project/pytest/][CITED: https://pypi.org/project/ruff/] Phase 4 should stay on repo-locked versions unless a separate upgrade phase is created. [VERIFIED: AGENTS.md][ASSUMED]

## Architecture Patterns

### Recommended Project Structure

```text
src/quantum_runtime/
├── runtime/
│   ├── compare.py          # Existing canonical policy vocabulary
│   ├── contracts.py        # Schema payloads and machine-readable error envelopes
│   ├── observability.py    # Gate and JSONL helper blocks
│   ├── doctor.py           # Raw doctor evidence + CI classification hook
│   ├── exit_codes.py       # Stable FluxQ exit-code family
│   └── policy.py           # Recommended new shared policy evaluators
├── diagnostics/
│   └── benchmark.py        # Raw benchmark evidence + persistence only
└── cli.py                  # Thin option parsing and payload emission
tests/
├── test_runtime_compare.py
├── test_runtime_policy.py
├── test_cli_compare.py
├── test_cli_bench.py
└── test_cli_doctor.py
```

This structure keeps evidence generation in `runtime/compare.py`, `diagnostics/benchmark.py`, and `runtime/doctor.py`, while concentrating new cross-command policy logic in one runtime-layer module instead of duplicating CLI-only checks. [VERIFIED: AGENTS.md][VERIFIED: src/quantum_runtime/runtime/compare.py][VERIFIED: src/quantum_runtime/diagnostics/benchmark.py][VERIFIED: src/quantum_runtime/runtime/doctor.py][ASSUMED]

### Pattern 1: Shared Gate Envelope

**What:** Normalize compare, benchmark, and doctor outputs onto one machine-readable acceptance shape: raw evidence plus `policy`, `verdict`, `reason_codes`, `next_actions`, and `gate`. [VERIFIED: src/quantum_runtime/runtime/compare.py][ASSUMED]

**When to use:** Any policy-facing JSON or persisted gate artifact that a CI job or agent will consume directly. [VERIFIED: ROADMAP.md][ASSUMED]

**Example:**

```python
# Source: src/quantum_runtime/runtime/compare.py
class CompareVerdict(BaseModel):
    status: Literal["not_requested", "pass", "fail"]
    summary: str
    failed_checks: list[str] = Field(default_factory=list)
    passed_checks: list[str] = Field(default_factory=list)
```

The compare command already proves the envelope shape; Phase 4 should reuse it rather than creating separate benchmark and doctor verdict schemas. [VERIFIED: src/quantum_runtime/runtime/compare.py][ASSUMED]

### Pattern 2: Evidence First, Policy Second

**What:** Compute raw evidence first, then evaluate policy against that evidence in a separate step. [VERIFIED: src/quantum_runtime/runtime/compare.py][ASSUMED]

**When to use:** Benchmark threshold checks, doctor CI mode, and any future “accept/reject” policy evaluation layered on existing reports. [VERIFIED: ROADMAP.md][ASSUMED]

**Example:**

```python
# Source: src/quantum_runtime/runtime/compare.py
verdict = _evaluate_policy(
    policy=policy,
    same_subject=same_subject,
    same_qspec=same_qspec,
    same_report=same_report,
    report_drift_detected=report_drift_detected,
    backend_regressions=backend_regressions,
    replay_integrity_regressions=replay_integrity_regressions,
)
```

This separation is already established in compare and should be preserved for benchmark and doctor so persisted evidence remains useful outside one CLI invocation. [VERIFIED: src/quantum_runtime/runtime/compare.py][ASSUMED]

### Pattern 3: Baseline Composition Through Existing Import Resolution

**What:** Resolve the saved baseline via `resolve_workspace_baseline()` and compare imported evidence only after subject identity is confirmed. [VERIFIED: src/quantum_runtime/runtime/imports.py][VERIFIED: src/quantum_runtime/runtime/compare.py][ASSUMED]

**When to use:** Benchmark-to-baseline gating and any future composed acceptance command. [VERIFIED: ROADMAP.md][ASSUMED]

**Example:**

```python
# Source: src/quantum_runtime/runtime/imports.py and compare.py
baseline = resolve_workspace_baseline(workspace_root)
current = resolve_workspace_current(workspace_root)
result = compare_import_resolutions(baseline.resolution, current, policy=policy)
```

For benchmark policy, the same composition rule should hold: baseline subject parity first, same backend on both sides second, numeric threshold checks last. [VERIFIED: src/quantum_runtime/runtime/imports.py][VERIFIED: src/quantum_runtime/diagnostics/benchmark.py][ASSUMED]

### Anti-Patterns to Avoid

- **CLI-only policy logic:** Do not bury benchmark or doctor gate evaluation entirely inside `cli.py`; compare already keeps policy semantics in the runtime layer. [VERIFIED: src/quantum_runtime/cli.py][VERIFIED: src/quantum_runtime/runtime/compare.py]
- **Status-as-verdict:** Do not treat `status == "degraded"` as synonymous with “reject” without a gate block; compare proves that evidence and verdict are distinct concepts. [VERIFIED: src/quantum_runtime/runtime/compare.py][VERIFIED: src/quantum_runtime/runtime/exit_codes.py]
- **Benchmarking unlike subjects:** Do not compare benchmark metrics across revisions until semantic subject identity matches and backend comparability is explicit. [VERIFIED: src/quantum_runtime/runtime/compare.py][VERIFIED: src/quantum_runtime/diagnostics/benchmark.py][ASSUMED]
- **Exit-code proliferation:** Do not create one exit code per drift class; FluxQ already owns a stable exit-code family and CI only needs stable zero vs non-zero semantics at the shell boundary. [VERIFIED: src/quantum_runtime/runtime/exit_codes.py][CITED: https://click.palletsprojects.com/en/stable/exceptions/][ASSUMED]
- **Persisting unschematized gate artifacts:** Do not keep writing compare gate artifacts without `schema_version`; Phase 4 should close that gap rather than replicate it. [VERIFIED: src/quantum_runtime/runtime/compare.py][VERIFIED: src/quantum_runtime/runtime/contracts.py][VERIFIED: local reproduction][ASSUMED]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Machine-readable error envelopes. [VERIFIED: codebase grep] | New ad hoc JSON error dicts per command. [ASSUMED] | `runtime/contracts.py` payload builders plus `dump_schema_payload()`. [VERIFIED: src/quantum_runtime/runtime/contracts.py] | FluxQ already centralizes schema versioning, remediation, and workspace-safety details there. [VERIFIED: src/quantum_runtime/runtime/contracts.py] |
| Gate summaries and next actions. [VERIFIED: codebase grep] | New per-command gate key layouts. [ASSUMED] | `gate_block()`, `decision_block()`, and `next_actions_for_reason_codes()`. [VERIFIED: src/quantum_runtime/runtime/observability.py] | These helpers already define the current agent-facing vocabulary for readiness and remediation. [VERIFIED: src/quantum_runtime/runtime/observability.py] |
| Baseline and revision resolution. [VERIFIED: codebase grep] | Manual path joins for reports/specs/baselines. [ASSUMED] | `resolve_workspace_baseline()`, `resolve_import_reference()`, and `WorkspaceBaseline`. [VERIFIED: src/quantum_runtime/runtime/imports.py][VERIFIED: src/quantum_runtime/workspace/baseline.py] | Existing import resolution already enforces provenance, revision, and hash integrity. [VERIFIED: src/quantum_runtime/runtime/imports.py] |
| Integrity hashing for policy evidence. [VERIFIED: codebase grep] | A second digest scheme or handwritten checksum format. [ASSUMED] | Existing SHA-256 helpers in reporters, imports, baseline, export, and run manifest code. [VERIFIED: codebase grep] | Policy gates sit on top of the current trust model; changing hash semantics here would create avoidable migration risk. [VERIFIED: AGENTS.md][VERIFIED: codebase grep][ASSUMED] |
| Workspace-safe persistence. [VERIFIED: Phase 03 summaries] | Direct file writes from new gate code. [ASSUMED] | `acquire_workspace_lock()`, `pending_atomic_write_files()`, and `atomic_write_text()`. [VERIFIED: src/quantum_runtime/workspace][VERIFIED: 03-concurrent-workspace-safety-04-SUMMARY.md] | Phase 3 already established the non-exec writer contract that Phase 4 must reuse. [VERIFIED: 03-concurrent-workspace-safety-04-SUMMARY.md] |

**Key insight:** The hard part of Phase 4 is not threshold math; it is preserving FluxQ’s existing trust, schema, and workspace-safety contracts while making accept/reject decisions first-class. [VERIFIED: PROJECT.md][VERIFIED: 03-concurrent-workspace-safety-04-SUMMARY.md][ASSUMED]

## Common Pitfalls

### Pitfall 1: Confusing Evidence Status with Acceptance Verdict

**What goes wrong:** A command returns `status: "degraded"` or `status: "same_subject"` and callers treat that alone as the CI decision. [VERIFIED: src/quantum_runtime/runtime/compare.py][VERIFIED: src/quantum_runtime/diagnostics/benchmark.py][VERIFIED: src/quantum_runtime/runtime/doctor.py]

**Why it happens:** Compare already separates evidence from policy verdict, but benchmark and doctor currently do not. [VERIFIED: src/quantum_runtime/runtime/compare.py][VERIFIED: src/quantum_runtime/diagnostics/benchmark.py][VERIFIED: src/quantum_runtime/runtime/doctor.py]

**How to avoid:** Standardize all three commands on an explicit gate envelope and keep exit-code mapping downstream of that envelope. [VERIFIED: src/quantum_runtime/runtime/compare.py][VERIFIED: src/quantum_runtime/runtime/exit_codes.py][ASSUMED]

**Warning signs:** Shell scripts parse `status` directly or inspect free-form `issues` strings to decide pass/fail. [ASSUMED]

### Pitfall 2: Comparing Benchmarks Without Subject or Comparability Checks

**What goes wrong:** Benchmark thresholds are compared across different workloads or incomparable backend modes, producing false failures or false passes. [VERIFIED: src/quantum_runtime/diagnostics/benchmark.py][ASSUMED]

**Why it happens:** `BenchmarkReport` carries `subject.semantic_hash`, backend-level `comparable`, `benchmark_mode`, `target_parity`, and `comparability_reason`, but current CLI logic does not enforce those as policy preconditions. [VERIFIED: src/quantum_runtime/diagnostics/benchmark.py]

**How to avoid:** Require subject parity through compare, then require same backend keys and `details.comparable` or an explicit fallback policy before applying metric thresholds. [VERIFIED: src/quantum_runtime/runtime/compare.py][VERIFIED: src/quantum_runtime/diagnostics/benchmark.py][ASSUMED]

**Warning signs:** A baseline benchmark file exists, but its revision or semantic hash does not match the baseline revision being gated. [VERIFIED: local reproduction][ASSUMED]

### Pitfall 3: Misclassifying Optional Backends in Doctor CI Mode

**What goes wrong:** Missing optional backends become hard blockers even when the active QSpec does not require them. [VERIFIED: src/quantum_runtime/runtime/doctor.py][VERIFIED: tests/test_cli_doctor.py]

**Why it happens:** Doctor currently classifies missing optional unrequested backends as `advisories`, but missing requested backends as `issues`. [VERIFIED: src/quantum_runtime/runtime/doctor.py][VERIFIED: tests/test_cli_doctor.py]

**How to avoid:** Preserve the existing required-backend check and surface a separate CI classification block instead of rewriting the underlying issue classifier. [VERIFIED: src/quantum_runtime/runtime/doctor.py][ASSUMED]

**Warning signs:** `classiq` becomes blocking in an empty or Qiskit-only workspace. [VERIFIED: tests/test_cli_doctor.py]

### Pitfall 4: Persisting Gate Artifacts Inconsistently

**What goes wrong:** CLI JSON output is schema-versioned, but persisted compare artifacts or imported benchmark history are not trustworthy enough for later composed policy evaluation. [VERIFIED: src/quantum_runtime/runtime/compare.py][VERIFIED: src/quantum_runtime/runtime/contracts.py][VERIFIED: src/quantum_runtime/diagnostics/benchmark.py][VERIFIED: local reproduction]

**Why it happens:** Compare persists `CompareResult.model_dump()` directly, and benchmark history uses `workspace.manifest.current_revision` even when the benchmarked QSpec came from another revision. [VERIFIED: src/quantum_runtime/runtime/compare.py][VERIFIED: src/quantum_runtime/diagnostics/benchmark.py][VERIFIED: local reproduction]

**How to avoid:** Fix persistence semantics before adding composed policy workflows that read `compare/latest.json` or `benchmarks/history/<revision>.json`. [VERIFIED: local reproduction][ASSUMED]

**Warning signs:** `compare/latest.json` lacks `schema_version`, or a benchmarked `rev_000001` report lands in `benchmarks/history/rev_000002.json`. [VERIFIED: local reproduction]

## Code Examples

Verified patterns from current FluxQ sources:

### Existing Compare Gate Vocabulary

```python
# Source: src/quantum_runtime/runtime/compare.py
return CompareResult(
    status="same_subject" if same_subject else "different_subject",
    same_subject=same_subject,
    reason_codes=reason_codes,
    next_actions=next_actions,
    gate=gate_block(
        ready=gate_ready,
        severity=severity,
        reason_codes=reason_codes,
        next_actions=next_actions,
    ),
    policy=policy.model_dump(mode="json") if policy is not None else {},
    verdict=verdict.model_dump(mode="json"),
    left=_compare_side(left),
    right=_compare_side(right),
)
```

This is the canonical shape to extend for benchmark and doctor. [VERIFIED: src/quantum_runtime/runtime/compare.py][ASSUMED]

### Thin CLI Exit Mapping

```python
# Source: src/quantum_runtime/cli.py
if json_output:
    _echo_json(result, exclude_none=True)
    raise typer.Exit(code=exit_code_for_compare(result, structured=True))
```

Typer explicitly supports non-zero exit codes through `typer.Exit(code=...)`, and FluxQ already uses that pattern broadly. [VERIFIED: src/quantum_runtime/cli.py][CITED: https://typer.tiangolo.com/tutorial/terminating/]

### Stable Pydantic JSON Serialization

```python
# Source: src/quantum_runtime/runtime/doctor.py
serialized = report.model_dump_json(indent=2)
atomic_write_text(latest_path, serialized)
```

Pydantic documents `model_dump_json()` as the direct JSON-string serialization path, which matches the current FluxQ persistence pattern. [VERIFIED: src/quantum_runtime/runtime/doctor.py][CITED: https://pydantic.dev/docs/validation/latest/concepts/serialization/]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw command status plus wrapper-script interpretation. [VERIFIED: REQUIREMENTS.md][ASSUMED] | Compare already ships a first-class `policy` + `verdict` + `gate` contract, but benchmark and doctor do not. [VERIFIED: src/quantum_runtime/runtime/compare.py][VERIFIED: src/quantum_runtime/diagnostics/benchmark.py][VERIFIED: src/quantum_runtime/runtime/doctor.py] | Current codebase before Phase 4 planning on 2026-04-13. [VERIFIED: system date][VERIFIED: codebase grep] | Phase 4 should unify the policy surface instead of inventing a second acceptance path. [ASSUMED] |
| Non-exec mutators previously risked current/history corruption. [VERIFIED: 03-concurrent-workspace-safety-03-SUMMARY.md][VERIFIED: 03-concurrent-workspace-safety-04-SUMMARY.md] | All compare, benchmark, doctor, baseline, export, and pack writers now use lease-guarded, atomic persistence. [VERIFIED: 03-concurrent-workspace-safety-04-SUMMARY.md] | 2026-04-12 during Phase 3. [VERIFIED: 03-concurrent-workspace-safety-04-SUMMARY.md] | Phase 4 can add gate persistence safely if it reuses Phase 3 primitives. [VERIFIED: 03-concurrent-workspace-safety-04-SUMMARY.md][ASSUMED] |

**Deprecated/outdated:**

- External wrapper logic that infers policy acceptance only from `status` or ad hoc shell parsing is outdated for this milestone because the pending requirements explicitly call for FluxQ-native accept/reject behavior. [VERIFIED: REQUIREMENTS.md][ASSUMED]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Phase 4 should add a shared runtime `policy.py`-style module instead of scattering benchmark and doctor gating logic across `cli.py`. [ASSUMED] | Architecture Patterns | The planner could over-centralize or under-centralize the implementation and create cross-command drift. |
| A2 | Policy rejection should keep using exit code `2` instead of introducing new policy-specific exit codes. [ASSUMED] | Summary, Standard Stack, Architecture Patterns | Existing CI/agent consumers may need remapping if the product actually wants a richer shell-level contract. |
| A3 | Benchmark policy should require baseline subject parity and backend comparability before applying numeric thresholds. [ASSUMED] | Phase Requirements, Architecture Patterns, Common Pitfalls | The planner could design benchmark gates that are too strict or too permissive for intended product semantics. |
| A4 | `QSpec.runtime.policy_hints` should remain advisory/default input rather than a mandatory single source of truth for all Phase 4 policies. [ASSUMED] | Open Questions | The planner could miss an intended product decision about policy configuration precedence. |

## Open Questions

1. **Should Phase 4 auto-consume `QSpec.runtime.policy_hints`, or keep CLI flags as the only policy input?**
   - What we know: `QSpec.runtime.policy_hints` already exists with `fail_on`, `compare_expectation`, and `allow_report_drift`, but compare CLI currently ignores it and takes policy only from flags. [VERIFIED: src/quantum_runtime/qspec/model.py][VERIFIED: src/quantum_runtime/intent/planner.py][VERIFIED: src/quantum_runtime/cli.py]
   - What's unclear: Whether product intent is “policy hints seed defaults” or “policy hints become the canonical stored policy.” [ASSUMED]
   - Recommendation: Plan Phase 4 assuming CLI flags remain authoritative and `policy_hints` can optionally seed defaults in a backward-compatible follow-up step. [ASSUMED]

2. **Should benchmark baseline gating consume persisted benchmark history or recompute benchmark evidence on demand?**
   - What we know: Current benchmark history persistence is revision-mislabeled for imported revision inputs, so persisted history is not yet safe enough to be treated as canonical policy evidence in every case. [VERIFIED: src/quantum_runtime/diagnostics/benchmark.py][VERIFIED: local reproduction]
   - What's unclear: Whether product wants benchmark policy to read only stored evidence or to recompute a fresh “current vs baseline” pair inside one command. [ASSUMED]
   - Recommendation: Fix persistence first, then prefer stored evidence for auditability; recompute only as an explicit mode, not hidden behavior. [ASSUMED]

3. **Should compare persistence be backfilled to include `schema_version`, and is that an additive migration or a compatibility hazard?**
   - What we know: CLI compare JSON is schema-versioned through `ensure_schema_payload()`, but persisted compare artifacts are not. [VERIFIED: src/quantum_runtime/runtime/contracts.py][VERIFIED: src/quantum_runtime/runtime/compare.py][VERIFIED: local reproduction]
   - What's unclear: Whether any downstream consumer is diffing raw compare artifact JSON shape today. [ASSUMED]
   - Recommendation: Treat the fix as an additive schema hardening step, preserve all existing compare keys, and add a regression test before changing persisted compare payloads. [ASSUMED]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Project Python runtime | Implementation and local tests. [VERIFIED: AGENTS.md] | ✓ [VERIFIED: exec_command] | `.venv/bin/python 3.11.15`. [VERIFIED: exec_command] | Use this interpreter for all Phase 4 verification work. [VERIFIED: exec_command] |
| Shell `python3` | Ad hoc scripts only. [VERIFIED: exec_command] | ✓ but wrong version for repo work. [VERIFIED: exec_command] | `3.13.2`. [VERIFIED: exec_command] | Do not use it for repo execution; use `.venv/bin/python` instead. [VERIFIED: exec_command] |
| `uv` | Environment sync and package workflows. [VERIFIED: AGENTS.md] | ✓ [VERIFIED: exec_command] | `0.11.1`. [VERIFIED: exec_command] | CI can still install through `python -m pip install -e '.[dev,qiskit]'`. [VERIFIED: .github/workflows/ci.yml] |
| `pytest` | Nyquist validation sampling. [VERIFIED: .planning/config.json][VERIFIED: .github/workflows/ci.yml] | ✓ [VERIFIED: exec_command] | `9.0.2` in the active `.venv`. [VERIFIED: exec_command] | `./.venv/bin/python -m pytest ...` works and was verified locally. [VERIFIED: local test run] |
| `ruff` | Lint gate. [VERIFIED: .github/workflows/ci.yml] | ✓ [VERIFIED: exec_command] | `0.15.8`. [VERIFIED: exec_command] | The `ruff` CLI binary is available in the active environment. [VERIFIED: exec_command] |
| `mypy` | Type gate. [VERIFIED: .github/workflows/ci.yml][VERIFIED: mypy.ini] | ✗ local launcher is broken. [VERIFIED: exec_command] | `.venv/bin/mypy` points at a stale path under `Nutstore Files/...`. [VERIFIED: exec_command] | Recreate or refresh the virtualenv before local type-check sampling. [ASSUMED] |

**Missing dependencies with no fallback:**

- A working local `mypy` launcher is not currently available in this workspace. [VERIFIED: exec_command]

**Missing dependencies with fallback:**

- The default shell `python3` is available but not usable for repo tasks because the project requires Python 3.11; `.venv/bin/python` is the verified fallback. [VERIFIED: AGENTS.md][VERIFIED: exec_command]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest 9.0.2` locally; CI runs `pytest` in GitHub Actions. [VERIFIED: exec_command][VERIFIED: .github/workflows/ci.yml] |
| Config file | `pyproject.toml` under `[tool.pytest.ini_options]`. [VERIFIED: pyproject.toml] |
| Quick run command | `./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_runtime_compare.py -q --maxfail=1`. [VERIFIED: local test run] |
| Full suite command | `./.venv/bin/python -m pytest -q --ignore tests/test_classiq_backend.py --ignore tests/test_classiq_emitter.py --ignore tests/test_qspec_validation.py`. [VERIFIED: .github/workflows/ci.yml][ASSUMED] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| POLC-01 | Compare baseline/current and fail on requested drift classes without wrapper logic. [VERIFIED: REQUIREMENTS.md] | Unit + CLI integration. [VERIFIED: tests/test_runtime_compare.py][VERIFIED: tests/test_cli_compare.py] | `./.venv/bin/python -m pytest tests/test_runtime_compare.py tests/test_cli_compare.py tests/test_cli_runtime_gap.py -q --maxfail=1`. [VERIFIED: local test run][ASSUMED] | ✅ [VERIFIED: codebase grep] |
| POLC-02 | Treat benchmark results as policy evidence, including baseline workflows. [VERIFIED: REQUIREMENTS.md] | Runtime policy unit tests + CLI integration. [VERIFIED: tests/test_cli_bench.py][ASSUMED] | `./.venv/bin/python -m pytest tests/test_cli_bench.py -q --maxfail=1`. [VERIFIED: codebase grep][ASSUMED] | ✅ [VERIFIED: codebase grep] |
| POLC-03 | Expose doctor CI mode with blocking vs advisory outputs. [VERIFIED: REQUIREMENTS.md] | Runtime classification unit tests + CLI integration. [VERIFIED: tests/test_cli_doctor.py][ASSUMED] | `./.venv/bin/python -m pytest tests/test_cli_doctor.py -q --maxfail=1`. [VERIFIED: codebase grep][ASSUMED] | ✅ [VERIFIED: codebase grep] |

### Sampling Rate

- **Per task commit:** Run the targeted policy suite for the touched command or evaluator. [VERIFIED: local test run][ASSUMED]
- **Per wave merge:** Run the Phase 4 quick suite plus the relevant lint/type gates if the environment is repaired. [VERIFIED: .github/workflows/ci.yml][VERIFIED: exec_command][ASSUMED]
- **Phase gate:** Full CI-equivalent pytest suite green before `/gsd-verify-work`. [VERIFIED: .github/workflows/ci.yml][ASSUMED]

### Wave 0 Gaps

- [ ] `tests/test_runtime_policy.py` — add shared benchmark/doctor gate evaluator coverage so policy math is not only exercised through CLI plumbing. [ASSUMED]
- [ ] `tests/test_cli_bench.py` — add imported-revision persistence regression coverage for the current history-labeling bug before building benchmark-to-baseline gates. [VERIFIED: local reproduction][ASSUMED]
- [ ] `tests/test_cli_compare.py` or `tests/test_cli_runtime_gap.py` — add a regression that persisted compare artifacts include `schema_version` once Phase 4 fixes compare persistence. [VERIFIED: local reproduction][ASSUMED]
- [ ] `tests/test_cli_doctor.py` — add `--ci` blocking/advisory JSON and JSONL coverage. [ASSUMED]
- [ ] Local type-check sampling — repair `.venv/bin/mypy` or recreate the virtualenv before claiming Phase 4 type verification is complete. [VERIFIED: exec_command][ASSUMED]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no. [VERIFIED: PROJECT.md] | Local CLI phase; no auth surface is in scope. [VERIFIED: PROJECT.md] |
| V3 Session Management | no. [VERIFIED: PROJECT.md] | Local CLI phase; no session layer is present. [VERIFIED: PROJECT.md] |
| V4 Access Control | no. [VERIFIED: PROJECT.md] | Workspace access is local filesystem access, not an application ACL surface. [VERIFIED: PROJECT.md][ASSUMED] |
| V5 Input Validation | yes. [VERIFIED: codebase grep] | Typer parameter parsing plus Pydantic model validation for policies and payloads. [VERIFIED: src/quantum_runtime/cli.py][VERIFIED: src/quantum_runtime/runtime/compare.py][CITED: https://pydantic.dev/docs/validation/latest/concepts/serialization/] |
| V6 Cryptography | yes. [VERIFIED: codebase grep] | Existing SHA-256 integrity digests in the standard library `hashlib`; never hand-roll a second scheme in Phase 4. [VERIFIED: codebase grep] |

### Known Threat Patterns for FluxQ Policy Gating

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Tampered baseline or report evidence. [VERIFIED: codebase grep] | Tampering | Reuse `resolve_workspace_baseline()`, run-manifest integrity checks, and artifact-provenance validation before policy evaluation. [VERIFIED: src/quantum_runtime/runtime/imports.py][VERIFIED: src/quantum_runtime/artifact_provenance.py] |
| Partial or conflicting gate-artifact writes. [VERIFIED: Phase 03 summaries] | Denial of Service / Tampering | Keep lease-guarded atomic persistence using `acquire_workspace_lock()`, `pending_atomic_write_files()`, and `atomic_write_text()`. [VERIFIED: 03-concurrent-workspace-safety-04-SUMMARY.md][VERIFIED: src/quantum_runtime/workspace] |
| Invalid or ambiguous policy input. [VERIFIED: codebase grep] | Tampering | Validate policy models through Pydantic and emit schema-versioned `invalid_compare_policy` or equivalent machine errors. [VERIFIED: src/quantum_runtime/cli.py][VERIFIED: src/quantum_runtime/runtime/contracts.py] |
| Path confusion from copied report files. [VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_runtime_imports.py] | Spoofing / Tampering | Reuse report import resolution and artifact provenance normalization instead of trusting raw file locations. [VERIFIED: src/quantum_runtime/runtime/imports.py][VERIFIED: src/quantum_runtime/artifact_provenance.py] |

## Sources

### Primary (HIGH confidence)

- `src/quantum_runtime/runtime/compare.py` - current compare policy, verdict, and gate contract. [VERIFIED: codebase grep]
- `src/quantum_runtime/diagnostics/benchmark.py` - benchmark evidence structure and persistence behavior. [VERIFIED: codebase grep]
- `src/quantum_runtime/runtime/doctor.py` - doctor evidence structure and current issue/advisory split. [VERIFIED: codebase grep]
- `src/quantum_runtime/cli.py` - CLI option surface, JSON emission, and exit behavior. [VERIFIED: codebase grep]
- `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/runtime/observability.py`, `src/quantum_runtime/runtime/exit_codes.py` - schema payloads, gate blocks, reason codes, and exit mappings. [VERIFIED: codebase grep]
- `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/workspace/baseline.py`, `src/quantum_runtime/artifact_provenance.py` - baseline, revision, and trust-resolution rules. [VERIFIED: codebase grep]
- `tests/test_cli_compare.py`, `tests/test_runtime_compare.py`, `tests/test_cli_bench.py`, `tests/test_cli_doctor.py`, `tests/test_cli_runtime_gap.py` - current regression coverage and missing Phase 4 coverage. [VERIFIED: codebase grep]
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/PROJECT.md`, `.planning/STATE.md` - phase scope, requirements, and milestone constraints. [VERIFIED: files_to_read]
- `.planning/phases/03-concurrent-workspace-safety/*-SUMMARY.md` and `03-REVIEWS.md` - workspace-safety contract inherited by Phase 4. [VERIFIED: files_to_read]
- Typer docs - `https://typer.tiangolo.com/tutorial/terminating/` for explicit exit-code control. [CITED: https://typer.tiangolo.com/tutorial/terminating/]
- Click docs - `https://click.palletsprojects.com/en/stable/exceptions/` for default CLI exception and exit-code semantics. [CITED: https://click.palletsprojects.com/en/stable/exceptions/]
- Pydantic serialization docs - `https://pydantic.dev/docs/validation/latest/concepts/serialization/` for `model_dump_json()` behavior. [CITED: https://pydantic.dev/docs/validation/latest/concepts/serialization/]
- PyPI pages and JSON endpoints for current package/version verification. [VERIFIED: pypi.org JSON][CITED: https://pypi.org/project/pydantic/][CITED: https://pypi.org/project/pytest/][CITED: https://pypi.org/project/ruff/]

### Secondary (MEDIUM confidence)

- None. Core findings were grounded in code, local reproductions, or official docs rather than secondary commentary. [VERIFIED: codebase grep][VERIFIED: local reproduction][CITED: https://typer.tiangolo.com/tutorial/terminating/][CITED: https://pydantic.dev/docs/validation/latest/concepts/serialization/]

### Tertiary (LOW confidence)

- None. Uncertainty is isolated in the Assumptions Log instead of being presented as sourced fact. [VERIFIED: codebase grep][ASSUMED]

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - The phase stays on the existing brownfield stack already pinned in project docs, `pyproject.toml`, and the active `.venv`. [VERIFIED: AGENTS.md][VERIFIED: pyproject.toml][VERIFIED: installed package]
- Architecture: MEDIUM - The current compare pattern is clear, but benchmark and doctor still need additive design decisions around shared policy evaluation and configuration precedence. [VERIFIED: codebase grep][ASSUMED]
- Pitfalls: HIGH - The main risks were verified directly in code, tests, and local reproductions. [VERIFIED: codebase grep][VERIFIED: local reproduction][VERIFIED: local test run]

**Research date:** 2026-04-13 [VERIFIED: system date]
**Valid until:** 2026-05-13 for repo-internal findings; re-check PyPI package metadata earlier if dependency upgrades become part of scope. [VERIFIED: system date][ASSUMED]
