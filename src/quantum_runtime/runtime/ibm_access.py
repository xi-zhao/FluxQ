"""IBM access profile persistence and service construction helpers."""

from __future__ import annotations

import importlib
import os
import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, model_validator

from quantum_runtime.workspace import WorkspaceManager, WorkspacePaths
from quantum_runtime.workspace.manifest import atomic_write_text


IBM_CHANNEL = "ibm_quantum_platform"
IBM_CREDENTIAL_MODES = {"env", "saved_account"}


class IbmAccessError(RuntimeError):
    """Domain error raised while building an IBM service."""

    def __init__(self, code: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.details = details or {}


class IbmAccessProfile(BaseModel):
    """Non-secret IBM access reference persisted in `qrun.toml`."""

    channel: Literal["ibm_quantum_platform"] = IBM_CHANNEL
    credential_mode: Literal["env", "saved_account"]
    instance: str
    token_env: str | None = None
    saved_account_name: str | None = None

    @model_validator(mode="after")
    def _validate_mode_requirements(self) -> "IbmAccessProfile":
        if not self.instance.strip():
            raise ValueError("instance is required")
        if self.credential_mode == "env":
            if not self.token_env or self.saved_account_name is not None:
                raise ValueError("env mode requires token_env only")
            return self
        if not self.saved_account_name or self.token_env is not None:
            raise ValueError("saved_account mode requires saved_account_name only")
        return self


class IbmAccessResolution(BaseModel):
    """Resolved IBM access state for doctor and backend discovery flows."""

    status: Literal["ok", "error", "not_configured"]
    configured: bool
    channel: str | None = None
    credential_mode: str | None = None
    instance: str | None = None
    token_env: str | None = None
    saved_account_name: str | None = None
    error_code: str | None = None
    reason_codes: list[str] = Field(default_factory=list)


class IbmConfigureResult(BaseModel):
    """Machine-readable IBM configure result."""

    status: Literal["ok"] = "ok"
    workspace: str
    profile: IbmAccessProfile


def load_ibm_profile(*, workspace_root: Path) -> IbmAccessProfile | None:
    """Load a valid IBM access profile from `qrun.toml` if present."""
    payload = _load_qrun_payload(WorkspacePaths(root=workspace_root).qrun_toml)
    block = _extract_ibm_block(payload)
    if block is None:
        return None
    try:
        return IbmAccessProfile.model_validate(block)
    except ValidationError as exc:
        raise ValueError("Invalid IBM access profile in qrun.toml") from exc


def write_ibm_profile(*, workspace_root: Path, profile: IbmAccessProfile) -> IbmConfigureResult:
    """Persist a non-secret IBM access profile to `qrun.toml`."""
    handle = WorkspaceManager.load_or_init(workspace_root)
    qrun_toml = handle.paths.qrun_toml
    payload = _load_qrun_payload(qrun_toml)

    remote_block = payload.setdefault("remote", {})
    if not isinstance(remote_block, dict):
        raise ValueError("Expected [remote] table in qrun.toml")
    remote_block["ibm"] = profile.model_dump(mode="json", exclude_none=True)

    atomic_write_text(qrun_toml, _dump_toml(payload))
    return IbmConfigureResult(
        workspace=str(handle.root),
        profile=profile,
    )


def resolve_ibm_access(*, workspace_root: Path) -> IbmAccessResolution:
    """Resolve persisted IBM access state without touching remote services."""
    payload = _load_qrun_payload(WorkspacePaths(root=workspace_root).qrun_toml)
    block = _extract_ibm_block(payload)
    if block is None:
        return IbmAccessResolution(
            status="not_configured",
            configured=False,
        )

    channel = _string_value(block.get("channel"), default=IBM_CHANNEL)
    credential_mode = _string_value(block.get("credential_mode"))
    instance = _string_value(block.get("instance"))
    token_env = _string_value(block.get("token_env"))
    saved_account_name = _string_value(block.get("saved_account_name"))

    if channel != IBM_CHANNEL:
        return _error_resolution(
            channel=channel,
            credential_mode=credential_mode,
            instance=instance,
            token_env=token_env,
            saved_account_name=saved_account_name,
            error_code="ibm_config_invalid",
        )
    if not instance:
        return _error_resolution(
            channel=channel,
            credential_mode=credential_mode,
            instance=instance,
            token_env=token_env,
            saved_account_name=saved_account_name,
            error_code="ibm_instance_required",
        )
    if credential_mode == "env":
        if not token_env or saved_account_name is not None:
            return _error_resolution(
                channel=channel,
                credential_mode=credential_mode,
                instance=instance,
                token_env=token_env,
                saved_account_name=saved_account_name,
                error_code="ibm_config_invalid",
            )
        return IbmAccessResolution(
            status="ok",
            configured=True,
            channel=channel,
            credential_mode=credential_mode,
            instance=instance,
            token_env=token_env,
        )
    if credential_mode == "saved_account":
        if not saved_account_name or token_env is not None:
            return _error_resolution(
                channel=channel,
                credential_mode=credential_mode,
                instance=instance,
                token_env=token_env,
                saved_account_name=saved_account_name,
                error_code="ibm_config_invalid",
            )
        return IbmAccessResolution(
            status="ok",
            configured=True,
            channel=channel,
            credential_mode=credential_mode,
            instance=instance,
            saved_account_name=saved_account_name,
        )

    return _error_resolution(
        channel=channel,
        credential_mode=credential_mode,
        instance=instance,
        token_env=token_env,
        saved_account_name=saved_account_name,
        error_code="ibm_config_invalid",
    )


def build_ibm_service(*, resolution: IbmAccessResolution) -> object:
    """Construct a `QiskitRuntimeService` from resolved IBM access state."""
    if resolution.status != "ok":
        raise IbmAccessError(
            resolution.error_code or "ibm_config_invalid",
            details=resolution.model_dump(mode="json", exclude_none=True),
        )

    service_class = _load_service_class()
    if resolution.credential_mode == "env":
        if resolution.token_env is None:
            raise IbmAccessError("ibm_config_invalid")
        token = os.environ.get(resolution.token_env)
        if not token:
            raise IbmAccessError(
                "ibm_token_external_required",
                details={"token_env": resolution.token_env},
            )
        return service_class(
            channel=resolution.channel or IBM_CHANNEL,
            token=token,
            instance=resolution.instance,
        )

    if resolution.saved_account_name is None:
        raise IbmAccessError("ibm_config_invalid")
    return service_class(
        channel=resolution.channel or IBM_CHANNEL,
        name=resolution.saved_account_name,
        instance=resolution.instance,
    )


def _error_resolution(
    *,
    channel: str | None,
    credential_mode: str | None,
    instance: str | None,
    token_env: str | None,
    saved_account_name: str | None,
    error_code: str,
) -> IbmAccessResolution:
    return IbmAccessResolution(
        status="error",
        configured=True,
        channel=channel,
        credential_mode=credential_mode,
        instance=instance,
        token_env=token_env,
        saved_account_name=saved_account_name,
        error_code=error_code,
        reason_codes=[error_code],
    )


def _load_qrun_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Expected qrun.toml to decode to a table")
    return payload


def _extract_ibm_block(payload: dict[str, Any]) -> dict[str, Any] | None:
    remote_block = payload.get("remote")
    if not isinstance(remote_block, dict):
        return None
    ibm_block = remote_block.get("ibm")
    if not isinstance(ibm_block, dict):
        return None
    return ibm_block


def _load_service_class() -> type[object]:
    try:
        module = importlib.import_module("qiskit_ibm_runtime")
    except ModuleNotFoundError as exc:
        raise IbmAccessError("ibm_runtime_dependency_missing") from exc

    service_class = getattr(module, "QiskitRuntimeService", None)
    if service_class is None:
        raise IbmAccessError("ibm_runtime_dependency_missing")
    return service_class


def _string_value(value: object, *, default: str | None = None) -> str | None:
    if value is None:
        return default
    rendered = str(value).strip()
    if not rendered:
        return default
    return rendered


def _dump_toml(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    _append_toml_table(lines, (), payload)
    return "\n".join(lines).rstrip() + "\n"


def _append_toml_table(lines: list[str], prefix: tuple[str, ...], table: dict[str, Any]) -> None:
    scalar_items: list[tuple[str, Any]] = []
    nested_items: list[tuple[str, dict[str, Any]]] = []

    for key, value in table.items():
        if isinstance(value, dict):
            nested_items.append((key, value))
        else:
            scalar_items.append((key, value))

    if prefix:
        lines.append(f"[{'.'.join(prefix)}]")
    for key, value in scalar_items:
        lines.append(f"{key} = {_toml_value(value)}")
    if prefix and (scalar_items or nested_items):
        lines.append("")

    for index, (key, nested_table) in enumerate(nested_items):
        _append_toml_table(lines, prefix + (key,), nested_table)
        if index != len(nested_items) - 1:
            lines.append("")


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f"\"{escaped}\""
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    raise TypeError(f"Unsupported TOML value: {value!r}")
