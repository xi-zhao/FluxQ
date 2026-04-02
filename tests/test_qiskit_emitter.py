from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import QFTGate
from qiskit.quantum_info import Operator

from quantum_runtime.intent.parser import parse_intent_file, parse_intent_text
from quantum_runtime.intent.planner import plan_to_qspec
from quantum_runtime.lowering.qiskit_emitter import (
    build_qiskit_circuit,
    emit_qiskit_source,
    write_qiskit_program,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_emit_ghz_qiskit_source_matches_golden_snapshot() -> None:
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)

    source = emit_qiskit_source(qspec)
    golden = (PROJECT_ROOT / "tests" / "golden" / "qiskit_ghz_main.py").read_text()

    assert source == golden


def test_written_qiskit_program_imports_and_simulates(tmp_path: Path) -> None:
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    output_path = tmp_path / "main.py"

    write_qiskit_program(qspec, output_path)

    spec = importlib.util.spec_from_file_location("generated_qiskit_program", output_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    circuit = module.build_circuit()
    counts = module.simulate_counts(shots=128)

    assert circuit.num_qubits == 4
    assert circuit.num_clbits == 4
    assert sum(counts.values()) == 128
    assert set(counts).issubset({"0000", "1111"})

    command = subprocess.run(
        [sys.executable, str(output_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert command.returncode == 0, command.stderr
    assert set(json.loads(command.stdout)).issubset({"0000", "1111"})


def test_emit_supported_patterns_without_error() -> None:
    samples = [
        "Create a Bell pair and measure both qubits.",
        "Build a 5-qubit QFT circuit.",
        "Generate a 4-qubit hardware efficient ansatz.",
        "Build a 4-qubit MaxCut QAOA ansatz.",
    ]

    for goal in samples:
        intent = parse_intent_text(goal)
        qspec = plan_to_qspec(intent)
        source = emit_qiskit_source(qspec)
        assert "def build_circuit()" in source


def test_build_qft_circuit_matches_qiskit_reference_up_to_global_phase() -> None:
    intent = parse_intent_text("Build a 5-qubit QFT circuit.")
    qspec = plan_to_qspec(intent)

    emitted = build_qiskit_circuit(qspec)
    emitted.remove_final_measurements()

    reference = QuantumCircuit(5)
    reference.append(QFTGate(5), range(5))

    assert _equivalent_up_to_global_phase(emitted, reference)


def test_emit_parameterized_qaoa_source_and_circuit_reflect_layers_and_edges() -> None:
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-qaoa-maxcut.md")
    qspec = plan_to_qspec(intent)

    source = emit_qiskit_source(qspec)
    circuit = build_qiskit_circuit(qspec)
    counts = circuit.count_ops()

    assert source.count("qc.rz(") == 8
    assert source.count("qc.rx(") == 8
    assert source.count("qc.cx(") == 16
    assert counts["h"] == 4
    assert counts["rz"] == 8
    assert counts["rx"] == 8
    assert counts["cx"] == 16


def _equivalent_up_to_global_phase(left: QuantumCircuit, right: QuantumCircuit) -> bool:
    left_matrix = Operator(left).data
    right_matrix = Operator(right).data

    phase = None
    for row in range(right_matrix.shape[0]):
        for column in range(right_matrix.shape[1]):
            if abs(right_matrix[row, column]) > 1e-9:
                phase = left_matrix[row, column] / right_matrix[row, column]
                break
        if phase is not None:
            break

    return phase is not None and bool(np.allclose(left_matrix, phase * right_matrix))
