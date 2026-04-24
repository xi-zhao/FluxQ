"""Workspace baseline persistence helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from quantum_runtime.errors import WorkspaceConflictError, WorkspaceRecoveryRequiredError
from quantum_runtime.workspace.locking import WorkspaceLockConflict, acquire_workspace_lock
from quantum_runtime.workspace.manifest import atomic_write_text, pending_atomic_write_files
from quantum_runtime.workspace.paths import WorkspacePaths


class WorkspaceBaseline(BaseModel):
    """Persisted baseline record for one workspace."""

    source_kind: str
    source: str
    workspace_root: str
    workspace_project_id: str
    revision: str
    report_path: str
    qspec_path: str
    report_hash: str
    qspec_hash: str
    report_status: str | None = None
    qspec_summary: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_import_resolution(cls, resolution: Any) -> "WorkspaceBaseline":
        """Create a baseline record from a resolved runtime input."""
        workspace_root = Path(str(getattr(resolution, "workspace_root")))
        revision = str(getattr(resolution, "revision"))
        report_path = _canonicalize_history_path(
            workspace_root=workspace_root,
            value=Path(str(getattr(resolution, "report_path"))),
            history_subdir="reports/history",
            filename=f"{revision}.json",
            expected_hash=str(getattr(resolution, "report_hash")),
        )
        qspec_path = _canonicalize_history_path(
            workspace_root=workspace_root,
            value=Path(str(getattr(resolution, "qspec_path"))),
            history_subdir="specs/history",
            filename=f"{revision}.json",
            expected_hash=str(getattr(resolution, "qspec_hash")),
        )
        return cls(
            source_kind=str(getattr(resolution, "source_kind")),
            source=str(getattr(resolution, "source")),
            workspace_root=str(workspace_root),
            workspace_project_id=str(getattr(resolution, "workspace_project_id")),
            revision=revision,
            report_path=str(report_path),
            qspec_path=str(qspec_path),
            report_hash=str(getattr(resolution, "report_hash")),
            qspec_hash=str(getattr(resolution, "qspec_hash")),
            report_status=(
                None
                if getattr(resolution, "report_status", None) is None
                else str(getattr(resolution, "report_status"))
            ),
            qspec_summary=dict(getattr(resolution, "qspec_summary", {}) or {}),
        )

    @classmethod
    def load(cls, path: Path) -> "WorkspaceBaseline":
        """Load a baseline record from disk."""
        return cls.model_validate_json(path.read_text())

    def save(self, path: Path) -> None:
        """Persist the baseline record."""
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, self.model_dump_json(indent=2))


def save_workspace_baseline(*, workspace_root: Path, baseline: WorkspaceBaseline) -> Path:
    """Persist the workspace baseline under the shared mutation lease."""
    paths = WorkspacePaths(root=workspace_root)
    baseline_path = paths.baseline_current_json
    try:
        with acquire_workspace_lock(paths.root, command="qrun baseline set"):
            pending_files = pending_atomic_write_files(baseline_path)
            if pending_files:
                raise WorkspaceRecoveryRequiredError(
                    workspace=paths.root,
                    pending_files=pending_files,
                    last_valid_revision=None,
                )
            baseline.save(baseline_path)
    except WorkspaceLockConflict as exc:
        raise WorkspaceConflictError(
            workspace=paths.root,
            lock_path=Path(exc.lock_path),
            holder=exc.holder.model_dump(mode="json"),
        ) from exc
    return baseline_path


def clear_workspace_baseline(*, workspace_root: Path) -> tuple[Path, bool]:
    """Clear the current baseline under the shared mutation lease."""
    paths = WorkspacePaths(root=workspace_root)
    baseline_path = paths.baseline_current_json.resolve()
    try:
        with acquire_workspace_lock(paths.root, command="qrun baseline clear"):
            pending_files = pending_atomic_write_files(baseline_path)
            if pending_files:
                raise WorkspaceRecoveryRequiredError(
                    workspace=paths.root,
                    pending_files=pending_files,
                    last_valid_revision=None,
                )
            cleared = baseline_path.exists()
            if cleared:
                baseline_path.unlink()
    except WorkspaceLockConflict as exc:
        raise WorkspaceConflictError(
            workspace=paths.root,
            lock_path=Path(exc.lock_path),
            holder=exc.holder.model_dump(mode="json"),
        ) from exc
    return baseline_path, cleared


def _canonicalize_history_path(
    *,
    workspace_root: Path,
    value: Path,
    history_subdir: str,
    filename: str,
    expected_hash: str,
) -> Path:
    candidate = (workspace_root / history_subdir / filename).resolve()
    resolved = value.resolve()
    if resolved == candidate:
        return candidate
    if candidate.exists() and _sha256_file(candidate) == expected_hash:
        return candidate
    return resolved


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"
