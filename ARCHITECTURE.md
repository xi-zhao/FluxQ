# Architecture

## Overview

FluxQ is an agent-first quantum runtime CLI. It turns natural language ingress, structured intent files, JSON intent payloads, QSpec inputs, and report replays into revisioned run objects with stable machine-readable outputs.

The runtime is designed for agent hosts and CI systems that prefer file I/O, JSON contracts, and shell commands over host-specific plugin protocols. `prompt` is ingress, `resolve` is normalization, and canonical `QSpec` is the truth layer for execution, comparison, and export.

The core shape is:

`prompt / resolve -> qspec -> execute/export -> report + manifest + events.jsonl -> pack -> compare/continue`

## Flow

1. `Intent`
   The runtime reads markdown plus YAML front matter, JSON intent payloads, or natural language prompts and normalizes them into `IntentResolution` and `ResolveResult`. Natural language is ingress, not the long-term source of truth.

2. `QSpec`
   The resolver converts supported inputs into a stable `QSpec` intermediate representation. `QSpec` is the source of truth for later lowering, comparison, and diagnostics, while runtime metadata records workload identity, export requirements, policy hints, and provenance.

3. `Adapter / Lowering`
   Backends emit artifacts from `QSpec`:
   - Qiskit Python
   - OpenQASM 3
   - Classiq Python SDK

4. `Diagnostics`
   The runtime runs local simulation, transpile validation, resource estimation, circuit diagrams, and structural backend benchmarking.

5. `Reporting`
   The runtime writes revisioned `intent.json`, `plan.json`, `qspec.json`, `report.json`, immutable `manifests/history/<revision>.json`, revision history copies, compact summaries, and canonical `events.jsonl` workspace events for agent hosts. The trace log in `trace/events.ndjson` remains the append-only event source behind that workspace artifact.

6. `Packaging`
   `qrun pack` assembles one approved revision into a portable bundle with the revisioned runtime objects, export outputs, and provenance preserved together.

7. `Control Plane`
   The CLI exposes read-mostly runtime control-plane commands such as `prompt`, `resolve`, `plan`, `status`, `show`, `compare`, `export`, `bench`, `doctor`, and `pack`.

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
  End-to-end execution flow plus control-plane contracts for `qrun prompt`, `qrun resolve`, `qrun exec`, `qrun plan`, `qrun status`, `qrun show`, `qrun compare`, `qrun export`, `qrun bench`, `qrun doctor`, and `qrun pack`.

- `src/quantum_runtime/workspace`
  Workspace layout, revision history, canonical `events.jsonl`, and pack directory helpers.
