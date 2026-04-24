"""Canonical remote submit orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import Field

from quantum_runtime.errors import WorkspaceConflictError, WorkspaceRecoveryRequiredError
from quantum_runtime.qspec import summarize_qspec_semantics
from quantum_runtime.runtime.contracts import SchemaPayload, remediation_for_error
from quantum_runtime.runtime.ibm_access import (
    IbmAccessError,
    IbmAccessResolution,
    build_ibm_service,
    resolve_ibm_access,
)
from quantum_runtime.runtime.ibm_remote_submit import submit_ibm_job
from quantum_runtime.runtime.observability import decision_block, gate_block, next_actions_for_reason_codes
from quantum_runtime.runtime.remote_attempts import (
    RemoteAttemptArtifactPaths,
    RemoteAttemptBackend,
    RemoteAttemptInput,
    RemoteAttemptJob,
    RemoteAttemptQspec,
    persist_remote_attempt,
)
from quantum_runtime.runtime.resolve import resolve_runtime_input
from quantum_runtime.workspace import (
    WorkspaceHandle,
    WorkspaceLockConflict,
    WorkspaceManager,
    pending_atomic_write_files,
)


class RemoteSubmitResult(SchemaPayload):
    """Machine-readable result for a successful remote submit."""

    status: Literal["ok"] = "ok"
    workspace: str
    attempt_id: str = Field(pattern=r"attempt_\d{6}")
    provider: str
    auth_source: str
    backend: RemoteAttemptBackend
    job: RemoteAttemptJob
    input: RemoteAttemptInput
    qspec: RemoteAttemptQspec
    artifacts: RemoteAttemptArtifactPaths
    reason_codes: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    decision: dict[str, Any] = Field(default_factory=dict)


class RemoteSubmitBlockedResult(SchemaPayload):
    """Machine-readable result for a blocked remote submit."""

    status: Literal["degraded"] = "degraded"
    workspace: str
    provider: str = "ibm"
    attempt_id: str | None = Field(default=None, pattern=r"attempt_\d{6}")
    job: RemoteAttemptJob | None = None
    reason: str
    error_code: str
    remediation: str
    details: dict[str, Any] = Field(default_factory=dict)
    reason_codes: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    gate: dict[str, Any] = Field(default_factory=dict)


def submit_remote_input(
    *,
    workspace_root: Path,
    backend_name: str,
    intent_file: Path | None = None,
    intent_json_file: Path | None = None,
    qspec_file: Path | None = None,
    report_file: Path | None = None,
    revision: str | None = None,
    intent_text: str | None = None,
    event_sink: Callable[[str, dict[str, Any], str | None, str], None] | None = None,
) -> RemoteSubmitResult | RemoteSubmitBlockedResult:
    """Resolve one canonical input, submit it remotely, and persist the attempt."""
    selected_backend_name = backend_name.strip()
    if not selected_backend_name:
        raise ValueError("remote_backend_required")

    resolved = resolve_runtime_input(
        workspace_root=workspace_root,
        intent_file=intent_file,
        intent_json_file=intent_json_file,
        qspec_file=qspec_file,
        report_file=report_file,
        revision=revision,
        intent_text=intent_text,
    )
    if event_sink is not None:
        event_sink(
            "submit_started",
            {
                "provider": "ibm",
                "backend": selected_backend_name,
                "source_kind": resolved.source_kind,
            },
            None,
            "ok",
        )
    _ensure_remote_attempt_persistence_ready(workspace_root)
    handle = _load_workspace_handle(workspace_root)
    access = resolve_ibm_access(workspace_root=handle.root)
    if access.status != "ok":
        blocked_result = _blocked_result(
            workspace_root=handle.root,
            reason_codes=_resolution_reason_codes(access),
            details=access.model_dump(mode="json", exclude_none=True),
        )
        _emit_submit_completion(event_sink=event_sink, result=blocked_result)
        return blocked_result
    try:
        service = build_ibm_service(resolution=access)
    except IbmAccessError as exc:
        blocked_result = _blocked_result(
            workspace_root=handle.root,
            reason_codes=_service_reason_codes(exc.code, resolution=access),
            details=exc.details,
        )
        _emit_submit_completion(event_sink=event_sink, result=blocked_result)
        return blocked_result
    try:
        submit_result = submit_ibm_job(
            service=service,
            backend_name=selected_backend_name,
            qspec=resolved.qspec,
            shots=int(resolved.intent_model.shots),
        )
    except IbmAccessError as exc:
        blocked_result = _blocked_result(
            workspace_root=handle.root,
            reason_codes=_submit_reason_codes(exc.code),
            details=exc.details,
        )
        _emit_submit_completion(event_sink=event_sink, result=blocked_result)
        return blocked_result
    except Exception as exc:
        blocked_result = _blocked_result(
            workspace_root=handle.root,
            reason_codes=["remote_submit_failed"],
            details={
                "error_type": type(exc).__name__,
                "message": str(exc),
            },
        )
        _emit_submit_completion(event_sink=event_sink, result=blocked_result)
        return blocked_result

    attempt_id = _reserve_attempt_id(handle)
    semantics = summarize_qspec_semantics(resolved.qspec)
    reason_codes = ["remote_submit_persisted"]
    next_actions = next_actions_for_reason_codes(reason_codes)
    decision = decision_block(
        status="ok",
        reason_codes=reason_codes,
        next_actions=next_actions,
    )
    try:
        record = persist_remote_attempt(
            workspace=handle,
            attempt_id=attempt_id,
            resolved_input=resolved,
            semantic_hashes={
                "semantic_hash": semantics["semantic_hash"],
                "execution_hash": semantics["execution_hash"],
            },
            provider="ibm",
            auth_source=_auth_source(access),
            backend={
                "name": selected_backend_name,
                "instance": access.instance,
            },
            job={
                "id": _submit_value(submit_result, "job_id"),
                "status": _submit_value(submit_result, "job_status"),
            },
            decision_block=decision,
            submit_payload={
                "provider": "ibm",
                "primitive": _submit_value(submit_result, "primitive", default="sampler_v2"),
                "job_id": _submit_value(submit_result, "job_id"),
                "job_status": _submit_value(submit_result, "job_status"),
                "backend": selected_backend_name,
                "instance": access.instance,
                "shots": int(resolved.intent_model.shots),
            },
            reason_codes=reason_codes,
            next_actions=next_actions,
        )
    except (WorkspaceConflictError, WorkspaceRecoveryRequiredError):
        raise
    except Exception as exc:
        blocked_result = _blocked_result(
            workspace_root=handle.root,
            reason_codes=["remote_attempt_persist_failed"],
            attempt_id=attempt_id,
            job={
                "id": _submit_value(submit_result, "job_id"),
                "status": _submit_value(submit_result, "job_status"),
            },
            details={
                "attempt_id": attempt_id,
                "job_id": _submit_value(submit_result, "job_id"),
                "backend": selected_backend_name,
                "error_type": type(exc).__name__,
                "message": str(exc),
            },
        )
        _emit_submit_completion(event_sink=event_sink, result=blocked_result)
        return blocked_result

    if event_sink is not None:
        event_sink(
            "submit_persisted",
            {
                "attempt_id": record.attempt_id,
                "job_id": record.job.id,
                "backend": record.backend.name,
                "provider": record.provider,
            },
            None,
            "ok",
        )

    result = RemoteSubmitResult(
        workspace=str(handle.root.resolve()),
        attempt_id=record.attempt_id,
        provider=record.provider,
        auth_source=record.auth_source,
        backend=record.backend,
        job=record.job,
        input=record.input,
        qspec=record.qspec,
        artifacts=record.artifacts,
        reason_codes=list(record.reason_codes),
        next_actions=list(record.next_actions),
        decision=decision,
    )
    _emit_submit_completion(event_sink=event_sink, result=result)
    return result


def _load_workspace_handle(workspace_root: Path) -> WorkspaceHandle:
    try:
        return WorkspaceManager.load_or_init(workspace_root)
    except WorkspaceLockConflict as exc:
        raise _workspace_conflict_error(workspace_root=workspace_root, conflict=exc) from exc


def _reserve_attempt_id(handle: WorkspaceHandle) -> str:
    try:
        return handle.reserve_attempt()
    except WorkspaceLockConflict as exc:
        raise _workspace_conflict_error(workspace_root=handle.root, conflict=exc) from exc


def _workspace_conflict_error(*, workspace_root: Path, conflict: WorkspaceLockConflict) -> WorkspaceConflictError:
    return WorkspaceConflictError(
        workspace=workspace_root.resolve(),
        lock_path=Path(conflict.lock_path),
        holder=conflict.holder.model_dump(mode="json"),
    )


def _auth_source(access: IbmAccessResolution) -> str:
    if access.credential_mode == "env" and access.token_env:
        return f"env:{access.token_env}"
    if access.credential_mode == "saved_account" and access.saved_account_name:
        return f"saved_account:{access.saved_account_name}"
    return access.credential_mode or "unknown"


def _submit_value(receipt: object, field: str, *, default: Any = None) -> Any:
    if isinstance(receipt, dict):
        return receipt.get(field, default)
    return getattr(receipt, field, default)


def _blocked_result(
    *,
    workspace_root: Path,
    reason_codes: list[str],
    details: dict[str, Any] | None = None,
    attempt_id: str | None = None,
    job: RemoteAttemptJob | dict[str, Any] | None = None,
) -> RemoteSubmitBlockedResult:
    normalized_reason_codes = list(dict.fromkeys(str(code) for code in reason_codes if str(code).strip()))
    if not normalized_reason_codes:
        normalized_reason_codes = ["remote_submit_failed"]
    next_actions = next_actions_for_reason_codes(normalized_reason_codes)
    primary_reason = normalized_reason_codes[0]
    return RemoteSubmitBlockedResult(
        workspace=str(workspace_root.resolve()),
        attempt_id=attempt_id,
        job=RemoteAttemptJob.model_validate(job) if job is not None else None,
        reason=primary_reason,
        error_code=primary_reason,
        remediation=remediation_for_error(primary_reason),
        details=_sanitize_details(details or {}),
        reason_codes=normalized_reason_codes,
        next_actions=next_actions,
        gate=gate_block(
            ready=False,
            severity="error",
            reason_codes=normalized_reason_codes,
            next_actions=next_actions,
        ),
    )


def _resolution_reason_codes(resolution: IbmAccessResolution) -> list[str]:
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
    return ["ibm_access_unresolved"]


def _submit_reason_codes(error_code: str) -> list[str]:
    if error_code == "ibm_backend_lookup_failed":
        return ["remote_backend_not_ready", "ibm_backend_lookup_failed"]
    if error_code == "remote_backend_not_ready":
        return ["remote_backend_not_ready"]
    if error_code in {
        "ibm_profile_missing",
        "ibm_instance_unset",
        "ibm_token_env_missing",
        "ibm_saved_account_missing",
        "ibm_runtime_dependency_missing",
        "ibm_access_unresolved",
    }:
        return [error_code]
    return ["remote_submit_failed"]


def _sanitize_details(details: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in details.items():
        sanitized[key] = _sanitize_value(key, value)
    return sanitized


def _sanitize_value(key: str, value: Any) -> Any:
    lowered_key = key.lower()
    if lowered_key in {"authorization", "token"}:
        return "[redacted]"
    if isinstance(value, dict):
        return {item_key: _sanitize_value(item_key, item_value) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(key, item) for item in value]
    if isinstance(value, str) and "bearer " in value.lower():
        return "[redacted]"
    return value


def _emit_submit_completion(
    *,
    event_sink: Callable[[str, dict[str, Any], str | None, str], None] | None,
    result: RemoteSubmitResult | RemoteSubmitBlockedResult,
) -> None:
    if event_sink is None:
        return
    event_sink(
        "submit_completed",
        result.model_dump(mode="json", exclude_none=True),
        None,
        result.status,
    )


def _ensure_remote_attempt_persistence_ready(workspace_root: Path) -> None:
    handle = _load_workspace_handle(workspace_root)
    paths = handle.paths
    pending_files = pending_atomic_write_files(paths.remote_attempt_latest_json)
    if not pending_files:
        return
    raise WorkspaceRecoveryRequiredError(
        workspace=handle.root.resolve(),
        pending_files=pending_files,
        last_valid_revision=None,
    )
