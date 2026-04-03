# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

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
