# FluxQ

![Release](https://img.shields.io/github/v/release/xi-zhao/FluxQ?sort=semver)
![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-3776AB.svg)

Agent-first quantum runtime control plane for reproducible quantum runs.

FluxQ is an agent-first quantum runtime CLI. It turns natural language ingress, structured intent files, QSpec inputs, and report replays into executable, revisioned, and machine-readable run objects that coding agents and CI systems can trust.

Natural language is ingress, not the source of truth. FluxQ's product core is the runtime: canonical `QSpec`, immutable run manifests, reproducible reports, semantic comparison, and explicit provenance for export, benchmark, and diagnostics flows.

Package: `quantum-runtime`  
CLI: `qrun`  
Current release: `0.3.1`

## Why FluxQ

- prompt text is useful as ingress, but agents need a canonical runtime object they can re-run and compare later
- replayable reports and immutable manifests let hosts continue a workflow from revision-stable state instead of from prompt folklore
- semantic workload comparison is more useful than raw file diff when you need to know whether a circuit family actually changed
- one workload can be exported into Qiskit, OpenQASM 3, and Classiq Python outputs without losing surrounding workspace history
- local simulation, transpile validation, diagrams, structural benchmarking, and `doctor` checks make iteration fast before deeper backend work begins

## Use FluxQ If

- quantum developers who want circuits, exports, and diagnostics anchored to a stable workspace
- agent and CI builders who need file-based orchestration, schema-versioned JSON, and stable exit codes
- teams that want to compare revisions, catch replay regressions, and keep generated quantum workflows understandable over time

## Install

For CLI use from the public GitHub release:

```bash
uv tool install git+https://github.com/xi-zhao/FluxQ@v0.3.1
```

This public install includes the local `qiskit-local` runtime stack. `classiq` remains optional.

For local development and contributor workflows:

```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e '.[dev]'
```

FluxQ currently targets Python `3.11`.

For a one-shot local bootstrap and verification flow from the repository root:

```bash
./scripts/dev-bootstrap.sh all
```

For mainland China networks, the same helper can switch to a mirror without editing your shell profile:

```bash
./scripts/dev-bootstrap.sh all --mirror tsinghua
```

## First Run

```bash
qrun prompt "Build a 4-qubit GHZ circuit and measure all qubits." --json
qrun resolve --workspace .quantum --intent-file examples/intent-ghz.md --json
qrun init --workspace .quantum --json
qrun plan --workspace .quantum --intent-file examples/intent-ghz.md --json
qrun exec --workspace .quantum --intent-file examples/intent-ghz.md --jsonl
qrun baseline set --workspace .quantum --revision rev_000001 --json
qrun compare --workspace .quantum --baseline --fail-on subject_drift --json
qrun doctor --workspace .quantum --json --ci
qrun pack --workspace .quantum --revision rev_000001 --json
qrun pack-inspect --pack-root .quantum/packs/rev_000001 --json
qrun pack-import --pack-root .quantum/packs/rev_000001 --workspace downstream/.quantum --json
```

This first supported path is prompt/resolve -> init/plan/exec -> baseline -> compare -> doctor --ci -> pack -> pack-inspect -> pack-import.

After one GHZ run, FluxQ writes:

- `.quantum/specs/current.json`
- `.quantum/manifests/latest.json`
- `.quantum/artifacts/qiskit/main.py`
- `.quantum/artifacts/qasm/main.qasm`
- `.quantum/figures/circuit.png`
- `.quantum/reports/latest.json`

You can also execute from existing workspace state instead of starting from an intent every time:

```bash
qrun exec --workspace .quantum --qspec-file .quantum/specs/current.json --json
qrun exec --workspace .quantum --report-file .quantum/reports/latest.json --json
qrun exec --workspace .quantum --intent-text "Generate a 4-qubit GHZ circuit and measure all qubits." --json
```

## Runtime Object

FluxQ is designed to be orchestrated by coding agents through files plus shell commands. The release focus is not just generation, but a stable runtime control plane.

- natural language or markdown intent is ingress
- canonical `QSpec` is the truth layer for planning, compare, and export
- normalized `intent.json` and `plan.json` are persisted per revision so agents can consume ingress and feasibility separately from execution
- every run persists `qspec.json`, `report.json`, and immutable `manifest.json` state
- `qrun prompt`, `qrun resolve`, `qrun plan`, `qrun status`, `qrun show`, and `qrun schema` are machine-first control-plane commands for agents and CI
- `qrun exec|compare|bench|doctor --jsonl` expose event streams for incremental agent consumption

## Trust And Replay

- reports include stable provenance metadata for replay and inspection
- manifests persist a join record for one revision so agents can identify what was run, exported, and selected
- copied report files remain replayable as long as their recorded revision snapshots are still available
- workspace baselines persist approved report/QSpec states at `.quantum/baselines/current.json`
- `qrun compare --baseline --json` compares the saved baseline against the current workspace without retyping revisions
- all machine-readable command payloads include `schema_version`
- `qrun status`, `qrun show`, `qrun inspect`, and `qrun compare` now expose `health`, `reason_codes`, `next_actions`, and `decision` or `gate` blocks
- `--jsonl` event streams for `qrun exec`, `qrun compare`, `qrun bench`, and `qrun doctor` make long-running steps incrementally consumable
- workspace event streams are also persisted at `.quantum/events.jsonl` as a canonical alias for `trace/events.ndjson`
- report-backed imports now enforce replay integrity for QSpec identity instead of trusting path existence alone
- baseline-backed compares also enforce stored report/QSpec identity so tampered baseline inputs fail closed
- `qrun export --json` reports `source_kind`, `source_revision`, `source_report_path`, and `source_qspec_path`
- `qrun status --json` reports workspace, active artifact, and baseline readiness
- `qrun show --json` returns one selected run plus its baseline relation
- `qrun compare --json` reports `detached_report_inputs` so hosts can detect copied-report replay explicitly
- `qrun inspect --json` reports `replay_integrity` so hosts can detect legacy, degraded, or invalid replay trust directly
- `qrun inspect --json` reports a `baseline` block so hosts can tell whether the current workspace still matches the approved baseline
- `qrun compare --json` reports side-level `replay_integrity`, `replay_integrity_delta`, and `replay_integrity_regressions`
- reports, inspect, and compare all expose stable semantic hashes for workload identity
- `qrun compare` separates workload identity drift from generated artifact output drift and diagnostics drift
- `qrun compare --forbid-replay-integrity-regressions --json` lets CI fail when the right-hand replay input is less trustworthy than the baseline
- Detached copied reports still replay, but `qrun compare --json` degrades with exit code `2` so CI and hosts can treat replay trust as weaker than in-workspace history inputs

## Decision Loop

FluxQ `0.3.1` is organized around a simple decision loop for agent and CI workflows:

1. plan a workload into a canonical runtime object
2. execute that workload into a revisioned workspace
3. save an approved baseline
4. compare the current workspace against that baseline
5. show or export the selected run with explicit provenance
6. benchmark and run `doctor` before continuing so dependency assumptions are explicit

This keeps the first supported path grounded in `plan -> exec -> baseline -> compare -> show/export -> bench/doctor` rather than a bag of unrelated commands.

## Agent Observability

- `--json` is for one-shot machine results
- `--jsonl` is for long-running command streams with stable event envelopes
- `status/show/inspect/compare` expose compact decision signals so agents can act without opening workspace files directly
- `next_actions` are short machine hints such as `run_exec`, `set_baseline`, `review_compare`, and `run_doctor`

## Benchmark Honesty

FluxQ labels benchmark entries as `structural_only`, `target_aware`, and `synthesis_backed`.

FluxQ does not present Qiskit transpile metrics and Classiq synthesis metrics as directly equivalent by default. `qrun bench --json` exposes `benchmark_mode`, `comparable`, `comparability_reason`, `target_parity`, `target_assumptions`, and `fallback_reason` so hosts can decide when a comparison is trustworthy.

When `--backends` is omitted, `qrun bench` defaults to `qiskit-local` plus any optional backend the active QSpec explicitly requests.

`qrun doctor --json` now treats missing optional backends as advisories unless the active workspace actually depends on them, so hosts can distinguish environment drift from a truly blocking runtime dependency.

## Parameterized Local Evaluation

FluxQ `0.3.1` keeps the existing local parameter workflow contract for `qaoa_ansatz` and `hardware_efficient_ansatz`. This batch remains intentionally local and explicit: `qiskit-local` exact evaluation, small bindings or sweeps, and declared Pauli-sum observables.

- `parameter_workflow.mode` is `binding` or `sweep`
- observables are explicit weighted `X/Y/Z` Pauli-string terms
- QAOA MaxCut lowers a built-in cost observable into explicit Pauli-sum terms
- local expectation values are evaluated from the pre-measure state with `exact_statevector` on `qiskit-local`
- exported Qiskit/QASM/Classiq source and diagrams follow the representative evaluated point for the run
- `best_point` currently supports one objective observable, not multi-objective optimization
- this is bounded local evaluation rather than a general optimizer workflow
- `0.3.1` is not an optimizer, gradient engine, or remote execution story

Example:

```bash
qrun exec --workspace .quantum --intent-file examples/intent-qaoa-maxcut-sweep.md --json
```

## Workspace Layout

`qrun init --workspace .quantum` creates:

```text
.quantum/
├─ events.jsonl
├─ workspace.json
├─ manifests/
├─ qrun.toml
├─ baselines/
├─ intents/history/
├─ plans/history/
├─ specs/history/
├─ artifacts/qiskit/
├─ artifacts/classiq/
├─ artifacts/qasm/
├─ artifacts/history/
├─ figures/
├─ reports/history/
├─ trace/events.ndjson
└─ cache/
```

## Command Reference

- `qrun init --workspace .quantum --json`
- `qrun prompt "Generate a 4-qubit GHZ circuit and measure all qubits." --json`
- `qrun resolve --workspace .quantum --intent-file examples/intent-ghz.md --json`
- `qrun resolve --workspace .quantum --intent-json-file intent.json --json`
- `qrun plan --workspace .quantum --intent-file examples/intent-ghz.md --json`
- `qrun exec --workspace .quantum --intent-file examples/intent-ghz.md --json`
- `qrun exec --workspace .quantum --intent-file examples/intent-ghz.md --jsonl`
- `qrun exec --workspace .quantum --intent-json-file intent.json --json`
- `qrun exec --workspace .quantum --qspec-file .quantum/specs/current.json --json`
- `qrun exec --workspace .quantum --report-file .quantum/reports/latest.json --json`
- `qrun exec --workspace .quantum --intent-text "Generate a 4-qubit GHZ circuit and measure all qubits." --json`
- `qrun baseline set --workspace .quantum --revision rev_000001 --json`
- `qrun baseline show --workspace .quantum --json`
- `qrun baseline clear --workspace .quantum --json`
- `qrun status --workspace .quantum --json`
- `qrun show --workspace .quantum --json`
- `qrun show --workspace .quantum --revision rev_000001 --json`
- `qrun schema manifest`
- `qrun schema intent`
- `qrun inspect --workspace .quantum --json`
- `qrun compare --workspace .quantum --baseline --expect same-subject --json`
- `qrun compare --workspace .quantum --baseline --fail-on report_drift --detail --json`
- `qrun export --workspace .quantum --report-file .quantum/reports/latest.json --format qasm3 --json`
- `qrun export --workspace .quantum --format qiskit --profile qiskit-native --json`
- `qrun bench --workspace .quantum --report-file .quantum/reports/latest.json --json`
- `qrun bench --workspace .quantum --json`
- `qrun compare --workspace .quantum --left-revision rev_000001 --right-revision rev_000002 --expect same-subject --json`
- `qrun compare --workspace .quantum --left-revision rev_000001 --right-revision rev_000002 --jsonl`
- `qrun compare --workspace .quantum --left-report-file .quantum/reports/history/rev_000001.json --forbid-replay-integrity-regressions --json`
- `qrun doctor --workspace .quantum --json --fix`
- `qrun doctor --workspace .quantum --jsonl --fix`
- `qrun bench --workspace .quantum --jsonl`
- `qrun pack --workspace .quantum --revision rev_000001 --json`
- `qrun backend list --json`
- `qrun version`

## Agent And Host Integration

- aionrs integration examples: `docs/aionrs-integration.md`
- parameterized QAOA example: `examples/intent-qaoa-maxcut-sweep.md`
- sample `CLAUDE.md`: `integrations/aionrs/CLAUDE.md.example`
- sample hooks: `integrations/aionrs/hooks.example.toml`

## Open Source

FluxQ is released under `Apache-2.0`.

- Repository: `https://github.com/xi-zhao/FluxQ`
- Release: `https://github.com/xi-zhao/FluxQ/releases/tag/v0.3.1`
- Release notes source: `docs/releases/v0.3.1.md`
- License: `LICENSE`
- Contributing guide: `CONTRIBUTING.md`
- Security policy: `SECURITY.md`
- Support guide: `SUPPORT.md`

## Development

```bash
uv run --python 3.11 --extra dev --extra qiskit pytest -q
```

Or run the repository helper:

```bash
./scripts/dev-bootstrap.sh verify
```

## Docs

- Architecture: `ARCHITECTURE.md`
- Product strategy: `docs/product-strategy.md`
- Product roadmap: `docs/plans/2026-04-02-product-roadmap.md`
- Versioning: `docs/versioning.md`
- aionrs integration: `docs/aionrs-integration.md`
- QAOA MaxCut case study: `docs/fluxq-qaoa-maxcut-case-study.md`
- Changelog: `CHANGELOG.md`
- License: `LICENSE`
- Contributing: `CONTRIBUTING.md`
- Security: `SECURITY.md`
- Support: `SUPPORT.md`
