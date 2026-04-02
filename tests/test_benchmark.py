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
    assert report.backends["qiskit-local"].status == "ok"
    assert report.backends["qiskit-local"].width == 4
    assert report.backends["qiskit-local"].depth == 5
    assert report.backends["qiskit-local"].two_qubit_gates == 3
    assert report.backends["classiq"].status == "dependency_missing"
    assert report.backends["classiq"].reason == "classiq_not_installed"
