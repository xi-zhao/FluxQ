"""Domain errors for Quantum Runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping


class QuantumRuntimeError(Exception):
    """Base exception for Quantum Runtime failures."""


class StructuredQuantumRuntimeError(QuantumRuntimeError):
    """Base error carrying a stable machine-readable code."""

    code: str = "runtime_error"

    def __init__(
        self,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = _coerce_details(details or {})


class ManualQspecRequiredError(StructuredQuantumRuntimeError):
    """Raised when rule-based planning cannot infer a safe QSpec."""

    code = "manual_qspec_required"


class WorkspaceConflictError(StructuredQuantumRuntimeError):
    """Raised when another process or agent currently holds the workspace lease."""

    code = "workspace_conflict"

    def __init__(
        self,
        *,
        workspace: Path,
        lock_path: Path,
        holder: Mapping[str, Any] | None = None,
    ) -> None:
        holder_details = _coerce_details(holder or {})
        holder_summary = _holder_summary(holder_details)
        message = f"Workspace conflict at {workspace}"
        if holder_summary:
            message = f"{message}; held by {holder_summary}"
        message = f"{message}. Safe to retry when the workspace is free."
        super().__init__(
            message,
            details={
                "workspace": workspace,
                "lock_path": lock_path,
                "holder": holder_details,
            },
        )


class WorkspaceRecoveryRequiredError(StructuredQuantumRuntimeError):
    """Raised when interrupted writes left the workspace in a recovery-needed state."""

    code = "workspace_recovery_required"

    def __init__(
        self,
        *,
        workspace: Path,
        pending_files: list[Path],
        last_valid_revision: str | None = None,
        alias_paths: list[Path] | None = None,
        recovery_mode: str = "pending_files",
    ) -> None:
        pending_list = [str(item) for item in pending_files]
        alias_list = [str(item) for item in (alias_paths or [])]
        if recovery_mode == "alias_mismatch":
            message = (
                f"Workspace recovery required at {workspace}; mismatched aliases: {', '.join(alias_list)}"
            )
        else:
            message = (
                f"Workspace recovery required at {workspace}; pending files: {', '.join(pending_list)}"
            )
        if last_valid_revision:
            message = f"{message}; last valid revision: {last_valid_revision}"
        message = f"{message}. Run qrun doctor --fix before retrying."
        super().__init__(
            message,
            details={
                "workspace": workspace,
                "pending_files": pending_files,
                "last_valid_revision": last_valid_revision,
                "alias_paths": alias_paths or [],
                "recovery_mode": recovery_mode,
            },
        )


def _coerce_details(value: Mapping[str, Any] | list[Any] | tuple[Any, ...] | Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _coerce_details(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_coerce_details(item) for item in value]
    if isinstance(value, tuple):
        return [_coerce_details(item) for item in value]
    return value


def _holder_summary(holder: Mapping[str, Any]) -> str:
    parts: list[str] = []
    hostname = holder.get("hostname")
    pid = holder.get("pid")
    operation = holder.get("operation")
    if hostname:
        parts.append(str(hostname))
    if pid is not None:
        parts.append(f"pid {pid}")
    if operation:
        parts.append(f"running {operation}")
    return " ".join(parts)
