"""Workspace manifest persistence."""

from __future__ import annotations

import os
import re
import secrets
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field


def atomic_write_text(path: Path, content: str) -> None:
    """Write text via a same-directory temp file and atomic replace."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.tmp-",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())

    os.replace(temp_path, path)


class WorkspaceManifest(BaseModel):
    """Serialized workspace metadata stored in `workspace.json`."""

    workspace_version: str = "0.1"
    project_id: str
    created_at: str
    current_revision: str = "rev_000000"
    active_spec: str = "specs/current.json"
    active_report: str = "reports/latest.json"
    default_exports: list[str] = Field(default_factory=lambda: ["qiskit", "qasm3"])
    history_limit: int = 50

    @classmethod
    def create_default(cls) -> "WorkspaceManifest":
        """Create a fresh manifest with stable defaults."""
        return cls(
            project_id=f"proj_{secrets.token_hex(4)}",
            created_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        )

    @classmethod
    def load(cls, path: Path) -> "WorkspaceManifest":
        """Load a manifest from disk."""
        return cls.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, path: Path) -> None:
        """Persist the manifest to disk."""
        atomic_write_text(path, self.model_dump_json(indent=2))

    def next_revision(self) -> str:
        """Return the next sequential revision identifier."""
        match = re.fullmatch(r"rev_(\d{6})", self.current_revision)
        if not match:
            raise ValueError(f"Invalid revision format: {self.current_revision}")
        return f"rev_{int(match.group(1)) + 1:06d}"

    def bump_revision(self) -> str:
        """Advance and store the current revision."""
        self.current_revision = self.next_revision()
        return self.current_revision
