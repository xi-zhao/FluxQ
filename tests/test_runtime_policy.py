from __future__ import annotations

from quantum_runtime.diagnostics.benchmark import BackendBenchmark, BenchmarkReport
from quantum_runtime.runtime.doctor import DoctorReport
from quantum_runtime.runtime.policy import BenchmarkPolicy, apply_benchmark_policy, apply_doctor_policy


def _benchmark_report(
    *,
    workload_hash: str,
    semantic_hash: str,
    depth: int = 5,
    two_qubit_gates: int = 3,
    comparable: bool = True,
    backend_status: str = "ok",
) -> BenchmarkReport:
    return BenchmarkReport(
        status="ok",
        subject={
            "pattern": "ghz",
            "workload_hash": workload_hash,
            "semantic_hash": semantic_hash,
        },
        backends={
            "qiskit-local": BackendBenchmark(
                backend="qiskit-local",
                status=backend_status,
                width=3,
                depth=depth,
                two_qubit_gates=two_qubit_gates,
                measure_count=3,
                details={
                    "comparable": comparable,
                    "comparability_reason": "target_aware_transpile" if comparable else "structural_only",
                },
            )
        },
    )


def test_apply_benchmark_policy_fails_when_subject_changes() -> None:
    baseline = _benchmark_report(
        workload_hash="sha256:baseline",
        semantic_hash="sha256:baseline-semantic",
    )
    current = _benchmark_report(
        workload_hash="sha256:current",
        semantic_hash="sha256:current-semantic",
    )

    result = apply_benchmark_policy(
        report=current,
        baseline_report=baseline,
        baseline_revision="rev_000001",
        policy=BenchmarkPolicy(),
    )

    assert result.verdict["status"] == "fail"
    assert result.reason_codes == ["benchmark_subject_changed"]
    assert result.gate["ready"] is False


def test_apply_benchmark_policy_fails_when_backend_metric_regresses() -> None:
    baseline = _benchmark_report(
        workload_hash="sha256:same",
        semantic_hash="sha256:same-semantic",
        depth=4,
    )
    current = _benchmark_report(
        workload_hash="sha256:same",
        semantic_hash="sha256:same-semantic",
        depth=5,
    )

    result = apply_benchmark_policy(
        report=current,
        baseline_report=baseline,
        baseline_revision="rev_000001",
        policy=BenchmarkPolicy(max_depth_regression=0),
    )

    assert result.verdict["status"] == "fail"
    assert "benchmark_metric_regressed:qiskit-local:depth" in result.reason_codes
    assert result.gate["ready"] is False


def test_apply_doctor_policy_maps_issues_and_advisories_into_ci_fields() -> None:
    report = DoctorReport(
        status="degraded",
        workspace_ok=True,
        workspace={
            "root": "/tmp/.quantum",
            "root_exists": True,
        },
        dependencies={},
        issues=["active_report_missing", "classiq unavailable: No module named 'classiq'"],
        advisories=["optional_backend_unavailable"],
    )

    result = apply_doctor_policy(report=report)

    assert result.blocking_issues == ["active_report_missing", "classiq unavailable: No module named 'classiq'"]
    assert result.advisory_issues == ["optional_backend_unavailable"]
    assert result.verdict["status"] == "fail"
    assert result.gate["ready"] is False
    assert "doctor_blocking_issue:active_report_missing" in result.reason_codes
    assert "doctor_advisory_issue:optional_backend_unavailable" in result.reason_codes
