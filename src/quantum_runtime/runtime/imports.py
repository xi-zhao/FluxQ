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
from quantum_runtime.runtime.run_manifest import RunManifestIntegrityError, load_run_manifest
from quantum_runtime.workspace import WorkspaceBaseline, WorkspaceManifest, WorkspacePaths


ImportSourceKind = Literal["workspace_current", "report_file", "report_revision"]
_REVISION_PATTERN = re.compile(r"rev_\d{6}")


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


def validate_revision(revision: str, *, source: str | None = None) -> str:
    """Validate one immutable revision identifier."""
    if not _REVISION_PATTERN.fullmatch(revision):
        raise ImportSourceError(
            "invalid_revision",
            source=source or revision,
            details={"expected_pattern": "rev_000001"},
        )
    return revision


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
    report_path, report_resolution_source = _resolve_workspace_current_report_path(
        workspace_root=workspace_root,
        manifest=manifest,
    )
    prefer_history = manifest.current_revision != "rev_000000"

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
    qspec_path, qspec_resolution_source = _resolve_qspec_path_from_report(
        report_path=report_path,
        report_payload=report_payload,
        workspace_root=workspace_root,
        prefer_history=prefer_history,
    )
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
        provenance={
            "workspace_source": "manifest",
            "report_resolution_source": report_resolution_source,
            "qspec_resolution_source": qspec_resolution_source,
        },
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
    candidates = _resolve_report_workspace_candidates(
        report_path=report_path,
        report_payload=report_payload,
        workspace_root=workspace_root,
    )
    if not candidates:
        raise ImportSourceError(
            "workspace_root_required_for_report_file",
            source=str(report_path),
        )

    last_error: ImportSourceError | None = None
    for candidate_root, workspace_source, relocated in candidates:
        try:
            candidate_payload = (
                _relocate_report_payload_for_workspace(
                    report_payload=report_payload,
                    workspace_root=candidate_root,
                    revision=_report_revision(report_payload, fallback=report_path.stem),
                )
                if relocated
                else report_payload
            )
            return _resolve_report_file_against_workspace(
                report_path=report_path,
                report_payload=candidate_payload,
                workspace_root=candidate_root,
                workspace_source=workspace_source,
            )
        except ImportSourceError as exc:
            last_error = exc
            if exc.code not in _report_resolution_retryable_codes():
                raise
            continue

    assert last_error is not None
    raise last_error


def resolve_report_revision(workspace_root: Path, revision: str) -> ImportResolution:
    """Resolve a report history revision inside a workspace."""
    revision = validate_revision(revision, source=revision)
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
    paths = WorkspacePaths(root=workspace_root)
    expected_qspec_history_path = paths.root / "specs" / "history" / f"{revision}.json"
    expected_report_history_path = paths.root / "reports" / "history" / f"{revision}.json"
    manifest_payload = _load_run_manifest_if_present(
        workspace_root=workspace_root,
        revision=revision,
        expected_qspec_path=expected_qspec_history_path,
        expected_report_path=expected_report_history_path,
        source=str(paths.manifest_history_json(revision)),
    )
    report_summary["manifest_path"] = (
        str(paths.manifest_history_json(revision))
        if manifest_payload is not None
        else None
    )
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
            "run_manifest_path": report_summary.get("manifest_path"),
            "artifacts": artifact_provenance,
            "replay_integrity": replay_integrity,
        },
    )


def _resolve_report_file_against_workspace(
    *,
    report_path: Path,
    report_payload: dict[str, Any],
    workspace_root: Path,
    workspace_source: str,
) -> ImportResolution:
    workspace_root_path = workspace_root.resolve()
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


def _load_run_manifest_if_present(
    *,
    workspace_root: Path,
    revision: str,
    expected_qspec_path: Path,
    expected_report_path: Path,
    source: str,
) -> dict[str, Any] | None:
    try:
        return load_run_manifest(
            workspace_root=workspace_root,
            revision=revision,
            expected_qspec_path=expected_qspec_path,
            expected_report_path=expected_report_path,
        )
    except RunManifestIntegrityError as exc:
        raise ImportSourceError(
            "run_manifest_integrity_invalid",
            source=source,
            details=exc.details or {"mismatches": exc.mismatches},
        ) from exc
    except (ValidationError, json.JSONDecodeError, ValueError) as exc:
        raise ImportSourceError(
            "run_manifest_invalid",
            source=source,
            details={"error": str(exc)},
        ) from exc


def _resolve_workspace_current_report_path(
    *,
    workspace_root: Path,
    manifest: WorkspaceManifest,
) -> tuple[Path, str]:
    active_report_path = (workspace_root / manifest.active_report).resolve()
    if manifest.current_revision != "rev_000000":
        history_report_path = workspace_root / "reports" / "history" / f"{manifest.current_revision}.json"
        if history_report_path.exists():
            return history_report_path.resolve(), "workspace_history"
    return active_report_path, "workspace_manifest_alias"


def _relocate_report_payload_for_workspace(
    *,
    report_payload: dict[str, Any],
    workspace_root: Path,
    revision: str,
) -> dict[str, Any]:
    relocated = json.loads(json.dumps(report_payload))
    normalized_root = Path(workspace_root).resolve()

    qspec_block = relocated.get("qspec")
    if not isinstance(qspec_block, dict):
        qspec_block = {}
        relocated["qspec"] = qspec_block
    qspec_block["path"] = str(normalized_root / "specs" / "history" / f"{revision}.json")

    artifacts = relocated.get("artifacts")
    if not isinstance(artifacts, dict):
        artifacts = {}
    relocated_artifacts = dict(artifacts)
    relocated_artifacts["qspec"] = str(normalized_root / "specs" / "history" / f"{revision}.json")
    relocated_artifacts["report"] = str(normalized_root / "reports" / "history" / f"{revision}.json")

    artifact_mapping = {
        "qiskit_code": normalized_root / "artifacts" / "history" / revision / "qiskit" / "main.py",
        "qasm3": normalized_root / "artifacts" / "history" / revision / "qasm" / "main.qasm",
        "classiq_code": normalized_root / "artifacts" / "history" / revision / "classiq" / "main.py",
        "classiq_results": normalized_root / "artifacts" / "history" / revision / "classiq" / "synthesis.json",
        "diagram_txt": normalized_root / "artifacts" / "history" / revision / "figures" / "circuit.txt",
        "diagram_png": normalized_root / "artifacts" / "history" / revision / "figures" / "circuit.png",
    }
    for artifact_name, candidate_path in artifact_mapping.items():
        if artifact_name in relocated_artifacts:
            relocated_artifacts[artifact_name] = str(candidate_path)
    relocated["artifacts"] = relocated_artifacts

    provenance = relocated.get("provenance")
    if not isinstance(provenance, dict):
        provenance = {}
    else:
        provenance = dict(provenance)
    provenance["workspace_root"] = str(normalized_root)
    provenance.pop("artifacts", None)
    relocated["provenance"] = provenance

    return relocated


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
    artifact_output_digests = {
        name: expected_digest
        for name, expected_digest in _string_mapping(stored_digests).items()
        if expected_digest is not None
    }
    trust_level: Literal["trusted", "legacy"] = "trusted" if artifact_output_digests else "legacy"
    verified_artifacts: list[str] = []
    missing_artifacts: list[str] = []
    mismatched_artifacts: list[str] = []
    for name, expected_digest in sorted(artifact_output_digests.items()):
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

    if missing_artifacts:
        raise ImportSourceError(
            "artifact_outputs_missing",
            source=str(report_path),
            details=_replay_integrity_payload(
                status="ok",
                trust_level=trust_level,
                qspec_hash_matches=expected_qspec_hash is None or qspec_hash == expected_qspec_hash,
                qspec_semantic_hash_matches=(
                    expected_semantic_hash is None
                    or actual_semantic_hash is None
                    or actual_semantic_hash == expected_semantic_hash
                ),
                artifact_digests_present=bool(artifact_output_digests),
                verified_artifacts=verified_artifacts,
                missing_artifacts=missing_artifacts,
                mismatched_artifacts=mismatched_artifacts,
                warnings=["artifact_outputs_missing"],
            ),
        )
    if mismatched_artifacts:
        raise ImportSourceError(
            "artifact_outputs_mismatched",
            source=str(report_path),
            details=_replay_integrity_payload(
                status="ok",
                trust_level=trust_level,
                qspec_hash_matches=expected_qspec_hash is None or qspec_hash == expected_qspec_hash,
                qspec_semantic_hash_matches=(
                    expected_semantic_hash is None
                    or actual_semantic_hash is None
                    or actual_semantic_hash == expected_semantic_hash
                ),
                artifact_digests_present=bool(artifact_output_digests),
                verified_artifacts=verified_artifacts,
                missing_artifacts=missing_artifacts,
                mismatched_artifacts=mismatched_artifacts,
                warnings=["artifact_outputs_mismatched"],
            ),
        )

    status: Literal["ok", "legacy"] = "legacy" if trust_level == "legacy" else "ok"
    warnings = ["artifact_output_digests_missing"] if trust_level == "legacy" else []

    return _replay_integrity_payload(
        status=status,
        trust_level=trust_level,
        qspec_hash_matches=expected_qspec_hash is None or qspec_hash == expected_qspec_hash,
        qspec_semantic_hash_matches=(
            expected_semantic_hash is None
            or actual_semantic_hash is None
            or actual_semantic_hash == expected_semantic_hash
        ),
        artifact_digests_present=bool(artifact_output_digests),
        verified_artifacts=verified_artifacts,
        missing_artifacts=missing_artifacts,
        mismatched_artifacts=mismatched_artifacts,
        warnings=warnings,
    )


def _replay_integrity_payload(
    *,
    status: str,
    trust_level: str,
    qspec_hash_matches: bool,
    qspec_semantic_hash_matches: bool,
    artifact_digests_present: bool,
    verified_artifacts: list[str],
    missing_artifacts: list[str],
    mismatched_artifacts: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "status": status,
        "trust_level": trust_level,
        "qspec_hash_matches": qspec_hash_matches,
        "qspec_semantic_hash_matches": qspec_semantic_hash_matches,
        "artifact_digests_present": artifact_digests_present,
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


def _resolve_report_workspace_candidates(
    *,
    report_path: Path,
    report_payload: dict[str, Any],
    workspace_root: Path | None,
) -> list[tuple[Path, str, bool]]:
    candidates: list[tuple[Path, str, bool]] = []
    seen: set[tuple[Path, bool]] = set()

    def add_candidate(path: Path | None, source: str | None, relocated: bool = False) -> None:
        if path is None or source is None:
            return
        resolved = Path(path).resolve()
        key = (resolved, relocated)
        if key in seen:
            return
        seen.add(key)
        candidates.append((resolved, source, relocated))

    payload_root, payload_source = _infer_workspace_root_from_report_payload(report_payload)
    add_candidate(payload_root, payload_source)

    path_root = _infer_workspace_root_from_report_path(report_path)
    add_candidate(path_root, "inferred_from_report_path" if path_root is not None else None)

    if workspace_root is not None:
        explicit_root = Path(workspace_root)
        add_candidate(explicit_root, "workspace_option")
        add_candidate(explicit_root, "workspace_option_relocated_report", relocated=True)

    return candidates


def _report_resolution_retryable_codes() -> set[str]:
    return {
        "workspace_manifest_missing",
        "workspace_manifest_invalid",
        "report_qspec_missing",
        "artifact_provenance_invalid",
    }


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
    exports = diagnostics.get("exports") if isinstance(diagnostics, dict) else {}
    transpile = diagnostics.get("transpile") if isinstance(diagnostics, dict) else {}
    resources = diagnostics.get("resources") if isinstance(diagnostics, dict) else {}
    representative_expectations = _summarize_expectation_values(
        simulation.get("expectation_values") if isinstance(simulation, dict) else None
    )
    best_point = _summarize_best_point(
        simulation.get("best_point") if isinstance(simulation, dict) else None
    )
    representative_bindings = _float_mapping(
        simulation.get("representative_bindings") if isinstance(simulation, dict) else None
    )
    export_bindings = _float_mapping(exports.get("bindings") if isinstance(exports, dict) else None)

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
        "parameter_mode": simulation.get("parameter_mode") if isinstance(simulation, dict) else None,
        "representative_point_label": (
            simulation.get("representative_point_label") if isinstance(simulation, dict) else None
        ),
        "representative_bindings": representative_bindings,
        "representative_bindings_hash": _hash_payload(representative_bindings),
        "representative_expectations": representative_expectations,
        "representative_expectations_hash": _hash_payload(representative_expectations),
        "best_point": best_point,
        "best_point_hash": _hash_payload(best_point),
        "export_point_label": exports.get("point_label") if isinstance(exports, dict) else None,
        "export_parameter_mode": exports.get("parameter_mode") if isinstance(exports, dict) else None,
        "export_bindings_hash": _hash_payload(export_bindings),
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
        "observable_count": semantics["observable_count"],
        "workload_hash": semantics["workload_hash"],
        "execution_hash": semantics["execution_hash"],
        "semantic_hash": semantics["semantic_hash"],
        "pattern_args": semantics["pattern_args"],
        "observables": semantics["observables"],
        "parameter_workflow_mode": semantics["parameter_workflow_mode"],
        "parameter_workflow": semantics["parameter_workflow"],
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


def _summarize_expectation_values(value: object) -> dict[str, float]:
    if not isinstance(value, list):
        return {}
    summary: dict[str, float] = {}
    for entry in value:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()
        if not name:
            continue
        raw_value = entry.get("value")
        if raw_value is None:
            continue
        try:
            summary[name] = float(raw_value)
        except (TypeError, ValueError):
            continue
    return summary


def _summarize_best_point(value: object) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    summary: dict[str, Any] = {}
    for key in ("label", "objective_observable", "objective"):
        raw = value.get(key)
        if raw is not None:
            summary[key] = str(raw)
    raw_objective_value = value.get("objective_value")
    if raw_objective_value is not None:
        try:
            summary["objective_value"] = float(raw_objective_value)
        except (TypeError, ValueError):
            pass
    return summary or None


def _float_mapping(value: object) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    summary: dict[str, float] = {}
    for key, raw in value.items():
        try:
            summary[str(key)] = float(raw)
        except (TypeError, ValueError):
            continue
    return summary


def _hash_payload(payload: object) -> str:
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
