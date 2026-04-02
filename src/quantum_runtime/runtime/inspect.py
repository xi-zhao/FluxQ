"""Workspace inspection helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from quantum_runtime.qspec import QSpec, summarize_qspec_semantics
from quantum_runtime.runtime.doctor import collect_backend_capabilities
from quantum_runtime.workspace import WorkspaceManifest, WorkspacePaths


class InspectReport(BaseModel):
    """Stable workspace summary for debugging and host inspection."""

    status: Literal["ok", "degraded", "error"]
    revision: str
    workspace: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
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
    revision = manifest.current_revision if manifest is not None else "unknown"

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
    provenance = _build_provenance(
        latest_report=latest_report,
        workspace_root=workspace_root,
        revision=revision,
        active_spec_path=active_spec_path,
        active_report_path=active_report_path,
    )

    status: Literal["ok", "degraded", "error"] = "error" if errors else "degraded" if issues else "ok"

    return InspectReport(
        status=status,
        revision=revision,
        workspace=workspace_info,
        provenance=provenance,
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

    semantics = summarize_qspec_semantics(qspec)
    return (
        {
            "status": "ok",
            "path": str(path),
            "goal": qspec.goal,
            "program_id": qspec.program_id,
            "pattern": semantics["pattern"],
            "layers": semantics["layers"],
            "parameter_count": semantics["parameter_count"],
            "semantic_hash": semantics["semantic_hash"],
            "registers": {
                "qubits": qspec.registers[0].size,
                "cbits": qspec.registers[1].size,
            },
            "parameters": semantics["parameters"],
            "pattern_args": semantics["pattern_args"],
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


def _build_provenance(
    *,
    latest_report: dict[str, Any],
    workspace_root: Path,
    revision: str,
    active_spec_path: Path,
    active_report_path: Path,
) -> dict[str, Any]:
    """Return a stable provenance block for inspect output."""
    provenance: dict[str, Any] = {}
    if isinstance(latest_report, dict):
        nested = latest_report.get("provenance")
        if isinstance(nested, dict):
            provenance.update(nested)

    provenance.setdefault("workspace_root", str(workspace_root))
    provenance.setdefault("revision", revision)
    provenance.setdefault(
        "input",
        {
            "mode": "report",
            "path": str(active_report_path),
        },
    )
    provenance.setdefault(
        "report",
        {
            "path": str(active_report_path),
        },
    )
    provenance.setdefault(
        "qspec",
        _inspect_qspec_provenance(latest_report=latest_report, active_spec_path=active_spec_path),
    )
    provenance.setdefault(
        "subject",
        _inspect_subject_provenance(latest_report=latest_report),
    )
    provenance["artifacts"] = _inspect_artifact_provenance(
        latest_report=latest_report,
        workspace_root=workspace_root,
        revision=revision,
    )
    return provenance


def _inspect_qspec_provenance(*, latest_report: dict[str, Any], active_spec_path: Path) -> dict[str, Any]:
    semantic_hash = None
    nested_qspec = latest_report.get("qspec")
    if isinstance(nested_qspec, dict):
        semantic_hash = nested_qspec.get("semantic_hash")

    payload: dict[str, Any] = {"path": str(active_spec_path)}
    if semantic_hash is not None:
        payload["semantic_hash"] = semantic_hash
    return payload


def _inspect_subject_provenance(*, latest_report: dict[str, Any]) -> dict[str, Any]:
    nested_provenance = latest_report.get("provenance")
    if isinstance(nested_provenance, dict):
        subject = nested_provenance.get("subject")
        if isinstance(subject, dict):
            return subject
    return {}


def _inspect_artifact_provenance(
    *,
    latest_report: dict[str, Any],
    workspace_root: Path,
    revision: str,
) -> dict[str, Any]:
    snapshot_root = workspace_root / "artifacts" / "history" / revision
    current_root = workspace_root / "artifacts"
    paths: dict[str, str] = {}
    current_aliases: dict[str, str] = {}
    artifacts = latest_report.get("artifacts")
    if isinstance(artifacts, dict):
        for name, raw_path in artifacts.items():
            if not isinstance(raw_path, str) or not raw_path.strip():
                continue
            artifact_path = Path(raw_path)
            alias_path = _derive_current_artifact_alias(
                name=str(name),
                artifact_path=artifact_path,
                workspace_root=workspace_root,
                revision=revision,
                snapshot_root=snapshot_root,
                current_root=current_root,
            )
            if alias_path is None:
                continue
            paths[str(name)] = str(artifact_path)
            current_aliases[str(name)] = str(alias_path)

    reconstructed = {
        "snapshot_root": str(snapshot_root),
        "current_root": str(current_root),
        "paths": paths,
        "current_aliases": current_aliases,
    }
    nested_provenance = latest_report.get("provenance")
    if isinstance(nested_provenance, dict):
        artifact_provenance = nested_provenance.get("artifacts")
        if isinstance(artifact_provenance, dict):
            merged_paths = dict(reconstructed["paths"])
            merged_paths.update(artifact_provenance.get("paths", {}))
            merged_aliases = dict(reconstructed["current_aliases"])
            merged_aliases.update(artifact_provenance.get("current_aliases", {}))
            return {
                "snapshot_root": artifact_provenance.get("snapshot_root", reconstructed["snapshot_root"]),
                "current_root": artifact_provenance.get("current_root", reconstructed["current_root"]),
                "paths": merged_paths,
                "current_aliases": merged_aliases,
            }
    return reconstructed


def _derive_current_artifact_alias(
    *,
    name: str,
    artifact_path: Path,
    workspace_root: Path,
    revision: str,
    snapshot_root: Path,
    current_root: Path,
) -> Path | None:
    if name == "qspec":
        if artifact_path == workspace_root / "specs" / "current.json":
            return artifact_path
        if artifact_path == workspace_root / "specs" / "history" / f"{revision}.json":
            return workspace_root / "specs" / "current.json"
    if name == "report":
        if artifact_path == workspace_root / "reports" / "latest.json":
            return artifact_path
        if artifact_path == workspace_root / "reports" / "history" / f"{revision}.json":
            return workspace_root / "reports" / "latest.json"

    if artifact_path.is_absolute():
        if artifact_path.is_relative_to(snapshot_root):
            return current_root / artifact_path.relative_to(snapshot_root)
        if artifact_path.is_relative_to(current_root):
            return artifact_path
        return None

    if artifact_path.parts[:3] == ("artifacts", "history", snapshot_root.name):
        return current_root / Path(*artifact_path.parts[3:])
    if artifact_path.parts[:1] == ("artifacts",):
        return artifact_path
    return None
