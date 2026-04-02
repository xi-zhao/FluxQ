"""Workspace inspection helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from quantum_runtime.qspec import QSpec
from quantum_runtime.runtime.doctor import collect_backend_capabilities
from quantum_runtime.workspace import WorkspaceManifest, WorkspacePaths


class InspectReport(BaseModel):
    """Stable workspace summary for debugging and host inspection."""

    revision: str
    qspec: dict[str, Any]
    artifacts: dict[str, Any] = Field(default_factory=dict)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    backend_capabilities: dict[str, dict[str, Any]] = Field(default_factory=dict)


def inspect_workspace(workspace_root: Path) -> InspectReport:
    """Read the current workspace state into a compact inspection payload."""
    paths = WorkspacePaths(root=workspace_root)
    manifest = WorkspaceManifest.load(paths.workspace_json)
    qspec = QSpec.model_validate_json((workspace_root / manifest.active_spec).read_text())
    latest_report_path = workspace_root / manifest.active_report
    latest_report = json.loads(latest_report_path.read_text()) if latest_report_path.exists() else {}

    return InspectReport(
        revision=manifest.current_revision,
        qspec={
            "goal": qspec.goal,
            "program_id": qspec.program_id,
            "registers": {
                "qubits": qspec.registers[0].size,
                "cbits": qspec.registers[1].size,
            },
            "body_nodes": len(qspec.body),
        },
        artifacts=latest_report.get("artifacts", {}),
        diagnostics=latest_report.get("diagnostics", {}),
        backend_capabilities=collect_backend_capabilities(),
    )
