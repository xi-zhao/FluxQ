from __future__ import annotations

from pathlib import Path

from quantum_runtime.backends import ClassiqBackendReport
from quantum_runtime.diagnostics.benchmark import run_structural_benchmark
from quantum_runtime.intent.parser import parse_intent_file
from quantum_runtime.intent.planner import plan_to_qspec
from quantum_runtime.workspace import WorkspaceManager


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_run_structural_benchmark_reports_qiskit_and_classiq_statuses(
    tmp_path: Path,
    monkeypatch,
) -> None:
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    qspec.backend_preferences.append("classiq")
    qspec.constraints.basis_gates = ["h", "cx", "measure"]
    qspec.constraints.connectivity_map = [(0, 1), (1, 2), (2, 3)]

    monkeypatch.setattr(
        "quantum_runtime.diagnostics.benchmark.run_classiq_backend",
        lambda qspec, workspace, parameter_bindings=None: ClassiqBackendReport(
            status="dependency_missing",
            reason="classiq_not_installed",
            code_path=workspace.root / "artifacts" / "classiq" / "main.py",
        ),
    )

    report = run_structural_benchmark(qspec, handle, ["qiskit-local", "classiq"])

    assert report.status == "degraded"
    assert report.subject["pattern"] == "ghz"
    assert report.subject["parameter_count"] == 0
    assert report.backends["qiskit-local"].status == "ok"
    assert report.backends["qiskit-local"].width == 4
    assert report.backends["qiskit-local"].depth == 5
    assert report.backends["qiskit-local"].transpiled_depth == 5
    assert report.backends["qiskit-local"].two_qubit_gates == 3
    assert report.backends["qiskit-local"].details["resource_source"] == "qiskit_local"
    assert report.backends["qiskit-local"].details["benchmark_mode"] == "target_aware"
    assert report.backends["qiskit-local"].details["comparable"] is True
    assert report.backends["qiskit-local"].details["comparability_reason"] == "target_aware_transpile"
    assert report.backends["qiskit-local"].details["transpile_status"] == "ok"
    assert report.backends["qiskit-local"].details["transpile_performed"] is True
    assert any("local" in note.lower() for note in report.backends["qiskit-local"].notes)
    assert report.backends["classiq"].status == "dependency_missing"
    assert report.backends["classiq"].reason == "classiq_not_installed"
    assert report.backends["classiq"].details["benchmark_mode"] == "unavailable"
    assert report.backends["classiq"].details["comparable"] is False
    assert report.backends["classiq"].details["fallback_reason"] == "classiq_not_installed"
    assert any("dependency" in note.lower() for note in report.backends["classiq"].notes)


def test_run_structural_benchmark_uses_classiq_synthesis_metrics(
    tmp_path: Path,
    monkeypatch,
) -> None:
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    qspec.backend_preferences.append("classiq")

    monkeypatch.setattr(
        "quantum_runtime.diagnostics.benchmark.run_classiq_backend",
        lambda qspec, workspace, parameter_bindings=None: ClassiqBackendReport(
            status="ok",
            reason=None,
            code_path=workspace.root / "artifacts" / "classiq" / "main.py",
            synthesis_metrics={
                "width": 8,
                "depth": 11,
                "two_qubit_gates": 5,
                "measure_count": 4,
            },
            details={
                "resource_source": "classiq_synthesis",
                "synthesis_metrics": {
                    "width": 8,
                    "depth": 11,
                    "two_qubit_gates": 5,
                    "measure_count": 4,
                },
                "target_assumptions": {
                    "applied_constraints": {"max_width": 4},
                    "applied_preferences": {"optimization_level": 2},
                    "unsupported_constraints": [],
                },
            },
        ),
    )

    report = run_structural_benchmark(qspec, handle, ["classiq"])

    classiq = report.backends["classiq"]
    assert report.status == "ok"
    assert report.subject["semantic_hash"].startswith("sha256:")
    assert classiq.status == "ok"
    assert classiq.width == 8
    assert classiq.depth == 11
    assert classiq.transpiled_depth == 11
    assert classiq.two_qubit_gates == 5
    assert classiq.transpiled_two_qubit_gates == 5
    assert classiq.measure_count == 4
    assert classiq.details["resource_source"] == "classiq_synthesis"
    assert classiq.details["benchmark_mode"] == "synthesis_backed"
    assert classiq.details["comparable"] is False
    assert classiq.details["target_parity"] == "partial"
    assert classiq.details["comparability_reason"] == "partial_target_parity"
    assert classiq.details["parameter_count"] == 0
    assert classiq.details["synthesis_metrics"] == {
        "width": 8,
        "depth": 11,
        "two_qubit_gates": 5,
        "measure_count": 4,
    }
    assert classiq.details["target_assumptions"]["applied_constraints"] == {"max_width": 4}
    assert classiq.details["target_assumptions"]["unsupported_constraints"] == []


def test_run_structural_benchmark_falls_back_when_classiq_metrics_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    qspec.backend_preferences.append("classiq")

    monkeypatch.setattr(
        "quantum_runtime.diagnostics.benchmark.run_classiq_backend",
        lambda qspec, workspace, parameter_bindings=None: ClassiqBackendReport(
            status="ok",
            reason=None,
            code_path=workspace.root / "artifacts" / "classiq" / "main.py",
            synthesis_metrics={},
            details={},
        ),
    )

    report = run_structural_benchmark(qspec, handle, ["classiq"])

    classiq = report.backends["classiq"]
    assert report.status == "ok"
    assert classiq.status == "ok"
    assert classiq.width == 4
    assert classiq.depth == 5
    assert classiq.transpiled_depth == 5
    assert classiq.two_qubit_gates == 3
    assert classiq.transpiled_two_qubit_gates == 3
    assert classiq.measure_count == 4
    assert classiq.details["resource_source"] == "qspec_baseline"
    assert classiq.details["benchmark_mode"] == "structural_only"
    assert classiq.details["comparable"] is False
    assert classiq.details["fallback_reason"] == "missing_synthesis_metrics"
    assert classiq.details["target_parity"] == "unavailable"
    assert classiq.details["comparability_reason"] == "missing_synthesis_metrics"
    assert classiq.details["target_assumptions"]["unsupported_constraints"] == []
    assert classiq.details["semantic_hash"].startswith("sha256:")
    assert any("fallback" in note.lower() for note in classiq.notes)


def test_run_structural_benchmark_marks_qiskit_transpile_metrics_as_skipped(
    tmp_path: Path,
) -> None:
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    qspec.constraints.max_depth = None
    qspec.constraints.basis_gates = None
    qspec.constraints.connectivity_map = None

    report = run_structural_benchmark(qspec, handle, ["qiskit-local"])

    qiskit_local = report.backends["qiskit-local"]
    assert qiskit_local.status == "ok"
    assert qiskit_local.transpiled_depth is None
    assert qiskit_local.transpiled_two_qubit_gates is None
    assert qiskit_local.details["benchmark_mode"] == "structural_only"
    assert qiskit_local.details["comparable"] is False
    assert qiskit_local.details["comparability_reason"] == "no_target_constraints"
    assert qiskit_local.details["transpile_status"] == "skipped"
    assert qiskit_local.details["transpile_performed"] is False
    assert any("skipped" in note.lower() for note in qiskit_local.notes)


def test_run_structural_benchmark_marks_qiskit_target_validation_failures_as_errors(
    tmp_path: Path,
) -> None:
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    qspec.constraints.basis_gates = ["h", "cx", "measure"]
    qspec.constraints.connectivity_map = [(0, 1)]

    report = run_structural_benchmark(qspec, handle, ["qiskit-local"])

    qiskit_local = report.backends["qiskit-local"]
    assert report.status == "error"
    assert qiskit_local.status == "error"
    assert qiskit_local.reason == "target_validation_failed"
    assert qiskit_local.details["benchmark_mode"] == "target_aware"
    assert qiskit_local.details["comparable"] is False
    assert qiskit_local.details["transpile_status"] == "error"
    assert qiskit_local.details["error"] is not None
    assert "coupling" in qiskit_local.details["error"].lower() or "connected" in qiskit_local.details["error"].lower()
    assert any("failed" in note.lower() for note in qiskit_local.notes)
