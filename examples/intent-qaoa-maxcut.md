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
  qaoa_layers: 2
  maxcut_edges:
    - [0, 1]
    - [1, 2]
    - [2, 3]
    - [3, 0]
shots: 512
---

Build a 4-qubit MaxCut QAOA ansatz with 2 layers on a ring graph.
