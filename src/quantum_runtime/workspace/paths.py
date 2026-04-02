"""Path helpers for workspace layout."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspacePaths:
    """Resolved filesystem paths for a workspace root."""

    root: Path

    @property
    def workspace_json(self) -> Path:
        return self.root / "workspace.json"

    @property
    def qrun_toml(self) -> Path:
        return self.root / "qrun.toml"

    @property
    def trace_events(self) -> Path:
        return self.root / "trace" / "events.ndjson"

    def required_directories(self) -> list[Path]:
        """Return the required directory skeleton for a workspace."""
        return [
            self.root,
            self.root / "intents",
            self.root / "intents" / "history",
            self.root / "specs",
            self.root / "specs" / "history",
            self.root / "artifacts",
            self.root / "artifacts" / "qiskit",
            self.root / "artifacts" / "classiq",
            self.root / "artifacts" / "qasm",
            self.root / "figures",
            self.root / "reports",
            self.root / "reports" / "history",
            self.root / "trace",
            self.root / "cache",
        ]
