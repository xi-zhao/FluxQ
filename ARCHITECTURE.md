# Architecture

## Overview

FluxQ is an agent-first quantum runtime CLI. It turns natural language ingress, structured intent files, QSpec inputs, and report replays into revisioned run objects with stable machine-readable outputs.

The runtime is designed for agent hosts and CI systems that prefer file I/O, JSON contracts, and shell commands over host-specific plugin protocols.

The core shape is:

`intent -> qspec -> execute/export -> report + manifest -> compare/continue`

## Flow

1. `Intent`
   The runtime reads markdown plus YAML front matter and normalizes it into `IntentModel`. Natural language is ingress, not the long-term source of truth.

2. `QSpec`
   The planner converts supported intents into a stable `QSpec` intermediate representation. `QSpec` is the source of truth for later lowering and diagnostics.

3. `Adapter / Lowering`
   Backends emit artifacts from `QSpec`:
   - Qiskit Python
   - OpenQASM 3
   - Classiq Python SDK

4. `Diagnostics`
   The runtime runs local simulation, transpile validation, resource estimation, circuit diagrams, and structural backend benchmarking.

5. `Reporting`
   The runtime writes `reports/latest.json`, immutable `manifests/history/<revision>.json`, revision history copies, compact summaries, and trace events for agent hosts.

6. `Control Plane`
   The CLI exposes read-mostly runtime control-plane commands such as `plan`, `status`, `show`, `compare`, `export`, `bench`, and `doctor`.

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
  End-to-end execution flow plus control-plane contracts for `qrun exec`, `qrun plan`, `qrun status`, `qrun show`, `qrun compare`, `qrun export`, and `qrun doctor`.
