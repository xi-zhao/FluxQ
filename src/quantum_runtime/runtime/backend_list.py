"""Backend listing helpers for the CLI."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from quantum_runtime.runtime.doctor import collect_backend_capabilities


class BackendListReport(BaseModel):
    """Stable backend availability listing."""

    backends: dict[str, dict[str, Any]] = Field(default_factory=dict)


def list_backends() -> BackendListReport:
    """Return known runtime backends and their current availability."""
    capabilities = collect_backend_capabilities()
    return BackendListReport(
        backends={
            "qiskit-local": {
                "available": bool(
                    capabilities["qiskit"]["available"] and capabilities["qiskit_aer"]["available"]
                ),
                "reason": capabilities["qiskit"]["error"] or capabilities["qiskit_aer"]["error"],
            },
            "classiq": {
                "available": bool(capabilities["classiq"]["available"]),
                "reason": capabilities["classiq"]["error"],
            },
        }
    )
