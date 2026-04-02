from __future__ import annotations

from pathlib import Path

from quantum_runtime.diagnostics.diagrams import write_diagrams
from quantum_runtime.diagnostics.resources import estimate_resources
from quantum_runtime.diagnostics.simulate import run_local_simulation
from quantum_runtime.intent.parser import parse_intent_file
from quantum_runtime.intent.planner import plan_to_qspec
from quantum_runtime.workspace import WorkspaceManager


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_run_local_simulation_for_ghz() -> None:
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)

    report = run_local_simulation(qspec, shots=128)

    assert report.status == "ok"
    assert report.shots == 128
    assert report.error is None
    assert report.elapsed_ms >= 0
    assert sum(report.counts.values()) == 128
    assert set(report.counts).issubset({"0000", "1111"})


def test_estimate_resources_for_ghz() -> None:
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)

    report = estimate_resources(qspec)

    assert report.width == 4
    assert report.two_qubit_gates == 3
    assert report.measure_count == 4
    assert report.parameter_count == 0
    assert report.parameter_names == []
    assert report.gate_histogram["cx"] == 3
    assert report.gate_histogram["measure"] == 4


def test_estimate_resources_for_parameterized_qaoa() -> None:
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-qaoa-maxcut.md")
    qspec = plan_to_qspec(intent)

    report = estimate_resources(qspec)

    assert report.width == 4
    assert report.two_qubit_gates == 16
    assert report.measure_count == 4
    assert report.parameter_count == 4
    assert report.parameter_names == ["gamma_0", "beta_0", "gamma_1", "beta_1"]
    assert report.gate_histogram["rz"] == 8
    assert report.gate_histogram["rx"] == 8


def test_write_diagrams_creates_text_and_png(tmp_path: Path) -> None:
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")

    artifacts = write_diagrams(qspec, handle)

    assert artifacts.text_path.exists()
    assert artifacts.png_path.exists()
    assert artifacts.png_path.stat().st_size > 0
    text = artifacts.text_path.read_text()
    assert "q_0" in text
    assert "measure" in text.lower() or "c:" in text.lower()
