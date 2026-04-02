---
title: QAOA MaxCut
exports:
  - qiskit
  - qasm3
backend_preferences:
  - qiskit-local
constraints:
  max_width: 4
  max_depth: 128
  basis_gates:
    - h
    - cx
    - rz
    - rx
  optimization_level: 2
shots: 512
---

Build a 4-qubit MaxCut QAOA ansatz.
