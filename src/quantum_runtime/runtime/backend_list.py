"""Backend listing helpers for the CLI."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from quantum_runtime.runtime.backend_registry import collect_backend_capabilities


class BackendListReport(BaseModel):
    """Stable backend availability listing."""

    backends: dict[str, dict[str, Any]] = Field(default_factory=dict)


def list_backends() -> BackendListReport:
    """Return known runtime backends and their current availability."""
    capabilities = collect_backend_capabilities()
    return BackendListReport(
        backends={
            name: {
                "available": descriptor.available,
                "reason": descriptor.reason,
                "provider": descriptor.provider,
                "module_dependencies": [dependency.model_dump(mode="json") for dependency in descriptor.module_dependencies],
                "capabilities": descriptor.capabilities,
                "notes": descriptor.notes,
            }
            for name, descriptor in capabilities.items()
        }
    )
