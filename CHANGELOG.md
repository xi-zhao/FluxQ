# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

- expand `qrun exec` coverage beyond intent-only input
- deepen `hardware_efficient_ansatz` and `qaoa_ansatz` with explicit layer, topology, and parameter semantics
- deepen backend benchmarking and Classiq synthesis reporting
- stabilize semantic provenance across `report`, `inspect`, and `bench` outputs
- improve packaging and release automation

## 0.1.0

- initialize deterministic `.quantum` workspaces
- parse markdown intents and lower them into QSpec
- emit Qiskit Python, OpenQASM 3, and Classiq Python SDK source
- run local simulation, transpile validation, diagrams, reports, and structural benchmarking
- provide aionrs integration examples and runnable CLI JSON workflows
