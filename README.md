# Quantum Runtime CLI

Quantum Runtime CLI is an agent-facing, deterministic runtime for quantum code generation workflows. It is designed to be called by any coding agent through file I/O plus shell commands rather than custom host-specific tools.

## Features

- deterministic workspace initialization with revision tracking
- markdown intent parsing with YAML front matter
- QSpec v0.1 planning for `ghz`, `bell`, `qft`, `hardware_efficient_ansatz`, and `qaoa_ansatz`
- Qiskit, OpenQASM 3, and Classiq Python emission
- local simulation, transpile validation, diagrams, and structural benchmarking
- agent-host friendly JSON output through `qrun init`, `qrun exec`, `qrun inspect`, `qrun export`, `qrun bench`, and `qrun doctor`

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
- Versioning: `docs/versioning.md`
- aionrs integration: `docs/aionrs-integration.md`
- Changelog: `CHANGELOG.md`
