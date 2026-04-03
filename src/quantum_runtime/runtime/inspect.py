"""Workspace inspection helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from quantum_runtime.artifact_provenance import (
    ArtifactProvenanceMismatch,
    canonicalize_artifact_provenance,
    select_accessible_artifact_paths,
)
from quantum_runtime.qspec import QSpec, summarize_qspec_semantics
from quantum_runtime.runtime.compare import compare_workspace_baseline
from quantum_runtime.runtime.doctor import collect_backend_capabilities
from quantum_runtime.runtime.imports import (
    ImportSourceError,
    resolve_report_file,
    resolve_workspace_baseline,
)
from quantum_runtime.workspace import WorkspaceBaseline, WorkspaceManifest, WorkspacePaths


class InspectReport(BaseModel):
    """Stable workspace summary for debugging and host inspection."""

    status: Literal["ok", "degraded", "error"]
    revision: str
    workspace: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    qspec: dict[str, Any]
    artifacts: dict[str, Any] = Field(default_factory=dict)
    baseline: dict[str, Any] = Field(default_factory=dict)
    replay_integrity: dict[str, Any] = Field(default_factory=dict)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    backend_capabilities: dict[str, dict[str, Any]] = Field(default_factory=dict)
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


def inspect_workspace(workspace_root: Path) -> InspectReport:
    """Read the current workspace state into a compact inspection payload."""
    paths = WorkspacePaths(root=workspace_root)
    normalized_root = paths.root
    issues: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []
    workspace_info: dict[str, Any] = {
        "root": str(normalized_root),
        "exists": normalized_root.exists(),
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
    active_spec_path = normalized_root / active_spec_rel
    active_report_path = normalized_root / active_report_rel

    workspace_info.update(
        {
            "current_revision": manifest.current_revision if manifest is not None else "unknown",
            "active_spec_path": str(active_spec_path),
            "active_report_path": str(active_report_path),
        }
    )
    revision = manifest.current_revision if manifest is not None else "unknown"

    if normalized_root.exists():
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
    provenance, canonical_artifacts, provenance_errors = _safe_build_provenance(
        latest_report=latest_report,
        workspace_root=normalized_root,
        revision=revision,
        active_spec_path=active_spec_path,
        active_report_path=active_report_path,
    )
    errors.extend(provenance_errors)
    replay_integrity, replay_issues, replay_errors = _load_replay_integrity(
        active_report_path=active_report_path,
        workspace_root=normalized_root,
    )
    issues.extend(replay_issues)
    errors.extend(replay_errors)
    baseline, baseline_issues = _load_baseline_summary(workspace_root=normalized_root)
    issues.extend(baseline_issues)

    status: Literal["ok", "degraded", "error"] = "error" if errors else "degraded" if issues else "ok"

    return InspectReport(
        status=status,
        revision=revision,
        workspace=workspace_info,
        provenance=provenance,
        qspec=qspec_summary,
        artifacts=canonical_artifacts,
        baseline=baseline,
        replay_integrity=replay_integrity,
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


def _safe_build_provenance(
    *,
    latest_report: dict[str, Any],
    workspace_root: Path,
    revision: str,
    active_spec_path: Path,
    active_report_path: Path,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    try:
        provenance = _build_provenance(
            latest_report=latest_report,
            workspace_root=workspace_root,
            revision=revision,
            active_spec_path=active_spec_path,
            active_report_path=active_report_path,
        )
        raw_artifact_provenance = provenance.get("artifacts") if isinstance(provenance, dict) else {}
        artifact_provenance = raw_artifact_provenance if isinstance(raw_artifact_provenance, dict) else {}
        return provenance, select_accessible_artifact_paths(artifact_provenance), []
    except ArtifactProvenanceMismatch:
        sanitized_report = dict(latest_report)
        sanitized_report.pop("artifacts", None)
        nested_provenance = sanitized_report.get("provenance")
        if isinstance(nested_provenance, dict):
            sanitized_nested = dict(nested_provenance)
            sanitized_nested.pop("artifacts", None)
            sanitized_report["provenance"] = sanitized_nested
        provenance = _build_provenance(
            latest_report=sanitized_report,
            workspace_root=workspace_root,
            revision=revision,
            active_spec_path=active_spec_path,
            active_report_path=active_report_path,
        )
        raw_artifact_provenance = provenance.get("artifacts") if isinstance(provenance, dict) else {}
        artifact_provenance = raw_artifact_provenance if isinstance(raw_artifact_provenance, dict) else {}
        return provenance, select_accessible_artifact_paths(artifact_provenance), ["artifact_provenance_invalid"]


def _load_replay_integrity(
    *,
    active_report_path: Path,
    workspace_root: Path,
) -> tuple[dict[str, Any], list[str], list[str]]:
    if not active_report_path.exists():
        return {}, [], []
    try:
        resolution = resolve_report_file(active_report_path, workspace_root=workspace_root)
    except ImportSourceError as exc:
        return (
            {
                "status": "error",
                "reason": exc.code,
                "warnings": [],
                "errors": [exc.code],
            },
            [],
            [exc.code],
        )

    replay_integrity = (
        resolution.replay_integrity
        if isinstance(resolution.replay_integrity, dict)
        else {}
    )
    status = replay_integrity.get("status")
    issues: list[str] = []
    if status == "legacy":
        issues.append("replay_integrity_legacy")
    elif status == "degraded":
        issues.append("replay_integrity_degraded")
    return replay_integrity, issues, []


def _load_baseline_summary(*, workspace_root: Path) -> tuple[dict[str, Any], list[str]]:
    record_path = WorkspacePaths(root=workspace_root).baseline_current_json.resolve()
    if not record_path.exists():
        return {
            "status": "not_set",
            "path": str(record_path),
        }, []

    metadata = _load_baseline_record_metadata(record_path)
    try:
        baseline_resolution = resolve_workspace_baseline(workspace_root)
        comparison = compare_workspace_baseline(workspace_root)
    except ImportSourceError as exc:
        payload = {
            "status": "degraded",
            "path": str(record_path),
            "reason": exc.code,
        }
        payload.update(metadata)
        return payload, [f"baseline_invalid:{exc.code}"]

    return {
        "status": "ok",
        "path": str(record_path),
        "source_kind": baseline_resolution.record.source_kind,
        "source": baseline_resolution.record.source,
        "revision": baseline_resolution.record.revision,
        "same_subject": comparison.same_subject,
        "same_qspec": comparison.same_qspec,
        "same_report": comparison.same_report,
        "compare_status": comparison.status,
        "highlight": comparison.highlights[0] if comparison.highlights else None,
    }, []


def _load_baseline_record_metadata(record_path: Path) -> dict[str, Any]:
    try:
        record = WorkspaceBaseline.load(record_path)
    except Exception:
        return {}

    return {
        "source_kind": record.source_kind,
        "source": record.source,
        "revision": record.revision,
    }


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
    nested_provenance = latest_report.get("provenance")
    stored_artifact_provenance = nested_provenance.get("artifacts") if isinstance(nested_provenance, dict) else None
    return canonicalize_artifact_provenance(
        workspace_root=workspace_root,
        revision=revision,
        artifacts=latest_report.get("artifacts"),
        stored_provenance=stored_artifact_provenance,
    )
