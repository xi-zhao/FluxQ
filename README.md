# Quantum Runtime CLI

Quantum Runtime CLI is an agent-facing, deterministic runtime for quantum code generation workflows. It is designed to be called by any coding agent through file I/O plus shell commands rather than custom host-specific tools.

## Features

- deterministic workspace initialization with revision tracking
- revision-stable artifact snapshots for replayable reports and exports
- markdown intent parsing with YAML front matter
- QSpec v0.1 planning for `ghz`, `bell`, `qft`, `hardware_efficient_ansatz`, and `qaoa_ansatz`
- Qiskit, OpenQASM 3, and Classiq Python emission
- local simulation, transpile validation, diagrams, and structural benchmarking
- agent-host friendly JSON output through `qrun init`, `qrun exec`, `qrun inspect`, `qrun export`, `qrun bench`, `qrun compare`, and `qrun doctor`

## Quick Start

```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e '.[dev,qiskit]'
qrun init --workspace .quantum --json
qrun exec --workspace .quantum --intent-file examples/intent-ghz.md --json
qrun exec --workspace .quantum --qspec-file .quantum/specs/current.json --json
qrun exec --workspace .quantum --report-file .quantum/reports/latest.json --json
qrun exec --workspace .quantum --intent-text "Generate a 4-qubit GHZ circuit and measure all qubits." --json
qrun export --workspace .quantum --report-file .quantum/reports/latest.json --format qasm3 --json
qrun bench --workspace .quantum --report-file .quantum/reports/latest.json --json
qrun inspect --workspace .quantum --json
qrun compare --workspace .quantum --left-revision rev_000001 --right-revision rev_000002 --expect same-subject --json
qrun export --workspace .quantum --format qasm3 --json
qrun bench --workspace .quantum --json
qrun doctor --workspace .quantum --json --fix
```

The GHZ example writes:

- `.quantum/specs/current.json`
- `.quantum/artifacts/qiskit/main.py`
- `.quantum/artifacts/qasm/main.qasm`
- `.quantum/figures/circuit.png`
- `.quantum/reports/latest.json`

## Host Integration

Quantum Runtime CLI is intended to be orchestrated by coding agents through files plus shell commands.

- aionrs integration examples: `docs/aionrs-integration.md`
- sample `CLAUDE.md`: `integrations/aionrs/CLAUDE.md.example`
- sample hooks: `integrations/aionrs/hooks.example.toml`
- reports include stable provenance metadata for replay and inspection
- copied report files remain replayable as long as their recorded revision snapshots are still available
- `qrun export --json` reports `source_kind`, `source_revision`, `source_report_path`, and `source_qspec_path`
- `qrun compare --json` reports `detached_report_inputs` so hosts can detect copied-report replay explicitly
- reports, inspect, and compare all expose stable semantic hashes for workload identity
- `qrun compare` separates workload identity drift from generated artifact output drift and diagnostics drift
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

## Commands

- `qrun init --workspace .quantum --json`
- `qrun exec --workspace .quantum --intent-file examples/intent-ghz.md --json`
- `qrun exec --workspace .quantum --qspec-file .quantum/specs/current.json --json`
- `qrun exec --workspace .quantum --report-file .quantum/reports/latest.json --json`
- `qrun exec --workspace .quantum --intent-text "Generate a 4-qubit GHZ circuit and measure all qubits." --json`
- `qrun export --workspace .quantum --report-file .quantum/reports/latest.json --format qasm3 --json`
- `qrun bench --workspace .quantum --report-file .quantum/reports/latest.json --json`
- `qrun inspect --workspace .quantum --json`
- `qrun compare --workspace .quantum --left-revision rev_000001 --right-revision rev_000002 --expect same-subject --json`
- `qrun export --workspace .quantum --format qiskit --json`
- `qrun bench --workspace .quantum --json`
- `qrun doctor --workspace .quantum --json --fix`
- `qrun backend list --json`
- `qrun version`

## Development

```bash
uv run --python 3.11 --extra dev --extra qiskit pytest -q
```

## Docs

- Architecture: `ARCHITECTURE.md`
- Product roadmap: `docs/plans/2026-04-02-product-roadmap.md`
- Versioning: `docs/versioning.md`
- aionrs integration: `docs/aionrs-integration.md`
- Changelog: `CHANGELOG.md`
