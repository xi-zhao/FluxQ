"""Workspace and dependency health checks."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from quantum_runtime.workspace import WorkspaceManager, WorkspacePaths


class DoctorReport(BaseModel):
    """Structured diagnostics for CLI health checks."""

    status: Literal["ok", "degraded", "error"]
    workspace_ok: bool
    fix_applied: bool = False
    dependencies: dict[str, dict[str, Any]]
    issues: list[str]


def run_doctor(*, workspace_root: Path, fix: bool = False) -> DoctorReport:
    """Check workspace integrity and optional dependency availability."""
    if fix:
        handle = WorkspaceManager.load_or_init(workspace_root)
        paths = handle.paths
        workspace_ok = True
        issues: list[str] = []
    else:
        paths = WorkspacePaths(root=workspace_root)
        issues = _workspace_issues(paths)
        workspace_ok = not issues

    dependencies = collect_backend_capabilities()
    dependency_issues = [
        f"{name} unavailable: {details['error']}"
        for name, details in dependencies.items()
        if not details["available"]
    ]
    all_issues = issues + dependency_issues
    status: Literal["ok", "degraded", "error"] = "ok" if not all_issues else "degraded"

    return DoctorReport(
        status=status,
        workspace_ok=workspace_ok,
        fix_applied=fix,
        dependencies=dependencies,
        issues=all_issues,
    )


def collect_backend_capabilities() -> dict[str, dict[str, Any]]:
    """Return import availability for key runtime backends."""
    return {
        "qiskit": _check_import("qiskit"),
        "qiskit_aer": _check_import("qiskit_aer"),
        "classiq": _check_import("classiq"),
    }


def _workspace_issues(paths: WorkspacePaths) -> list[str]:
    issues: list[str] = []
    if not paths.root.exists():
        issues.append("workspace_root_missing")
        return issues
    if not paths.workspace_json.exists():
        issues.append("workspace_manifest_missing")
    missing_directories = [str(path) for path in paths.required_directories() if not path.exists()]
    if missing_directories:
        issues.append("missing_directories:" + ",".join(missing_directories))
    return issues


def _check_import(module_name: str) -> dict[str, Any]:
    try:
        importlib.import_module(module_name)
    except Exception as exc:
        return {"module": module_name, "available": False, "error": str(exc)}
    return {"module": module_name, "available": True, "error": None}
