"""Compare runtime inputs and reports through stable semantic summaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from quantum_runtime.errors import WorkspaceConflictError, WorkspaceRecoveryRequiredError
from quantum_runtime.runtime.contracts import ensure_schema_payload
from quantum_runtime.runtime.observability import gate_block, next_actions_for_reason_codes, normalize_reason_codes
from quantum_runtime.runtime.imports import (
    ImportResolution,
    resolve_workspace_baseline,
    resolve_workspace_current,
)
from quantum_runtime.workspace import (
    WorkspaceLockConflict,
    acquire_workspace_lock,
    atomic_write_text,
    pending_atomic_write_files,
)


CompareExpectation = Literal[
    "same-subject",
    "different-subject",
    "same-qspec",
    "different-qspec",
    "same-report",
    "different-report",
]

CompareFailOn = Literal[
    "subject_drift",
    "qspec_drift",
    "report_drift",
    "backend_regression",
    "replay_integrity_regression",
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
    replay_integrity: dict[str, Any] = Field(default_factory=dict)
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
    replay_integrity_delta: dict[str, Any] = Field(default_factory=dict)
    highlights: list[str] = Field(default_factory=list)
    detached_report_inputs: list[str] = Field(default_factory=list)
    report_drift_detected: bool = False
    backend_regressions: list[str] = Field(default_factory=list)
    replay_integrity_regressions: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    gate: dict[str, Any] = Field(default_factory=dict)
    policy: dict[str, Any] = Field(default_factory=dict)
    verdict: dict[str, Any] = Field(default_factory=dict)
    baseline: dict[str, Any] | None = None
    left: CompareSide
    right: CompareSide


class ComparePolicy(BaseModel):
    """Optional guardrail policy for compare results."""

    expect: CompareExpectation | None = None
    fail_on: list[CompareFailOn] = Field(default_factory=list)
    allow_report_drift: bool = True
    forbid_backend_regressions: bool = False
    forbid_replay_integrity_regressions: bool = False


class CompareVerdict(BaseModel):
    """Policy verdict for a compare result."""

    status: Literal["not_requested", "pass", "fail"]
    summary: str
    failed_checks: list[str] = Field(default_factory=list)
    passed_checks: list[str] = Field(default_factory=list)


def compare_workspace_baseline(
    workspace_root: Path,
    *,
    policy: ComparePolicy | None = None,
) -> CompareResult:
    """Compare the saved workspace baseline against the current workspace state."""
    baseline = resolve_workspace_baseline(workspace_root)
    current = resolve_workspace_current(workspace_root)
    result = compare_import_resolutions(
        baseline.resolution,
        current,
        policy=policy,
    )
    return result.model_copy(
        update={
            "baseline": {
                "side": "left",
                "path": str(baseline.record_path),
                "source_kind": baseline.record.source_kind,
                "source": baseline.record.source,
                "revision": baseline.record.revision,
            }
        }
    )


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
    left_replay_integrity = left.replay_integrity if isinstance(left.replay_integrity, dict) else {}
    right_replay_integrity = right.replay_integrity if isinstance(right.replay_integrity, dict) else {}

    left_workload_hash = _identity_hash(left_qspec, preferred_key="workload_hash")
    right_workload_hash = _identity_hash(right_qspec, preferred_key="workload_hash")
    same_subject = bool(left_workload_hash and left_workload_hash == right_workload_hash)
    same_qspec = left.qspec_hash == right.qspec_hash
    same_report = left.report_hash == right.report_hash

    semantic_delta = _semantic_delta(left_qspec, right_qspec)
    report_delta = _report_delta(left_report, right_report)
    diagnostic_delta = _diagnostic_delta(left_report, right_report)
    backend_delta = _backend_delta(left_report, right_report)
    replay_integrity_delta = _replay_integrity_delta(left_replay_integrity, right_replay_integrity)
    detached_report_inputs = _detached_report_inputs(left, right)
    report_drift_detected = _report_drift_detected(
        report_delta=report_delta,
        diagnostic_delta=diagnostic_delta,
        backend_delta=backend_delta,
    )
    backend_regressions = _backend_regressions(left_report, right_report)
    replay_integrity_regressions = _replay_integrity_regressions(
        left_replay_integrity,
        right_replay_integrity,
    )
    differences = _differences(
        same_subject=same_subject,
        same_qspec=same_qspec,
        same_report=same_report,
        semantic_delta=semantic_delta,
        report_delta=report_delta,
        diagnostic_delta=diagnostic_delta,
        backend_delta=backend_delta,
        replay_integrity_delta=replay_integrity_delta,
        replay_integrity_regressions=replay_integrity_regressions,
    )
    highlights = _highlights(
        same_subject=same_subject,
        same_qspec=same_qspec,
        same_report=same_report,
        semantic_delta=semantic_delta,
        report_delta=report_delta,
        diagnostic_delta=diagnostic_delta,
        backend_delta=backend_delta,
        replay_integrity_delta=replay_integrity_delta,
        detached_report_inputs=detached_report_inputs,
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
        replay_integrity_regressions=replay_integrity_regressions,
    )
    reason_codes = _reason_codes(
        differences=differences,
        replay_integrity_regressions=replay_integrity_regressions,
        verdict=verdict.model_dump(mode="json"),
    )
    next_actions = next_actions_for_reason_codes(reason_codes) or (["review_compare"] if differences else [])
    gate_ready = same_subject and not replay_integrity_regressions and verdict.status != "fail"
    severity: Literal["info", "warning", "error"]
    if verdict.status == "fail":
        severity = "error"
    elif differences or replay_integrity_regressions:
        severity = "warning"
    else:
        severity = "info"

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
        replay_integrity_delta=replay_integrity_delta,
        highlights=highlights,
        detached_report_inputs=detached_report_inputs,
        report_drift_detected=report_drift_detected,
        backend_regressions=backend_regressions,
        replay_integrity_regressions=replay_integrity_regressions,
        reason_codes=reason_codes,
        next_actions=next_actions,
        gate=gate_block(
            ready=gate_ready,
            severity=severity,
            reason_codes=reason_codes,
            next_actions=next_actions,
        ),
        policy=policy.model_dump(mode="json") if policy is not None else {},
        verdict=verdict.model_dump(mode="json"),
        left=_compare_side(left),
        right=_compare_side(right),
    )


def persist_compare_result(*, workspace_root: Path, result: CompareResult) -> dict[str, str]:
    """Persist the latest compare result into the workspace."""
    compare_root = workspace_root / "compare"
    history_root = compare_root / "history"
    latest_path = compare_root / "latest.json"
    history_path = history_root / f"{_compare_history_name(result)}.json"
    serialized = json.dumps(ensure_schema_payload(result), indent=2, ensure_ascii=True)
    try:
        with acquire_workspace_lock(workspace_root, command="qrun compare"):
            pending_files = pending_atomic_write_files(latest_path)
            if pending_files:
                raise WorkspaceRecoveryRequiredError(
                    workspace=workspace_root.resolve(),
                    pending_files=pending_files,
                    last_valid_revision=None,
                )
            history_root.mkdir(parents=True, exist_ok=True)
            atomic_write_text(latest_path, serialized)
            atomic_write_text(history_path, serialized)
    except WorkspaceLockConflict as exc:
        raise WorkspaceConflictError(
            workspace=workspace_root.resolve(),
            lock_path=Path(exc.lock_path),
            holder=exc.holder.model_dump(mode="json"),
        ) from exc
    return {"latest_path": str(latest_path), "history_path": str(history_path)}


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
        replay_integrity=resolution.replay_integrity,
        provenance=resolution.provenance,
    )


def _compare_history_name(result: CompareResult) -> str:
    if result.baseline is not None:
        return f"baseline__{result.right.revision}"
    return f"{result.left.revision}__{result.right.revision}"


def _reason_codes(
    *,
    differences: list[str],
    replay_integrity_regressions: list[str],
    verdict: dict[str, Any],
) -> list[str]:
    codes: list[str] = []
    for difference in differences:
        if difference.startswith("semantic_subject_changed"):
            codes.append("semantic_subject_changed")
        else:
            codes.append(f"compare_difference:{difference}")
    if replay_integrity_regressions:
        codes.append("replay_integrity_regressed")
    if verdict.get("status") == "fail":
        codes.append("compare_policy_failed")
    return normalize_reason_codes(codes)


def _semantic_delta(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "pattern",
        "width",
        "layers",
        "parameter_count",
        "observable_count",
        "parameter_workflow_mode",
        "workload_hash",
        "execution_hash",
    )
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
    left_output_digests = _string_mapping(left.get("artifact_output_digests"))
    right_output_digests = _string_mapping(right.get("artifact_output_digests"))
    changed_outputs = [
        name
        for name in sorted(set(left_output_digests) | set(right_output_digests))
        if left_output_digests.get(name) != right_output_digests.get(name)
    ]
    left_missing_outputs = set(_string_list(left.get("artifact_output_missing")))
    right_missing_outputs = set(_string_list(right.get("artifact_output_missing")))
    return {
        "status_changed": left.get("status") != right.get("status"),
        "input_mode_changed": left.get("input_mode") != right.get("input_mode"),
        "artifact_names_added": sorted(right_artifacts - left_artifacts),
        "artifact_names_removed": sorted(left_artifacts - right_artifacts),
        "artifact_output_set_hash_changed": (
            left.get("artifact_output_set_hash") != right.get("artifact_output_set_hash")
        ),
        "artifact_output_names_changed": changed_outputs,
        "artifact_output_missing_added": sorted(right_missing_outputs - left_missing_outputs),
        "artifact_output_missing_removed": sorted(left_missing_outputs - right_missing_outputs),
        "backend_names_added": sorted(right_backends - left_backends),
        "backend_names_removed": sorted(left_backends - right_backends),
        "warning_count_delta": int(right.get("warning_count", 0) or 0) - int(left.get("warning_count", 0) or 0),
        "error_count_delta": int(right.get("error_count", 0) or 0) - int(left.get("error_count", 0) or 0),
    }


def _diagnostic_delta(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_resources = left.get("resource_summary")
    right_resources = right.get("resource_summary")
    fields = ("width", "depth", "two_qubit_gates", "measure_count", "parameter_count")
    execution_fields = (
        "parameter_mode",
        "representative_point_label",
        "representative_bindings_hash",
        "representative_expectations_hash",
        "best_point_hash",
        "export_point_label",
        "export_parameter_mode",
        "export_bindings_hash",
    )
    changed_fields = [
        field
        for field in fields
        if _resource_value(left_resources, field) != _resource_value(right_resources, field)
    ]
    execution_fields_changed = [
        field
        for field in execution_fields
        if left.get(field) != right.get(field)
    ]
    return {
        "simulation_status_changed": left.get("simulation_status") != right.get("simulation_status"),
        "transpile_status_changed": left.get("transpile_status") != right.get("transpile_status"),
        "resource_fields_changed": changed_fields,
        "execution_fields_changed": execution_fields_changed,
        "left": {
            "simulation_status": left.get("simulation_status"),
            "parameter_mode": left.get("parameter_mode"),
            "representative_point_label": left.get("representative_point_label"),
            "representative_expectations": left.get("representative_expectations"),
            "best_point": left.get("best_point"),
            "export_point_label": left.get("export_point_label"),
            "transpile_status": left.get("transpile_status"),
            "resources": {
                field: _resource_value(left_resources, field)
                for field in fields
            },
        },
        "right": {
            "simulation_status": right.get("simulation_status"),
            "parameter_mode": right.get("parameter_mode"),
            "representative_point_label": right.get("representative_point_label"),
            "representative_expectations": right.get("representative_expectations"),
            "best_point": right.get("best_point"),
            "export_point_label": right.get("export_point_label"),
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


def _replay_integrity_delta(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_warnings = set(_string_list(left.get("warnings")))
    right_warnings = set(_string_list(right.get("warnings")))
    left_missing = set(_string_list(left.get("missing_artifacts")))
    right_missing = set(_string_list(right.get("missing_artifacts")))
    left_mismatched = set(_string_list(left.get("mismatched_artifacts")))
    right_mismatched = set(_string_list(right.get("mismatched_artifacts")))
    return {
        "status_changed": left.get("status") != right.get("status"),
        "warnings_added": sorted(right_warnings - left_warnings),
        "warnings_removed": sorted(left_warnings - right_warnings),
        "missing_artifacts_added": sorted(right_missing - left_missing),
        "missing_artifacts_removed": sorted(left_missing - right_missing),
        "mismatched_artifacts_added": sorted(right_mismatched - left_mismatched),
        "mismatched_artifacts_removed": sorted(left_mismatched - right_mismatched),
        "left": {
            "status": left.get("status"),
            "warnings": sorted(left_warnings),
            "missing_artifacts": sorted(left_missing),
            "mismatched_artifacts": sorted(left_mismatched),
            "verified_artifacts": _string_list(left.get("verified_artifacts")),
        },
        "right": {
            "status": right.get("status"),
            "warnings": sorted(right_warnings),
            "missing_artifacts": sorted(right_missing),
            "mismatched_artifacts": sorted(right_mismatched),
            "verified_artifacts": _string_list(right.get("verified_artifacts")),
        },
    }


def _detached_report_inputs(left: ImportResolution, right: ImportResolution) -> list[str]:
    detached: list[str] = []
    for side_name, resolution in (("left", left), ("right", right)):
        if resolution.source_kind != "report_file":
            continue
        try:
            report_path = resolution.report_path.resolve()
            reports_root = resolution.workspace_root.resolve() / "reports"
            if not report_path.is_relative_to(reports_root):
                detached.append(side_name)
        except OSError:
            detached.append(side_name)
    return detached


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
    if report_delta.get("artifact_output_names_changed"):
        return True
    if report_delta.get("artifact_output_missing_added") or report_delta.get("artifact_output_missing_removed"):
        return True
    if report_delta.get("backend_names_added") or report_delta.get("backend_names_removed"):
        return True
    if diagnostic_delta.get("simulation_status_changed") or diagnostic_delta.get("transpile_status_changed"):
        return True
    resource_fields_changed = diagnostic_delta.get("resource_fields_changed")
    if isinstance(resource_fields_changed, list) and resource_fields_changed:
        return True
    execution_fields_changed = diagnostic_delta.get("execution_fields_changed")
    if isinstance(execution_fields_changed, list) and execution_fields_changed:
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


def _replay_integrity_regressions(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    regressions: list[str] = []
    left_status = _optional_string(left.get("status"))
    right_status = _optional_string(right.get("status"))
    if _replay_integrity_rank(right_status) > _replay_integrity_rank(left_status):
        regressions.append(f"status:{left_status or 'unknown'}->{right_status or 'unknown'}")

    for name in sorted(set(_string_list(right.get("missing_artifacts"))) - set(_string_list(left.get("missing_artifacts")))):
        regressions.append(f"missing_artifacts:{name}")
    for name in sorted(set(_string_list(right.get("mismatched_artifacts"))) - set(_string_list(left.get("mismatched_artifacts")))):
        regressions.append(f"mismatched_artifacts:{name}")
    return regressions


def _differences(
    *,
    same_subject: bool,
    same_qspec: bool,
    same_report: bool,
    semantic_delta: dict[str, Any],
    report_delta: dict[str, Any],
    diagnostic_delta: dict[str, Any],
    backend_delta: dict[str, Any],
    replay_integrity_delta: dict[str, Any],
    replay_integrity_regressions: list[str],
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
    if report_delta.get("artifact_output_names_changed"):
        differences.append("artifact_outputs_changed")
    if report_delta.get("artifact_output_missing_added") or report_delta.get("artifact_output_missing_removed"):
        differences.append("artifact_outputs_missing_changed")
    if report_delta.get("backend_names_added") or report_delta.get("backend_names_removed"):
        differences.append("backend_set_changed")
    if diagnostic_delta.get("simulation_status_changed"):
        differences.append("simulation_status_changed")
    if diagnostic_delta.get("transpile_status_changed"):
        differences.append("transpile_status_changed")
    resource_fields_changed = diagnostic_delta.get("resource_fields_changed")
    if isinstance(resource_fields_changed, list) and resource_fields_changed:
        differences.append("resource_metrics_changed:" + ",".join(str(field) for field in resource_fields_changed))
    execution_fields_changed = diagnostic_delta.get("execution_fields_changed")
    if isinstance(execution_fields_changed, list) and execution_fields_changed:
        differences.append("execution_diagnostics_changed")
    status_changed = backend_delta.get("status_changed")
    if isinstance(status_changed, dict) and status_changed:
        differences.append("backend_status_changed")
    if (
        replay_integrity_delta.get("status_changed")
        or replay_integrity_delta.get("warnings_added")
        or replay_integrity_delta.get("warnings_removed")
        or replay_integrity_delta.get("missing_artifacts_added")
        or replay_integrity_delta.get("missing_artifacts_removed")
        or replay_integrity_delta.get("mismatched_artifacts_added")
        or replay_integrity_delta.get("mismatched_artifacts_removed")
    ):
        differences.append("replay_integrity_changed")
    if replay_integrity_regressions:
        differences.append("replay_integrity_regressed")
    return differences


def _highlights(
    *,
    same_subject: bool,
    same_qspec: bool,
    same_report: bool,
    semantic_delta: dict[str, Any],
    report_delta: dict[str, Any],
    diagnostic_delta: dict[str, Any],
    backend_delta: dict[str, Any],
    replay_integrity_delta: dict[str, Any],
    detached_report_inputs: list[str],
    left_report: dict[str, Any],
    right_report: dict[str, Any],
) -> list[str]:
    highlights: list[str] = []

    if replay_integrity_delta.get("status_changed"):
        left_status = replay_integrity_delta.get("left", {}).get("status", "unknown")
        right_status = replay_integrity_delta.get("right", {}).get("status", "unknown")
        highlights.append(f"Replay trust changed: {left_status} -> {right_status}.")

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

    changed_outputs = report_delta.get("artifact_output_names_changed")
    if isinstance(changed_outputs, list) and changed_outputs:
        names = ", ".join(str(name) for name in changed_outputs[:4])
        highlights.append(f"Generated artifact outputs changed: {names}.")

    if detached_report_inputs:
        sides = ", ".join(detached_report_inputs)
        highlights.append(f"Detached report replay input on: {sides}.")

    warnings_added = replay_integrity_delta.get("warnings_added")
    if isinstance(warnings_added, list) and warnings_added:
        names = ", ".join(str(name) for name in warnings_added[:4])
        highlights.append(f"Replay integrity warnings added: {names}.")

    missing_added = replay_integrity_delta.get("missing_artifacts_added")
    if isinstance(missing_added, list) and missing_added:
        names = ", ".join(str(name) for name in missing_added[:4])
        highlights.append(f"Replay artifacts missing on right side: {names}.")

    resource_fields_changed = diagnostic_delta.get("resource_fields_changed")
    if isinstance(resource_fields_changed, list) and resource_fields_changed:
        left_resources = diagnostic_delta.get("left", {}).get("resources", {})
        right_resources = diagnostic_delta.get("right", {}).get("resources", {})
        fields = ", ".join(
            f"{field} {left_resources.get(field)} -> {right_resources.get(field)}"
            for field in resource_fields_changed[:3]
        )
        highlights.append(f"Structural diagnostics changed: {fields}.")

    execution_fields_changed = diagnostic_delta.get("execution_fields_changed")
    if isinstance(execution_fields_changed, list) and execution_fields_changed:
        left_best_raw = diagnostic_delta.get("left", {}).get("best_point")
        right_best_raw = diagnostic_delta.get("right", {}).get("best_point")
        left_best = left_best_raw if isinstance(left_best_raw, dict) else {}
        right_best = right_best_raw if isinstance(right_best_raw, dict) else {}
        left_name = left_best.get("objective_observable")
        right_name = right_best.get("objective_observable")
        left_value = left_best.get("objective_value")
        right_value = right_best.get("objective_value")
        if left_name and right_name and left_value is not None and right_value is not None:
            highlights.append(
                f"Best sweep point changed: {left_name} {left_value} -> {right_value}."
            )
        else:
            left_label = diagnostic_delta.get("left", {}).get("representative_point_label")
            right_label = diagnostic_delta.get("right", {}).get("representative_point_label")
            highlights.append(
                f"Representative execution point changed: {left_label} -> {right_label}."
            )

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
    replay_integrity_regressions: list[str],
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

    for gate in policy.fail_on:
        if gate == "subject_drift":
            if same_subject:
                passed_checks.append("subject_drift")
            else:
                failed_checks.append("subject_drift")
        elif gate == "qspec_drift":
            if same_qspec:
                passed_checks.append("qspec_drift")
            else:
                failed_checks.append("qspec_drift")
        elif gate == "report_drift":
            if report_drift_detected:
                failed_checks.append("report_drift")
            else:
                passed_checks.append("report_drift")
        elif gate == "backend_regression":
            if backend_regressions:
                failed_checks.append("backend_regression")
            else:
                passed_checks.append("backend_regression")
        elif gate == "replay_integrity_regression":
            if replay_integrity_regressions:
                failed_checks.append("replay_integrity_regression")
            else:
                passed_checks.append("replay_integrity_regression")

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

    if policy.forbid_replay_integrity_regressions:
        if replay_integrity_regressions:
            failed_checks.append("replay_integrity_regressions:forbidden")
        else:
            passed_checks.append("replay_integrity_regressions:none")
    else:
        passed_checks.append("replay_integrity_regressions:allowed")

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


def _identity_hash(summary: dict[str, Any], *, preferred_key: str) -> str | None:
    value = summary.get(preferred_key)
    if value is None:
        value = summary.get("semantic_hash")
    return _optional_string(value)


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


def _replay_integrity_rank(status: str | None) -> int:
    ordering = {
        "ok": 0,
        "legacy": 1,
        "degraded": 2,
    }
    if status is None:
        return 3
    return ordering.get(status, 3)


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
