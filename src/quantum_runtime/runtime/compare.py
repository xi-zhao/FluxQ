"""Compare runtime inputs and reports through stable semantic summaries."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from quantum_runtime.runtime.imports import ImportResolution


class CompareSide(BaseModel):
    """Compact description of one side of a runtime comparison."""

    source_kind: str
    source: str
    workspace_root: str
    revision: str
    report_path: str
    qspec_path: str
    report_hash: str
    qspec_hash: str
    report_status: str | None = None
    qspec_summary: dict[str, Any] = Field(default_factory=dict)
    report_summary: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)


class CompareResult(BaseModel):
    """Machine-readable workload comparison result."""

    status: Literal["same_subject", "different_subject"]
    same_subject: bool
    same_qspec: bool
    same_report: bool
    differences: list[str] = Field(default_factory=list)
    semantic_delta: dict[str, Any] = Field(default_factory=dict)
    report_delta: dict[str, Any] = Field(default_factory=dict)
    left: CompareSide
    right: CompareSide


def compare_import_resolutions(left: ImportResolution, right: ImportResolution) -> CompareResult:
    """Compare two resolved runtime inputs for workload and report equality."""
    left_qspec = left.qspec_summary if isinstance(left.qspec_summary, dict) else {}
    right_qspec = right.qspec_summary if isinstance(right.qspec_summary, dict) else {}
    left_report = left.report_summary if isinstance(left.report_summary, dict) else {}
    right_report = right.report_summary if isinstance(right.report_summary, dict) else {}

    left_semantic_hash = left_qspec.get("semantic_hash")
    right_semantic_hash = right_qspec.get("semantic_hash")
    same_subject = bool(left_semantic_hash and left_semantic_hash == right_semantic_hash)
    same_qspec = left.qspec_hash == right.qspec_hash
    same_report = left.report_hash == right.report_hash

    semantic_delta = _semantic_delta(left_qspec, right_qspec)
    report_delta = _report_delta(left_report, right_report)
    differences = _differences(
        same_subject=same_subject,
        same_qspec=same_qspec,
        same_report=same_report,
        semantic_delta=semantic_delta,
        report_delta=report_delta,
    )

    return CompareResult(
        status="same_subject" if same_subject else "different_subject",
        same_subject=same_subject,
        same_qspec=same_qspec,
        same_report=same_report,
        differences=differences,
        semantic_delta=semantic_delta,
        report_delta=report_delta,
        left=_compare_side(left),
        right=_compare_side(right),
    )


def _compare_side(resolution: ImportResolution) -> CompareSide:
    return CompareSide(
        source_kind=resolution.source_kind,
        source=resolution.source,
        workspace_root=str(resolution.workspace_root),
        revision=resolution.revision,
        report_path=str(resolution.report_path),
        qspec_path=str(resolution.qspec_path),
        report_hash=resolution.report_hash,
        qspec_hash=resolution.qspec_hash,
        report_status=resolution.report_status,
        qspec_summary=resolution.qspec_summary,
        report_summary=resolution.report_summary,
        provenance=resolution.provenance,
    )


def _semantic_delta(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    fields = ("pattern", "width", "layers", "parameter_count", "semantic_hash")
    changed_fields = [
        field
        for field in fields
        if left.get(field) != right.get(field)
    ]
    return {
        "changed_fields": changed_fields,
        "left": {field: left.get(field) for field in fields},
        "right": {field: right.get(field) for field in fields},
    }


def _report_delta(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_artifacts = set(_string_list(left.get("artifact_names")))
    right_artifacts = set(_string_list(right.get("artifact_names")))
    left_backends = set(_string_list(left.get("backend_names")))
    right_backends = set(_string_list(right.get("backend_names")))
    return {
        "status_changed": left.get("status") != right.get("status"),
        "input_mode_changed": left.get("input_mode") != right.get("input_mode"),
        "artifact_names_added": sorted(right_artifacts - left_artifacts),
        "artifact_names_removed": sorted(left_artifacts - right_artifacts),
        "backend_names_added": sorted(right_backends - left_backends),
        "backend_names_removed": sorted(left_backends - right_backends),
        "warning_count_delta": int(right.get("warning_count", 0) or 0) - int(left.get("warning_count", 0) or 0),
        "error_count_delta": int(right.get("error_count", 0) or 0) - int(left.get("error_count", 0) or 0),
    }


def _differences(
    *,
    same_subject: bool,
    same_qspec: bool,
    same_report: bool,
    semantic_delta: dict[str, Any],
    report_delta: dict[str, Any],
) -> list[str]:
    differences: list[str] = []
    if not same_subject:
        changed_fields = semantic_delta.get("changed_fields", [])
        if isinstance(changed_fields, list) and changed_fields:
            differences.append("semantic_subject_changed:" + ",".join(str(field) for field in changed_fields))
        else:
            differences.append("semantic_subject_changed")
    if same_subject and not same_qspec:
        differences.append("qspec_file_changed")
    if same_subject and not same_report:
        differences.append("report_artifact_changed")
    if report_delta.get("status_changed"):
        differences.append("report_status_changed")
    if report_delta.get("input_mode_changed"):
        differences.append("report_input_mode_changed")
    if report_delta.get("warning_count_delta"):
        differences.append("warning_count_changed")
    if report_delta.get("error_count_delta"):
        differences.append("error_count_changed")
    if report_delta.get("artifact_names_added") or report_delta.get("artifact_names_removed"):
        differences.append("artifact_set_changed")
    if report_delta.get("backend_names_added") or report_delta.get("backend_names_removed"):
        differences.append("backend_set_changed")
    return differences


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]
