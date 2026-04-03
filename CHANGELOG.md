# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

- polish the public README with clearer install, first-run, and trust-surface sections
- add curated `v0.2.0` release notes and stronger public release discoverability
- add workspace baseline persistence with `qrun baseline set/show/clear`
- add `qrun compare --baseline` so CI and agents can compare the current workspace against a saved approved baseline
- surface baseline state in `qrun inspect --json` and degrade cleanly when the saved baseline can no longer be resolved
- enforce stored report/QSpec identity when replaying saved baselines, including copied-report canonicalization back to stable history paths when hashes match

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
