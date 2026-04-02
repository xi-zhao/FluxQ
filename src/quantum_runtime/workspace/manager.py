"""Workspace initialization and loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from .manifest import WorkspaceManifest
from .paths import WorkspacePaths
from .trace import TraceWriter


DEFAULT_QRUN_TOML = """[workspace]
default_exports = ["qiskit", "qasm3"]
history_limit = 50
"""


class InitResult(BaseModel):
    """Machine-readable result returned by `qrun init --json`."""

    status: str = "ok"
    workspace: str
    workspace_version: str = "0.1"
    project_id: str
    current_revision: str
    created: bool


@dataclass
class WorkspaceHandle:
    """Live workspace state used by later runtime stages."""

    root: Path
    paths: WorkspacePaths
    manifest: WorkspaceManifest
    trace: TraceWriter

    def reserve_revision(self) -> str:
        """Advance the workspace revision and persist the manifest."""
        revision = self.manifest.bump_revision()
        self.manifest.save(self.paths.workspace_json)
        return revision


class WorkspaceManager:
    """Create and load the deterministic workspace layout."""

    @classmethod
    def init_workspace(cls, root: Path) -> InitResult:
        """Initialize the workspace if needed and return a stable summary."""
        handle = cls.load_or_init(root)
        created = handle.paths.root.exists() and handle.paths.workspace_json.exists()
        return InitResult(
            workspace=str(handle.root),
            workspace_version=handle.manifest.workspace_version,
            project_id=handle.manifest.project_id,
            current_revision=handle.manifest.current_revision,
            created=created,
        )

    @classmethod
    def load_or_init(cls, root: Path) -> WorkspaceHandle:
        """Load an existing workspace or create a new one in-place."""
        paths = WorkspacePaths(root=root)
        for directory in paths.required_directories():
            directory.mkdir(parents=True, exist_ok=True)

        manifest = cls._load_or_create_manifest(paths)

        if not paths.qrun_toml.exists():
            paths.qrun_toml.write_text(DEFAULT_QRUN_TOML)

        if not paths.trace_events.exists():
            paths.trace_events.write_text("")

        return WorkspaceHandle(
            root=paths.root,
            paths=paths,
            manifest=manifest,
            trace=TraceWriter(paths.trace_events),
        )

    @staticmethod
    def _load_or_create_manifest(paths: WorkspacePaths) -> WorkspaceManifest:
        if paths.workspace_json.exists():
            return WorkspaceManifest.load(paths.workspace_json)

        manifest = WorkspaceManifest.create_default()
        manifest.save(paths.workspace_json)
        return manifest
