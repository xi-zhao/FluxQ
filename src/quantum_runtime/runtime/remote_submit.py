"""Canonical remote submit orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from quantum_runtime.errors import WorkspaceConflictError
from quantum_runtime.qspec import summarize_qspec_semantics
from quantum_runtime.runtime.contracts import SchemaPayload
from quantum_runtime.runtime.ibm_access import IbmAccessResolution, build_ibm_service, resolve_ibm_access
from quantum_runtime.runtime.ibm_remote_submit import submit_ibm_job
from quantum_runtime.runtime.remote_attempts import (
    RemoteAttemptArtifactPaths,
    RemoteAttemptBackend,
    RemoteAttemptInput,
    RemoteAttemptJob,
    RemoteAttemptQspec,
    persist_remote_attempt,
)
from quantum_runtime.runtime.resolve import resolve_runtime_input
from quantum_runtime.workspace import WorkspaceHandle, WorkspaceLockConflict, WorkspaceManager


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
) -> RemoteSubmitResult:
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
    handle = _load_workspace_handle(workspace_root)
    access = resolve_ibm_access(workspace_root=handle.root)
    service = build_ibm_service(resolution=access)
    submit_result = submit_ibm_job(
        service=service,
        backend_name=selected_backend_name,
        qspec=resolved.qspec,
        shots=int(resolved.intent_model.shots),
    )
    attempt_id = _reserve_attempt_id(handle)
    semantics = summarize_qspec_semantics(resolved.qspec)
    gate = {
        "status": "open",
        "summary": "Remote submit accepted. Poll the provider job before finalization.",
    }
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
        decision_block=gate,
        submit_payload={
            "provider": "ibm",
            "primitive": _submit_value(submit_result, "primitive", default="sampler_v2"),
            "job_id": _submit_value(submit_result, "job_id"),
            "job_status": _submit_value(submit_result, "job_status"),
            "backend": selected_backend_name,
            "instance": access.instance,
            "shots": int(resolved.intent_model.shots),
        },
        reason_codes=["remote_submit_accepted"],
        next_actions=["poll_remote_job"],
    )
    return RemoteSubmitResult(
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
        gate=dict(record.gate),
    )


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
