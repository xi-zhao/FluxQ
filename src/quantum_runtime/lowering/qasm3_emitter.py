"""Emit OpenQASM 3 source from QSpec via Qiskit."""

from __future__ import annotations

from pathlib import Path

from qiskit.qasm3 import dumps

from quantum_runtime.lowering.qiskit_emitter import build_qiskit_circuit
from quantum_runtime.qspec import QSpec


def emit_qasm3_source(qspec: QSpec) -> str:
    """Render a deterministic OpenQASM 3 program for the given QSpec."""
    source = dumps(build_qiskit_circuit(qspec))
    if not source.endswith("\n"):
        source = f"{source}\n"
    return source


def write_qasm3_program(qspec: QSpec, output_path: Path) -> Path:
    """Write the emitted OpenQASM 3 program to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(emit_qasm3_source(qspec))
    return output_path
