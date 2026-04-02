from __future__ import annotations

import json

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator


def build_circuit() -> QuantumCircuit:
    qc = QuantumCircuit(4, 4)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.cx(2, 3)
    qc.measure([0, 1, 2, 3], [0, 1, 2, 3])
    return qc


def simulate_counts(shots: int = 1024) -> dict[str, int]:
    backend = AerSimulator()
    compiled = transpile(build_circuit(), backend)
    result = backend.run(compiled, shots=shots).result()
    counts = result.get_counts()
    return dict(sorted(counts.items()))


if __name__ == "__main__":
    print(json.dumps(simulate_counts(), sort_keys=True))
