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
    assert payload["diagnostics"]["simulation"]["status"] == "ok"
    assert payload["diagnostics"]["resources"]["two_qubit_gates"] == 3
    assert payload["artifacts"]["diagram_png"] == str(diagrams.png_path)
    assert "suggestions" in payload
    assert report == payload


def test_summarize_report_keeps_key_signals_short(tmp_path: Path) -> None:
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")
    revision = handle.reserve_revision()
    qspec_path = handle.root / "specs" / "current.json"
    qspec_path.write_text('{"version":"0.1"}')

    report = write_report(
        workspace=handle,
        revision=revision,
        input_data={"mode": "intent", "path": "examples/intent-ghz.md"},
        qspec_path=qspec_path,
        artifacts={"qspec": str(qspec_path)},
        diagnostics={"simulation": {"status": "ok", "shots": 32}},
        backend_reports={},
        warnings=[],
        errors=[],
    )

    summary = summarize_report(report)

    assert len(summary) <= 1200
    assert revision in summary
    assert "status" in summary.lower()
    assert "artifacts" in summary.lower()
    assert "simulation" in summary.lower()
    assert "next" in summary.lower()


def test_write_report_adds_backend_specific_suggestions(tmp_path: Path) -> None:
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")
    revision = handle.reserve_revision()
    qspec_path = handle.root / "specs" / "current.json"
    qspec_path.write_text('{"version":"0.1"}')

    report = write_report(
        workspace=handle,
        revision=revision,
        input_data={"mode": "intent", "path": "examples/intent-ghz.md"},
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
