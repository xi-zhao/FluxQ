from __future__ import annotations

import json
from pathlib import Path

from quantum_runtime.diagnostics.diagrams import write_diagrams
from quantum_runtime.diagnostics.resources import estimate_resources
from quantum_runtime.diagnostics.simulate import run_local_simulation
from quantum_runtime.intent.parser import parse_intent_file
from quantum_runtime.intent.planner import plan_to_qspec
from quantum_runtime.reporters.summary import summarize_report
from quantum_runtime.reporters.writer import write_report
from quantum_runtime.workspace import WorkspaceManager


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_write_report_persists_latest_report(tmp_path: Path) -> None:
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")
    revision = handle.reserve_revision()

    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)

    qspec_path = handle.root / "specs" / "current.json"
    qspec_path.write_text(qspec.model_dump_json(indent=2))

    diagrams = write_diagrams(qspec, handle)
    simulation = run_local_simulation(qspec, shots=64)
    resources = estimate_resources(qspec)

    report = write_report(
        workspace=handle,
        revision=revision,
        input_data={"mode": "intent", "path": "examples/intent-ghz.md"},
        qspec=qspec,
        qspec_path=qspec_path,
        artifacts={
            "qspec": str(qspec_path),
            "diagram_txt": str(diagrams.text_path),
            "diagram_png": str(diagrams.png_path),
        },
        diagnostics={
            "simulation": simulation.model_dump(mode="json"),
            "resources": resources.model_dump(mode="json"),
            "diagram": {
                "text_path": str(diagrams.text_path),
                "png_path": str(diagrams.png_path),
            },
        },
        backend_reports={},
        warnings=[],
        errors=[],
    )

    latest_path = handle.root / "reports" / "latest.json"
    assert latest_path.exists()

    payload = json.loads(latest_path.read_text())
    assert payload["status"] == "ok"
    assert payload["revision"] == revision
    assert payload["qspec"]["path"] == str(qspec_path)
    assert payload["qspec"]["semantic_hash"] == payload["semantics"]["semantic_hash"]
    assert payload["semantics"]["semantic_hash"] == payload["semantics"]["execution_hash"]
    assert payload["semantics"]["workload_hash"].startswith("sha256:")
    assert payload["semantics"]["execution_hash"].startswith("sha256:")
    assert payload["provenance"]["workspace_root"] == str(handle.root)
    assert payload["provenance"]["revision"] == revision
    assert payload["provenance"]["input"]["mode"] == "intent"
    assert payload["provenance"]["input"]["path"] == "examples/intent-ghz.md"
    assert payload["provenance"]["subject"]["pattern"] == "ghz"
    assert payload["provenance"]["subject"]["parameter_count"] == 0
    assert payload["semantics"]["pattern"] == "ghz"
    assert payload["semantics"]["parameter_count"] == 0
    assert payload["diagnostics"]["simulation"]["status"] == "ok"
    assert payload["diagnostics"]["resources"]["two_qubit_gates"] == 3
    assert payload["artifacts"]["diagram_png"] == str(diagrams.png_path)
    assert "suggestions" in payload
    assert report == payload


def test_write_report_records_revision_artifact_provenance(tmp_path: Path) -> None:
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")
    revision = handle.reserve_revision()

    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)

    qspec_path = handle.root / "specs" / "history" / f"{revision}.json"
    qspec_path.write_text(qspec.model_dump_json(indent=2))

    snapshot_root = handle.root / "artifacts" / "history" / revision
    qiskit_snapshot = snapshot_root / "qiskit" / "main.py"
    diagram_txt_snapshot = snapshot_root / "figures" / "circuit.txt"
    diagram_png_snapshot = snapshot_root / "figures" / "circuit.png"
    for path, content in (
        (qiskit_snapshot, "from qiskit import QuantumCircuit\n"),
        (diagram_txt_snapshot, "q0: --H--\n"),
        (diagram_png_snapshot, "png"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    report = write_report(
        workspace=handle,
        revision=revision,
        input_data={"mode": "intent", "path": "examples/intent-ghz.md"},
        qspec=qspec,
        qspec_path=qspec_path,
        artifacts={
            "qspec": str(qspec_path),
            "qiskit_code": str(qiskit_snapshot),
            "diagram_txt": str(diagram_txt_snapshot),
            "diagram_png": str(diagram_png_snapshot),
        },
        diagnostics={
            "simulation": {"status": "ok", "shots": 64},
            "resources": {"width": 4, "depth": 4, "two_qubit_gates": 3},
            "diagram": {
                "text_path": str(diagram_txt_snapshot),
                "png_path": str(diagram_png_snapshot),
            },
        },
        backend_reports={},
        warnings=[],
        errors=[],
    )

    artifact_provenance = report["provenance"]["artifacts"]
    assert artifact_provenance["snapshot_root"] == str(snapshot_root)
    assert artifact_provenance["current_root"] == str(handle.root / "artifacts")
    assert artifact_provenance["paths"]["qiskit_code"] == str(qiskit_snapshot)
    assert artifact_provenance["paths"]["diagram_txt"] == str(diagram_txt_snapshot)
    assert artifact_provenance["current_aliases"]["qiskit_code"] == str(
        handle.root / "artifacts" / "qiskit" / "main.py"
    )
    assert artifact_provenance["current_aliases"]["diagram_png"] == str(
        handle.root / "artifacts" / "figures" / "circuit.png"
    )


def test_summarize_report_keeps_key_signals_short(tmp_path: Path) -> None:
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")
    revision = handle.reserve_revision()

    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    qspec_path = handle.root / "specs" / "current.json"
    qspec_path.write_text(qspec.model_dump_json(indent=2))

    diagrams = write_diagrams(qspec, handle)
    simulation = run_local_simulation(qspec, shots=64)
    resources = estimate_resources(qspec)

    report = write_report(
        workspace=handle,
        revision=revision,
        input_data={"mode": "intent", "path": "examples/intent-ghz.md"},
        qspec=qspec,
        qspec_path=qspec_path,
        artifacts={
            "qspec": str(qspec_path),
            "diagram_txt": str(diagrams.text_path),
            "diagram_png": str(diagrams.png_path),
        },
        diagnostics={
            "simulation": simulation.model_dump(mode="json"),
            "resources": resources.model_dump(mode="json"),
            "diagram": {
                "text_path": str(diagrams.text_path),
                "png_path": str(diagrams.png_path),
            },
        },
        backend_reports={},
        warnings=[],
        errors=[],
    )

    summary = summarize_report(report)
    golden = (PROJECT_ROOT / "tests" / "golden" / "report_summary_ghz.txt").read_text().strip()
    normalized_summary = summary.replace(revision, "<revision>").replace(str(qspec_path), "<qspec_path>")

    assert len(summary) <= 1200
    assert revision in summary
    assert "status" in summary.lower()
    assert "artifacts" in summary.lower()
    assert "simulation" in summary.lower()
    assert "next" in summary.lower()
    assert normalized_summary == golden


def test_write_report_adds_backend_specific_suggestions(tmp_path: Path) -> None:
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")
    revision = handle.reserve_revision()
    qspec_path = handle.root / "specs" / "current.json"
    qspec_path.write_text('{"version":"0.1"}')

    report = write_report(
        workspace=handle,
        revision=revision,
        input_data={"mode": "intent", "path": "examples/intent-ghz.md"},
        qspec=plan_to_qspec(parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")),
        qspec_path=qspec_path,
        artifacts={"qspec": str(qspec_path)},
        diagnostics={"simulation": {"status": "ok", "shots": 32}},
        backend_reports={
            "classiq": {
                "status": "dependency_missing",
                "reason": "classiq_not_installed",
            }
        },
        warnings=[],
        errors=[],
    )

    assert report["status"] == "degraded"
    assert any("classiq" in suggestion.lower() for suggestion in report["suggestions"])
    assert any("install" in suggestion.lower() for suggestion in report["suggestions"])
