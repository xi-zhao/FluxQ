"""Local Qiskit simulation diagnostics."""

from __future__ import annotations

import time

from pydantic import BaseModel, Field
from qiskit import transpile
from qiskit_aer import AerSimulator

from quantum_runtime.lowering.qiskit_emitter import build_qiskit_circuit
from quantum_runtime.qspec import QSpec


class SimulationReport(BaseModel):
    """Structured local simulation result."""

    status: str
    shots: int
    counts: dict[str, int] = Field(default_factory=dict)
    error: str | None = None
    elapsed_ms: int


def run_local_simulation(qspec: QSpec, shots: int = 1024) -> SimulationReport:
    """Simulate a QSpec on the local Aer simulator."""
    start = time.perf_counter()
    try:
        circuit = build_qiskit_circuit(qspec)
        backend = AerSimulator()
        compiled = transpile(circuit, backend)
        result = backend.run(compiled, shots=shots).result()
        counts = dict(sorted(result.get_counts().items()))
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return SimulationReport(
            status="ok",
            shots=shots,
            counts=counts,
            elapsed_ms=elapsed_ms,
        )
    except Exception as exc:  # pragma: no cover - defensive path
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return SimulationReport(
            status="error",
            shots=shots,
            counts={},
            error=str(exc),
            elapsed_ms=elapsed_ms,
        )
