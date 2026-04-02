from __future__ import annotations

from pathlib import Path

from quantum_runtime.runtime import (
    ComparePolicy,
    ImportReference,
    ImportResolution,
    compare_import_resolutions,
    execute_intent,
    resolve_import_reference,
)


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
    constraints: dict[str, object] | None = None,
    backend_preferences: list[str] | None = None,
) -> ImportResolution:
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
        },
        artifacts={},
        provenance={},
    )
