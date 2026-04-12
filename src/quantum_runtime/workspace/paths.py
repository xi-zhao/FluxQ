"""Path helpers for workspace layout."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspacePaths:
    """Resolved filesystem paths for a workspace root."""

    root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", self.root.resolve())

    @property
    def workspace_json(self) -> Path:
        return self.root / "workspace.json"

    @property
    def qrun_toml(self) -> Path:
        return self.root / "qrun.toml"

    @property
    def trace_events(self) -> Path:
        return self.root / "trace" / "events.ndjson"

    @property
    def manifests_dir(self) -> Path:
        return self.root / "manifests"

    @property
    def manifests_history_dir(self) -> Path:
        return self.manifests_dir / "history"

    @property
    def manifests_latest_json(self) -> Path:
        return self.manifests_dir / "latest.json"

    def manifest_history_json(self, revision: str) -> Path:
        return self.manifests_history_dir / f"{revision}.json"

    @property
    def baselines_dir(self) -> Path:
        return self.root / "baselines"

    @property
    def baseline_current_json(self) -> Path:
        return self.baselines_dir / "current.json"

    def required_directories(self) -> list[Path]:
        """Return the required directory skeleton for a workspace."""
        return [
            self.root,
            self.baselines_dir,
            self.root / "intents",
            self.root / "intents" / "history",
            self.root / "specs",
            self.root / "specs" / "history",
            self.manifests_dir,
            self.manifests_history_dir,
            self.root / "artifacts",
            self.root / "artifacts" / "history",
            self.root / "artifacts" / "qiskit",
            self.root / "artifacts" / "classiq",
            self.root / "artifacts" / "qasm",
            self.root / "figures",
            self.root / "reports",
            self.root / "reports" / "history",
            self.root / "trace",
            self.root / "cache",
        ]
