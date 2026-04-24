"""Artifact re-export helpers from the current workspace QSpec."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from quantum_runtime.errors import WorkspaceConflictError, WorkspaceRecoveryRequiredError
from quantum_runtime.lowering import (
    emit_classiq_source,
    emit_qasm3_source,
    emit_qiskit_source,
)
from quantum_runtime.qspec import QSpec, summarize_qspec_semantics
from quantum_runtime.qspec.parameter_workflow import (
    representative_bindings as qspec_representative_bindings,
)
from quantum_runtime.runtime.imports import (
    ImportReference,
    ImportResolution,
    ImportSourceError,
    resolve_import_reference,
)
from quantum_runtime.workspace import (
    WorkspaceHandle,
    WorkspaceLockConflict,
    WorkspaceManager,
    acquire_workspace_lock,
    atomic_write_text,
    pending_atomic_write_files,
)


class ExportResult(BaseModel):
    """Stable result for `qrun export`."""

    status: Literal["ok", "unsupported"]
    format: str
    profile: str | None = None
    path: str | None = None
    artifact_hash: str | None = None
    reason: str | None = None
    source_kind: str | None = None
    source_revision: str | None = None
    source_report_path: str | None = None
    source_qspec_path: str | None = None
    source_artifact_snapshot_root: str | None = None


def export_artifact(*, workspace_root: Path, output_format: str, profile: str | None = None) -> ExportResult:
    """Re-emit a single artifact from the current workspace QSpec."""
    try:
        handle = WorkspaceManager.load_or_init(workspace_root)
    except WorkspaceLockConflict as exc:
        raise WorkspaceConflictError(
            workspace=Path(workspace_root).resolve(),
            lock_path=Path(exc.lock_path),
            holder=exc.holder.model_dump(mode="json"),
        ) from exc
    qspec_path = handle.root / "specs" / "current.json"
    qspec = QSpec.model_validate_json(qspec_path.read_text())
    resolution: ImportResolution | None = None
    try:
        resolution = _resolve_current_export_resolution(
            handle=handle,
            qspec_path=qspec_path,
            qspec=qspec,
        )
    except ImportSourceError as exc:
        # Keep export usable for manually prepared workspaces that have a current QSpec
        # but have not emitted an active report yet. Integrity and provenance mismatches
        # still fail closed instead of silently dropping source metadata.
        if exc.code not in {"current_report_missing", "report_file_missing"}:
            raise
        resolution = None
    return _export_from_qspec(
        handle=handle,
        qspec=qspec,
        output_format=output_format,
        profile=profile,
        parameter_bindings=_export_parameter_bindings(qspec, resolution=resolution),
        resolution=resolution,
    )


def export_artifact_from_report(
    *,
    workspace_root: Path,
    report_file: Path,
    output_format: str,
    profile: str | None = None,
) -> ExportResult:
    """Re-emit a single artifact from a report-derived QSpec."""
    resolution = resolve_import_reference(ImportReference(report_file=report_file))
    return export_artifact_from_resolution(
        workspace_root=workspace_root,
        resolution=resolution,
        output_format=output_format,
        profile=profile,
    )


def export_artifact_from_resolution(
    *,
    workspace_root: Path,
    resolution: ImportResolution,
    output_format: str,
    profile: str | None = None,
) -> ExportResult:
    """Re-emit a single artifact from an already-resolved runtime input."""
    try:
        handle = WorkspaceManager.load_or_init(workspace_root)
    except WorkspaceLockConflict as exc:
        raise WorkspaceConflictError(
            workspace=Path(workspace_root).resolve(),
            lock_path=Path(exc.lock_path),
            holder=exc.holder.model_dump(mode="json"),
        ) from exc
    qspec = resolution.load_qspec()
    return _export_from_qspec(
        handle=handle,
        qspec=qspec,
        output_format=output_format,
        profile=profile,
        parameter_bindings=_export_parameter_bindings(qspec, resolution=resolution),
        resolution=resolution,
    )


def _export_from_qspec(
    *,
    handle: WorkspaceHandle,
    qspec: QSpec,
    output_format: str,
    profile: str | None = None,
    parameter_bindings: dict[str, float] | None = None,
    resolution: ImportResolution | None = None,
) -> ExportResult:
    if output_format not in {"qiskit", "qasm3", "classiq-python"}:
        return ExportResult(
            status="unsupported",
            format=output_format,
            profile=profile,
            reason="unsupported_export_format",
        )
    resolved_profile = _resolve_export_profile(output_format=output_format, profile=profile)
    if resolved_profile is None:
        return ExportResult(
            status="unsupported",
            format=output_format,
            profile=profile,
            reason="unsupported_export_profile",
        )
    try:
        with acquire_workspace_lock(handle.root, command=f"qrun export {output_format}"):
            if output_format == "qiskit":
                path = handle.root / "artifacts" / "qiskit" / "main.py"
                _guard_export_output(path)
                atomic_write_text(
                    path,
                    emit_qiskit_source(qspec, parameter_bindings=parameter_bindings),
                )
                return _build_export_result(
                    output_format=output_format,
                    profile=resolved_profile,
                    path=path,
                    resolution=resolution,
                )
            if output_format == "qasm3":
                path = handle.root / "artifacts" / "qasm" / "main.qasm"
                _guard_export_output(path)
                atomic_write_text(
                    path,
                    emit_qasm3_source(qspec, parameter_bindings=parameter_bindings),
                )
                return _build_export_result(
                    output_format=output_format,
                    profile=resolved_profile,
                    path=path,
                    resolution=resolution,
                )
            if output_format == "classiq-python":
                path = handle.root / "artifacts" / "classiq" / "main.py"
                _guard_export_output(path)
                result = emit_classiq_source(qspec, parameter_bindings=parameter_bindings)
                if result.status != "ok" or result.source is None:
                    return _build_export_result(
                        output_format=output_format,
                        profile=resolved_profile,
                        path=result.path,
                        reason=result.reason,
                        status=result.status,
                        resolution=resolution,
                    )
                atomic_write_text(path, result.source)
                return _build_export_result(
                    output_format=output_format,
                    profile=resolved_profile,
                    path=path,
                    resolution=resolution,
                )
    except WorkspaceLockConflict as exc:
        raise WorkspaceConflictError(
            workspace=handle.root,
            lock_path=Path(exc.lock_path),
            holder=exc.holder.model_dump(mode="json"),
        ) from exc
    return ExportResult(status="unsupported", format=output_format, profile=profile, reason="unsupported_export_format")


def _build_export_result(
    *,
    output_format: str,
    profile: str,
    path: Path | None,
    resolution: ImportResolution | None,
    status: Literal["ok", "unsupported"] = "ok",
    reason: str | None = None,
) -> ExportResult:
    artifact_hash = _sha256_file(path) if path is not None and path.exists() else None
    payload: dict[str, str | None] = {
        "status": status,
        "format": output_format,
        "profile": profile,
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


def _resolve_export_profile(*, output_format: str, profile: str | None) -> str | None:
    defaults = {
        "qiskit": "qiskit-native",
        "qasm3": "qasm3-generic",
        "classiq-python": "classiq-native",
    }
    aliases = {
        "qiskit": {"native": "qiskit-native", "qiskit-native": "qiskit-native"},
        "qasm3": {"generic": "qasm3-generic", "qasm3-generic": "qasm3-generic"},
        "classiq-python": {"native": "classiq-native", "classiq-native": "classiq-native"},
    }
    normalized = profile or defaults.get(output_format)
    if normalized is None:
        return None
    return aliases.get(output_format, {}).get(str(normalized))


def _guard_export_output(path: Path) -> None:
    pending_files = pending_atomic_write_files(path)
    if not pending_files:
        return
    raise WorkspaceRecoveryRequiredError(
        workspace=path.parents[2],
        pending_files=pending_files,
        last_valid_revision=None,
    )


def _resolve_current_export_resolution(
    *,
    handle: WorkspaceHandle,
    qspec_path: Path,
    qspec: QSpec,
) -> ImportResolution:
    latest_report_path = handle.root / "reports" / "latest.json"
    resolution = resolve_import_reference(
        ImportReference(report_file=latest_report_path, workspace_root=handle.root),
    )
    _validate_current_workspace_report(
        report_path=latest_report_path,
        report_payload=resolution.load_report(),
        qspec_path=qspec_path,
        qspec=qspec,
    )
    return resolution.model_copy(
        update={
            "source_kind": "workspace_current",
            "source": f"workspace:{handle.root}",
            "report_path": latest_report_path.resolve(),
            "qspec_path": qspec_path.resolve(),
        }
    )


def _validate_current_workspace_report(
    *,
    report_path: Path,
    report_payload: dict[str, object],
    qspec_path: Path,
    qspec: QSpec,
) -> None:
    qspec_block = report_payload.get("qspec") if isinstance(report_payload, dict) else {}
    replay_block = report_payload.get("replay_integrity") if isinstance(report_payload, dict) else {}
    expected_qspec_hash = _optional_string(
        replay_block.get("qspec_hash") if isinstance(replay_block, dict) else None
    ) or _optional_string(qspec_block.get("hash") if isinstance(qspec_block, dict) else None)
    actual_qspec_hash = _sha256_file(qspec_path)
    if expected_qspec_hash is not None and actual_qspec_hash != expected_qspec_hash:
        raise ImportSourceError(
            "report_qspec_hash_mismatch",
            source=str(report_path),
            details={"expected_hash": expected_qspec_hash, "actual_hash": actual_qspec_hash},
        )

    expected_semantic_hash = _optional_string(
        replay_block.get("qspec_semantic_hash") if isinstance(replay_block, dict) else None
    ) or _optional_string(qspec_block.get("semantic_hash") if isinstance(qspec_block, dict) else None)
    actual_semantic_hash = _optional_string(summarize_qspec_semantics(qspec).get("semantic_hash"))
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


def _export_parameter_bindings(
    qspec: QSpec,
    *,
    resolution: ImportResolution | None,
) -> dict[str, float] | None:
    if resolution is not None:
        report_payload = resolution.load_report()
        diagnostics = report_payload.get("diagnostics") if isinstance(report_payload, dict) else {}
        exports = diagnostics.get("exports") if isinstance(diagnostics, dict) else {}
        simulation = diagnostics.get("simulation") if isinstance(diagnostics, dict) else {}
        for raw_bindings in (
            exports.get("bindings") if isinstance(exports, dict) else None,
            simulation.get("representative_bindings") if isinstance(simulation, dict) else None,
            resolution.report_summary.get("representative_bindings")
            if isinstance(resolution.report_summary, dict)
            else None,
        ):
            bindings = _float_mapping(raw_bindings)
            if bindings:
                return bindings

    bindings = qspec_representative_bindings(qspec)
    return bindings or None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _float_mapping(value: object) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    return {
        str(name): float(raw_value)
        for name, raw_value in value.items()
    }


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
