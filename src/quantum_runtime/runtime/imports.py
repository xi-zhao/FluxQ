"""Shared import resolution helpers for workspace-native runtime commands."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from quantum_runtime.qspec import QSpec, summarize_qspec_semantics
from quantum_runtime.workspace import WorkspaceManifest, WorkspacePaths


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
    artifacts: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)

    def load_qspec(self) -> QSpec:
        """Load the resolved QSpec from disk."""
        return QSpec.model_validate_json(self.qspec_path.read_text())

    def load_report(self) -> dict[str, Any]:
        """Load the resolved report payload from disk."""
        return json.loads(self.report_path.read_text())


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
    qspec_path = workspace_root / manifest.active_spec

    report_payload = _load_json_file(
        report_path,
        missing_code="current_report_missing",
        invalid_json_code="current_report_invalid_json",
        invalid_payload_code="current_report_invalid_payload",
        source=str(report_path),
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
        qspec_path=qspec_path.resolve(),
        report_payload=report_payload,
        qspec=qspec,
        provenance={"workspace_source": "manifest"},
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
    inferred_root = workspace_root or _infer_workspace_root_from_report_path(report_path)
    if inferred_root is None:
        raise ImportSourceError(
            "workspace_root_required_for_report_file",
            source=str(report_path),
        )

    workspace_root_path = Path(inferred_root).resolve()
    qspec_path, qspec_resolution_source = _resolve_qspec_path_from_report(
        report_path=report_path,
        report_payload=report_payload,
        workspace_root=workspace_root_path,
        prefer_history=report_path.parent.name == "history",
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
            "workspace_source": "inferred_from_report_path",
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
    report_hash = _sha256_file(report_path)
    qspec_hash = _sha256_file(qspec_path)
    report_summary = _summarize_report(report_payload)
    qspec_summary = _summarize_qspec(qspec)
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
        artifacts=report_payload.get("artifacts", {}) if isinstance(report_payload.get("artifacts"), dict) else {},
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
        },
    )


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

    candidate = workspace_root / candidate
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


def _report_revision(report_payload: dict[str, Any], fallback: str) -> str:
    revision = report_payload.get("revision")
    if isinstance(revision, str) and revision:
        return revision
    return fallback


def _summarize_report(report_payload: dict[str, Any]) -> dict[str, Any]:
    artifacts = report_payload.get("artifacts") if isinstance(report_payload, dict) else {}
    backend_reports = report_payload.get("backend_reports") if isinstance(report_payload, dict) else {}
    warnings = report_payload.get("warnings") if isinstance(report_payload, dict) else []
    errors = report_payload.get("errors") if isinstance(report_payload, dict) else []
    input_block = report_payload.get("input") if isinstance(report_payload, dict) else {}
    diagnostics = report_payload.get("diagnostics") if isinstance(report_payload, dict) else {}
    simulation = diagnostics.get("simulation") if isinstance(diagnostics, dict) else {}
    transpile = diagnostics.get("transpile") if isinstance(diagnostics, dict) else {}
    resources = diagnostics.get("resources") if isinstance(diagnostics, dict) else {}

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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
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
