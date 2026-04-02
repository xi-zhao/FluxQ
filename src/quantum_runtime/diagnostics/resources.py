"""Static circuit resource estimation."""

from __future__ import annotations

from pydantic import BaseModel, Field

from quantum_runtime.lowering.qiskit_emitter import build_qiskit_circuit
from quantum_runtime.qspec import QSpec


class ResourceReport(BaseModel):
    """Normalized resource metrics for a generated circuit."""

    width: int
    depth: int
    size: int
    gate_histogram: dict[str, int] = Field(default_factory=dict)
    two_qubit_gates: int
    measure_count: int
    parameter_count: int


def estimate_resources(qspec: QSpec) -> ResourceReport:
    """Estimate basic structural metrics from the generated Qiskit circuit."""
    circuit = build_qiskit_circuit(qspec)
    gate_histogram = {
        str(name): int(count)
        for name, count in sorted(circuit.count_ops().items())
    }
    two_qubit_gates = sum(
        1
        for item in circuit.data
        if len(item.qubits) == 2 and item.operation.name != "barrier"
    )
    measure_count = sum(
        1
        for item in circuit.data
        if item.operation.name == "measure"
    )
    return ResourceReport(
        width=circuit.num_qubits,
        depth=int(circuit.depth() or 0),
        size=len(circuit.data),
        gate_histogram=gate_histogram,
        two_qubit_gates=two_qubit_gates,
        measure_count=measure_count,
        parameter_count=len(circuit.parameters),
    )
