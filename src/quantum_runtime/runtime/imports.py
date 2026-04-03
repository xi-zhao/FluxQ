"""Shared import resolution helpers for workspace-native runtime commands."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from quantum_runtime.artifact_provenance import (
    ArtifactProvenanceMismatch,
    canonicalize_artifact_provenance,
    select_accessible_artifact_paths,
)
from quantum_runtime.qspec import QSpec, summarize_qspec_semantics
from quantum_runtime.workspace import WorkspaceBaseline, WorkspaceManifest, WorkspacePaths


ImportSourceKind = Literal["workspace_current", "report_file", "report_revision"]


class ImportSourceError(ValueError):
    """Raised when an import source cannot be resolved."""

    def __init__(
        self,
        code: str,
        *,
        source: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.source = source
        self.details = details or {}
        super().__init__(f"{code}: {source}")


class ImportReference(BaseModel):
    """Generic import request for a runtime command."""

    workspace_root: Path | None = None
    report_file: Path | None = None
    revision: str | None = None


class ImportResolution(BaseModel):
    """Structured runtime import metadata."""

    source_kind: ImportSourceKind
    source: str
    workspace_root: Path
    workspace_manifest_path: Path
    workspace_project_id: str
    revision: str
    report_path: Path
    qspec_path: Path
    report_hash: str
    qspec_hash: str
    input_mode: str | None = None
    input_path: str | None = None
    report_status: str | None = None
    qspec_status: str = "ok"
    qspec_summary: dict[str, Any] = Field(default_factory=dict)
    report_summary: dict[str, Any] = Field(default_factory=dict)
    replay_integrity: dict[str, Any] = Field(default_factory=dict)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)

    def load_qspec(self) -> QSpec:
        """Load the resolved QSpec from disk."""
        return QSpec.model_validate_json(self.qspec_path.read_text())

    def load_report(self) -> dict[str, Any]:
        """Load the resolved report payload from disk."""
        return json.loads(self.report_path.read_text())


class WorkspaceBaselineResolution(BaseModel):
    """Resolved workspace baseline plus its underlying runtime input."""

    record_path: Path
    record: WorkspaceBaseline
    resolution: ImportResolution


def resolve_import_reference(reference: ImportReference) -> ImportResolution:
    """Resolve the best matching import source from a generic request."""
    if reference.report_file is not None and reference.revision is not None:
        raise ImportSourceError(
            "ambiguous_import_reference",
            source=_reference_source(reference),
            details={"fields": ["report_file", "revision"]},
        )

    if reference.report_file is not None:
        return resolve_report_file(reference.report_file, workspace_root=reference.workspace_root)

    if reference.revision is not None:
        if reference.workspace_root is None:
            raise ImportSourceError(
                "workspace_root_required_for_revision",
                source=_reference_source(reference),
            )
        return resolve_report_revision(reference.workspace_root, reference.revision)

    if reference.workspace_root is not None:
        return resolve_workspace_current(reference.workspace_root)

    raise ImportSourceError(
        "empty_import_reference",
        source=_reference_source(reference),
    )


def resolve_workspace_current(workspace_root: Path) -> ImportResolution:
    """Resolve the active QSpec/report pair from a workspace manifest."""
    paths = WorkspacePaths(root=workspace_root)
    workspace_root = paths.root.resolve()
    workspace_json = paths.workspace_json

    manifest = _load_manifest(workspace_json)
    report_path = workspace_root / manifest.active_report

    report_payload = _load_json_file(
        report_path,
        missing_code="current_report_missing",
        invalid_json_code="current_report_invalid_json",
        invalid_payload_code="current_report_invalid_payload",
        source=str(report_path),
    )
    _extract_artifact_provenance(
        workspace_root=workspace_root,
        revision=manifest.current_revision,
        artifacts=report_payload.get("artifacts"),
        provenance=report_payload.get("provenance"),
        source=str(report_path),
    )
    qspec_path = (workspace_root / manifest.active_spec).resolve()
    qspec = _load_qspec_file(
        qspec_path,
        missing_code="current_qspec_missing",
        invalid_json_code="current_qspec_invalid_json",
        source=str(qspec_path),
    )

    return _build_resolution(
        source_kind="workspace_current",
        source=f"workspace:{workspace_root}",
        workspace_root=workspace_root,
        workspace_manifest_path=workspace_json.resolve(),
        workspace_project_id=manifest.project_id,
        revision=manifest.current_revision,
        report_path=report_path.resolve(),
        qspec_path=qspec_path,
        report_payload=report_payload,
        qspec=qspec,
        provenance={"workspace_source": "manifest"},
    )


def resolve_workspace_baseline(workspace_root: Path) -> WorkspaceBaselineResolution:
    """Resolve the persisted workspace baseline into a runtime input."""
    paths = WorkspacePaths(root=workspace_root)
    record_path = paths.baseline_current_json.resolve()
    if not record_path.exists():
        raise ImportSourceError(
            "baseline_missing",
            source=str(record_path),
        )

    try:
        record = WorkspaceBaseline.load(record_path)
    except ValidationError as exc:
        raise ImportSourceError(
            "baseline_invalid",
            source=str(record_path),
            details={"errors": exc.errors()},
        ) from exc

    resolution = resolve_report_file(
        Path(record.report_path),
        workspace_root=Path(record.workspace_root),
    )
    mismatches: list[str] = []
    if resolution.revision != record.revision:
        mismatches.append("revision")
    if resolution.report_hash != record.report_hash:
        mismatches.append("report_hash")
    if resolution.qspec_hash != record.qspec_hash:
        mismatches.append("qspec_hash")
    if mismatches:
        raise ImportSourceError(
            "baseline_integrity_invalid",
            source=str(record_path),
            details={"mismatches": mismatches},
        )
    return WorkspaceBaselineResolution(
        record_path=record_path,
        record=record,
        resolution=resolution,
    )


def resolve_report_file(report_file: Path, *, workspace_root: Path | None = None) -> ImportResolution:
    """Resolve a report file and its linked QSpec."""
    report_path = report_file.resolve()
    report_payload = _load_json_file(
        report_path,
        missing_code="report_file_missing",
        invalid_json_code="report_file_invalid_json",
        invalid_payload_code="report_file_invalid_payload",
        source=str(report_path),
    )
    inferred_root, workspace_source = _resolve_report_workspace_root(
        report_path=report_path,
        report_payload=report_payload,
        workspace_root=workspace_root,
    )
    if inferred_root is None or workspace_source is None:
        raise ImportSourceError(
            "workspace_root_required_for_report_file",
            source=str(report_path),
        )

    workspace_root_path = inferred_root.resolve()
    qspec_path, qspec_resolution_source = _resolve_qspec_path_from_report(
        report_path=report_path,
        report_payload=report_payload,
        workspace_root=workspace_root_path,
        prefer_history=report_path.parent.name == "history",
    )
    _extract_artifact_provenance(
        workspace_root=workspace_root_path,
        revision=_report_revision(report_payload, fallback=report_path.stem),
        artifacts=report_payload.get("artifacts"),
        provenance=report_payload.get("provenance"),
        source=str(report_path),
    )
    qspec = _load_qspec_file(
        qspec_path,
        missing_code="report_qspec_missing",
        invalid_json_code="report_qspec_invalid_json",
        source=str(qspec_path),
    )
    manifest = _load_manifest(workspace_root_path / "workspace.json")

    return _build_resolution(
        source_kind="report_file",
        source=f"report_file:{report_path}",
        workspace_root=workspace_root_path,
        workspace_manifest_path=workspace_root_path / "workspace.json",
        workspace_project_id=manifest.project_id,
        revision=_report_revision(report_payload, fallback=report_path.stem),
        report_path=report_path,
        qspec_path=qspec_path,
        report_payload=report_payload,
        qspec=qspec,
        provenance={
            "workspace_source": workspace_source,
            "qspec_resolution_source": qspec_resolution_source,
        },
    )


def resolve_report_revision(workspace_root: Path, revision: str) -> ImportResolution:
    """Resolve a report history revision inside a workspace."""
    if not re.fullmatch(r"rev_\d{6}", revision):
        raise ImportSourceError(
            "invalid_revision",
            source=revision,
            details={"expected_pattern": "rev_000001"},
        )

    paths = WorkspacePaths(root=workspace_root)
    workspace_root = paths.root.resolve()
    workspace_json = paths.workspace_json
    manifest = _load_manifest(workspace_json)

    report_path = workspace_root / "reports" / "history" / f"{revision}.json"
    if not report_path.exists() and manifest.current_revision == revision:
        report_path = workspace_root / manifest.active_report

    report_payload = _load_json_file(
        report_path,
        missing_code="report_revision_missing",
        invalid_json_code="report_revision_invalid_json",
        invalid_payload_code="report_revision_invalid_payload",
        source=str(report_path),
    )
    qspec_path, qspec_resolution_source = _resolve_qspec_path_from_report(
        report_path=report_path,
        report_payload=report_payload,
        workspace_root=workspace_root,
        prefer_history=True,
    )
    qspec = _load_qspec_file(
        qspec_path,
        missing_code="revision_qspec_missing",
        invalid_json_code="revision_qspec_invalid_json",
        source=str(qspec_path),
    )

    return _build_resolution(
        source_kind="report_revision",
        source=f"revision:{revision}",
        workspace_root=workspace_root,
        workspace_manifest_path=workspace_json.resolve(),
        workspace_project_id=manifest.project_id,
        revision=revision,
        report_path=report_path.resolve(),
        qspec_path=qspec_path.resolve(),
        report_payload=report_payload,
        qspec=qspec,
        provenance={
            "workspace_source": "manifest",
            "report_revision": revision,
            "qspec_resolution_source": qspec_resolution_source,
        },
    )


def _build_resolution(
    *,
    source_kind: ImportSourceKind,
    source: str,
    workspace_root: Path,
    workspace_manifest_path: Path,
    workspace_project_id: str,
    revision: str,
    report_path: Path,
    qspec_path: Path,
    report_payload: dict[str, Any],
    qspec: QSpec,
    provenance: dict[str, Any],
) -> ImportResolution:
    artifact_provenance = _extract_artifact_provenance(
        workspace_root=workspace_root,
        revision=revision,
        artifacts=report_payload.get("artifacts"),
        provenance=report_payload.get("provenance"),
        source=str(report_path),
    )
    resolved_artifacts = select_accessible_artifact_paths(artifact_provenance)
    report_hash = _sha256_file(report_path)
    qspec_hash = _sha256_file(qspec_path)
    report_summary = _summarize_report(
        report_payload,
        resolved_artifacts=resolved_artifacts,
        artifact_provenance=artifact_provenance,
    )
    qspec_summary = _summarize_qspec(qspec)
    replay_integrity = _evaluate_replay_integrity(
        report_payload=report_payload,
        report_path=report_path,
        qspec=qspec,
        qspec_hash=qspec_hash,
        resolved_artifacts=resolved_artifacts,
    )
    report_summary["replay_integrity_status"] = replay_integrity["status"]
    report_summary["replay_integrity_warnings"] = replay_integrity["warnings"]
    report_summary["replay_integrity_missing_artifacts"] = replay_integrity["missing_artifacts"]
    report_summary["replay_integrity_mismatched_artifacts"] = replay_integrity["mismatched_artifacts"]
    input_block = report_payload.get("input") if isinstance(report_payload, dict) else {}
    input_mode = input_block.get("mode") if isinstance(input_block, dict) else None
    input_path = input_block.get("path") if isinstance(input_block, dict) else None

    return ImportResolution(
        source_kind=source_kind,
        source=source,
        workspace_root=workspace_root,
        workspace_manifest_path=workspace_manifest_path,
        workspace_project_id=workspace_project_id,
        revision=revision,
        report_path=report_path,
        qspec_path=qspec_path,
        report_hash=report_hash,
        qspec_hash=qspec_hash,
        input_mode=input_mode if isinstance(input_mode, str) else None,
        input_path=input_path if isinstance(input_path, str) else None,
        report_status=report_summary.get("status"),
        qspec_status="ok",
        qspec_summary=qspec_summary,
        report_summary=report_summary,
        replay_integrity=replay_integrity,
        artifacts=resolved_artifacts,
        provenance={
            **provenance,
            "source_kind": source_kind,
            "source": source,
            "workspace_root": str(workspace_root),
            "workspace_manifest_path": str(workspace_manifest_path),
            "report_path": str(report_path),
            "qspec_path": str(qspec_path),
            "report_hash": report_hash,
            "qspec_hash": qspec_hash,
            "revision": revision,
            "artifacts": artifact_provenance,
            "replay_integrity": replay_integrity,
        },
    )


def _extract_artifact_provenance(
    *,
    workspace_root: Path,
    revision: str,
    artifacts: Any,
    provenance: Any,
    source: str,
) -> dict[str, Any]:
    stored_artifact_provenance = provenance.get("artifacts") if isinstance(provenance, dict) else None
    try:
        return canonicalize_artifact_provenance(
            workspace_root=workspace_root,
            revision=revision,
            artifacts=artifacts,
            stored_provenance=stored_artifact_provenance,
        )
    except ArtifactProvenanceMismatch as exc:
        raise ImportSourceError(
            "artifact_provenance_invalid",
            source=source,
            details=exc.to_dict(),
        ) from exc


def _evaluate_replay_integrity(
    *,
    report_payload: dict[str, Any],
    report_path: Path,
    qspec: QSpec,
    qspec_hash: str,
    resolved_artifacts: dict[str, str],
) -> dict[str, Any]:
    qspec_block = report_payload.get("qspec") if isinstance(report_payload, dict) else {}
    replay_block = report_payload.get("replay_integrity") if isinstance(report_payload, dict) else {}
    expected_qspec_hash = _optional_string(
        replay_block.get("qspec_hash") if isinstance(replay_block, dict) else None
    ) or _optional_string(qspec_block.get("hash") if isinstance(qspec_block, dict) else None)
    expected_semantic_hash = _optional_string(
        replay_block.get("qspec_semantic_hash") if isinstance(replay_block, dict) else None
    ) or _optional_string(qspec_block.get("semantic_hash") if isinstance(qspec_block, dict) else None)
    actual_semantic_hash = _optional_string(summarize_qspec_semantics(qspec).get("semantic_hash"))

    if expected_qspec_hash is not None and qspec_hash != expected_qspec_hash:
        raise ImportSourceError(
            "report_qspec_hash_mismatch",
            source=str(report_path),
            details={"expected_hash": expected_qspec_hash, "actual_hash": qspec_hash},
        )
    if (
        expected_semantic_hash is not None
        and actual_semantic_hash is not None
        and actual_semantic_hash != expected_semantic_hash
    ):
        raise ImportSourceError(
            "report_qspec_semantic_hash_mismatch",
            source=str(report_path),
            details={
                "expected_semantic_hash": expected_semantic_hash,
                "actual_semantic_hash": actual_semantic_hash,
            },
        )

    stored_digests = replay_block.get("artifact_output_digests") if isinstance(replay_block, dict) else None
    artifact_output_digests = _string_mapping(stored_digests)
    verified_artifacts: list[str] = []
    missing_artifacts: list[str] = []
    mismatched_artifacts: list[str] = []
    for name, expected_digest in sorted(artifact_output_digests.items()):
        if expected_digest is None:
            continue
        raw_path = resolved_artifacts.get(name)
        if raw_path is None:
            missing_artifacts.append(name)
            continue
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            missing_artifacts.append(name)
            continue
        actual_digest = _sha256_file(path)
        if actual_digest != expected_digest:
            mismatched_artifacts.append(name)
            continue
        verified_artifacts.append(name)

    warnings: list[str] = []
    if not artifact_output_digests:
        warnings.append("artifact_output_digests_missing")
    if missing_artifacts:
        warnings.append("artifact_outputs_missing")
    if mismatched_artifacts:
        warnings.append("artifact_outputs_mismatched")

    status: Literal["ok", "legacy", "degraded"]
    if warnings:
        status = "legacy" if warnings == ["artifact_output_digests_missing"] else "degraded"
    else:
        status = "ok"

    return {
        "status": status,
        "qspec_hash_matches": expected_qspec_hash is None or qspec_hash == expected_qspec_hash,
        "qspec_semantic_hash_matches": (
            expected_semantic_hash is None
            or actual_semantic_hash is None
            or actual_semantic_hash == expected_semantic_hash
        ),
        "artifact_digests_present": bool(artifact_output_digests),
        "verified_artifacts": verified_artifacts,
        "missing_artifacts": missing_artifacts,
        "mismatched_artifacts": mismatched_artifacts,
        "warnings": warnings,
    }


def _load_manifest(path: Path) -> WorkspaceManifest:
    if not path.exists():
        raise ImportSourceError("workspace_manifest_missing", source=str(path))
    try:
        return WorkspaceManifest.load(path)
    except Exception as exc:
        raise ImportSourceError(
            "workspace_manifest_invalid",
            source=str(path),
            details={"error": str(exc)},
        ) from exc


def _load_json_file(
    path: Path,
    *,
    missing_code: str,
    invalid_json_code: str,
    invalid_payload_code: str,
    source: str,
) -> dict[str, Any]:
    if not path.exists():
        raise ImportSourceError(missing_code, source=source)
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ImportSourceError(
            invalid_json_code,
            source=source,
            details={"error": str(exc)},
        ) from exc

    if not isinstance(payload, dict):
        raise ImportSourceError(
            invalid_payload_code,
            source=source,
        )
    return payload


def _load_qspec_file(
    path: Path,
    *,
    missing_code: str,
    invalid_json_code: str,
    source: str,
) -> QSpec:
    if not path.exists():
        raise ImportSourceError(missing_code, source=source)
    try:
        return QSpec.model_validate_json(path.read_text())
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ImportSourceError(
            invalid_json_code,
            source=source,
            details={"error": str(exc)},
        ) from exc


def _resolve_qspec_path_from_report(
    *,
    report_path: Path,
    report_payload: dict[str, Any],
    workspace_root: Path,
    prefer_history: bool,
) -> tuple[Path, str]:
    revision = _report_revision(report_payload, fallback=report_path.stem)
    history_candidate = workspace_root / "specs" / "history" / f"{revision}.json"
    artifact_provenance = _extract_artifact_provenance(
        workspace_root=workspace_root,
        revision=revision,
        artifacts=report_payload.get("artifacts"),
        provenance=report_payload.get("provenance"),
        source=str(report_path),
    )
    resolved_artifacts = select_accessible_artifact_paths(artifact_provenance)
    canonical_qspec_path = Path(artifact_provenance["paths"]["qspec"])
    if canonical_qspec_path.exists():
        return canonical_qspec_path, "artifact_provenance"
    resolved_qspec_path = resolved_artifacts.get("qspec")
    if isinstance(resolved_qspec_path, str) and Path(resolved_qspec_path).exists():
        return Path(resolved_qspec_path), "artifact_provenance_fallback"
    if prefer_history and history_candidate.exists():
        return history_candidate, "workspace_history"

    qspec_block = report_payload.get("qspec")
    if not isinstance(qspec_block, dict):
        raise ImportSourceError(
            "report_qspec_block_missing",
            source=str(report_path),
        )

    raw_path = qspec_block.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ImportSourceError(
            "report_qspec_path_missing",
            source=str(report_path),
        )

    candidate = Path(raw_path)
    if candidate.is_absolute():
        if candidate.exists():
            return candidate, "report_payload"
        if prefer_history and history_candidate.exists():
            return history_candidate, "workspace_history"
        raise ImportSourceError(
            "report_qspec_missing",
            source=str(report_path),
            details={"qspec_path": str(candidate)},
        )

    candidate = (workspace_root / candidate).resolve()
    if candidate.exists():
        return candidate, "report_payload"

    if prefer_history and history_candidate.exists():
        return history_candidate, "workspace_history"

    raise ImportSourceError(
        "report_qspec_missing",
        source=str(report_path),
        details={"qspec_path": str(candidate)},
    )


def _infer_workspace_root_from_report_path(report_path: Path) -> Path | None:
    if report_path.parent.name == "reports":
        return report_path.parent.parent
    if report_path.parent.name == "history" and report_path.parent.parent.name == "reports":
        return report_path.parent.parent.parent
    return None


def _resolve_report_workspace_root(
    *,
    report_path: Path,
    report_payload: dict[str, Any],
    workspace_root: Path | None,
) -> tuple[Path | None, str | None]:
    payload_root, payload_source = _infer_workspace_root_from_report_payload(report_payload)
    if payload_root is not None and payload_source is not None:
        return payload_root, payload_source

    path_root = _infer_workspace_root_from_report_path(report_path)
    if path_root is not None:
        return path_root, "inferred_from_report_path"

    if workspace_root is not None:
        return Path(workspace_root), "workspace_option"

    return None, None


def _infer_workspace_root_from_report_payload(report_payload: dict[str, Any]) -> tuple[Path | None, str | None]:
    provenance = report_payload.get("provenance") if isinstance(report_payload, dict) else None
    if isinstance(provenance, dict):
        raw_workspace_root = provenance.get("workspace_root")
        if isinstance(raw_workspace_root, str) and raw_workspace_root.strip():
            return Path(raw_workspace_root), "report_provenance.workspace_root"

        artifact_provenance = provenance.get("artifacts")
        artifact_root = _infer_workspace_root_from_artifact_provenance(artifact_provenance)
        if artifact_root is not None:
            return artifact_root, "report_provenance.artifacts"

    qspec_block = report_payload.get("qspec") if isinstance(report_payload, dict) else None
    if isinstance(qspec_block, dict):
        qspec_root = _infer_workspace_root_from_path_string(qspec_block.get("path"))
        if qspec_root is not None:
            return qspec_root, "report_qspec_path"

    artifacts = report_payload.get("artifacts") if isinstance(report_payload, dict) else None
    if isinstance(artifacts, dict):
        qspec_root = _infer_workspace_root_from_path_string(artifacts.get("qspec"))
        if qspec_root is not None:
            return qspec_root, "report_artifacts.qspec"

    return None, None


def _infer_workspace_root_from_artifact_provenance(artifact_provenance: Any) -> Path | None:
    if not isinstance(artifact_provenance, dict):
        return None

    for key in ("snapshot_root", "current_root"):
        inferred = _infer_workspace_root_from_path_string(artifact_provenance.get(key))
        if inferred is not None:
            return inferred

    for key in ("paths", "current_aliases"):
        mapping = artifact_provenance.get(key)
        if not isinstance(mapping, dict):
            continue
        for artifact_name in ("qspec", "report"):
            inferred = _infer_workspace_root_from_path_string(mapping.get(artifact_name))
            if inferred is not None:
                return inferred

    return None


def _infer_workspace_root_from_path_string(raw_path: Any) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None

    candidate = Path(raw_path)
    if not candidate.is_absolute():
        return None

    for current in (candidate, *candidate.parents):
        if current.name in {"reports", "specs", "artifacts"}:
            return current.parent
        if current.name == "history" and current.parent.name in {"reports", "specs", "artifacts"}:
            return current.parent.parent

    return None


def _report_revision(report_payload: dict[str, Any], fallback: str) -> str:
    revision = report_payload.get("revision")
    if isinstance(revision, str) and revision:
        return revision
    return fallback


def _summarize_report(
    report_payload: dict[str, Any],
    *,
    resolved_artifacts: dict[str, str],
    artifact_provenance: dict[str, Any],
) -> dict[str, Any]:
    artifacts = report_payload.get("artifacts") if isinstance(report_payload, dict) else {}
    backend_reports = report_payload.get("backend_reports") if isinstance(report_payload, dict) else {}
    warnings = report_payload.get("warnings") if isinstance(report_payload, dict) else []
    errors = report_payload.get("errors") if isinstance(report_payload, dict) else []
    input_block = report_payload.get("input") if isinstance(report_payload, dict) else {}
    diagnostics = report_payload.get("diagnostics") if isinstance(report_payload, dict) else {}
    simulation = diagnostics.get("simulation") if isinstance(diagnostics, dict) else {}
    transpile = diagnostics.get("transpile") if isinstance(diagnostics, dict) else {}
    resources = diagnostics.get("resources") if isinstance(diagnostics, dict) else {}

    artifact_outputs = _summarize_artifact_outputs(resolved_artifacts)
    artifact_paths = artifact_provenance.get("paths", {})

    return {
        "status": report_payload.get("status"),
        "revision": report_payload.get("revision"),
        "input_mode": input_block.get("mode") if isinstance(input_block, dict) else None,
        "input_path": input_block.get("path") if isinstance(input_block, dict) else None,
        "artifact_names": sorted(artifacts.keys()) if isinstance(artifacts, dict) else [],
        "backend_names": sorted(backend_reports.keys()) if isinstance(backend_reports, dict) else [],
        "backend_statuses": {
            str(name): report.get("status")
            for name, report in sorted(backend_reports.items())
            if isinstance(report, dict)
        }
        if isinstance(backend_reports, dict)
        else {},
        "simulation_status": simulation.get("status") if isinstance(simulation, dict) else None,
        "transpile_status": transpile.get("status") if isinstance(transpile, dict) else None,
        "resource_summary": {
            key: resources.get(key)
            for key in ("width", "depth", "two_qubit_gates", "measure_count", "parameter_count")
        }
        if isinstance(resources, dict)
        else {},
        "warning_count": len(warnings) if isinstance(warnings, list) else 0,
        "error_count": len(errors) if isinstance(errors, list) else 0,
        "artifact_snapshot_root": artifact_provenance.get("snapshot_root"),
        "artifact_current_aliases": artifact_provenance.get("current_aliases", {}),
        "artifact_paths": artifact_paths,
        "artifact_output_names": sorted(
            name
            for name in artifact_paths.keys()
            if isinstance(name, str) and name not in {"qspec", "report"}
        ),
        "artifact_output_digests": artifact_outputs["digests"],
        "artifact_output_missing": artifact_outputs["missing"],
        "artifact_output_set_hash": artifact_outputs["set_hash"],
        "artifact_set_hash": artifact_outputs["set_hash"],
    }


def _summarize_qspec(qspec: QSpec) -> dict[str, Any]:
    semantics = summarize_qspec_semantics(qspec)
    return {
        "version": qspec.version,
        "program_id": qspec.program_id,
        "goal": qspec.goal,
        "entrypoint": qspec.entrypoint,
        "pattern": semantics["pattern"],
        "width": semantics["width"],
        "layers": semantics["layers"],
        "parameter_count": semantics["parameter_count"],
        "workload_hash": semantics["workload_hash"],
        "execution_hash": semantics["execution_hash"],
        "semantic_hash": semantics["semantic_hash"],
        "pattern_args": semantics["pattern_args"],
        "registers": {
            "qubits": qspec.registers[0].size,
            "cbits": qspec.registers[1].size,
        },
        "body_nodes": len(qspec.body),
        "backend_preferences": list(qspec.backend_preferences),
        "constraints": qspec.constraints.model_dump(mode="json"),
    }


def _string_mapping(value: object) -> dict[str, str | None]:
    if not isinstance(value, dict):
        return {}
    return {str(key): _optional_string(item) for key, item in value.items()}


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _summarize_artifact_outputs(resolved_artifacts: dict[str, str]) -> dict[str, Any]:
    digests: dict[str, str] = {}
    missing: list[str] = []

    for name, raw_path in sorted(resolved_artifacts.items()):
        if name in {"qspec", "report"}:
            continue
        path = Path(raw_path)
        if path.exists() and path.is_file():
            digests[name] = _sha256_file(path)
        else:
            missing.append(name)

    payload = {"digests": digests, "missing": missing}
    return {
        **payload,
        "set_hash": _hash_payload(payload),
    }


def _hash_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _reference_source(reference: ImportReference) -> str:
    pieces = []
    if reference.workspace_root is not None:
        pieces.append(f"workspace_root={reference.workspace_root}")
    if reference.report_file is not None:
        pieces.append(f"report_file={reference.report_file}")
    if reference.revision is not None:
        pieces.append(f"revision={reference.revision}")
    return ", ".join(pieces) or "<empty>"
