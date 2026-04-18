"""IBM Runtime remote-submit adapter."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from qiskit import transpile

from quantum_runtime.lowering.qiskit_emitter import build_qiskit_circuit
from quantum_runtime.qspec import QSpec
from quantum_runtime.runtime.ibm_access import IbmAccessError

try:
    from qiskit_ibm_runtime import SamplerV2
except Exception:
    SamplerV2 = None


class IbmSubmitJobResult(BaseModel):
    """Sanitized IBM submit receipt."""

    job_id: str
    job_status: str | None = None
    primitive: str = "sampler_v2"


def submit_ibm_job(
    *,
    service: Any,
    backend_name: str,
    qspec: QSpec,
    shots: int,
) -> IbmSubmitJobResult:
    """Submit one canonical QSpec to IBM Runtime in job mode."""
    selected_backend_name = backend_name.strip()
    if not selected_backend_name:
        raise ValueError("remote_backend_required")
    if SamplerV2 is None:
        raise IbmAccessError("ibm_runtime_dependency_missing")

    try:
        backend = service.backend(selected_backend_name)
    except Exception as exc:
        raise IbmAccessError(
            "ibm_backend_lookup_failed",
            details={"backend_name": selected_backend_name},
        ) from exc

    circuit = build_qiskit_circuit(qspec)
    transpiled = transpile(circuit, backend=backend)
    sampler = SamplerV2(mode=backend)
    job = sampler.run([transpiled], shots=int(shots))
    return IbmSubmitJobResult(
        job_id=str(job.job_id()),
        job_status=_status_text(job),
    )


def _status_text(job: object) -> str | None:
    status = getattr(job, "status", None)
    if callable(status):
        status = status()
    if status is None:
        return None
    name = getattr(status, "name", None)
    if isinstance(name, str) and name:
        return name
    return str(status)
