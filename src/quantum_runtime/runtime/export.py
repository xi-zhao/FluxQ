"""Artifact re-export helpers from the current workspace QSpec."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from quantum_runtime.lowering import (
    write_classiq_program,
    write_qasm3_program,
    write_qiskit_program,
)
from quantum_runtime.qspec import QSpec
from quantum_runtime.runtime.imports import (
    ImportReference,
    ImportResolution,
    ImportSourceError,
    resolve_import_reference,
)
from quantum_runtime.workspace import WorkspaceHandle, WorkspaceManager


class ExportResult(BaseModel):
    """Stable result for `qrun export`."""

    status: Literal["ok", "unsupported"]
    format: str
    path: str | None = None
    artifact_hash: str | None = None
    reason: str | None = None
    source_kind: str | None = None
    source_revision: str | None = None
    source_report_path: str | None = None
    source_qspec_path: str | None = None
    source_artifact_snapshot_root: str | None = None


def export_artifact(*, workspace_root: Path, output_format: str) -> ExportResult:
    """Re-emit a single artifact from the current workspace QSpec."""
    handle = WorkspaceManager.load_or_init(workspace_root)
    qspec_path = handle.root / "specs" / "current.json"
    qspec = QSpec.model_validate_json(qspec_path.read_text())
    resolution: ImportResolution | None = None
    try:
        resolution = resolve_import_reference(ImportReference(workspace_root=handle.root))
    except ImportSourceError:
        # Keep export usable for manually prepared workspaces that have a current QSpec
        # but do not yet have a matching active report/import surface.
        resolution = None
    return _export_from_qspec(
        handle=handle,
        qspec=qspec,
        output_format=output_format,
        resolution=resolution,
    )


def export_artifact_from_report(*, workspace_root: Path, report_file: Path, output_format: str) -> ExportResult:
    """Re-emit a single artifact from a report-derived QSpec."""
    resolution = resolve_import_reference(ImportReference(report_file=report_file))
    return export_artifact_from_resolution(
        workspace_root=workspace_root,
        resolution=resolution,
        output_format=output_format,
    )


def export_artifact_from_resolution(
    *,
    workspace_root: Path,
    resolution: ImportResolution,
    output_format: str,
) -> ExportResult:
    """Re-emit a single artifact from an already-resolved runtime input."""
    handle = WorkspaceManager.load_or_init(workspace_root)
    qspec = resolution.load_qspec()
    return _export_from_qspec(
        handle=handle,
        qspec=qspec,
        output_format=output_format,
        resolution=resolution,
    )


def _export_from_qspec(
    *,
    handle: WorkspaceHandle,
    qspec: QSpec,
    output_format: str,
    resolution: ImportResolution | None = None,
) -> ExportResult:
    if output_format == "qiskit":
        path = write_qiskit_program(qspec, handle.root / "artifacts" / "qiskit" / "main.py")
        return _build_export_result(output_format=output_format, path=path, resolution=resolution)
    if output_format == "qasm3":
        path = write_qasm3_program(qspec, handle.root / "artifacts" / "qasm" / "main.qasm")
        return _build_export_result(output_format=output_format, path=path, resolution=resolution)
    if output_format == "classiq-python":
        result = write_classiq_program(qspec, handle.root / "artifacts" / "classiq" / "main.py")
        return _build_export_result(
            output_format=output_format,
            path=result.path,
            reason=result.reason,
            status=result.status,
            resolution=resolution,
        )
    return ExportResult(
        status="unsupported",
        format=output_format,
        reason="unsupported_export_format",
    )


def _build_export_result(
    *,
    output_format: str,
    path: Path | None,
    resolution: ImportResolution | None,
    status: Literal["ok", "unsupported"] = "ok",
    reason: str | None = None,
) -> ExportResult:
    artifact_hash = _sha256_file(path) if path is not None and path.exists() else None
    payload: dict[str, str | None] = {
        "status": status,
        "format": output_format,
        "path": str(path) if path is not None else None,
        "artifact_hash": artifact_hash,
        "reason": reason,
        "source_kind": None,
        "source_revision": None,
        "source_report_path": None,
        "source_qspec_path": None,
        "source_artifact_snapshot_root": None,
    }
    if resolution is not None:
        payload.update(
            {
                "source_kind": resolution.source_kind,
                "source_revision": resolution.revision,
                "source_report_path": str(resolution.report_path),
                "source_qspec_path": str(resolution.qspec_path),
                "source_artifact_snapshot_root": _optional_string(
                    resolution.report_summary.get("artifact_snapshot_root")
                ),
            }
        )
    return ExportResult.model_validate(payload)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
