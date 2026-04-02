# Quantum Runtime CLI

Quantum Runtime CLI is an agent-facing, deterministic runtime for quantum code generation workflows. It is designed to be called by any coding agent through file I/O plus shell commands rather than custom host-specific tools.

## Current Status

Step 1 is implemented:
- package scaffold
- `qrun init`
- deterministic workspace initialization
- basic CLI tests

Step 2 foundation is now implemented:
- markdown intent parsing with YAML front matter
- workspace manifest loading and revision reservation
- NDJSON trace event writer

Step 3 foundation is now implemented:
- v0.1 QSpec Pydantic models
- rule-based planner for `ghz`, `bell`, `qft`, `hardware_efficient_ansatz`, and `qaoa_ansatz`
- stable GHZ golden snapshot coverage

Step 4 foundation is now implemented:
- Qiskit Python emitter
- runnable GHZ program generation
- local import-and-simulate coverage for emitted code

## Quick Start

```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e '.[dev]'
qrun init --workspace .quantum --json
qrun version
```

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

## Next Steps

The next implementation step adds:
- intent parsing
- workspace revision management
- manifest and trace events
