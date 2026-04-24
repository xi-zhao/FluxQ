"""Workspace and dependency health checks."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field

from quantum_runtime.errors import WorkspaceConflictError, WorkspaceRecoveryRequiredError
from quantum_runtime.qspec import QSpec
from quantum_runtime.runtime.backend_registry import backend_capabilities_as_dict
from quantum_runtime.runtime.ibm_access import (
    IbmAccessError,
    IbmAccessResolution,
    build_ibm_service,
    resolve_ibm_access,
)
from quantum_runtime.runtime.policy import DoctorPolicy, apply_doctor_policy
from quantum_runtime.workspace import (
    WorkspaceLockConflict,
    WorkspaceManifest,
    WorkspaceManager,
    WorkspacePaths,
    acquire_workspace_lock,
    atomic_write_text,
    pending_atomic_write_files,
)


SCHEMA_VERSION = "0.3.0"


class DoctorReport(BaseModel):
    """Structured diagnostics for CLI health checks."""

    schema_version: str = SCHEMA_VERSION
    status: Literal["ok", "degraded", "error"]
    workspace_ok: bool
    fix_applied: bool = False
    workspace: dict[str, Any]
    dependencies: dict[str, dict[str, Any]]
    issues: list[str]
    advisories: list[str] = Field(default_factory=list)
    blocking_issues: list[str] | None = None
    advisory_issues: list[str] | None = None
    policy: dict[str, Any] | None = None
    verdict: dict[str, Any] | None = None
    reason_codes: list[str] | None = None
    next_actions: list[str] | None = None
    gate: dict[str, Any] | None = None


def run_doctor(
    *,
    workspace_root: Path,
    fix: bool = False,
    ci: bool = False,
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
    ibm_issues, ibm_reason_codes = _ibm_doctor_findings(paths=paths)
    if event_sink is not None:
        event_sink(
            "dependencies_checked",
            {
                "issue_count": len(dependency_issues) + len(ibm_issues),
                "advisory_count": len(dependency_advisories),
            },
            current_revision,
            "ok" if not dependency_issues and not ibm_issues else "degraded",
        )
    all_issues = issues + dependency_issues + ibm_issues
    status: Literal["ok", "degraded", "error"] = "ok" if not all_issues else "degraded"
    report = DoctorReport(
        status=status,
        workspace_ok=workspace_ok,
        fix_applied=fix,
        workspace=_workspace_health(paths, manifest=manifest, current_revision=current_revision),
        dependencies=dependencies,
        issues=all_issues,
        advisories=dependency_advisories,
        reason_codes=ibm_reason_codes if ci and ibm_reason_codes else None,
    )
    if ci:
        report = apply_doctor_policy(
            report=report,
            policy=DoctorPolicy(mode="ci", block_on_issues=True),
        )
    revision = current_revision if current_revision and current_revision != "rev_000000" else None
    if revision is not None:
        written_paths = _persist_doctor_report(workspace_root=paths.root, report=report, revision=revision)
        if event_sink is not None:
            event_sink(
                "doctor_written",
                {"paths": written_paths, "status": report.status},
                current_revision,
                report.status,
            )
    return report


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


def _persist_doctor_report(*, workspace_root: Path, report: DoctorReport, revision: str) -> dict[str, str]:
    doctor_root = workspace_root / "doctor"
    serialized = report.model_dump_json(indent=2, exclude_none=True)
    latest_path = doctor_root / "latest.json"
    history_path = doctor_root / "history" / f"{revision}.json"
    try:
        with acquire_workspace_lock(workspace_root, command="qrun doctor"):
            pending_files = pending_atomic_write_files(latest_path)
            if pending_files:
                raise WorkspaceRecoveryRequiredError(
                    workspace=workspace_root.resolve(),
                    pending_files=pending_files,
                    last_valid_revision=revision,
                )

            doctor_root.mkdir(parents=True, exist_ok=True)
            history_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(latest_path, serialized)
            atomic_write_text(history_path, serialized)
    except WorkspaceLockConflict as exc:
        raise WorkspaceConflictError(
            workspace=workspace_root.resolve(),
            lock_path=Path(exc.lock_path),
            holder=exc.holder.model_dump(mode="json"),
        ) from exc

    return {"latest": str(latest_path), "history": str(history_path)}


def _ibm_doctor_findings(*, paths: WorkspacePaths) -> tuple[list[str], list[str]]:
    if not _workspace_opted_into_ibm(paths.qrun_toml):
        return [], []

    try:
        resolution = resolve_ibm_access(workspace_root=paths.root)
    except Exception:
        reason_code = "ibm_access_unresolved"
        return [_ibm_issue_message(reason_code)], [reason_code]

    if resolution.status != "ok":
        reason_code = _ibm_resolution_reason_code(resolution)
        return [_ibm_issue_message(reason_code, resolution=resolution)], [reason_code]

    try:
        build_ibm_service(resolution=resolution)
    except IbmAccessError as exc:
        reason_code = _ibm_service_reason_code(exc.code, resolution=resolution)
        return [_ibm_issue_message(reason_code, resolution=resolution)], [reason_code]
    except Exception:
        reason_code = (
            "ibm_saved_account_missing"
            if resolution.credential_mode == "saved_account"
            else "ibm_access_unresolved"
        )
        return [_ibm_issue_message(reason_code, resolution=resolution)], [reason_code]

    return [], []


def _workspace_opted_into_ibm(qrun_toml: Path) -> bool:
    if not qrun_toml.exists():
        return False
    raw_toml = qrun_toml.read_text(encoding="utf-8")
    if "[remote.ibm]" not in raw_toml:
        return False
    try:
        payload = tomllib.loads(raw_toml)
    except Exception:
        return True

    remote = payload.get("remote")
    return isinstance(remote, dict) and isinstance(remote.get("ibm"), dict)


def _ibm_resolution_reason_code(resolution: IbmAccessResolution) -> str:
    if resolution.status == "not_configured":
        return "ibm_profile_missing"
    if resolution.error_code in {
        "ibm_profile_missing",
        "ibm_instance_unset",
        "ibm_token_env_missing",
        "ibm_saved_account_missing",
        "ibm_runtime_dependency_missing",
        "ibm_access_unresolved",
    }:
        return resolution.error_code
    if resolution.error_code == "ibm_instance_required":
        return "ibm_instance_unset"
    if resolution.error_code == "ibm_config_invalid":
        if not resolution.credential_mode:
            return "ibm_profile_missing"
        if resolution.credential_mode == "env" and not resolution.token_env:
            return "ibm_profile_missing"
        if resolution.credential_mode == "saved_account" and not resolution.saved_account_name:
            return "ibm_profile_missing"
    return "ibm_access_unresolved"


def _ibm_service_reason_code(error_code: str, *, resolution: IbmAccessResolution) -> str:
    if error_code in {
        "ibm_profile_missing",
        "ibm_instance_unset",
        "ibm_token_env_missing",
        "ibm_saved_account_missing",
        "ibm_runtime_dependency_missing",
        "ibm_access_unresolved",
    }:
        return error_code
    if error_code == "ibm_runtime_dependency_missing":
        return "ibm_runtime_dependency_missing"
    if error_code == "ibm_token_external_required":
        return "ibm_token_env_missing"
    if error_code == "ibm_saved_account_missing":
        return "ibm_saved_account_missing"
    if error_code == "ibm_instance_required":
        return "ibm_instance_unset"
    if error_code == "ibm_config_invalid":
        return _ibm_resolution_reason_code(resolution)
    if resolution.credential_mode == "saved_account":
        return "ibm_saved_account_missing"
    return "ibm_access_unresolved"


def _ibm_issue_message(
    reason_code: str,
    *,
    resolution: IbmAccessResolution | None = None,
) -> str:
    if reason_code == "ibm_profile_missing":
        return "ibm_profile_missing: configure [remote.ibm] with qrun ibm configure"
    if reason_code == "ibm_instance_unset":
        return "ibm_instance_unset: set remote.ibm.instance explicitly"
    if reason_code == "ibm_token_env_missing":
        token_env = resolution.token_env if resolution is not None else None
        token_label = token_env or "the configured IBM token env var"
        return f"ibm_token_env_missing: set {token_label} before running IBM doctor checks"
    if reason_code == "ibm_saved_account_missing":
        saved_account_name = resolution.saved_account_name if resolution is not None else None
        if saved_account_name:
            return f"ibm_saved_account_missing: verify IBM saved account {saved_account_name}"
        return "ibm_saved_account_missing: verify the configured IBM saved account"
    if reason_code == "ibm_runtime_dependency_missing":
        return "ibm_runtime_dependency_missing: install qiskit-ibm-runtime before running IBM doctor checks"
    return "ibm_access_unresolved: verify the configured IBM profile, credential reference, and instance"
