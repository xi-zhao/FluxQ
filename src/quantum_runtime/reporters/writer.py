"""Write stable report artifacts into the workspace."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from quantum_runtime.artifact_provenance import (
    canonicalize_artifact_provenance,
    select_accessible_artifact_paths,
)
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
    promote_latest: bool = False,
) -> dict[str, Any]:
    """Write a revision-scoped report and optionally promote `reports/latest.json`."""
    latest_path = workspace.root / "reports" / "latest.json"
    history_path = workspace.root / "reports" / "history" / f"{revision}.json"
    artifact_payload = dict(artifacts)
    artifact_payload["qspec"] = str(qspec_path)
    artifact_payload["report"] = str(history_path)
    artifact_provenance = canonicalize_artifact_provenance(
        workspace_root=workspace.root,
        revision=revision,
        artifacts=artifact_payload,
    )
    canonical_qspec_path = Path(str(artifact_provenance["paths"]["qspec"]))
    semantics = summarize_qspec_semantics(qspec)
    artifact_payload = dict(artifact_provenance["paths"])
    accessible_artifact_paths = select_accessible_artifact_paths(artifact_provenance)
    qspec_hash = _qspec_hash(
        qspec=qspec,
        canonical_qspec_path=canonical_qspec_path,
    )
    replay_integrity = _build_replay_integrity(
        qspec_hash=qspec_hash,
        qspec_semantic_hash=semantics["semantic_hash"],
        artifact_paths=accessible_artifact_paths,
    )
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
            qspec_path=canonical_qspec_path,
            qspec_hash=qspec_hash,
            semantics=semantics,
            artifact_provenance=artifact_provenance,
        ),
        "qspec": {
            "path": str(canonical_qspec_path),
            "hash": qspec_hash,
            "semantic_hash": semantics["semantic_hash"],
        },
        "semantics": semantics,
        "replay_integrity": replay_integrity,
        "artifacts": artifact_payload,
        "diagnostics": _canonicalize_diagnostics(
            diagnostics=diagnostics,
            artifact_paths=artifact_payload,
        ),
        "backend_reports": backend_reports,
        "warnings": warnings,
        "errors": errors,
        "suggestions": _build_suggestions(
            warnings=warnings,
            errors=errors,
            backend_reports=backend_reports,
        ),
    }

    serialized = json.dumps(payload, indent=2, ensure_ascii=True)
    history_path.write_text(serialized)
    if promote_latest:
        latest_path.write_text(serialized)
    return payload


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _sha256_bytes(data: bytes) -> str:
    digest = hashlib.sha256(data).hexdigest()
    return f"sha256:{digest}"


def _qspec_hash(*, qspec: QSpec, canonical_qspec_path: Path) -> str:
    if canonical_qspec_path.exists() and canonical_qspec_path.is_file():
        return _sha256_file(canonical_qspec_path)
    return _sha256_bytes(qspec.model_dump_json(indent=2).encode("utf-8"))


def _build_provenance(
    *,
    workspace: WorkspaceHandle,
    revision: str,
    input_data: dict[str, Any],
    qspec_path: Path,
    qspec_hash: str,
    semantics: dict[str, Any],
    artifact_provenance: dict[str, Any],
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
            "hash": qspec_hash,
            "semantic_hash": semantics["semantic_hash"],
        },
        "subject": {
            "pattern": semantics["pattern"],
            "width": semantics["width"],
            "layers": semantics["layers"],
            "parameter_count": semantics["parameter_count"],
        },
        "artifacts": artifact_provenance,
    }


def _canonicalize_diagnostics(
    *,
    diagnostics: dict[str, Any],
    artifact_paths: dict[str, str],
) -> dict[str, Any]:
    payload = json.loads(json.dumps(diagnostics))
    diagram = payload.get("diagram")
    if isinstance(diagram, dict):
        if "diagram_txt" in artifact_paths:
            diagram["text_path"] = artifact_paths["diagram_txt"]
        if "diagram_png" in artifact_paths:
            diagram["png_path"] = artifact_paths["diagram_png"]
    return payload


def _build_replay_integrity(
    *,
    qspec_hash: str,
    qspec_semantic_hash: str,
    artifact_paths: dict[str, str],
) -> dict[str, Any]:
    return {
        "qspec_hash": qspec_hash,
        "qspec_semantic_hash": qspec_semantic_hash,
        "artifact_output_digests": _artifact_output_digests(artifact_paths),
    }


def _artifact_output_digests(artifact_paths: dict[str, str]) -> dict[str, str]:
    digests: dict[str, str] = {}
    for name, raw_path in sorted(artifact_paths.items()):
        if name in {"qspec", "report"}:
            continue
        path = Path(raw_path)
        if path.exists() and path.is_file():
            digests[name] = _sha256_file(path)
    return digests


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
