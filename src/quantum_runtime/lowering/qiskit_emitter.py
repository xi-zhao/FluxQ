"""Emit runnable Qiskit Python programs from QSpec."""

from __future__ import annotations

import math
from pathlib import Path

from qiskit import QuantumCircuit

from quantum_runtime.qspec import MeasureNode, PatternNode, QSpec


def emit_qiskit_source(
    qspec: QSpec,
    *,
    parameter_bindings: dict[str, float] | None = None,
) -> str:
    """Render a standalone Python program for the given QSpec."""
    pattern_node = _first_pattern(qspec)
    measure_node = _first_measure(qspec)
    needs_math = pattern_node.pattern == "qft"
    parameter_defaults = _parameter_defaults(qspec, parameter_bindings=parameter_bindings)

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
    body_lines.extend(_render_pattern(pattern_node, parameter_defaults))
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


def write_qiskit_program(
    qspec: QSpec,
    output_path: Path,
    *,
    parameter_bindings: dict[str, float] | None = None,
) -> Path:
    """Write the emitted Qiskit program to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(emit_qiskit_source(qspec, parameter_bindings=parameter_bindings))
    return output_path


def build_qiskit_circuit(
    qspec: QSpec,
    *,
    parameter_bindings: dict[str, float] | None = None,
) -> QuantumCircuit:
    """Build an in-memory Qiskit circuit from QSpec."""
    pattern_node = _first_pattern(qspec)
    measure_node = _first_measure(qspec)
    size = qspec.registers[0].size
    circuit = QuantumCircuit(size, size)
    parameter_defaults = _parameter_defaults(qspec, parameter_bindings=parameter_bindings)

    if pattern_node.pattern == "ghz":
        circuit.h(0)
        for control in range(size - 1):
            circuit.cx(control, control + 1)
    elif pattern_node.pattern == "bell":
        if size != 2:
            raise ValueError("Bell pattern requires exactly 2 qubits.")
        circuit.h(0)
        circuit.cx(0, 1)
    elif pattern_node.pattern == "qft":
        for target in range(size - 1, -1, -1):
            circuit.h(target)
            for control in range(target - 1, -1, -1):
                circuit.cp(math.pi / (2 ** (target - control)), target, control)
        for index in range(size // 2):
            circuit.swap(index, size - index - 1)
    elif pattern_node.pattern == "hardware_efficient_ansatz":
        layers = int(pattern_node.args.get("layers", 1))
        rotation_blocks = _rotation_blocks(pattern_node)
        entanglement_edges = _edge_pairs(pattern_node.args.get("entanglement_edges", []), size=size)
        for layer in range(layers):
            for qubit in range(size):
                for block in rotation_blocks:
                    angle = _lookup_hea_angle(parameter_defaults, gate=block, layer=layer, qubit=qubit)
                    _apply_rotation(circuit, gate=block, angle=angle, qubit=qubit)
            _apply_entanglement(circuit, entanglement_edges)
    elif pattern_node.pattern == "qaoa_ansatz":
        layers = int(pattern_node.args.get("layers", 1))
        cost_edges = _edge_pairs(pattern_node.args.get("cost_edges", []), size=size)
        for qubit in range(size):
            circuit.h(qubit)
        for layer in range(layers):
            gamma = _lookup_parameter(parameter_defaults, f"gamma_{layer}")
            beta = _lookup_parameter(parameter_defaults, f"beta_{layer}")
            for left, right in cost_edges:
                circuit.cx(left, right)
                circuit.rz(2 * gamma, right)
                circuit.cx(left, right)
            for qubit in range(size):
                circuit.rx(2 * beta, qubit)
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


def _render_pattern(node: PatternNode, parameter_defaults: dict[str, float]) -> list[str]:
    size = int(node.args.get("size", 0))
    if node.pattern == "ghz":
        return _render_ghz(size)
    if node.pattern == "bell":
        return _render_bell()
    if node.pattern == "qft":
        return _render_qft(size)
    if node.pattern == "hardware_efficient_ansatz":
        return _render_hardware_efficient_ansatz(node, parameter_defaults)
    if node.pattern == "qaoa_ansatz":
        return _render_qaoa_ansatz(node, parameter_defaults)
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
    for target in range(size - 1, -1, -1):
        lines.append(f"    qc.h({target})")
        for control in range(target - 1, -1, -1):
            angle = f"math.pi / {2 ** (target - control)}"
            lines.append(f"    qc.cp({angle}, {target}, {control})")
    for index in range(size // 2):
        lines.append(f"    qc.swap({index}, {size - index - 1})")
    return lines


def _render_hardware_efficient_ansatz(
    node: PatternNode,
    parameter_defaults: dict[str, float],
) -> list[str]:
    size = int(node.args.get("size", 0))
    layers = int(node.args.get("layers", 1))
    rotation_blocks = _rotation_blocks(node)
    entanglement_edges = _edge_pairs(node.args.get("entanglement_edges", []), size=size)
    lines: list[str] = []
    for layer in range(layers):
        for qubit in range(size):
            for block in rotation_blocks:
                angle = _lookup_hea_angle(parameter_defaults, gate=block, layer=layer, qubit=qubit)
                lines.append(f"    qc.{block}({_format_float(angle)}, {qubit})")
        for left, right in entanglement_edges:
            lines.append(f"    qc.cx({left}, {right})")
    return lines


def _render_qaoa_ansatz(
    node: PatternNode,
    parameter_defaults: dict[str, float],
) -> list[str]:
    size = int(node.args.get("size", 0))
    layers = int(node.args.get("layers", 1))
    cost_edges = _edge_pairs(node.args.get("cost_edges", []), size=size)
    lines: list[str] = []
    for qubit in range(size):
        lines.append(f"    qc.h({qubit})")
    for layer in range(layers):
        gamma = _lookup_parameter(parameter_defaults, f"gamma_{layer}")
        beta = _lookup_parameter(parameter_defaults, f"beta_{layer}")
        for left, right in cost_edges:
            lines.append(f"    qc.cx({left}, {right})")
            lines.append(f"    qc.rz({_format_float(2 * gamma)}, {right})")
            lines.append(f"    qc.cx({left}, {right})")
        for qubit in range(size):
            lines.append(f"    qc.rx({_format_float(2 * beta)}, {qubit})")
    return lines


def _parameter_defaults(
    qspec: QSpec,
    parameter_bindings: dict[str, float] | None = None,
) -> dict[str, float]:
    defaults: dict[str, float] = {}
    for parameter in qspec.parameters:
        name = str(parameter.get("name", "")).strip()
        if not name:
            continue
        default = parameter.get("default")
        if isinstance(default, (int, float, str)):
            try:
                defaults[name] = float(default)
            except ValueError:
                continue
    if parameter_bindings:
        defaults.update({name: float(value) for name, value in parameter_bindings.items()})
    return defaults


def _rotation_blocks(node: PatternNode) -> list[str]:
    blocks = node.args.get("rotation_blocks", ["ry", "rz"])
    if not isinstance(blocks, list) or not blocks:
        return ["ry", "rz"]
    return [str(block).strip().lower() for block in blocks if str(block).strip()]


def _edge_pairs(value: object, *, size: int) -> list[tuple[int, int]]:
    if not isinstance(value, list):
        return [(index, index + 1) for index in range(size - 1)]
    edges: list[tuple[int, int]] = []
    for edge in value:
        if not isinstance(edge, (list, tuple)) or len(edge) != 2:
            continue
        edges.append((int(edge[0]), int(edge[1])))
    return edges


def _lookup_hea_angle(
    defaults: dict[str, float],
    *,
    gate: str,
    layer: int,
    qubit: int,
) -> float:
    return _lookup_parameter(
        defaults,
        f"theta_{gate}_l{layer}_q{qubit}",
    )


def _lookup_parameter(defaults: dict[str, float], name: str) -> float:
    if name not in defaults:
        raise ValueError(f"Missing parameter binding for {name}")
    return defaults[name]


def _apply_rotation(circuit: QuantumCircuit, *, gate: str, angle: float, qubit: int) -> None:
    if gate == "rx":
        circuit.rx(angle, qubit)
    elif gate == "ry":
        circuit.ry(angle, qubit)
    elif gate == "rz":
        circuit.rz(angle, qubit)
    else:  # pragma: no cover - guarded by planner / validation
        raise ValueError(f"Unsupported rotation block: {gate}")


def _apply_entanglement(circuit: QuantumCircuit, edges: list[tuple[int, int]]) -> None:
    for left, right in edges:
        circuit.cx(left, right)


def _format_float(value: float) -> str:
    rendered = f"{value:.6f}".rstrip("0").rstrip(".")
    return rendered or "0"
