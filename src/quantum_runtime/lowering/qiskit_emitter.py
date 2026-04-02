"""Emit runnable Qiskit Python programs from QSpec."""

from __future__ import annotations

import math
from pathlib import Path

from qiskit import QuantumCircuit

from quantum_runtime.qspec import MeasureNode, PatternNode, QSpec


def emit_qiskit_source(qspec: QSpec) -> str:
    """Render a standalone Python program for the given QSpec."""
    pattern_node = _first_pattern(qspec)
    measure_node = _first_measure(qspec)
    needs_math = pattern_node.pattern == "qft"

    imports = [
        "from __future__ import annotations",
        "",
        "import json",
    ]
    if needs_math:
        imports.extend(["import math"])
    imports.extend(
        [
            "",
            "from qiskit import QuantumCircuit, transpile",
            "from qiskit_aer import AerSimulator",
            "",
            "",
        ]
    )

    body_lines = ["def build_circuit() -> QuantumCircuit:"]
    size = qspec.registers[0].size
    body_lines.append(f"    qc = QuantumCircuit({size}, {size})")
    body_lines.extend(_render_pattern(pattern_node))
    body_lines.extend(_render_measurement(measure_node))
    body_lines.append("    return qc")
    body_lines.extend(
        [
            "",
            "",
            "def simulate_counts(shots: int = 1024) -> dict[str, int]:",
            "    backend = AerSimulator()",
            "    compiled = transpile(build_circuit(), backend)",
            "    result = backend.run(compiled, shots=shots).result()",
            "    counts = result.get_counts()",
            "    return dict(sorted(counts.items()))",
            "",
            "",
            'if __name__ == "__main__":',
            "    print(json.dumps(simulate_counts(), sort_keys=True))",
        ]
    )
    return "\n".join(imports + body_lines) + "\n"


def write_qiskit_program(qspec: QSpec, output_path: Path) -> Path:
    """Write the emitted Qiskit program to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(emit_qiskit_source(qspec))
    return output_path


def build_qiskit_circuit(qspec: QSpec) -> QuantumCircuit:
    """Build an in-memory Qiskit circuit from QSpec."""
    pattern_node = _first_pattern(qspec)
    measure_node = _first_measure(qspec)
    size = qspec.registers[0].size
    circuit = QuantumCircuit(size, size)

    if pattern_node.pattern == "ghz":
        circuit.h(0)
        for control in range(size - 1):
            circuit.cx(control, control + 1)
    elif pattern_node.pattern == "bell":
        circuit.h(0)
        circuit.cx(0, 1)
    elif pattern_node.pattern == "qft":
        for target in range(size):
            for control in range(target):
                circuit.cp(math.pi / (2 ** (target - control)), target, control)
            circuit.h(target)
        for index in range(size // 2):
            circuit.swap(index, size - index - 1)
    elif pattern_node.pattern == "hardware_efficient_ansatz":
        for qubit in range(size):
            circuit.ry(0.5, qubit)
            circuit.rz(0.25, qubit)
        for control in range(size - 1):
            circuit.cx(control, control + 1)
    elif pattern_node.pattern == "qaoa_ansatz":
        for qubit in range(size):
            circuit.h(qubit)
        for control in range(size - 1):
            target = control + 1
            circuit.cx(control, target)
            circuit.rz(0.8, target)
            circuit.cx(control, target)
        for qubit in range(size):
            circuit.rx(0.6, qubit)
    else:  # pragma: no cover - guarded by planner
        raise ValueError(f"Unsupported Qiskit pattern: {pattern_node.pattern}")

    qubits = [int(qubit.split("[", 1)[1].rstrip("]")) for qubit in measure_node.qubits]
    cbits = [int(cbit.split("[", 1)[1].rstrip("]")) for cbit in measure_node.cbits]
    circuit.measure(qubits, cbits)
    return circuit


def _first_pattern(qspec: QSpec) -> PatternNode:
    for node in qspec.body:
        if isinstance(node, PatternNode):
            return node
    raise ValueError("QSpec does not contain a pattern node.")


def _first_measure(qspec: QSpec) -> MeasureNode:
    for node in qspec.body:
        if isinstance(node, MeasureNode):
            return node
    raise ValueError("QSpec does not contain a measurement node.")


def _render_pattern(node: PatternNode) -> list[str]:
    size = int(node.args.get("size", 0))
    if node.pattern == "ghz":
        return _render_ghz(size)
    if node.pattern == "bell":
        return _render_bell()
    if node.pattern == "qft":
        return _render_qft(size)
    if node.pattern == "hardware_efficient_ansatz":
        return _render_hardware_efficient_ansatz(size)
    if node.pattern == "qaoa_ansatz":
        return _render_qaoa_ansatz(size)
    raise ValueError(f"Unsupported Qiskit pattern: {node.pattern}")


def _render_measurement(node: MeasureNode) -> list[str]:
    qubits = ", ".join(qubit.split("[", 1)[1].rstrip("]") for qubit in node.qubits)
    cbits = ", ".join(cbit.split("[", 1)[1].rstrip("]") for cbit in node.cbits)
    return [f"    qc.measure([{qubits}], [{cbits}])"]


def _render_ghz(size: int) -> list[str]:
    lines = ["    qc.h(0)"]
    for control in range(size - 1):
        lines.append(f"    qc.cx({control}, {control + 1})")
    return lines


def _render_bell() -> list[str]:
    return [
        "    qc.h(0)",
        "    qc.cx(0, 1)",
    ]


def _render_qft(size: int) -> list[str]:
    lines: list[str] = []
    for target in range(size):
        for control in range(target):
            angle = f"math.pi / {2 ** (target - control)}"
            lines.append(f"    qc.cp({angle}, {target}, {control})")
        lines.append(f"    qc.h({target})")
    for index in range(size // 2):
        lines.append(f"    qc.swap({index}, {size - index - 1})")
    return lines


def _render_hardware_efficient_ansatz(size: int) -> list[str]:
    lines: list[str] = []
    for qubit in range(size):
        lines.append(f"    qc.ry(0.5, {qubit})")
        lines.append(f"    qc.rz(0.25, {qubit})")
    for control in range(size - 1):
        lines.append(f"    qc.cx({control}, {control + 1})")
    return lines


def _render_qaoa_ansatz(size: int) -> list[str]:
    lines: list[str] = []
    for qubit in range(size):
        lines.append(f"    qc.h({qubit})")
    for control in range(size - 1):
        target = control + 1
        lines.append(f"    qc.cx({control}, {target})")
        lines.append(f"    qc.rz(0.8, {target})")
        lines.append(f"    qc.cx({control}, {target})")
    for qubit in range(size):
        lines.append(f"    qc.rx(0.6, {qubit})")
    return lines
