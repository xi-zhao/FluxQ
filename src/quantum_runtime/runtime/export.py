"""Artifact re-export helpers from the current workspace QSpec."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from quantum_runtime.lowering import (
    write_classiq_program,
    write_qasm3_program,
    write_qiskit_program,
)
from quantum_runtime.qspec import QSpec
from quantum_runtime.runtime.executor import load_qspec_from_report
from quantum_runtime.workspace import WorkspaceHandle, WorkspaceManager


class ExportResult(BaseModel):
    """Stable result for `qrun export`."""

    status: Literal["ok", "unsupported"]
    format: str
    path: str | None = None
    reason: str | None = None


def export_artifact(*, workspace_root: Path, output_format: str) -> ExportResult:
    """Re-emit a single artifact from the current workspace QSpec."""
    handle = WorkspaceManager.load_or_init(workspace_root)
    qspec_path = handle.root / "specs" / "current.json"
    qspec = QSpec.model_validate_json(qspec_path.read_text())
    return _export_from_qspec(handle=handle, qspec=qspec, output_format=output_format)


def export_artifact_from_report(*, workspace_root: Path, report_file: Path, output_format: str) -> ExportResult:
    """Re-emit a single artifact from a report-derived QSpec."""
    handle = WorkspaceManager.load_or_init(workspace_root)
    qspec = load_qspec_from_report(report_file)
    return _export_from_qspec(handle=handle, qspec=qspec, output_format=output_format)


def _export_from_qspec(*, handle: WorkspaceHandle, qspec: QSpec, output_format: str) -> ExportResult:
    if output_format == "qiskit":
        path = write_qiskit_program(qspec, handle.root / "artifacts" / "qiskit" / "main.py")
        return ExportResult(status="ok", format=output_format, path=str(path))
    if output_format == "qasm3":
        path = write_qasm3_program(qspec, handle.root / "artifacts" / "qasm" / "main.qasm")
        return ExportResult(status="ok", format=output_format, path=str(path))
    if output_format == "classiq-python":
        result = write_classiq_program(qspec, handle.root / "artifacts" / "classiq" / "main.py")
        return ExportResult(
            status=result.status,
            format=output_format,
            path=str(result.path) if result.path is not None else None,
            reason=result.reason,
        )
    return ExportResult(
        status="unsupported",
        format=output_format,
        reason="unsupported_export_format",
    )
