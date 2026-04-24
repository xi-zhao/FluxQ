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
        promote_latest=True,
    )

    latest_path = handle.root / "reports" / "latest.json"
    assert latest_path.exists()

    payload = json.loads(latest_path.read_text())
    assert payload["status"] == "ok"
    assert payload["revision"] == revision
    assert payload["qspec"]["path"] == str(handle.root / "specs" / "history" / f"{revision}.json")
    assert payload["qspec"]["semantic_hash"] == payload["semantics"]["semantic_hash"]
    assert payload["semantics"]["semantic_hash"] == payload["semantics"]["execution_hash"]
    assert payload["semantics"]["workload_hash"].startswith("sha256:")
    assert payload["semantics"]["execution_hash"].startswith("sha256:")
    assert payload["replay_integrity"]["qspec_hash"] == payload["qspec"]["hash"]
    assert payload["replay_integrity"]["qspec_semantic_hash"] == payload["qspec"]["semantic_hash"]
    assert sorted(payload["replay_integrity"]["artifact_output_digests"]) == ["diagram_png", "diagram_txt"]
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
    assert payload["artifacts"]["diagram_png"] == str(
        handle.root / "artifacts" / "history" / revision / "figures" / "circuit.png"
    )
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
    assert report["qspec"]["path"] == str(handle.root / "specs" / "history" / f"{revision}.json")
    assert report["artifacts"]["qspec"] == str(handle.root / "specs" / "history" / f"{revision}.json")
    assert report["artifacts"]["report"] == str(handle.root / "reports" / "history" / f"{revision}.json")
    assert report["artifacts"]["qiskit_code"] == str(qiskit_snapshot)
    assert report["diagnostics"]["diagram"]["text_path"] == str(diagram_txt_snapshot)
    assert report["diagnostics"]["diagram"]["png_path"] == str(diagram_png_snapshot)
    assert artifact_provenance["snapshot_root"] == str(snapshot_root)
    assert artifact_provenance["current_root"] == str(handle.root / "artifacts")
    assert artifact_provenance["paths"]["qiskit_code"] == str(qiskit_snapshot)
    assert artifact_provenance["paths"]["diagram_txt"] == str(diagram_txt_snapshot)
    assert artifact_provenance["current_aliases"]["qiskit_code"] == str(
        handle.root / "artifacts" / "qiskit" / "main.py"
    )
    assert artifact_provenance["current_aliases"]["diagram_txt"] == str(handle.root / "figures" / "circuit.txt")
    assert artifact_provenance["current_aliases"]["diagram_png"] == str(
        handle.root / "figures" / "circuit.png"
    )
    assert report["replay_integrity"]["artifact_output_digests"]["qiskit_code"].startswith("sha256:")
    assert report["replay_integrity"]["artifact_output_digests"]["diagram_txt"].startswith("sha256:")
    assert report["replay_integrity"]["artifact_output_digests"]["diagram_png"].startswith("sha256:")


def test_write_report_records_report_and_qspec_aliases_in_artifact_provenance(
    tmp_path: Path,
) -> None:
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")
    revision = handle.reserve_revision()

    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    qspec_path = handle.root / "specs" / "history" / f"{revision}.json"
    qspec_path.parent.mkdir(parents=True, exist_ok=True)
    qspec_path.write_text(qspec.model_dump_json(indent=2))

    report = write_report(
        workspace=handle,
        revision=revision,
        input_data={"mode": "intent", "path": "examples/intent-ghz.md"},
        qspec=qspec,
        qspec_path=qspec_path,
        artifacts={"qspec": str(qspec_path)},
        diagnostics={"simulation": {"status": "ok", "shots": 32}},
        backend_reports={},
        warnings=[],
        errors=[],
    )

    assert report["artifacts"]["report"] == str(handle.root / "reports" / "history" / f"{revision}.json")
    assert report["provenance"]["artifacts"]["paths"]["qspec"] == str(qspec_path)
    assert report["provenance"]["artifacts"]["paths"]["report"] == str(
        handle.root / "reports" / "history" / f"{revision}.json"
    )
    assert report["provenance"]["artifacts"]["current_aliases"]["qspec"] == str(
        handle.root / "specs" / "current.json"
    )
    assert report["provenance"]["artifacts"]["current_aliases"]["report"] == str(
        handle.root / "reports" / "latest.json"
    )


def test_write_report_canonicalizes_current_alias_artifacts(tmp_path: Path) -> None:
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")
    revision = handle.reserve_revision()

    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    qspec_path = handle.root / "specs" / "current.json"
    qspec_path.parent.mkdir(parents=True, exist_ok=True)
    qspec_path.write_text(qspec.model_dump_json(indent=2))

    qiskit_alias = handle.root / "artifacts" / "qiskit" / "main.py"
    qiskit_alias.parent.mkdir(parents=True, exist_ok=True)
    qiskit_alias.write_text("from qiskit import QuantumCircuit\n")

    report = write_report(
        workspace=handle,
        revision=revision,
        input_data={"mode": "intent", "path": "examples/intent-ghz.md"},
        qspec=qspec,
        qspec_path=qspec_path,
        artifacts={
            "qspec": str(qspec_path),
            "qiskit_code": str(qiskit_alias),
        },
        diagnostics={"simulation": {"status": "ok", "shots": 32}},
        backend_reports={},
        warnings=[],
        errors=[],
    )

    assert report["qspec"]["path"] == str(handle.root / "specs" / "history" / f"{revision}.json")
    assert report["artifacts"]["qspec"] == str(handle.root / "specs" / "history" / f"{revision}.json")
    assert report["artifacts"]["report"] == str(handle.root / "reports" / "history" / f"{revision}.json")
    assert report["provenance"]["qspec"]["path"] == str(
        handle.root / "specs" / "history" / f"{revision}.json"
    )
    assert report["provenance"]["qspec"]["path"] == report["qspec"]["path"]
    assert report["provenance"]["qspec"]["hash"] == report["qspec"]["hash"]
    assert report["artifacts"]["qiskit_code"] == str(
        handle.root / "artifacts" / "history" / revision / "qiskit" / "main.py"
    )
    assert report["provenance"]["artifacts"]["current_aliases"]["qiskit_code"] == str(qiskit_alias)


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
    canonical_qspec_path = handle.root / "specs" / "history" / f"{revision}.json"
    normalized_summary = (
        summary.replace(str(canonical_qspec_path), "<qspec_path>")
        .replace(revision, "<revision>")
        .replace(",report", "")
    )

    assert len(summary) <= 1200
    assert revision in summary
    assert "status" in summary.lower()
    assert "artifacts" in summary.lower()
    assert "simulation" in summary.lower()
    assert "next" in summary.lower()
    assert normalized_summary == golden


def test_summarize_report_includes_backend_benchmark_modes() -> None:
    report = {
        "status": "degraded",
        "revision": "rev_000123",
        "qspec": {"path": "/tmp/specs/history/rev_000123.json"},
        "semantics": {"pattern": "ghz", "parameter_count": 0},
        "artifacts": {},
        "diagnostics": {"simulation": {"status": "ok"}},
        "backend_reports": {
            "qiskit-local": {
                "status": "ok",
                "details": {
                    "benchmark_mode": "target_aware",
                },
            },
            "classiq": {
                "status": "ok",
                "details": {
                    "benchmark_mode": "synthesis_backed",
                    "target_parity": "partial",
                },
            },
        },
        "warnings": [],
        "errors": [],
        "suggestions": [],
    }

    summary = summarize_report(report)

    assert "qiskit-local:ok[target_aware]" in summary
    assert "classiq:ok[synthesis_backed,partial]" in summary


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
    assert report["qspec"]["path"] == str(handle.root / "specs" / "history" / f"{revision}.json")
    assert any("classiq" in suggestion.lower() for suggestion in report["suggestions"])
    assert any("install" in suggestion.lower() for suggestion in report["suggestions"])
