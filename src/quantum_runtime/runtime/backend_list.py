"""Backend listing helpers for the CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from quantum_runtime.runtime.backend_registry import collect_backend_capabilities
from quantum_runtime.runtime.contracts import remediation_for_error
from quantum_runtime.runtime.ibm_access import IbmAccessResolution, resolve_ibm_access


class BackendListReport(BaseModel):
    """Stable backend availability listing."""

    backends: dict[str, dict[str, Any]] = Field(default_factory=dict)
    remote: dict[str, Any] = Field(default_factory=dict)


def list_backends(*, workspace_root: Path = Path(".quantum")) -> BackendListReport:
    """Return known runtime backends and their current availability."""
    capabilities = collect_backend_capabilities()
    return BackendListReport(
        backends={
            name: {
                "available": descriptor.available,
                "optional": descriptor.optional,
                "reason": descriptor.reason,
                "provider": descriptor.provider,
                "module_dependencies": [dependency.model_dump(mode="json") for dependency in descriptor.module_dependencies],
                "capabilities": descriptor.capabilities,
                "notes": descriptor.notes,
            }
            for name, descriptor in capabilities.items()
        },
        remote=_ibm_remote_summary(
            workspace_root=workspace_root,
            sdk_available=capabilities.get("ibm-runtime").available if "ibm-runtime" in capabilities else False,
        ),
    )


def _ibm_remote_summary(*, workspace_root: Path, sdk_available: bool) -> dict[str, Any]:
    try:
        resolution = resolve_ibm_access(workspace_root=workspace_root)
    except Exception:
        return {
            "provider": "ibm",
            "configured": False,
            "auth_source": None,
            "instance": None,
            "sdk_available": sdk_available,
            "status": "blocked",
            "reason_codes": ["ibm_access_unresolved"],
            "next_actions": [remediation_for_error("ibm_access_unresolved")],
        }

    reason_codes = _remote_reason_codes(resolution)
    return {
        "provider": "ibm",
        "configured": resolution.configured,
        "auth_source": resolution.credential_mode,
        "instance": resolution.instance,
        "sdk_available": sdk_available,
        "status": _remote_status(resolution),
        "reason_codes": reason_codes,
        "next_actions": [remediation_for_error(code) for code in reason_codes],
    }


def _remote_status(resolution: IbmAccessResolution) -> str:
    if resolution.status == "not_configured":
        return "not_configured"
    if resolution.status == "ok":
        return "configured"
    return "blocked"


def _remote_reason_codes(resolution: IbmAccessResolution) -> list[str]:
    if resolution.status == "not_configured":
        return []
    if resolution.reason_codes:
        return list(resolution.reason_codes)
    if resolution.error_code is not None:
        return [resolution.error_code]
    return []
