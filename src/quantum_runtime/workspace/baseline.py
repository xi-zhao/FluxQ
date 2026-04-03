"""Workspace baseline persistence helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


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
        path.write_text(self.model_dump_json(indent=2))


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
