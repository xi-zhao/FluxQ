"""Remote submit attempt models and persistence helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from quantum_runtime.runtime.contracts import SchemaPayload
from quantum_runtime.workspace import WorkspaceHandle


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


def persist_remote_attempt(*args: Any, **kwargs: Any) -> RemoteAttemptRecord:
    """Persist a remote-attempt record and snapshots."""
    raise NotImplementedError("persist_remote_attempt is implemented in Task 2")


def load_remote_attempt(*, workspace_root: Path, attempt_id: str) -> RemoteAttemptRecord:
    """Load a persisted remote-attempt record."""
    raise NotImplementedError("load_remote_attempt is implemented in Task 2")
