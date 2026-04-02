"""Workspace and dependency health checks."""

from __future__ import annotations

import importlib
from importlib import metadata
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from quantum_runtime.qspec import QSpec
from quantum_runtime.workspace import WorkspaceManifest, WorkspaceManager, WorkspacePaths


class DoctorReport(BaseModel):
    """Structured diagnostics for CLI health checks."""

    status: Literal["ok", "degraded", "error"]
    workspace_ok: bool
    fix_applied: bool = False
    workspace: dict[str, Any]
    dependencies: dict[str, dict[str, Any]]
    issues: list[str]


def run_doctor(*, workspace_root: Path, fix: bool = False) -> DoctorReport:
    """Check workspace integrity and optional dependency availability."""
    current_revision = None
    manifest = None
    if fix:
        handle = WorkspaceManager.load_or_init(workspace_root)
        paths = handle.paths
        manifest = handle.manifest
        current_revision = manifest.current_revision
        workspace_ok = True
        issues = _workspace_issues(paths, manifest=manifest)
    else:
        paths = WorkspacePaths(root=workspace_root)
        manifest = _load_manifest(paths)
        if manifest is not None:
            current_revision = manifest.current_revision
        issues = _workspace_issues(paths, manifest=manifest)
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
        workspace=_workspace_health(paths, manifest=manifest, current_revision=current_revision),
        dependencies=dependencies,
        issues=all_issues,
    )


def collect_backend_capabilities() -> dict[str, dict[str, Any]]:
    """Return import availability for key runtime backends."""
    return {
        "qiskit": _dependency_metadata(module_name="qiskit", distribution_name="qiskit"),
        "qiskit_aer": _dependency_metadata(module_name="qiskit_aer", distribution_name="qiskit-aer"),
        "classiq": _dependency_metadata(module_name="classiq", distribution_name="classiq"),
    }


def _workspace_issues(paths: WorkspacePaths, *, manifest: WorkspaceManifest | None) -> list[str]:
    issues: list[str] = []
    if not paths.root.exists():
        issues.append("workspace_root_missing")
        return issues

    manifest_path = paths.workspace_json
    if manifest is None:
        if not manifest_path.exists():
            issues.append("workspace_manifest_missing")
        else:
            issues.append("workspace_manifest_invalid")

    required_active_artifacts = bool(
        manifest is not None and manifest.current_revision != "rev_000000"
    )
    if required_active_artifacts:
        assert manifest is not None
        active_spec_status = _check_file(paths.root / manifest.active_spec, kind="file", parse_qspec=True)
        active_report_status = _check_file(paths.root / manifest.active_report, kind="file", parse_json=True)
        if active_spec_status["status"] != "ok":
            issues.append(f"active_spec_{active_spec_status['status']}")
        if active_report_status["status"] != "ok":
            issues.append(f"active_report_{active_report_status['status']}")

    missing_directories = [
        str(path)
        for path in paths.required_directories()
        if not path.exists()
    ]
    if missing_directories:
        issues.append("missing_directories:" + ",".join(missing_directories))
    return issues


def _check_import(module_name: str) -> dict[str, Any]:
    try:
        importlib.import_module(module_name)
    except Exception as exc:
        return {
            "module": module_name,
            "available": False,
            "version": None,
            "location": None,
            "error": str(exc),
        }
    return {
        "module": module_name,
        "available": True,
        "version": _dependency_version(module_name),
        "location": _module_location(module_name),
        "error": None,
    }


def _dependency_metadata(*, module_name: str, distribution_name: str) -> dict[str, Any]:
    metadata_report = _check_import(module_name)
    metadata_report["distribution"] = distribution_name
    if metadata_report.get("available"):
        metadata_report["version"] = _dependency_version(distribution_name)
        metadata_report["location"] = _module_location(module_name)
    else:
        metadata_report.setdefault("version", None)
        metadata_report.setdefault("location", None)
    return metadata_report


def _dependency_version(distribution_name: str) -> str | None:
    try:
        return metadata.version(distribution_name)
    except metadata.PackageNotFoundError:
        return None


def _module_location(module_name: str) -> str | None:
    try:
        module = importlib.import_module(module_name)
    except Exception:
        return None
    return getattr(module, "__file__", None)


def _load_manifest(paths: WorkspacePaths) -> WorkspaceManifest | None:
    if not paths.workspace_json.exists():
        return None
    try:
        return WorkspaceManifest.load(paths.workspace_json)
    except Exception:
        return None


def _workspace_health(
    paths: WorkspacePaths,
    *,
    manifest: WorkspaceManifest | None,
    current_revision: str | None,
) -> dict[str, Any]:
    required_active_artifacts = bool(manifest and current_revision != "rev_000000")
    active_spec_path = (
        paths.root / manifest.active_spec if manifest is not None else paths.root / "specs" / "current.json"
    )
    active_report_path = (
        paths.root / manifest.active_report if manifest is not None else paths.root / "reports" / "latest.json"
    )
    return {
        "root": str(paths.root),
        "root_exists": paths.root.exists(),
        "current_revision": current_revision,
        "required_active_artifacts": required_active_artifacts,
        "manifest": _check_file(paths.workspace_json, kind="file", parse_json=True),
        "active_spec": _check_file(active_spec_path, kind="file", parse_qspec=True),
        "active_report": _check_file(active_report_path, kind="file", parse_json=True),
        "directories": {
            "intents": _check_path(paths.root / "intents", kind="directory"),
            "intents_history": _check_path(paths.root / "intents" / "history", kind="directory"),
            "specs": _check_path(paths.root / "specs", kind="directory"),
            "specs_history": _check_path(paths.root / "specs" / "history", kind="directory"),
            "artifacts": _check_path(paths.root / "artifacts", kind="directory"),
            "artifacts_qiskit": _check_path(paths.root / "artifacts" / "qiskit", kind="directory"),
            "artifacts_classiq": _check_path(paths.root / "artifacts" / "classiq", kind="directory"),
            "artifacts_qasm": _check_path(paths.root / "artifacts" / "qasm", kind="directory"),
            "figures": _check_path(paths.root / "figures", kind="directory"),
            "reports": _check_path(paths.root / "reports", kind="directory"),
            "reports_history": _check_path(paths.root / "reports" / "history", kind="directory"),
            "trace": _check_path(paths.root / "trace", kind="directory"),
            "cache": _check_path(paths.root / "cache", kind="directory"),
        },
    }


def _check_path(path: Path, *, kind: Literal["file", "directory"]) -> dict[str, Any]:
    exists = path.exists()
    return {
        "path": str(path),
        "kind": kind,
        "exists": exists,
        "status": "ok" if exists else "missing",
        "error": None,
    }


def _check_file(
    path: Path,
    *,
    kind: Literal["file", "directory"],
    parse_json: bool = False,
    parse_qspec: bool = False,
) -> dict[str, Any]:
    check = _check_path(path, kind=kind)
    if not check["exists"]:
        return check
    try:
        if parse_json:
            import json

            json.loads(path.read_text())
        elif parse_qspec:
            QSpec.model_validate_json(path.read_text())
    except Exception as exc:
        check["status"] = "invalid"
        check["error"] = str(exc)
    return check
