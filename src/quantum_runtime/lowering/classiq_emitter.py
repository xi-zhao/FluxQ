"""Emit Classiq Python SDK source from QSpec."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from quantum_runtime.qspec import PatternNode, QSpec


class ClassiqEmitResult(BaseModel):
    """Structured result for Classiq source emission."""

    status: Literal["ok", "unsupported"]
    source: str | None = None
    path: Path | None = None
    reason: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


def emit_classiq_source(qspec: QSpec) -> ClassiqEmitResult:
    """Render a deterministic Classiq Python SDK program for the given QSpec."""
    pattern_node = _first_pattern(qspec)
    size = int(pattern_node.args.get("size", qspec.registers[0].size))
    parameter_defaults = _parameter_defaults(qspec)

    if pattern_node.pattern == "ghz":
        source = _render_source(
            imports=["CX", "H", "Output", "QArray", "QBit", "allocate", "create_model", "qfunc"],
            helper_name="ghz_chain",
            helper_lines=[
                "    H(q[0])",
                *[f"    CX(q[{index}], q[{index + 1}])" for index in range(size - 1)],
            ],
            main_lines=[
                f"    allocate({size}, q)",
                "    ghz_chain(q)",
            ],
        )
        return ClassiqEmitResult(status="ok", source=source)

    if pattern_node.pattern == "bell":
        if size != 2:
            raise ValueError("Bell pattern requires exactly 2 qubits.")
        source = _render_source(
            imports=["CX", "H", "Output", "QArray", "QBit", "allocate", "create_model", "qfunc"],
            helper_name="bell_pair",
            helper_lines=[
                "    H(q[0])",
                "    CX(q[0], q[1])",
            ],
            main_lines=[
                f"    allocate({size}, q)",
                "    bell_pair(q)",
            ],
        )
        return ClassiqEmitResult(status="ok", source=source)

    if pattern_node.pattern == "qft":
        source = _render_source(
            imports=["Output", "QArray", "QBit", "allocate", "create_model", "qft", "qfunc"],
            helper_name=None,
            helper_lines=[],
            main_lines=[
                f"    allocate({size}, q)",
                "    qft(q)",
            ],
        )
        return ClassiqEmitResult(status="ok", source=source)

    if pattern_node.pattern == "hardware_efficient_ansatz":
        rotation_blocks = _rotation_blocks(pattern_node)
        gate_imports = sorted({_classiq_gate_name(block) for block in rotation_blocks} | {"CX"})
        entanglement_edges = _edge_pairs(pattern_node.args.get("entanglement_edges", []), size=size)
        layers = int(pattern_node.args.get("layers", 1))
        helper_lines: list[str] = []
        for layer in range(layers):
            for index in range(size):
                for block in rotation_blocks:
                    angle = _lookup_hea_angle(parameter_defaults, gate=block, layer=layer, qubit=index)
                    helper_lines.append(f"    {_classiq_gate_name(block)}({_format_float(angle)}, q[{index}])")
            for left, right in entanglement_edges:
                helper_lines.append(f"    CX(q[{left}], q[{right}])")
        source = _render_source(
            imports=[*gate_imports, "Output", "QArray", "QBit", "allocate", "create_model", "qfunc"],
            helper_name="hardware_efficient_layer",
            helper_lines=helper_lines,
            main_lines=[
                f"    allocate({size}, q)",
                "    hardware_efficient_layer(q)",
            ],
        )
        return ClassiqEmitResult(status="ok", source=source)

    if pattern_node.pattern == "qaoa_ansatz":
        layers = int(pattern_node.args.get("layers", 1))
        cost_edges = _edge_pairs(pattern_node.args.get("cost_edges", []), size=size)
        helper_lines = [f"    H(q[{index}])" for index in range(size)]
        for layer in range(layers):
            gamma = _lookup_parameter(parameter_defaults, f"gamma_{layer}", fallback=round(0.4 + (0.05 * layer), 3))
            beta = _lookup_parameter(parameter_defaults, f"beta_{layer}", fallback=round(0.3 + (0.04 * layer), 3))
            for left, right in cost_edges:
                helper_lines.extend(
                    [
                        f"    CX(q[{left}], q[{right}])",
                        f"    RZ({_format_float(2 * gamma)}, q[{right}])",
                        f"    CX(q[{left}], q[{right}])",
                    ]
                )
            helper_lines.extend(
                f"    RX({_format_float(2 * beta)}, q[{index}])"
                for index in range(size)
            )
        source = _render_source(
            imports=["CX", "H", "RX", "RZ", "Output", "QArray", "QBit", "allocate", "create_model", "qfunc"],
            helper_name="qaoa_layer",
            helper_lines=helper_lines,
            main_lines=[
                f"    allocate({size}, q)",
                "    qaoa_layer(q)",
            ],
        )
        return ClassiqEmitResult(status="ok", source=source)

    return ClassiqEmitResult(
        status="unsupported",
        reason="pattern_not_supported_by_classiq_emitter",
        details={"pattern": str(pattern_node.pattern)},
    )


def write_classiq_program(qspec: QSpec, output_path: Path) -> ClassiqEmitResult:
    """Write the emitted Classiq Python SDK program to disk if supported."""
    result = emit_classiq_source(qspec)
    if result.status != "ok" or result.source is None:
        return result

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.source)
    return result.model_copy(update={"path": output_path})


def _first_pattern(qspec: QSpec) -> PatternNode:
    for node in qspec.body:
        if isinstance(node, PatternNode):
            return node
    raise ValueError("QSpec does not contain a pattern node.")


def _render_source(
    *,
    imports: list[str],
    helper_name: str | None,
    helper_lines: list[str],
    main_lines: list[str],
) -> str:
    lines = [
        "from __future__ import annotations",
        "",
        f"from classiq import {', '.join(imports)}",
        "",
        "",
    ]

    if helper_name is not None:
        lines.extend(
            [
                "@qfunc",
                f"def {helper_name}(q: QArray[QBit]) -> None:",
                *helper_lines,
                "",
                "",
            ]
        )

    lines.extend(
        [
            "@qfunc",
            "def main(q: Output[QArray[QBit]]) -> None:",
            *main_lines,
            "",
            "",
            'if __name__ == "__main__":',
            "    qmod = create_model(main)",
            "    print(qmod)",
        ]
    )
    return "\n".join(lines) + "\n"


def _parameter_defaults(qspec: QSpec) -> dict[str, float]:
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
        fallback=_fallback_hea_angle(gate=gate, layer=layer, qubit=qubit),
    )


def _lookup_parameter(defaults: dict[str, float], name: str, *, fallback: float) -> float:
    return defaults.get(name, fallback)


def _fallback_hea_angle(*, gate: str, layer: int, qubit: int) -> float:
    base_by_gate = {
        "rx": 0.38,
        "ry": 0.5,
        "rz": 0.25,
    }
    base = base_by_gate.get(gate, 0.2)
    return round(base + (0.05 * layer) + (0.02 * qubit), 3)


def _classiq_gate_name(gate: str) -> str:
    return gate.upper()


def _format_float(value: float) -> str:
    rendered = f"{value:.6f}".rstrip("0").rstrip(".")
    return rendered or "0"
