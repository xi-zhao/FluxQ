"""Remote submit attempt models and persistence helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from quantum_runtime.errors import WorkspaceRecoveryRequiredError
from quantum_runtime.runtime.control_plane import build_execution_plan_from_resolved
from quantum_runtime.runtime.contracts import SchemaPayload
from quantum_runtime.runtime.resolve import ResolvedRuntimeInput
from quantum_runtime.workspace import (
    WorkspaceHandle,
    WorkspacePaths,
    acquire_workspace_lock,
    atomic_write_text,
    pending_atomic_write_files,
)


class RemoteAttemptBackend(BaseModel):
    """Non-secret backend coordinates for one remote submit attempt."""

    model_config = ConfigDict(extra="forbid")

    name: str
    instance: str | None = None


class RemoteAttemptJob(BaseModel):
    """Provider job handle captured at submit time."""

    model_config = ConfigDict(extra="forbid")

    id: str


class RemoteAttemptInput(BaseModel):
    """Canonical ingress provenance for one remote attempt."""

    model_config = ConfigDict(extra="forbid")

    source_kind: str
    source: str


class RemoteAttemptQspec(BaseModel):
    """Canonical QSpec provenance persisted for later reopen/finalization."""

    model_config = ConfigDict(extra="forbid")

    semantic_hash: str
    execution_hash: str
    path: str | None = None
    source: str | None = None


class RemoteAttemptArtifactPaths(BaseModel):
    """Artifact paths persisted for one remote attempt."""

    model_config = ConfigDict(extra="forbid")

    record_path: str
    latest_path: str
    qspec_path: str
    intent_path: str
    plan_path: str
    submit_payload_path: str


class RemoteAttemptRecord(SchemaPayload):
    """Schema-versioned durable record for one remote submit attempt."""

    model_config = ConfigDict(extra="forbid")

    status: str = "submitted"
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


def reserve_attempt_id(workspace: WorkspaceHandle) -> str:
    """Allocate and persist the next remote-attempt identifier."""
    return workspace.reserve_attempt()


def persist_remote_attempt(
    *,
    workspace: WorkspaceHandle,
    attempt_id: str,
    resolved_input: ResolvedRuntimeInput,
    semantic_hashes: dict[str, str],
    provider: str,
    auth_source: str,
    backend: RemoteAttemptBackend | dict[str, Any],
    job: RemoteAttemptJob | dict[str, Any],
    decision_block: dict[str, Any],
    submit_payload: dict[str, Any],
    reason_codes: list[str] | None = None,
    next_actions: list[str] | None = None,
) -> RemoteAttemptRecord:
    """Persist a remote-attempt record and snapshots."""
    paths = WorkspacePaths(root=workspace.root)
    artifact_paths = _artifact_paths_for_attempt(paths=paths, attempt_id=attempt_id)
    backend_model = RemoteAttemptBackend.model_validate(backend)
    job_model = RemoteAttemptJob.model_validate(job)
    plan_payload = build_execution_plan_from_resolved(
        workspace_root=workspace.root,
        resolved=resolved_input,
    ).model_dump(mode="json")
    record = RemoteAttemptRecord(
        attempt_id=attempt_id,
        provider=provider,
        auth_source=auth_source,
        backend=backend_model,
        job=job_model,
        input=RemoteAttemptInput(
            source_kind=resolved_input.source_kind,
            source=resolved_input.source,
        ),
        qspec=RemoteAttemptQspec(
            semantic_hash=semantic_hashes["semantic_hash"],
            execution_hash=semantic_hashes["execution_hash"],
            path=artifact_paths.qspec_path,
            source=resolved_input.source,
        ),
        artifacts=artifact_paths,
        reason_codes=list(reason_codes or []),
        next_actions=list(next_actions or []),
        gate=dict(decision_block),
    )
    serialized_record = record.model_dump_json(indent=2)

    with acquire_workspace_lock(workspace.root):
        _guard_remote_attempt_latest_path(
            workspace_root=workspace.root,
            latest_path=paths.remote_attempt_latest_json,
        )
        atomic_write_text(
            Path(artifact_paths.qspec_path),
            resolved_input.qspec.model_dump_json(indent=2),
        )
        atomic_write_text(
            Path(artifact_paths.intent_path),
            json.dumps(
                resolved_input.intent_resolution.model_dump(mode="json"),
                indent=2,
                ensure_ascii=True,
            ),
        )
        atomic_write_text(
            Path(artifact_paths.plan_path),
            json.dumps(plan_payload, indent=2, ensure_ascii=True),
        )
        atomic_write_text(
            Path(artifact_paths.submit_payload_path),
            json.dumps(submit_payload, indent=2, ensure_ascii=True),
        )
        atomic_write_text(Path(artifact_paths.record_path), serialized_record)
        atomic_write_text(Path(artifact_paths.latest_path), serialized_record)

    return record


def load_remote_attempt(*, workspace_root: Path, attempt_id: str) -> RemoteAttemptRecord:
    """Load a persisted remote-attempt record."""
    record_path = WorkspacePaths(root=workspace_root).remote_attempt_history_json(attempt_id)
    return RemoteAttemptRecord.model_validate_json(record_path.read_text(encoding="utf-8"))


def _artifact_paths_for_attempt(*, paths: WorkspacePaths, attempt_id: str) -> RemoteAttemptArtifactPaths:
    attempt_artifact_dir = paths.remote_artifact_attempt_dir(attempt_id)
    return RemoteAttemptArtifactPaths(
        record_path=str(paths.remote_attempt_history_json(attempt_id).resolve()),
        latest_path=str(paths.remote_attempt_latest_json.resolve()),
        qspec_path=str((attempt_artifact_dir / "qspec.json").resolve()),
        intent_path=str((attempt_artifact_dir / "intent.json").resolve()),
        plan_path=str((attempt_artifact_dir / "plan.json").resolve()),
        submit_payload_path=str((attempt_artifact_dir / "submit_payload.json").resolve()),
    )


def _guard_remote_attempt_latest_path(*, workspace_root: Path, latest_path: Path) -> None:
    pending_files = pending_atomic_write_files(latest_path)
    if not pending_files:
        return
    raise WorkspaceRecoveryRequiredError(
        workspace=workspace_root.resolve(),
        pending_files=pending_files,
        last_valid_revision=None,
    )
