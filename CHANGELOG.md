# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

- clarify stable, evolving, and optional runtime contracts for adopters
- align packaging metadata with the runtime control plane positioning

## 0.3.1

`0.3.1` is the agent-observability release for FluxQ: shared health signals, decision blocks, and JSONL event streams that make the runtime control plane easier for agents and CI to consume incrementally.

- add `health`, `reason_codes`, `next_actions`, and `decision` or `gate` blocks to the machine-facing control plane
- add `--jsonl` event streams for `qrun exec`, `qrun compare`, `qrun bench`, and `qrun doctor`
- keep `--json` as the one-shot result surface while making the terminal completed JSONL event carry the same core payload
- harden control-plane trust checks for active `qspec`, `report`, `manifest`, and baseline state
- improve copied-report portability when a caller-provided workspace can safely satisfy the expected revision inputs

## 0.3.0

`0.3.0` is the runtime control-plane release for FluxQ: agent-first command surfaces, immutable per-run manifests, and schema-versioned machine output across the CLI.

- reposition FluxQ as an agent-first quantum runtime CLI rather than a thin natural-language demo surface
- add immutable `manifests/history/<revision>.json` and `manifests/latest.json` artifacts alongside `qspec.json` and `report.json`
- add `qrun plan`, `qrun status`, `qrun show`, and `qrun schema`
- emit `schema_version` on machine-readable command payloads and core runtime artifacts
- add structured `error_code` and `remediation` fields to machine-readable CLI failures
- keep `QSpec.version` as the IR version while treating CLI/result/artifact `schema_version` as a separate compatibility surface

## 0.2.4

`0.2.4` is a patch release that tightens FluxQ's public install and trust contract without changing the core decision-loop surface introduced in `0.2.3`.

- move the local `qiskit-local` runtime stack into the base install so the public `qrun` entrypoint is runnable without extra dependency flags
- make default `qrun bench` scope follow the active QSpec instead of always appending `classiq`
- fail `qrun export --json` closed on current-workspace replay/provenance mismatches instead of silently dropping source metadata

## 0.2.3

`0.2.3` is the decision-grade release for FluxQ's current local runtime surface: baseline-backed compare, trust-honest benchmarking, bounded parameterized expectation workflows, and clearer dependency diagnostics for agent and CI loops.

- polish the public README with clearer install, first-run, and trust-surface sections
- add curated `v0.2.3` release notes and stronger public release discoverability
- add workspace baseline persistence with `qrun baseline set/show/clear`
- add `qrun compare --baseline` so CI and agents can compare the current workspace against a saved approved baseline
- surface baseline state in `qrun inspect --json` and degrade cleanly when the saved baseline can no longer be resolved
- enforce stored report/QSpec identity when replaying saved baselines, including copied-report canonicalization back to stable history paths when hashes match
- emit replay provenance fields from `qrun export --json` so hosts can trace `source_kind`, `source_revision`, `source_report_path`, and `source_qspec_path`
- surface `detached_report_inputs` in `qrun compare --json` so hosts can detect copied-report replay explicitly
- surface `replay_integrity` in `qrun inspect --json`
- add replay-trust deltas and `--forbid-replay-integrity-regressions` to `qrun compare`
- label benchmark entries as `structural_only`, `target_aware`, or `synthesis_backed`
- separate target-aware transpile provenance from Classiq synthesis-backed provenance so FluxQ does not overclaim cross-backend equivalence
- treat missing optional backends as advisories unless the active workspace requests them
- add parameterized local expectation workflows for `qaoa_ansatz` and `hardware_efficient_ansatz`
- report explicit parameter workflow metadata, weighted `X/Y/Z` Pauli-sum observable specs, exact local expectation values, representative-bound exports, and sampled best sweep points without claiming optimization or backend parity
- bound parameterized expectation workflows to local evaluation instead of presenting them as a general optimizer runtime

## 0.2.0

`0.2.0` is the first public release baseline for FluxQ: an agent-facing quantum workflow runtime rather than a narrow codegen demo.

- publish an Apache-2.0 open-source release surface with contributor, security, and support docs
- expand `qrun exec` coverage beyond intent-only input
- keep report-backed replay and export flows anchored to revision-stable qspec/report/artifact provenance
- let copied report files replay safely through stored workspace provenance and revision snapshots
- emit replay provenance fields from `qrun export --json` so hosts can trace `source_kind`, `source_revision`, `source_report_path`, and `source_qspec_path`
- surface `detached_report_inputs` in `qrun compare --json` so hosts can detect copied-report replay explicitly
- enforce replay-integrity checks for report-backed QSpec imports and surface `replay_integrity` in `qrun inspect --json`
- deepen `hardware_efficient_ansatz` and `qaoa_ansatz` with explicit layer, topology, and parameter semantics
- deepen backend benchmarking and Classiq synthesis reporting
- stabilize semantic provenance across `report`, `inspect`, and `bench` outputs
- add `qrun compare` for semantic workload identity checks across reports and revisions
- add compare policy verdicts for CI and agent guardrails
- add replay-trust deltas and `--forbid-replay-integrity-regressions` to `qrun compare`
- surface artifact output digests and output-set drift in compare/report summaries
- improve packaging and release automation

## 0.1.0

- initialize deterministic `.quantum` workspaces
- parse markdown intents and lower them into QSpec
- emit Qiskit Python, OpenQASM 3, and Classiq Python SDK source
- run local simulation, transpile validation, diagrams, reports, and structural benchmarking
- provide aionrs integration examples and runnable CLI JSON workflows
