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

    monkeypatch.setattr(
        "quantum_runtime.diagnostics.benchmark.run_classiq_backend",
        lambda qspec, workspace: ClassiqBackendReport(
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
    assert any("local" in note.lower() for note in report.backends["qiskit-local"].notes)
    assert report.backends["classiq"].status == "dependency_missing"
    assert report.backends["classiq"].reason == "classiq_not_installed"
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
        lambda qspec, workspace: ClassiqBackendReport(
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
    assert classiq.details["parameter_count"] == 0
    assert classiq.details["synthesis_metrics"] == {
        "width": 8,
        "depth": 11,
        "two_qubit_gates": 5,
        "measure_count": 4,
    }


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
        lambda qspec, workspace: ClassiqBackendReport(
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
    assert qiskit_local.details["transpile_status"] == "skipped"
    assert qiskit_local.details["transpile_performed"] is False
    assert any("skipped" in note.lower() for note in qiskit_local.notes)
