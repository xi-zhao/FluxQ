"""Write stable report artifacts into the workspace."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from quantum_runtime.qspec import QSpec, summarize_qspec_semantics
from quantum_runtime.workspace.manager import WorkspaceHandle


def write_report(
    *,
    workspace: WorkspaceHandle,
    revision: str,
    input_data: dict[str, Any],
    qspec: QSpec,
    qspec_path: Path,
    artifacts: dict[str, Any],
    diagnostics: dict[str, Any],
    backend_reports: dict[str, Any],
    warnings: list[str],
    errors: list[str],
) -> dict[str, Any]:
    """Write `reports/latest.json` and a revision history copy."""
    semantics = summarize_qspec_semantics(qspec)
    status = _derive_report_status(
        warnings=warnings,
        errors=errors,
        backend_reports=backend_reports,
    )
    payload: dict[str, Any] = {
        "status": status,
        "revision": revision,
        "input": input_data,
        "provenance": _build_provenance(
            workspace=workspace,
            revision=revision,
            input_data=input_data,
            qspec_path=qspec_path,
            semantics=semantics,
            artifacts=artifacts,
        ),
        "qspec": {
            "path": str(qspec_path),
            "hash": _sha256_file(qspec_path),
            "semantic_hash": semantics["semantic_hash"],
        },
        "semantics": semantics,
        "artifacts": artifacts,
        "diagnostics": diagnostics,
        "backend_reports": backend_reports,
        "warnings": warnings,
        "errors": errors,
        "suggestions": _build_suggestions(
            warnings=warnings,
            errors=errors,
            backend_reports=backend_reports,
        ),
    }

    latest_path = workspace.root / "reports" / "latest.json"
    history_path = workspace.root / "reports" / "history" / f"{revision}.json"
    serialized = json.dumps(payload, indent=2, ensure_ascii=True)
    latest_path.write_text(serialized)
    history_path.write_text(serialized)
    return payload


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _build_provenance(
    *,
    workspace: WorkspaceHandle,
    revision: str,
    input_data: dict[str, Any],
    qspec_path: Path,
    semantics: dict[str, Any],
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    """Create a stable provenance block for replay and inspection."""
    return {
        "workspace_root": str(workspace.root),
        "revision": revision,
        "input": {
            "mode": str(input_data.get("mode", "unknown")),
            "path": str(input_data.get("path", "unknown")),
        },
        "qspec": {
            "path": str(qspec_path),
            "hash": _sha256_file(qspec_path),
            "semantic_hash": semantics["semantic_hash"],
        },
        "subject": {
            "pattern": semantics["pattern"],
            "width": semantics["width"],
            "layers": semantics["layers"],
            "parameter_count": semantics["parameter_count"],
        },
        "artifacts": _build_artifact_provenance(
            workspace=workspace,
            revision=revision,
            artifacts=artifacts,
        ),
    }


def _build_artifact_provenance(
    *,
    workspace: WorkspaceHandle,
    revision: str,
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    snapshot_root = workspace.root / "artifacts" / "history" / revision
    current_root = workspace.root / "artifacts"
    paths: dict[str, str] = {}
    current_aliases: dict[str, str] = {}

    for name, raw_path in artifacts.items():
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        artifact_path = Path(raw_path)
        alias_path = _derive_current_artifact_alias(
            artifact_path=artifact_path,
            snapshot_root=snapshot_root,
            current_root=current_root,
        )
        if alias_path is None:
            continue
        paths[str(name)] = str(artifact_path)
        current_aliases[str(name)] = str(alias_path)

    return {
        "snapshot_root": str(snapshot_root),
        "current_root": str(current_root),
        "paths": paths,
        "current_aliases": current_aliases,
    }


def _derive_current_artifact_alias(
    *,
    artifact_path: Path,
    snapshot_root: Path,
    current_root: Path,
) -> Path | None:
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


def _derive_report_status(
    *,
    warnings: list[str],
    errors: list[str],
    backend_reports: dict[str, Any],
) -> str:
    if errors:
        return "error"

    backend_statuses = {
        str(report.get("status"))
        for report in backend_reports.values()
        if isinstance(report, dict) and report.get("status") is not None
    }
    if warnings or any(status != "ok" for status in backend_statuses):
        return "degraded"
    return "ok"


def _build_suggestions(
    *,
    warnings: list[str],
    errors: list[str],
    backend_reports: dict[str, Any],
) -> list[str]:
    suggestions = []
    if errors:
        suggestions.append("Inspect the diagnostics errors before attempting export or execution.")
    else:
        suggestions.append("Review the generated artifacts and diagnostics report for the next backend step.")

    classiq_status = None
    classiq_report = backend_reports.get("classiq")
    if isinstance(classiq_report, dict):
        classiq_status = classiq_report.get("status")

    if classiq_status == "dependency_missing":
        suggestions.append("Install the Classiq SDK extra to enable Classiq synthesis and benchmarking.")
    elif classiq_status and classiq_status != "ok":
        suggestions.append("Resolve degraded backend reports before comparing backend benchmark results.")

    if warnings:
        suggestions.append("Resolve warnings before adding target constraints or backend benchmarks.")
    elif not backend_reports:
        suggestions.append("Add target constraints or backend benchmarks to deepen validation.")
    else:
        suggestions.append("Inspect backend benchmark deltas before expanding to additional targets.")
    return suggestions
