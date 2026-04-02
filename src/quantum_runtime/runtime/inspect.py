"""Workspace inspection helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from quantum_runtime.qspec import QSpec
from quantum_runtime.runtime.doctor import collect_backend_capabilities
from quantum_runtime.workspace import WorkspaceManifest, WorkspacePaths


class InspectReport(BaseModel):
    """Stable workspace summary for debugging and host inspection."""

    status: Literal["ok", "degraded", "error"]
    revision: str
    workspace: dict[str, Any] = Field(default_factory=dict)
    qspec: dict[str, Any]
    artifacts: dict[str, Any] = Field(default_factory=dict)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    backend_capabilities: dict[str, dict[str, Any]] = Field(default_factory=dict)
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


def inspect_workspace(workspace_root: Path) -> InspectReport:
    """Read the current workspace state into a compact inspection payload."""
    paths = WorkspacePaths(root=workspace_root)
    issues: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []
    workspace_info: dict[str, Any] = {
        "root": str(workspace_root),
        "exists": workspace_root.exists(),
        "manifest_path": str(paths.workspace_json),
    }

    manifest: WorkspaceManifest | None = None
    if paths.workspace_json.exists():
        try:
            manifest = WorkspaceManifest.load(paths.workspace_json)
        except Exception as exc:
            errors.append("workspace_manifest_invalid_json")
            workspace_info["manifest_error"] = str(exc)
    else:
        issues.append("workspace_manifest_missing")

    active_spec_rel = manifest.active_spec if manifest is not None else "specs/current.json"
    active_report_rel = manifest.active_report if manifest is not None else "reports/latest.json"
    active_spec_path = workspace_root / active_spec_rel
    active_report_path = workspace_root / active_report_rel

    workspace_info.update(
        {
            "current_revision": manifest.current_revision if manifest is not None else "unknown",
            "active_spec_path": str(active_spec_path),
            "active_report_path": str(active_report_path),
        }
    )

    if workspace_root.exists():
        missing_directories = [str(path) for path in paths.required_directories() if not path.exists()]
        if missing_directories:
            issues.append("missing_directories:" + ",".join(missing_directories))
    else:
        errors.append("workspace_root_missing")

    qspec_summary, qspec_errors = _load_qspec_summary(active_spec_path)
    errors.extend(qspec_errors)
    if not active_spec_path.exists():
        issues.append("active_spec_missing")

    latest_report, report_issues, report_errors = _load_report_payload(active_report_path)
    issues.extend(report_issues)
    errors.extend(report_errors)

    status: Literal["ok", "degraded", "error"] = "error" if errors else "degraded" if issues else "ok"
    revision = manifest.current_revision if manifest is not None else "unknown"

    return InspectReport(
        status=status,
        revision=revision,
        workspace=workspace_info,
        qspec=qspec_summary,
        artifacts=latest_report.get("artifacts", {}) if isinstance(latest_report, dict) else {},
        diagnostics=latest_report.get("diagnostics", {}) if isinstance(latest_report, dict) else {},
        backend_capabilities=collect_backend_capabilities(),
        issues=issues,
        warnings=warnings,
        errors=errors,
    )


def _load_qspec_summary(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {"status": "missing", "path": str(path)}, []

    try:
        qspec = QSpec.model_validate_json(path.read_text())
    except ValidationError:
        return {"status": "error", "path": str(path)}, ["active_spec_invalid_json"]
    except json.JSONDecodeError:
        return {"status": "error", "path": str(path)}, ["active_spec_invalid_json"]

    return (
        {
            "status": "ok",
            "path": str(path),
            "goal": qspec.goal,
            "program_id": qspec.program_id,
            "registers": {
                "qubits": qspec.registers[0].size,
                "cbits": qspec.registers[1].size,
            },
            "body_nodes": len(qspec.body),
        },
        [],
    )


def _load_report_payload(path: Path) -> tuple[dict[str, Any], list[str], list[str]]:
    if not path.exists():
        return {}, ["active_report_missing"], []

    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}, [], ["active_report_invalid_json"]

    if not isinstance(payload, dict):
        return {}, [], ["active_report_invalid_json"]

    return payload, [], []
