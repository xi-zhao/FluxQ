"""Workspace initialization and loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from .locking import acquire_workspace_lock
from .manifest import WorkspaceManifest, atomic_write_text
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

    def reserve_revision(self, *, assume_locked: bool = False) -> str:
        """Advance the workspace revision and persist the manifest."""
        if assume_locked:
            manifest = WorkspaceManifest.load(self.paths.workspace_json)
            revision = manifest.bump_revision()
            manifest.save(self.paths.workspace_json)
        else:
            with acquire_workspace_lock(self.paths.root):
                manifest = WorkspaceManifest.load(self.paths.workspace_json)
                revision = manifest.bump_revision()
                manifest.save(self.paths.workspace_json)

        self.manifest = manifest
        return revision

    def reserve_attempt(self, *, assume_locked: bool = False) -> str:
        """Advance the remote-attempt identity and persist the manifest."""
        if assume_locked:
            manifest = WorkspaceManifest.load(self.paths.workspace_json)
            attempt_id = manifest.bump_attempt()
            manifest.save(self.paths.workspace_json)
        else:
            with acquire_workspace_lock(self.paths.root):
                manifest = WorkspaceManifest.load(self.paths.workspace_json)
                attempt_id = manifest.bump_attempt()
                manifest.save(self.paths.workspace_json)

        self.manifest = manifest
        return attempt_id


class WorkspaceManager:
    """Create and load the deterministic workspace layout."""

    @classmethod
    def init_workspace(cls, root: Path) -> InitResult:
        """Initialize the workspace if needed and return a stable summary."""
        workspace_json = WorkspacePaths(root=root).workspace_json
        created = not workspace_json.exists()
        handle = cls.load_or_init(root)
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
        paths.root.mkdir(parents=True, exist_ok=True)

        with acquire_workspace_lock(paths.root):
            for directory in paths.required_directories():
                directory.mkdir(parents=True, exist_ok=True)

            manifest = cls._load_or_create_manifest(paths)
            cls._seed_bootstrap_file(paths.qrun_toml, DEFAULT_QRUN_TOML)
            cls._seed_bootstrap_file(paths.trace_events, "")
            cls._seed_bootstrap_file(paths.events_jsonl, "")

        return WorkspaceHandle(
            root=paths.root,
            paths=paths,
            manifest=manifest,
            trace=TraceWriter(paths.trace_events, paths.events_jsonl),
        )

    @staticmethod
    def _load_or_create_manifest(paths: WorkspacePaths) -> WorkspaceManifest:
        if paths.workspace_json.exists():
            return WorkspaceManifest.load(paths.workspace_json)

        manifest = WorkspaceManifest.create_default()
        manifest.save(paths.workspace_json)
        return manifest

    @staticmethod
    def _seed_bootstrap_file(path: Path, content: str) -> None:
        if path.exists():
            return

        atomic_write_text(path, content)
