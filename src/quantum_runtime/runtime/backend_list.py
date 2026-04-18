"""Backend listing helpers for the CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, Field

from quantum_runtime.runtime.backend_registry import collect_backend_capabilities
from quantum_runtime.runtime.contracts import remediation_for_error
from quantum_runtime.runtime.ibm_access import (
    IbmAccessError,
    IbmAccessResolution,
    build_ibm_service,
    resolve_ibm_access,
)


class BackendListReport(BaseModel):
    """Stable backend availability listing."""

    backends: dict[str, dict[str, Any]] = Field(default_factory=dict)
    remote: dict[str, Any] = Field(default_factory=dict)


def list_backends(*, workspace_root: Path = Path(".quantum")) -> BackendListReport:
    """Return known runtime backends and their current availability."""
    capabilities = collect_backend_capabilities()
    ibm_descriptor = capabilities.get("ibm-runtime")
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
            sdk_available=ibm_descriptor.available if ibm_descriptor is not None else False,
        ),
    )


def _ibm_remote_summary(*, workspace_root: Path, sdk_available: bool) -> dict[str, Any]:
    try:
        resolution = resolve_ibm_access(workspace_root=workspace_root)
    except Exception:
        return _remote_payload(
            configured=False,
            auth_source=None,
            instance=None,
            sdk_available=sdk_available,
            readiness=_readiness_block(
                status="blocked",
                reason_codes=["ibm_access_unresolved"],
            ),
            targets=[],
        )

    if resolution.status != "ok":
        readiness_status = "not_configured" if resolution.status == "not_configured" else "blocked"
        return _remote_payload(
            configured=resolution.configured,
            auth_source=resolution.credential_mode,
            instance=resolution.instance,
            sdk_available=sdk_available,
            readiness=_readiness_block(
                status=readiness_status,
                reason_codes=_resolution_reason_codes(resolution),
            ),
            targets=[],
        )

    try:
        service = build_ibm_service(resolution=resolution)
        targets = [_project_target_readiness(target) for target in cast(Any, service).backends()]
    except IbmAccessError as exc:
        return _remote_payload(
            configured=resolution.configured,
            auth_source=resolution.credential_mode,
            instance=resolution.instance,
            sdk_available=sdk_available,
            readiness=_readiness_block(
                status="blocked",
                reason_codes=_service_reason_codes(exc.code, resolution=resolution),
            ),
            targets=[],
        )
    except Exception:
        fallback_reason = (
            "ibm_saved_account_missing"
            if resolution.credential_mode == "saved_account"
            else "ibm_access_unresolved"
        )
        return _remote_payload(
            configured=resolution.configured,
            auth_source=resolution.credential_mode,
            instance=resolution.instance,
            sdk_available=sdk_available,
            readiness=_readiness_block(
                status="blocked",
                reason_codes=[fallback_reason],
            ),
            targets=[],
        )

    return _remote_payload(
        configured=resolution.configured,
        auth_source=resolution.credential_mode,
        instance=resolution.instance,
        sdk_available=sdk_available,
        readiness=_readiness_block(
            status="ready",
            reason_codes=[],
        ),
        targets=targets,
    )


def _remote_payload(
    *,
    configured: bool,
    auth_source: str | None,
    instance: str | None,
    sdk_available: bool,
    readiness: dict[str, Any],
    targets: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "provider": "ibm",
        "configured": configured,
        "auth_source": auth_source,
        "instance": instance,
        "sdk_available": sdk_available,
        "status": readiness["status"],
        "reason_codes": readiness["reason_codes"],
        "next_actions": readiness["next_actions"],
        "readiness": readiness,
        "targets": targets,
    }


def _readiness_block(*, status: str, reason_codes: list[str], next_actions: list[str] | None = None) -> dict[str, Any]:
    return {
        "status": status,
        "reason_codes": list(reason_codes),
        "next_actions": next_actions if next_actions is not None else [remediation_for_error(code) for code in reason_codes],
    }


def _resolution_reason_codes(resolution: IbmAccessResolution) -> list[str]:
    if resolution.status == "not_configured":
        return []
    if resolution.reason_codes:
        return list(resolution.reason_codes)
    if resolution.error_code == "ibm_instance_required":
        return ["ibm_instance_unset"]
    if resolution.error_code == "ibm_config_invalid":
        if not resolution.credential_mode:
            return ["ibm_profile_missing"]
        if resolution.credential_mode == "env" and not resolution.token_env:
            return ["ibm_profile_missing"]
        if resolution.credential_mode == "saved_account" and not resolution.saved_account_name:
            return ["ibm_profile_missing"]
    if resolution.error_code is not None:
        return [resolution.error_code]
    return ["ibm_access_unresolved"]


def _service_reason_codes(error_code: str, *, resolution: IbmAccessResolution) -> list[str]:
    if error_code == "ibm_token_external_required":
        return ["ibm_token_env_missing"]
    if error_code == "ibm_instance_required":
        return ["ibm_instance_unset"]
    if error_code == "ibm_config_invalid":
        return _resolution_reason_codes(resolution)
    if error_code in {
        "ibm_profile_missing",
        "ibm_instance_unset",
        "ibm_token_env_missing",
        "ibm_saved_account_missing",
        "ibm_runtime_dependency_missing",
        "ibm_access_unresolved",
    }:
        return [error_code]
    if resolution.credential_mode == "saved_account":
        return ["ibm_saved_account_missing"]
    return ["ibm_access_unresolved"]


def _project_target_readiness(target: Any) -> dict[str, Any]:
    try:
        status = target.status()
    except Exception:
        return {
            "name": _target_value(target, "name"),
            "operational": False,
            "status_msg": None,
            "pending_jobs": None,
            "num_qubits": _target_value(target, "num_qubits"),
            "backend_version": _target_value(target, "backend_version"),
            "readiness": _readiness_block(
                status="blocked",
                reason_codes=["ibm_backend_status_unavailable"],
                next_actions=["Retry backend discovery or inspect IBM service health before selecting this backend."],
            ),
        }

    operational = bool(getattr(status, "operational", False))
    readiness = _readiness_block(
        status="ready" if operational else "degraded",
        reason_codes=[] if operational else ["ibm_backend_not_operational"],
        next_actions=[] if operational else ["Inspect status_msg and pending_jobs before selecting this backend for submit."],
    )
    return {
        "name": _target_value(target, "name"),
        "operational": operational,
        "status_msg": getattr(status, "status_msg", None),
        "pending_jobs": getattr(status, "pending_jobs", None),
        "num_qubits": _target_value(target, "num_qubits"),
        "backend_version": _target_value(target, "backend_version"),
        "readiness": readiness,
    }


def _target_value(target: Any, attribute: str) -> Any:
    value = getattr(target, attribute, None)
    return value() if callable(value) else value
