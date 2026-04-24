"""Emit OpenQASM 3 source from QSpec via Qiskit."""

from __future__ import annotations

from pathlib import Path

from qiskit.qasm3 import dumps

from quantum_runtime.lowering.qiskit_emitter import build_qiskit_circuit
from quantum_runtime.qspec import QSpec


def emit_qasm3_source(
    qspec: QSpec,
    *,
    parameter_bindings: dict[str, float] | None = None,
) -> str:
    """Render a deterministic OpenQASM 3 program for the given QSpec."""
    source = dumps(build_qiskit_circuit(qspec, parameter_bindings=parameter_bindings))
    if not source.endswith("\n"):
        source = f"{source}\n"
    return source


def write_qasm3_program(
    qspec: QSpec,
    output_path: Path,
    *,
    parameter_bindings: dict[str, float] | None = None,
) -> Path:
    """Write the emitted OpenQASM 3 program to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(emit_qasm3_source(qspec, parameter_bindings=parameter_bindings))
    return output_path
