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


def test_run_local_simulation_reports_qaoa_expectation_sweep() -> None:
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-qaoa-maxcut.md")
    qspec = plan_to_qspec(intent)
    qspec.metadata["parameter_workflow"] = {
        "mode": "sweep",
        "grid": {
            "gamma_0": [0.2, 0.4],
            "beta_0": [0.1, 0.3],
            "gamma_1": [0.45],
            "beta_1": [0.35],
        },
    }

    report = run_local_simulation(qspec, shots=96)

    assert report.status == "ok"
    assert report.parameter_mode == "sweep"
    assert report.observables[0]["name"] == "maxcut_cost"
    assert len(report.parameter_points) == 4
    assert report.best_point is not None
    assert report.best_point["objective_observable"] == "maxcut_cost"
    assert report.best_point["objective"] == "maximize"
    assert report.representative_point_label.startswith("sweep_")
    assert report.expectation_values[0]["name"] == "maxcut_cost"
    assert report.expectation_values[0]["evaluation_mode"] == "exact_statevector"
    assert sum(report.counts.values()) == 96


def test_run_local_simulation_reports_bound_hea_observable() -> None:
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    qspec.body[0] = qspec.body[0].model_copy(
        update={
            "pattern": "hardware_efficient_ansatz",
            "args": {
                "register": "q",
                "size": 4,
                "layers": 1,
                "rotation_blocks": ["ry"],
                "entanglement": "linear",
                "entanglement_edges": [[0, 1], [1, 2], [2, 3]],
            },
        }
    )
    qspec.parameters = [
        {
            "name": f"theta_ry_l0_q{qubit}",
            "kind": "angle",
            "family": "hardware_efficient_ansatz",
            "gate": "ry",
            "layer": 0,
            "qubit": qubit,
            "default": 0.5 + (0.1 * qubit),
        }
        for qubit in range(4)
    ]
    qspec.observables = [
        {
            "name": "z0_plus_z1z2",
            "kind": "pauli_sum",
            "objective": "maximize",
            "terms": [
                {"pauli": "Z", "qubits": [0], "coefficient": 1.0},
                {"pauli": "ZZ", "qubits": [1, 2], "coefficient": -0.5},
            ],
        }
    ]
    qspec.metadata["parameter_workflow"] = {
        "mode": "binding",
        "bindings": {
            "theta_ry_l0_q0": 0.12,
            "theta_ry_l0_q3": 0.91,
        },
    }

    report = run_local_simulation(qspec, shots=64)

    assert report.status == "ok"
    assert report.parameter_mode == "binding"
    assert report.representative_point_label == "bound"
    assert report.representative_bindings["theta_ry_l0_q0"] == 0.12
    assert report.representative_bindings["theta_ry_l0_q3"] == 0.91
    assert report.expectation_values[0]["name"] == "z0_plus_z1z2"
    assert report.expectation_values[0]["evaluation_mode"] == "exact_statevector"
    assert isinstance(report.expectation_values[0]["value"], float)
    assert sum(report.counts.values()) == 64


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
