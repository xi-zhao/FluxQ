# Architecture

## Overview

Quantum Runtime CLI is a deterministic Python CLI that turns an intent file into stable quantum artifacts and diagnostics. The runtime is designed for agent hosts that prefer file I/O and shell commands over host-specific plugin protocols.

## Flow

1. `Intent`
   The runtime reads markdown plus YAML front matter and normalizes it into `IntentModel`.

2. `QSpec`
   The planner converts supported intents into a stable `QSpec` intermediate representation. `QSpec` is the source of truth for later lowering and diagnostics.

3. `Lowering`
   Backends emit artifacts from `QSpec`:
   - Qiskit Python
   - OpenQASM 3
   - Classiq Python SDK

4. `Diagnostics`
   The runtime runs local simulation, transpile validation, resource estimation, circuit diagrams, and structural backend benchmarking.

5. `Reporting`
   The runtime writes `reports/latest.json`, revision history copies, compact summaries, and trace events for agent hosts.

## Main Components

- `src/quantum_runtime/intent`
  Intent parsing and rule-based planning.

- `src/quantum_runtime/qspec`
  Pydantic models for the stable IR.

- `src/quantum_runtime/lowering`
  Lowering and emitter logic for each output target.

- `src/quantum_runtime/diagnostics`
  Simulation, validation, resource, diagram, and benchmark helpers.

- `src/quantum_runtime/backends`
  Optional backend-specific execution paths such as Classiq synthesis.

- `src/quantum_runtime/reporters`
  Stable report writing and compact agent summaries.

- `src/quantum_runtime/runtime`
  End-to-end execution flow for `qrun exec`.
