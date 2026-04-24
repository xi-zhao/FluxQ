---
title: QAOA MaxCut Sweep
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
  parameter_sweep:
    gamma_0: [0.2, 0.4]
    beta_0: [0.1, 0.3]
    gamma_1: [0.45]
    beta_1: [0.35]
shots: 512
---

Build a 4-qubit MaxCut QAOA ansatz with 2 layers on a ring graph.
