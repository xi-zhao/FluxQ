"""Workspace and dependency health checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field

from quantum_runtime.qspec import QSpec
from quantum_runtime.runtime.backend_registry import backend_capabilities_as_dict
from quantum_runtime.workspace import WorkspaceManifest, WorkspaceManager, WorkspacePaths


class DoctorReport(BaseModel):
    """Structured diagnostics for CLI health checks."""

    status: Literal["ok", "degraded", "error"]
    workspace_ok: bool
    fix_applied: bool = False
    workspace: dict[str, Any]
    dependencies: dict[str, dict[str, Any]]
    issues: list[str]
    advisories: list[str] = Field(default_factory=list)


def run_doctor(
    *,
    workspace_root: Path,
    fix: bool = False,
    event_sink: Callable[[str, dict[str, Any], str | None, str], None] | None = None,
) -> DoctorReport:
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
    if event_sink is not None:
        event_sink(
            "workspace_checked",
            {"workspace_ok": workspace_ok, "issue_count": len(issues)},
            current_revision,
            "ok" if workspace_ok else "degraded",
        )

    dependencies = collect_backend_capabilities()
    required_backends = _required_backend_names(paths, manifest=manifest)
    dependency_issues, dependency_advisories = _dependency_findings(
        dependencies=dependencies,
        required_backends=required_backends,
    )
    if event_sink is not None:
        event_sink(
            "dependencies_checked",
            {
                "issue_count": len(dependency_issues),
                "advisory_count": len(dependency_advisories),
            },
            current_revision,
            "ok" if not dependency_issues else "degraded",
        )
    all_issues = issues + dependency_issues
    status: Literal["ok", "degraded", "error"] = "ok" if not all_issues else "degraded"

    return DoctorReport(
        status=status,
        workspace_ok=workspace_ok,
        fix_applied=fix,
        workspace=_workspace_health(paths, manifest=manifest, current_revision=current_revision),
        dependencies=dependencies,
        issues=all_issues,
        advisories=dependency_advisories,
    )


def collect_backend_capabilities() -> dict[str, dict[str, Any]]:
    """Return backend descriptors plus legacy dependency aliases for compatibility."""
    capabilities = backend_capabilities_as_dict()
    legacy_dependencies: dict[str, dict[str, Any]] = {}

    qiskit_local = capabilities.get("qiskit-local", {})
    module_dependencies = qiskit_local.get("module_dependencies", [])
    if isinstance(module_dependencies, list):
        for dependency in module_dependencies:
            if not isinstance(dependency, dict):
                continue
            module_name = dependency.get("module")
            if isinstance(module_name, str) and module_name not in capabilities:
                legacy_dependencies[module_name] = dependency

    return {**legacy_dependencies, **capabilities}


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


def _dependency_findings(
    *,
    dependencies: dict[str, dict[str, Any]],
    required_backends: set[str],
) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    advisories: list[str] = []
    for name, details in dependencies.items():
        if details.get("available"):
            continue
        message = f"{name} unavailable: {details.get('reason') or details.get('error') or 'backend_unavailable'}"
        if _is_optional_backend(details) and name not in required_backends:
            advisories.append(message)
        else:
            issues.append(message)
    return issues, advisories


def _required_backend_names(paths: WorkspacePaths, *, manifest: WorkspaceManifest | None) -> set[str]:
    if manifest is None or manifest.current_revision == "rev_000000":
        return set()
    active_spec_path = paths.root / manifest.active_spec
    if not active_spec_path.exists():
        return set()
    try:
        qspec = QSpec.model_validate_json(active_spec_path.read_text())
    except Exception:
        return set()

    required = {name for name in qspec.backend_preferences if name}
    backend_name = qspec.constraints.backend_name
    if backend_name:
        required.add(backend_name)
    backend_provider = qspec.constraints.backend_provider
    if backend_provider == "classiq":
        required.add("classiq")
    if backend_provider == "qiskit":
        required.add("qiskit-local")
    return required


def _is_optional_backend(details: dict[str, Any]) -> bool:
    raw = details.get("optional")
    return bool(raw)


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
