# Phase 1: Canonical Ingress Resolution - Research

**Researched:** 2026-04-12
**Confidence:** HIGH on current implementation shape; MEDIUM on Phase 1 closure because some equivalence and no-side-effect guarantees are implied by code but not directly covered by the current tests. `[VERIFIED: src/quantum_runtime/cli.py:217-442]` `[VERIFIED: src/quantum_runtime/runtime/resolve.py:71-171]` `[VERIFIED: tests/test_cli_runtime_gap.py:16-78]`

<phase_requirements>
## Phase Requirements

| ID | Requirement | Current Evidence | Gap / Risk |
|---|---|---|---|
| INGR-01 | Agent can submit prompt text and receive a normalized machine-readable intent without mutating workspace state. `[VERIFIED: .planning/REQUIREMENTS.md:10-15]` | `qrun prompt` exists, returns `IntentResolution`, and the command path only parses and echoes the payload. `[VERIFIED: src/quantum_runtime/cli.py:217-238]` `[VERIFIED: src/quantum_runtime/runtime/resolve.py:174-180]` | The provided tests validate payload shape for `qrun prompt`, but they do not explicitly assert that no workspace artifacts are created. `[VERIFIED: tests/test_cli_runtime_gap.py:16-33]` |
| INGR-02 | Agent can resolve prompt, markdown intent, and structured JSON intent into a canonical `QSpec` plus execution plan. `[VERIFIED: .planning/REQUIREMENTS.md:10-15]` | `qrun resolve` and `qrun plan` both call the shared resolver, and the shared resolver accepts `intent_text`, `intent_file`, and `intent_json_file` and lowers plannable inputs through `plan_to_qspec()`. `[VERIFIED: src/quantum_runtime/cli.py:240-442]` `[VERIFIED: src/quantum_runtime/runtime/control_plane.py:103-198]` `[VERIFIED: src/quantum_runtime/runtime/resolve.py:71-112]` `[VERIFIED: src/quantum_runtime/runtime/resolve.py:184-212]` | The provided tests prove markdown and structured JSON parity on `resolve`, but they do not cover `resolve --intent-text` parity against equivalent file-based inputs. `[VERIFIED: tests/test_cli_runtime_gap.py:36-78]` |
| INGR-03 | Semantically equivalent ingress inputs resolve to the same workload identity and semantic hash. `[VERIFIED: .planning/REQUIREMENTS.md:10-15]` | `summarize_qspec_semantics()` defines stable `workload_id`, `workload_hash`, `execution_hash`, and `semantic_hash`, and one test already proves identical `semantic_hash` for markdown and structured JSON inputs representing the same intent. `[VERIFIED: src/quantum_runtime/qspec/semantics.py:13-143]` `[VERIFIED: tests/test_cli_runtime_gap.py:36-78]` | `semantic_hash` is execution-oriented, not workload-only, so changes to defaults or runtime metadata can invalidate parity even when the circuit subject is unchanged. `[VERIFIED: src/quantum_runtime/qspec/semantics.py:21-56]` `[VERIFIED: src/quantum_runtime/intent/parser.py:26-37]` `[VERIFIED: src/quantum_runtime/intent/planner.py:210-241]` |
</phase_requirements>

## Summary

Phase 1 already has most of its control-plane spine in place: the product docs say FluxQ should treat prompt text as ingress, keep `QSpec` as the canonical truth layer, and normalize ingress before side effects; the architecture notes in `AGENTS.md` say every ingress path should go through `src/quantum_runtime/runtime/resolve.py` into `ResolvedRuntimeInput`. `[VERIFIED: .planning/PROJECT.md:5-7]` `[VERIFIED: .planning/PROJECT.md:56-60]` `[VERIFIED: AGENTS.md:138-145]` `[VERIFIED: AGENTS.md:183-188]`

The current code already matches that shape for the main Phase 1 path: `qrun prompt` returns normalized intent only, while `qrun resolve` and `qrun plan` route supported inputs through the same resolver, produce canonical `QSpec` semantics plus a dry-run execution plan, and do so without any visible write calls in the provided files. `[VERIFIED: src/quantum_runtime/cli.py:217-238]` `[VERIFIED: src/quantum_runtime/cli.py:240-442]` `[VERIFIED: src/quantum_runtime/runtime/control_plane.py:103-198]` `[VERIFIED: src/quantum_runtime/runtime/resolve.py:71-171]`

The remaining work is mostly guarantee-hardening, not architectural invention: the current tests prove prompt intent normalization and markdown-vs-structured-JSON semantic-hash parity, but they do not yet lock down prompt-text parity against equivalent markdown/JSON or explicitly assert that side-effect-free commands leave no workspace artifacts behind. `[VERIFIED: tests/test_cli_runtime_gap.py:16-78]`

## 1. What Ingress Surfaces Already Exist Now?

- The repo-level product docs already list supported runtime inputs as markdown intents, prompt text, structured JSON intents, `QSpec`, and replayable report inputs. `[VERIFIED: .planning/PROJECT.md:17-20]`
- `qrun prompt <text>` is a dedicated side-effect-free ingress surface that returns only normalized intent. `[VERIFIED: src/quantum_runtime/cli.py:217-238]`
- `qrun resolve` accepts `--intent-file`, `--intent-json-file`, `--qspec-file`, `--report-file`, `--revision`, and `--intent-text/--prompt-text`. `[VERIFIED: src/quantum_runtime/cli.py:240-340]`
- `qrun plan` accepts the same six ingress selectors as `qrun resolve`. `[VERIFIED: src/quantum_runtime/cli.py:343-442]`
- `qrun exec` also accepts the same six ingress selectors, but it is the mutating execution surface and belongs to the later runtime-artifact story rather than the side-effect-free Phase 1 contract. `[VERIFIED: src/quantum_runtime/cli.py:912-1056]` `[VERIFIED: .planning/ROADMAP.md:22-39]`
- Internally, the shared resolver models six `source_kind` values: `prompt_text`, `intent_file`, `intent_json_file`, `qspec_file`, `report_file`, and `report_revision`. `[VERIFIED: src/quantum_runtime/runtime/resolve.py:29-36]`

## 2. What Normalization Path Already Exists Now?

1. Prompt or markdown text is parsed into `IntentModel` by `parse_intent_text()`, which extracts front matter and sections, derives `goal`, and defaults `exports` to `["qiskit", "qasm3"]`, `backend_preferences` to `["qiskit-local"]`, and `shots` to `1024`. `[VERIFIED: src/quantum_runtime/intent/parser.py:17-37]`
2. Structured JSON intent is parsed into the same `IntentModel` contract through `IntentModel.model_validate()`. `[VERIFIED: src/quantum_runtime/intent/parser.py:40-50]`
3. `resolve_runtime_input()` enforces exactly one ingress source and dispatches all supported surfaces through one shared entrypoint. `[VERIFIED: src/quantum_runtime/runtime/resolve.py:71-87]`
4. Plannable ingress inputs (`intent_file`, `intent_json_file`, `prompt_text`) flow through `_resolved_from_intent()`, which calls `plan_to_qspec()` and then `_validated_qspec()`. `[VERIFIED: src/quantum_runtime/runtime/resolve.py:89-112]` `[VERIFIED: src/quantum_runtime/runtime/resolve.py:184-212]`
5. `_validated_qspec()` normalizes and validates every `QSpec` before it leaves the resolver. `[VERIFIED: src/quantum_runtime/runtime/resolve.py:259-267]`
6. `qspec_file` ingress bypasses the planner but still goes through `_validated_qspec()`, then synthesizes an `IntentModel` back from the canonical `QSpec`. `[VERIFIED: src/quantum_runtime/runtime/resolve.py:113-141]` `[VERIFIED: src/quantum_runtime/runtime/resolve.py:233-249]`
7. `report_file` and `revision` ingress rehydrate a `QSpec` through import resolution, validate it, and synthesize intent plus requested exports from the imported report artifacts. `[VERIFIED: src/quantum_runtime/runtime/resolve.py:143-171]` `[VERIFIED: src/quantum_runtime/runtime/resolve.py:285-296]`
8. `resolve_runtime_object()` wraps the normalized input with semantic `QSpec` summary and a dry-run plan, while `build_execution_plan_from_resolved()` adds backend, artifact, and baseline-readiness context. `[VERIFIED: src/quantum_runtime/runtime/control_plane.py:126-198]`

## 3. What Semantic / Hash Contracts Already Exist Now?

- `summarize_qspec_semantics()` defines the host-facing semantic summary for a canonical `QSpec`, including pattern, width, layers, parameters, observables, constraints, backend preferences, problem, parameter space, objective, export requirements, policy hints, provenance, `workload_id`, and `algorithm_family`. `[VERIFIED: src/quantum_runtime/qspec/semantics.py:13-57]`
- `workload_hash` is the SHA-256 hash of the workload payload, which includes workload identity plus structural and objective semantics. `[VERIFIED: src/quantum_runtime/qspec/semantics.py:54-55]` `[VERIFIED: src/quantum_runtime/qspec/semantics.py:102-118]` `[VERIFIED: src/quantum_runtime/qspec/semantics.py:129-132]`
- `execution_hash` is the SHA-256 hash of the full semantic summary except the hash fields themselves, and `semantic_hash` is currently an alias of `execution_hash`. `[VERIFIED: src/quantum_runtime/qspec/semantics.py:54-56]` `[VERIFIED: src/quantum_runtime/qspec/semantics.py:121-132]`
- `workload_id` comes from `qspec.runtime.workload_id` when present; otherwise it falls back to `pattern:widthq[:layersl]`. The planner emits the same string format when it builds runtime metadata. `[VERIFIED: src/quantum_runtime/qspec/semantics.py:135-143]` `[VERIFIED: src/quantum_runtime/intent/planner.py:210-248]`
- The control-plane summary returned by `resolve` and `plan` exposes `pattern`, `workload_id`, `algorithm_family`, `workload_hash`, `execution_hash`, `semantic_hash`, parameter-workflow fields, width, layers, and counts, so consumers already have a stable planning-oriented identity block. `[VERIFIED: src/quantum_runtime/runtime/control_plane.py:494-508]`
- One regression test already proves that equivalent markdown and structured JSON ingress for the same QAOA sweep resolve to the same `semantic_hash`. `[VERIFIED: tests/test_cli_runtime_gap.py:36-78]`
- Planner tests also lock down canonical `QSpec` shape for GHZ, QAOA MaxCut, and hardware-efficient ansatz, including parameter workflows and observable semantics. `[VERIFIED: tests/test_planner.py:16-145]`

## 4. What Is Still Missing Or Risky For Phase 1 Completion?

- The provided tests do not yet prove parity for `resolve --intent-text` against equivalent markdown or structured JSON inputs, even though the code routes them through the same shared resolver. `[VERIFIED: src/quantum_runtime/runtime/resolve.py:89-112]` `[VERIFIED: tests/test_cli_runtime_gap.py:16-78]`
- The provided tests do not explicitly assert that `qrun prompt`, `qrun resolve`, or `qrun plan` leave the workspace untouched. The code path in the allowed files is read-only, but the regression contract is not yet pinned by a test. `[VERIFIED: src/quantum_runtime/cli.py:217-442]` `[VERIFIED: src/quantum_runtime/runtime/control_plane.py:103-198]` `[VERIFIED: tests/test_cli_runtime_gap.py:16-78]`
- The planner is intentionally narrow today: it recognizes GHZ, Bell, QFT, hardware-efficient ansatz, and MaxCut QAOA, and unsupported goals raise `manual_qspec_required`. That is a valid current boundary, but it means Phase 1 should not be planned as “arbitrary natural language to QSpec.” `[VERIFIED: src/quantum_runtime/intent/planner.py:79-93]` `[VERIFIED: tests/test_planner.py:148-186]`
- `build_execution_plan_from_resolved()` mixes ingress normalization with backend-capability and baseline-readiness findings, so `plan` or `resolve` can become `degraded` for reasons unrelated to parsing or semantic equivalence. That is useful, but the planner should avoid treating every degraded result as a Phase 1 ingress failure. `[VERIFIED: src/quantum_runtime/runtime/control_plane.py:136-162]`
- `semantic_hash` is sensitive to execution-oriented metadata because it aliases `execution_hash`, and `execution_hash` includes the full semantic summary. Changing parser defaults, runtime metadata, export requirements, policy hints, or provenance will change the hash contract. `[VERIFIED: src/quantum_runtime/qspec/semantics.py:21-56]` `[VERIFIED: src/quantum_runtime/intent/parser.py:26-37]` `[VERIFIED: src/quantum_runtime/intent/planner.py:210-241]`
- Workspace defaults can influence requested exports for `qspec_file` and report/revision ingress through `_default_exports()` and report artifact inspection. That is outside the explicit Phase 1 success criteria, but it is a real coupling in the shared resolver. `[VERIFIED: src/quantum_runtime/runtime/resolve.py:270-296]` `[VERIFIED: .planning/ROADMAP.md:22-30]`

## 5. What Plan Constraints Should The Planner Honor To Avoid Regressions?

- Keep `QSpec` as the canonical truth layer and evolve it compatibly instead of introducing a new IR or bypass path. `[VERIFIED: .planning/PROJECT.md:46-50]` `[VERIFIED: .planning/PROJECT.md:56-60]`
- Keep all supported ingress normalization routed through `src/quantum_runtime/runtime/resolve.py` and `ResolvedRuntimeInput`; do not duplicate resolution logic inside CLI commands. `[VERIFIED: AGENTS.md:138-145]` `[VERIFIED: AGENTS.md:183-188]` `[VERIFIED: src/quantum_runtime/runtime/control_plane.py:103-198]`
- Preserve the side-effect-free contract for `prompt`, `resolve`, and `plan`; persisted `intent`, `plan`, and event artifacts belong to `exec` and the later runtime-artifact phases. `[VERIFIED: .planning/ROADMAP.md:22-39]` `[VERIFIED: .planning/REQUIREMENTS.md:10-20]` `[VERIFIED: tests/test_cli_runtime_gap.py:81-115]`
- Preserve existing machine-readable payload shape and schema-versioned behavior for the ingress surfaces that already have tests, including `schema_version == "0.3.0"` and the current `intent`, `qspec`, and `plan` blocks returned by JSON mode. `[VERIFIED: tests/test_cli_runtime_gap.py:16-78]`
- Do not change default prompt/markdown normalization lightly: default exports, backend preferences, shots, and supported pattern heuristics already affect `QSpec` generation and hash identity. `[VERIFIED: src/quantum_runtime/intent/parser.py:26-37]` `[VERIFIED: src/quantum_runtime/intent/planner.py:30-76]`
- Treat unsupported goals as a deliberate `manual_qspec_required` boundary unless requirements explicitly expand the planner’s language coverage. `[VERIFIED: src/quantum_runtime/intent/planner.py:79-93]` `[VERIFIED: tests/test_planner.py:180-186]`
- If Phase 1 adds new tests, prefer tests that prove cross-ingress parity and no-write behavior rather than broadening the planner’s pattern catalog. That aligns with the roadmap’s success criteria and avoids accidental Phase 2 scope creep. `[VERIFIED: .planning/ROADMAP.md:22-30]` `[VERIFIED: tests/test_cli_runtime_gap.py:16-78]`

## Sources

- `.planning/PROJECT.md` `[VERIFIED: .planning/PROJECT.md:1-80]`
- `.planning/ROADMAP.md` `[VERIFIED: .planning/ROADMAP.md:1-91]`
- `.planning/REQUIREMENTS.md` `[VERIFIED: .planning/REQUIREMENTS.md:1-80]`
- `AGENTS.md` `[VERIFIED: AGENTS.md:1-244]`
- `src/quantum_runtime/cli.py` `[VERIFIED: src/quantum_runtime/cli.py:217-442]` `[VERIFIED: src/quantum_runtime/cli.py:912-1056]`
- `src/quantum_runtime/runtime/resolve.py` `[VERIFIED: src/quantum_runtime/runtime/resolve.py:29-296]`
- `src/quantum_runtime/runtime/control_plane.py` `[VERIFIED: src/quantum_runtime/runtime/control_plane.py:103-198]` `[VERIFIED: src/quantum_runtime/runtime/control_plane.py:494-508]`
- `src/quantum_runtime/intent/parser.py` `[VERIFIED: src/quantum_runtime/intent/parser.py:12-78]`
- `src/quantum_runtime/intent/planner.py` `[VERIFIED: src/quantum_runtime/intent/planner.py:30-510]`
- `src/quantum_runtime/qspec/semantics.py` `[VERIFIED: src/quantum_runtime/qspec/semantics.py:13-143]`
- `tests/test_cli_runtime_gap.py` `[VERIFIED: tests/test_cli_runtime_gap.py:16-115]`
- `tests/test_planner.py` `[VERIFIED: tests/test_planner.py:16-186]`
