from __future__ import annotations

import json
import hashlib
from pathlib import Path

from quantum_runtime.runtime import (
    ComparePolicy,
    ImportReference,
    ImportResolution,
    compare_import_resolutions,
    compare_workspace_baseline,
    execute_intent,
    resolve_import_reference,
)
from quantum_runtime.workspace import WorkspaceBaseline, WorkspacePaths


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_compare_import_resolutions_detects_same_subject_across_workspaces(tmp_path: Path) -> None:
    left_workspace = tmp_path / ".quantum-left"
    right_workspace = tmp_path / ".quantum-right"
    intent_path = PROJECT_ROOT / "examples" / "intent-ghz.md"

    execute_intent(workspace_root=left_workspace, intent_file=intent_path)
    execute_intent(workspace_root=right_workspace, intent_file=intent_path)

    left = resolve_import_reference(ImportReference(workspace_root=left_workspace))
    right = resolve_import_reference(ImportReference(workspace_root=right_workspace))
    result = compare_import_resolutions(left, right)

    assert result.status == "same_subject"
    assert result.same_subject is True
    assert result.same_qspec is True
    assert result.same_report is False
    assert result.left.qspec_summary["pattern"] == "ghz"
    assert result.right.qspec_summary["pattern"] == "ghz"
    assert "report_artifact_changed" in result.differences
    assert result.report_drift_detected is False
    assert result.verdict["status"] == "not_requested"
    assert result.highlights[0] == "Same workload identity (ghz) across both inputs."
    assert result.highlights[1] == "Identical QSpec semantics, but report artifacts or runtime outputs differ."


def test_compare_import_resolutions_tracks_parameter_workflow_execution_drift() -> None:
    left = _synthetic_resolution(
        revision="rev_000001",
        pattern="qaoa_ansatz",
        workload_hash="sha256:same-workload",
        execution_hash="sha256:exec-defaults",
        qspec_hash="sha256:qspec-left",
        report_hash="sha256:report-left",
        report_status="ok",
        backend_statuses={"qiskit-local": "ok"},
        observable_count=1,
        parameter_workflow_mode="defaults",
    )
    right = _synthetic_resolution(
        revision="rev_000002",
        pattern="qaoa_ansatz",
        workload_hash="sha256:same-workload",
        execution_hash="sha256:exec-sweep",
        qspec_hash="sha256:qspec-right",
        report_hash="sha256:report-right",
        report_status="ok",
        backend_statuses={"qiskit-local": "ok"},
        observable_count=1,
        parameter_workflow_mode="sweep",
    )

    result = compare_import_resolutions(left, right)

    assert result.same_subject is True
    assert result.status == "same_subject"
    assert "parameter_workflow_mode" in result.semantic_delta["changed_fields"]
    assert "execution_hash" in result.semantic_delta["changed_fields"]


def test_compare_import_resolutions_surfaces_parameterized_expectation_drift() -> None:
    left = _synthetic_resolution(
        revision="rev_000001",
        pattern="qaoa_ansatz",
        workload_hash="sha256:same-workload",
        execution_hash="sha256:same-execution",
        qspec_hash="sha256:qspec-left",
        report_hash="sha256:report-left",
        report_status="ok",
        backend_statuses={"qiskit-local": "ok"},
        observable_count=1,
        parameter_workflow_mode="sweep",
        representative_point_label="sweep_000",
        representative_expectations={"maxcut_cost": 1.25},
        best_point={
            "label": "sweep_000",
            "objective_observable": "maxcut_cost",
            "objective": "maximize",
            "objective_value": 1.25,
        },
    )
    right = _synthetic_resolution(
        revision="rev_000002",
        pattern="qaoa_ansatz",
        workload_hash="sha256:same-workload",
        execution_hash="sha256:same-execution",
        qspec_hash="sha256:qspec-right",
        report_hash="sha256:report-right",
        report_status="ok",
        backend_statuses={"qiskit-local": "ok"},
        observable_count=1,
        parameter_workflow_mode="sweep",
        representative_point_label="sweep_003",
        representative_expectations={"maxcut_cost": 1.75},
        best_point={
            "label": "sweep_003",
            "objective_observable": "maxcut_cost",
            "objective": "maximize",
            "objective_value": 1.75,
        },
    )

    result = compare_import_resolutions(left, right)

    assert result.same_subject is True
    assert result.report_drift_detected is True
    assert "execution_diagnostics_changed" in result.differences
    assert any("Best sweep point changed:" in highlight for highlight in result.highlights)


def test_compare_import_resolutions_detects_semantic_drift_across_revisions(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    execute_intent(
        workspace_root=workspace,
        intent_file=PROJECT_ROOT / "examples" / "intent-ghz.md",
    )
    execute_intent(
        workspace_root=workspace,
        intent_file=PROJECT_ROOT / "examples" / "intent-qaoa-maxcut.md",
    )

    left = resolve_import_reference(ImportReference(workspace_root=workspace, revision="rev_000001"))
    right = resolve_import_reference(ImportReference(workspace_root=workspace, revision="rev_000002"))
    result = compare_import_resolutions(left, right)

    assert result.status == "different_subject"
    assert result.same_subject is False
    assert result.same_qspec is False
    assert result.same_report is False
    assert result.semantic_delta["left"]["pattern"] == "ghz"
    assert result.semantic_delta["right"]["pattern"] == "qaoa_ansatz"
    assert "pattern" in result.semantic_delta["changed_fields"]
    assert "parameter_count" in result.semantic_delta["changed_fields"]
    assert any(diff.startswith("semantic_subject_changed") for diff in result.differences)
    assert result.report_drift_detected is True
    assert result.diagnostic_delta["resource_fields_changed"] == [
        "depth",
        "two_qubit_gates",
        "parameter_count",
    ]
    assert result.highlights[0] == "Different workload identity: ghz -> qaoa_ansatz."
    assert any("Structural diagnostics changed:" in highlight for highlight in result.highlights)


def test_compare_import_resolutions_policy_passes_for_same_subject_without_drift(tmp_path: Path) -> None:
    left_workspace = tmp_path / ".quantum-left"
    right_workspace = tmp_path / ".quantum-right"
    intent_path = PROJECT_ROOT / "examples" / "intent-ghz.md"

    execute_intent(workspace_root=left_workspace, intent_file=intent_path)
    execute_intent(workspace_root=right_workspace, intent_file=intent_path)

    left = resolve_import_reference(ImportReference(workspace_root=left_workspace))
    right = resolve_import_reference(ImportReference(workspace_root=right_workspace))
    result = compare_import_resolutions(
        left,
        right,
        policy=ComparePolicy(expect="same-subject", allow_report_drift=False),
    )

    assert result.verdict["status"] == "pass"
    assert result.verdict["failed_checks"] == []
    assert "expect:same-subject" in result.verdict["passed_checks"]
    assert "report_drift:clean" in result.verdict["passed_checks"]


def test_compare_import_resolutions_policy_fails_for_wrong_subject_expectation(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    execute_intent(
        workspace_root=workspace,
        intent_file=PROJECT_ROOT / "examples" / "intent-ghz.md",
    )
    execute_intent(
        workspace_root=workspace,
        intent_file=PROJECT_ROOT / "examples" / "intent-qaoa-maxcut.md",
    )

    left = resolve_import_reference(ImportReference(workspace_root=workspace, revision="rev_000001"))
    right = resolve_import_reference(ImportReference(workspace_root=workspace, revision="rev_000002"))
    result = compare_import_resolutions(
        left,
        right,
        policy=ComparePolicy(expect="same-subject"),
    )

    assert result.verdict["status"] == "fail"
    assert "expect:same-subject" in result.verdict["failed_checks"]


def test_compare_import_resolutions_policy_passes_for_different_subject_expectation(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    execute_intent(
        workspace_root=workspace,
        intent_file=PROJECT_ROOT / "examples" / "intent-ghz.md",
    )
    execute_intent(
        workspace_root=workspace,
        intent_file=PROJECT_ROOT / "examples" / "intent-qaoa-maxcut.md",
    )

    left = resolve_import_reference(ImportReference(workspace_root=workspace, revision="rev_000001"))
    right = resolve_import_reference(ImportReference(workspace_root=workspace, revision="rev_000002"))
    result = compare_import_resolutions(
        left,
        right,
        policy=ComparePolicy(expect="different-subject"),
    )

    assert result.same_subject is False
    assert result.verdict["status"] == "pass"
    assert "expect:different-subject" in result.verdict["passed_checks"]


def test_compare_import_resolutions_policy_fails_on_backend_regression() -> None:
    left = _synthetic_resolution(
        revision="rev_000001",
        pattern="ghz",
        workload_hash="sha256:same",
        execution_hash="sha256:same",
        qspec_hash="sha256:qspec",
        report_hash="sha256:left",
        report_status="ok",
        backend_statuses={"classiq": "ok"},
    )
    right = _synthetic_resolution(
        revision="rev_000002",
        pattern="ghz",
        workload_hash="sha256:same",
        execution_hash="sha256:same",
        qspec_hash="sha256:qspec",
        report_hash="sha256:right",
        report_status="degraded",
        backend_statuses={"classiq": "dependency_missing"},
    )

    result = compare_import_resolutions(
        left,
        right,
        policy=ComparePolicy(
            expect="same-subject",
            forbid_backend_regressions=True,
        ),
    )

    assert result.same_subject is True
    assert result.backend_regressions == ["classiq"]
    assert result.verdict["status"] == "fail"
    assert "backend_regressions:forbidden" in result.verdict["failed_checks"]


def test_compare_import_resolutions_surfaces_replay_integrity_regression() -> None:
    left = _synthetic_resolution(
        revision="rev_000001",
        pattern="ghz",
        workload_hash="sha256:same",
        execution_hash="sha256:same",
        qspec_hash="sha256:qspec",
        report_hash="sha256:left",
        report_status="ok",
        backend_statuses={"qiskit-local": "ok"},
        replay_integrity={
            "status": "ok",
            "warnings": [],
            "verified_artifacts": ["qiskit_code"],
            "missing_artifacts": [],
            "mismatched_artifacts": [],
        },
    )
    right = _synthetic_resolution(
        revision="rev_000002",
        pattern="ghz",
        workload_hash="sha256:same",
        execution_hash="sha256:same",
        qspec_hash="sha256:qspec",
        report_hash="sha256:right",
        report_status="ok",
        backend_statuses={"qiskit-local": "ok"},
        replay_integrity={
            "status": "legacy",
            "warnings": ["artifact_output_digests_missing"],
            "verified_artifacts": [],
            "missing_artifacts": [],
            "mismatched_artifacts": [],
        },
    )

    result = compare_import_resolutions(left, right)

    assert result.left.replay_integrity["status"] == "ok"
    assert result.right.replay_integrity["status"] == "legacy"
    assert result.replay_integrity_delta["status_changed"] is True
    assert result.replay_integrity_delta["left"]["status"] == "ok"
    assert result.replay_integrity_delta["right"]["status"] == "legacy"
    assert result.replay_integrity_delta["warnings_added"] == ["artifact_output_digests_missing"]
    assert result.replay_integrity_regressions == ["status:ok->legacy"]
    assert "replay_integrity_changed" in result.differences
    assert any("Replay trust changed: ok -> legacy." == highlight for highlight in result.highlights)


def test_compare_import_resolutions_policy_fails_on_replay_integrity_regression() -> None:
    left = _synthetic_resolution(
        revision="rev_000001",
        pattern="ghz",
        workload_hash="sha256:same",
        execution_hash="sha256:same",
        qspec_hash="sha256:qspec",
        report_hash="sha256:left",
        report_status="ok",
        backend_statuses={"qiskit-local": "ok"},
        replay_integrity={
            "status": "ok",
            "warnings": [],
            "verified_artifacts": ["qiskit_code"],
            "missing_artifacts": [],
            "mismatched_artifacts": [],
        },
    )
    right = _synthetic_resolution(
        revision="rev_000002",
        pattern="ghz",
        workload_hash="sha256:same",
        execution_hash="sha256:same",
        qspec_hash="sha256:qspec",
        report_hash="sha256:right",
        report_status="ok",
        backend_statuses={"qiskit-local": "ok"},
        replay_integrity={
            "status": "degraded",
            "warnings": ["artifact_outputs_missing"],
            "verified_artifacts": [],
            "missing_artifacts": ["qiskit_code"],
            "mismatched_artifacts": [],
        },
    )

    result = compare_import_resolutions(
        left,
        right,
        policy=ComparePolicy(
            expect="same-subject",
            forbid_replay_integrity_regressions=True,
        ),
    )

    assert result.replay_integrity_regressions == ["status:ok->degraded", "missing_artifacts:qiskit_code"]
    assert result.verdict["status"] == "fail"
    assert "replay_integrity_regressions:forbidden" in result.verdict["failed_checks"]


def test_compare_import_resolutions_keeps_same_subject_for_execution_config_changes() -> None:
    left = _synthetic_resolution(
        revision="rev_000001",
        pattern="ghz",
        workload_hash="sha256:workload",
        execution_hash="sha256:exec-left",
        qspec_hash="sha256:qspec-left",
        report_hash="sha256:report-left",
        report_status="ok",
        backend_statuses={"qiskit-local": "ok"},
        constraints={"max_depth": 64, "optimization_level": 2},
        backend_preferences=["qiskit-local"],
    )
    right = _synthetic_resolution(
        revision="rev_000002",
        pattern="ghz",
        workload_hash="sha256:workload",
        execution_hash="sha256:exec-right",
        qspec_hash="sha256:qspec-right",
        report_hash="sha256:report-right",
        report_status="ok",
        backend_statuses={"qiskit-local": "ok", "classiq": "backend_unavailable"},
        constraints={"max_depth": 128, "optimization_level": 3, "backend_name": "mock-backend"},
        backend_preferences=["qiskit-local", "classiq"],
    )

    result = compare_import_resolutions(left, right)

    assert result.same_subject is True
    assert result.status == "same_subject"
    assert result.same_qspec is False
    assert result.left.qspec_summary["workload_hash"] == result.right.qspec_summary["workload_hash"]
    assert result.left.qspec_summary["execution_hash"] != result.right.qspec_summary["execution_hash"]
    assert result.semantic_delta["changed_fields"] == ["execution_hash"]
    assert result.highlights[0] == "Same workload identity (ghz) across both inputs."


def test_compare_workspace_baseline_uses_saved_baseline_record(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    execute_intent(
        workspace_root=workspace,
        intent_file=PROJECT_ROOT / "examples" / "intent-ghz.md",
    )
    baseline_resolution = resolve_import_reference(ImportReference(workspace_root=workspace))
    WorkspaceBaseline.from_import_resolution(baseline_resolution).save(
        WorkspacePaths(root=workspace).baseline_current_json
    )

    execute_intent(
        workspace_root=workspace,
        intent_file=PROJECT_ROOT / "examples" / "intent-qaoa-maxcut.md",
    )

    result = compare_workspace_baseline(workspace)

    assert result.status == "different_subject"
    assert result.baseline is not None
    assert result.baseline["side"] == "left"
    assert result.baseline["path"].endswith("baselines/current.json")
    assert result.baseline["revision"] == "rev_000001"
    assert result.left.revision == "rev_000001"
    assert result.right.revision == "rev_000002"
    assert result.left.qspec_summary["pattern"] == "ghz"
    assert result.right.qspec_summary["pattern"] == "qaoa_ansatz"


def _synthetic_resolution(
    *,
    revision: str,
    pattern: str,
    workload_hash: str,
    execution_hash: str,
    qspec_hash: str,
    report_hash: str,
    report_status: str,
    backend_statuses: dict[str, str],
    observable_count: int = 0,
    parameter_workflow_mode: str = "defaults",
    representative_point_label: str = "defaults",
    representative_expectations: dict[str, float] | None = None,
    best_point: dict[str, object] | None = None,
    constraints: dict[str, object] | None = None,
    backend_preferences: list[str] | None = None,
    replay_integrity: dict[str, object] | None = None,
) -> ImportResolution:
    replay_payload = replay_integrity or {
        "status": "ok",
        "warnings": [],
        "verified_artifacts": ["qiskit_code"],
        "missing_artifacts": [],
        "mismatched_artifacts": [],
    }
    representative_expectations_payload = representative_expectations or {}
    best_point_payload = best_point
    return ImportResolution(
        source_kind="report_revision",
        source=f"revision:{revision}",
        workspace_root=Path("/tmp/synthetic-workspace"),
        workspace_manifest_path=Path("/tmp/synthetic-workspace/workspace.json"),
        workspace_project_id="synthetic",
        revision=revision,
        report_path=Path(f"/tmp/synthetic-workspace/reports/history/{revision}.json"),
        qspec_path=Path(f"/tmp/synthetic-workspace/specs/history/{revision}.json"),
        report_hash=report_hash,
        qspec_hash=qspec_hash,
        input_mode="intent",
        input_path="synthetic.md",
        report_status=report_status,
        qspec_status="ok",
        qspec_summary={
            "pattern": pattern,
            "width": 4,
            "layers": None,
            "parameter_count": 0,
            "observable_count": observable_count,
            "parameter_workflow_mode": parameter_workflow_mode,
            "workload_hash": workload_hash,
            "execution_hash": execution_hash,
            "semantic_hash": execution_hash,
            "constraints": constraints or {},
            "backend_preferences": backend_preferences or ["qiskit-local"],
        },
        report_summary={
            "status": report_status,
            "input_mode": "intent",
            "artifact_names": ["qiskit_code", "report"],
            "backend_names": sorted(backend_statuses),
            "backend_statuses": backend_statuses,
            "simulation_status": "ok",
            "transpile_status": "ok",
            "resource_summary": {
                "width": 4,
                "depth": 5,
                "two_qubit_gates": 3,
                "measure_count": 4,
                "parameter_count": 0,
            },
            "warning_count": 0,
            "error_count": 0,
            "parameter_mode": parameter_workflow_mode,
            "representative_point_label": representative_point_label,
            "representative_expectations": representative_expectations_payload,
            "representative_expectations_hash": _stable_hash(representative_expectations_payload),
            "best_point": best_point_payload,
            "best_point_hash": _stable_hash(best_point_payload),
            "replay_integrity_status": replay_payload["status"],
            "replay_integrity_warnings": replay_payload["warnings"],
            "replay_integrity_missing_artifacts": replay_payload["missing_artifacts"],
            "replay_integrity_mismatched_artifacts": replay_payload["mismatched_artifacts"],
        },
        replay_integrity=replay_payload,
        artifacts={},
        provenance={},
    )


def _stable_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"
