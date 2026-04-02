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
        source = _render_source(
            imports=["CX", "H", "Output", "QArray", "QBit", "allocate", "create_model", "qfunc"],
            helper_name="bell_pair",
            helper_lines=[
                "    H(q[0])",
                "    CX(q[0], q[1])",
            ],
            main_lines=[
                "    allocate(2, q)",
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
        source = _render_source(
            imports=["CX", "RY", "RZ", "Output", "QArray", "QBit", "allocate", "create_model", "qfunc"],
            helper_name="hardware_efficient_layer",
            helper_lines=[
                *[f"    RY(0.5, q[{index}])" for index in range(size)],
                *[f"    RZ(0.25, q[{index}])" for index in range(size)],
                *[f"    CX(q[{index}], q[{index + 1}])" for index in range(size - 1)],
            ],
            main_lines=[
                f"    allocate({size}, q)",
                "    hardware_efficient_layer(q)",
            ],
        )
        return ClassiqEmitResult(status="ok", source=source)

    if pattern_node.pattern == "qaoa_ansatz":
        source = _render_source(
            imports=["CX", "H", "RX", "RZ", "Output", "QArray", "QBit", "allocate", "create_model", "qfunc"],
            helper_name="qaoa_layer",
            helper_lines=[
                *[f"    H(q[{index}])" for index in range(size)],
                *[
                    line
                    for index in range(size - 1)
                    for line in (
                        f"    CX(q[{index}], q[{index + 1}])",
                        f"    RZ(0.8, q[{index + 1}])",
                        f"    CX(q[{index}], q[{index + 1}])",
                    )
                ],
                *[f"    RX(0.6, q[{index}])" for index in range(size)],
            ],
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
