"""Compare runtime inputs and reports through stable semantic summaries."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from quantum_runtime.runtime.imports import ImportResolution


CompareExpectation = Literal[
    "same-subject",
    "different-subject",
    "same-qspec",
    "different-qspec",
    "same-report",
    "different-report",
]


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
    diagnostic_delta: dict[str, Any] = Field(default_factory=dict)
    backend_delta: dict[str, Any] = Field(default_factory=dict)
    highlights: list[str] = Field(default_factory=list)
    report_drift_detected: bool = False
    backend_regressions: list[str] = Field(default_factory=list)
    policy: dict[str, Any] = Field(default_factory=dict)
    verdict: dict[str, Any] = Field(default_factory=dict)
    left: CompareSide
    right: CompareSide


class ComparePolicy(BaseModel):
    """Optional guardrail policy for compare results."""

    expect: CompareExpectation | None = None
    allow_report_drift: bool = True
    forbid_backend_regressions: bool = False


class CompareVerdict(BaseModel):
    """Policy verdict for a compare result."""

    status: Literal["not_requested", "pass", "fail"]
    summary: str
    failed_checks: list[str] = Field(default_factory=list)
    passed_checks: list[str] = Field(default_factory=list)


def compare_import_resolutions(
    left: ImportResolution,
    right: ImportResolution,
    *,
    policy: ComparePolicy | None = None,
) -> CompareResult:
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
    diagnostic_delta = _diagnostic_delta(left_report, right_report)
    backend_delta = _backend_delta(left_report, right_report)
    report_drift_detected = _report_drift_detected(
        report_delta=report_delta,
        diagnostic_delta=diagnostic_delta,
        backend_delta=backend_delta,
    )
    backend_regressions = _backend_regressions(left_report, right_report)
    differences = _differences(
        same_subject=same_subject,
        same_qspec=same_qspec,
        same_report=same_report,
        semantic_delta=semantic_delta,
        report_delta=report_delta,
        diagnostic_delta=diagnostic_delta,
        backend_delta=backend_delta,
    )
    highlights = _highlights(
        same_subject=same_subject,
        same_qspec=same_qspec,
        same_report=same_report,
        semantic_delta=semantic_delta,
        diagnostic_delta=diagnostic_delta,
        backend_delta=backend_delta,
        left_report=left_report,
        right_report=right_report,
    )
    verdict = _evaluate_policy(
        policy=policy,
        same_subject=same_subject,
        same_qspec=same_qspec,
        same_report=same_report,
        report_drift_detected=report_drift_detected,
        backend_regressions=backend_regressions,
    )

    return CompareResult(
        status="same_subject" if same_subject else "different_subject",
        same_subject=same_subject,
        same_qspec=same_qspec,
        same_report=same_report,
        differences=differences,
        semantic_delta=semantic_delta,
        report_delta=report_delta,
        diagnostic_delta=diagnostic_delta,
        backend_delta=backend_delta,
        highlights=highlights,
        report_drift_detected=report_drift_detected,
        backend_regressions=backend_regressions,
        policy=policy.model_dump(mode="json") if policy is not None else {},
        verdict=verdict.model_dump(mode="json"),
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


def _diagnostic_delta(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_resources = left.get("resource_summary")
    right_resources = right.get("resource_summary")
    fields = ("width", "depth", "two_qubit_gates", "measure_count", "parameter_count")
    changed_fields = [
        field
        for field in fields
        if _resource_value(left_resources, field) != _resource_value(right_resources, field)
    ]
    return {
        "simulation_status_changed": left.get("simulation_status") != right.get("simulation_status"),
        "transpile_status_changed": left.get("transpile_status") != right.get("transpile_status"),
        "resource_fields_changed": changed_fields,
        "left": {
            "simulation_status": left.get("simulation_status"),
            "transpile_status": left.get("transpile_status"),
            "resources": {
                field: _resource_value(left_resources, field)
                for field in fields
            },
        },
        "right": {
            "simulation_status": right.get("simulation_status"),
            "transpile_status": right.get("transpile_status"),
            "resources": {
                field: _resource_value(right_resources, field)
                for field in fields
            },
        },
    }


def _backend_delta(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_statuses = _string_mapping(left.get("backend_statuses"))
    right_statuses = _string_mapping(right.get("backend_statuses"))
    changed = {
        name: {
            "left": left_statuses.get(name),
            "right": right_statuses.get(name),
        }
        for name in sorted(set(left_statuses) & set(right_statuses))
        if left_statuses.get(name) != right_statuses.get(name)
    }
    return {
        "added": sorted(set(right_statuses) - set(left_statuses)),
        "removed": sorted(set(left_statuses) - set(right_statuses)),
        "status_changed": changed,
    }


def _report_drift_detected(
    *,
    report_delta: dict[str, Any],
    diagnostic_delta: dict[str, Any],
    backend_delta: dict[str, Any],
) -> bool:
    if report_delta.get("status_changed") or report_delta.get("input_mode_changed"):
        return True
    if report_delta.get("warning_count_delta") or report_delta.get("error_count_delta"):
        return True
    if report_delta.get("artifact_names_added") or report_delta.get("artifact_names_removed"):
        return True
    if report_delta.get("backend_names_added") or report_delta.get("backend_names_removed"):
        return True
    if diagnostic_delta.get("simulation_status_changed") or diagnostic_delta.get("transpile_status_changed"):
        return True
    resource_fields_changed = diagnostic_delta.get("resource_fields_changed")
    if isinstance(resource_fields_changed, list) and resource_fields_changed:
        return True
    status_changed = backend_delta.get("status_changed")
    if isinstance(status_changed, dict) and status_changed:
        return True
    return False


def _backend_regressions(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    left_statuses = _string_mapping(left.get("backend_statuses"))
    right_statuses = _string_mapping(right.get("backend_statuses"))
    regressions: list[str] = []

    for name, left_status in left_statuses.items():
        right_status = right_statuses.get(name)
        if right_status is None:
            regressions.append(name)
            continue
        if _status_rank(right_status) > _status_rank(left_status):
            regressions.append(name)
    return sorted(regressions)


def _differences(
    *,
    same_subject: bool,
    same_qspec: bool,
    same_report: bool,
    semantic_delta: dict[str, Any],
    report_delta: dict[str, Any],
    diagnostic_delta: dict[str, Any],
    backend_delta: dict[str, Any],
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
    if diagnostic_delta.get("simulation_status_changed"):
        differences.append("simulation_status_changed")
    if diagnostic_delta.get("transpile_status_changed"):
        differences.append("transpile_status_changed")
    resource_fields_changed = diagnostic_delta.get("resource_fields_changed")
    if isinstance(resource_fields_changed, list) and resource_fields_changed:
        differences.append("resource_metrics_changed:" + ",".join(str(field) for field in resource_fields_changed))
    status_changed = backend_delta.get("status_changed")
    if isinstance(status_changed, dict) and status_changed:
        differences.append("backend_status_changed")
    return differences


def _highlights(
    *,
    same_subject: bool,
    same_qspec: bool,
    same_report: bool,
    semantic_delta: dict[str, Any],
    diagnostic_delta: dict[str, Any],
    backend_delta: dict[str, Any],
    left_report: dict[str, Any],
    right_report: dict[str, Any],
) -> list[str]:
    highlights: list[str] = []

    if same_subject:
        pattern = semantic_delta.get("left", {}).get("pattern")
        highlights.append(f"Same workload identity ({pattern}) across both inputs.")
    else:
        left_pattern = semantic_delta.get("left", {}).get("pattern", "unknown")
        right_pattern = semantic_delta.get("right", {}).get("pattern", "unknown")
        highlights.append(f"Different workload identity: {left_pattern} -> {right_pattern}.")

    if same_subject and same_qspec and not same_report:
        highlights.append("Identical QSpec semantics, but report artifacts or runtime outputs differ.")
    elif same_subject and not same_qspec:
        highlights.append("Same workload identity, but serialized QSpec artifacts differ.")

    resource_fields_changed = diagnostic_delta.get("resource_fields_changed")
    if isinstance(resource_fields_changed, list) and resource_fields_changed:
        left_resources = diagnostic_delta.get("left", {}).get("resources", {})
        right_resources = diagnostic_delta.get("right", {}).get("resources", {})
        fields = ", ".join(
            f"{field} {left_resources.get(field)} -> {right_resources.get(field)}"
            for field in resource_fields_changed[:3]
        )
        highlights.append(f"Structural diagnostics changed: {fields}.")

    backend_status_changed = backend_delta.get("status_changed")
    if isinstance(backend_status_changed, dict) and backend_status_changed:
        fragments = ", ".join(
            f"{name} {delta.get('left')} -> {delta.get('right')}"
            for name, delta in sorted(backend_status_changed.items())
        )
        highlights.append(f"Backend status changes: {fragments}.")

    if backend_delta.get("added") or backend_delta.get("removed"):
        added = ",".join(str(name) for name in backend_delta.get("added", []))
        removed = ",".join(str(name) for name in backend_delta.get("removed", []))
        change_parts = []
        if added:
            change_parts.append(f"added {added}")
        if removed:
            change_parts.append(f"removed {removed}")
        highlights.append("Backend coverage changed: " + "; ".join(change_parts) + ".")

    warning_delta = int(right_report.get("warning_count", 0) or 0) - int(left_report.get("warning_count", 0) or 0)
    error_delta = int(right_report.get("error_count", 0) or 0) - int(left_report.get("error_count", 0) or 0)
    if warning_delta or error_delta:
        highlights.append(
            f"Quality signals changed: warnings {warning_delta:+d}, errors {error_delta:+d}."
        )

    return highlights


def _evaluate_policy(
    *,
    policy: ComparePolicy | None,
    same_subject: bool,
    same_qspec: bool,
    same_report: bool,
    report_drift_detected: bool,
    backend_regressions: list[str],
) -> CompareVerdict:
    if policy is None:
        return CompareVerdict(
            status="not_requested",
            summary="No compare policy requested.",
        )

    failed_checks: list[str] = []
    passed_checks: list[str] = []

    if policy.expect is not None:
        if _expectation_matches(
            expectation=policy.expect,
            same_subject=same_subject,
            same_qspec=same_qspec,
            same_report=same_report,
        ):
            passed_checks.append(f"expect:{policy.expect}")
        else:
            failed_checks.append(f"expect:{policy.expect}")

    if policy.allow_report_drift:
        passed_checks.append("report_drift:allowed")
    elif report_drift_detected:
        failed_checks.append("report_drift:forbidden")
    else:
        passed_checks.append("report_drift:clean")

    if policy.forbid_backend_regressions:
        if backend_regressions:
            failed_checks.append("backend_regressions:forbidden")
        else:
            passed_checks.append("backend_regressions:none")
    else:
        passed_checks.append("backend_regressions:allowed")

    if failed_checks:
        return CompareVerdict(
            status="fail",
            summary="Compare policy failed: " + ", ".join(failed_checks),
            failed_checks=failed_checks,
            passed_checks=passed_checks,
        )
    return CompareVerdict(
        status="pass",
        summary="Compare policy passed.",
        failed_checks=[],
        passed_checks=passed_checks,
    )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _string_mapping(value: object) -> dict[str, str | None]:
    if not isinstance(value, dict):
        return {}
    return {str(key): _optional_string(item) for key, item in value.items()}


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _resource_value(summary: object, field: str) -> Any:
    if not isinstance(summary, dict):
        return None
    return summary.get(field)


def _status_rank(status: str | None) -> int:
    ordering = {
        "ok": 0,
        "dependency_missing": 1,
        "backend_unavailable": 2,
        "error": 3,
    }
    if status is None:
        return 4
    return ordering.get(status, 4)


def _expectation_matches(
    *,
    expectation: CompareExpectation,
    same_subject: bool,
    same_qspec: bool,
    same_report: bool,
) -> bool:
    outcomes = {
        "same-subject": same_subject,
        "different-subject": not same_subject,
        "same-qspec": same_qspec,
        "different-qspec": not same_qspec,
        "same-report": same_report,
        "different-report": not same_report,
    }
    return outcomes[expectation]
