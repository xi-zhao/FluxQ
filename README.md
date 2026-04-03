# FluxQ

![Release](https://img.shields.io/github/v/release/xi-zhao/FluxQ?sort=semver)
![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-3776AB.svg)

Reproducible quantum workflows for coding agents, CI, and revision-aware teams.

FluxQ is a workspace-native quantum workflow runtime. It turns intents, QSpec inputs, and report replays into reproducible artifacts, reports, and comparisons that coding agents and CI systems can trust.

Instead of treating quantum generation as one-off code emission, FluxQ gives you revisioned workspaces, replayable reports, semantic workload comparison, and guardrails for drift and replay integrity.

Package: `quantum-runtime`  
CLI: `qrun`  
Current release: `0.2.0`

## Why FluxQ

- reproducible quantum runs should survive beyond one generated script
- replayable reports let hosts and developers re-run work from revision-stable inputs instead of rebuilding context from scratch
- semantic workload comparison is more useful than raw file diff when you need to know whether a circuit family actually changed
- one workload can be exported into Qiskit, OpenQASM 3, and Classiq Python outputs without losing the surrounding workspace history
- local simulation, transpile validation, diagrams, and structural benchmarking make iteration fast before deeper backend work begins

## Use FluxQ If

- quantum developers who want circuits, exports, and diagnostics anchored to a stable workspace
- agent and CI builders who need file-based orchestration, JSON output, and explicit trust signals
- teams that want to compare revisions, catch replay regressions, and keep generated quantum workflows understandable over time

## Install

For CLI use from the public GitHub release:

```bash
uv tool install git+https://github.com/xi-zhao/FluxQ@v0.2.0
```

For local development and contributor workflows:

```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e '.[dev,qiskit]'
```

FluxQ currently targets Python `3.11`.

## First Run

```bash
qrun init --workspace .quantum --json
qrun exec --workspace .quantum --intent-file examples/intent-ghz.md --json
qrun inspect --workspace .quantum --json
qrun export --workspace .quantum --format qasm3 --json
qrun bench --workspace .quantum --json
```

After one GHZ run, FluxQ writes:

- `.quantum/specs/current.json`
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

## Trust And Replay

FluxQ is designed to be orchestrated by coding agents through files plus shell commands. The release focus is not just generation, but repeatability and inspectability.

- reports include stable provenance metadata for replay and inspection
- copied report files remain replayable as long as their recorded revision snapshots are still available
- report-backed imports now enforce replay integrity for QSpec identity instead of trusting path existence alone
- `qrun export --json` reports `source_kind`, `source_revision`, `source_report_path`, and `source_qspec_path`
- `qrun compare --json` reports `detached_report_inputs` so hosts can detect copied-report replay explicitly
- `qrun inspect --json` reports `replay_integrity` so hosts can detect legacy, degraded, or invalid replay trust directly
- `qrun compare --json` reports side-level `replay_integrity`, `replay_integrity_delta`, and `replay_integrity_regressions`
- reports, inspect, and compare all expose stable semantic hashes for workload identity
- `qrun compare` separates workload identity drift from generated artifact output drift and diagnostics drift
- `qrun compare --forbid-replay-integrity-regressions --json` lets CI fail when the right-hand replay input is less trustworthy than the baseline
- Detached copied reports still replay, but `qrun compare --json` degrades with exit code `2` so CI and hosts can treat replay trust as weaker than in-workspace history inputs

## Workspace Layout

`qrun init --workspace .quantum` creates:

```text
.quantum/
├─ workspace.json
├─ qrun.toml
├─ intents/history/
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
- `qrun exec --workspace .quantum --intent-file examples/intent-ghz.md --json`
- `qrun exec --workspace .quantum --qspec-file .quantum/specs/current.json --json`
- `qrun exec --workspace .quantum --report-file .quantum/reports/latest.json --json`
- `qrun exec --workspace .quantum --intent-text "Generate a 4-qubit GHZ circuit and measure all qubits." --json`
- `qrun inspect --workspace .quantum --json`
- `qrun export --workspace .quantum --report-file .quantum/reports/latest.json --format qasm3 --json`
- `qrun export --workspace .quantum --format qiskit --json`
- `qrun bench --workspace .quantum --report-file .quantum/reports/latest.json --json`
- `qrun bench --workspace .quantum --json`
- `qrun compare --workspace .quantum --left-revision rev_000001 --right-revision rev_000002 --expect same-subject --json`
- `qrun compare --workspace .quantum --left-report-file .quantum/reports/history/rev_000001.json --forbid-replay-integrity-regressions --json`
- `qrun doctor --workspace .quantum --json --fix`
- `qrun backend list --json`
- `qrun version`

## Agent And Host Integration

- aionrs integration examples: `docs/aionrs-integration.md`
- sample `CLAUDE.md`: `integrations/aionrs/CLAUDE.md.example`
- sample hooks: `integrations/aionrs/hooks.example.toml`

## Open Source

FluxQ is released under `Apache-2.0`.

- Repository: `https://github.com/xi-zhao/FluxQ`
- Release: `https://github.com/xi-zhao/FluxQ/releases/tag/v0.2.0`
- Release notes source: `docs/releases/v0.2.0.md`
- License: `LICENSE`
- Contributing guide: `CONTRIBUTING.md`
- Security policy: `SECURITY.md`
- Support guide: `SUPPORT.md`

## Development

```bash
uv run --python 3.11 --extra dev --extra qiskit pytest -q
```

## Docs

- Architecture: `ARCHITECTURE.md`
- Product strategy: `docs/product-strategy.md`
- Product roadmap: `docs/plans/2026-04-02-product-roadmap.md`
- Versioning: `docs/versioning.md`
- aionrs integration: `docs/aionrs-integration.md`
- Changelog: `CHANGELOG.md`
- License: `LICENSE`
- Contributing: `CONTRIBUTING.md`
- Security: `SECURITY.md`
- Support: `SUPPORT.md`
