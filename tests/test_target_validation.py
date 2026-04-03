from __future__ import annotations

from pathlib import Path

from quantum_runtime.diagnostics.transpile_validate import validate_target_constraints
from quantum_runtime.intent.parser import parse_intent_file, parse_intent_text
from quantum_runtime.intent.planner import plan_to_qspec


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_validate_target_constraints_success_for_linear_chain() -> None:
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    qspec.constraints.basis_gates = ["h", "cx", "measure"]
    qspec.constraints.connectivity_map = [(0, 1), (1, 2), (2, 3)]

    report = validate_target_constraints(qspec)

    assert report.status == "ok"
    assert report.benchmark_mode == "target_aware"
    assert report.comparable is True
    assert report.error is None
    assert report.original_depth == 5
    assert report.transpiled_depth == 5
    assert report.original_two_qubit_gates == 3
    assert report.transpiled_two_qubit_gates == 3
    assert report.coupling_insertions == 0
    assert report.target_assumptions["optimization_level"] == 2
    assert report.target_assumptions["basis_gates"] == ["h", "cx", "measure"]
    assert report.target_assumptions["connectivity_map"] == [[0, 1], [1, 2], [2, 3]]
    assert report.target_assumptions["max_depth"] == 64
    assert "max_depth" in report.target_assumptions["constraint_fields"]
    assert "basis_gates" in report.target_assumptions["constraint_fields"]
    assert "connectivity_map" in report.target_assumptions["constraint_fields"]


def test_validate_target_constraints_failure_for_disconnected_map() -> None:
    intent = parse_intent_text(
        """---
constraints:
  max_width: 4
  basis_gates:
    - h
    - cx
    - measure
  connectivity_map:
    - [0, 1]
---

Generate a 4-qubit GHZ circuit and measure all qubits.
"""
    )
    qspec = plan_to_qspec(intent)

    report = validate_target_constraints(qspec)

    assert report.status == "error"
    assert report.benchmark_mode == "target_aware"
    assert report.comparable is False
    assert report.error is not None
    assert report.target_assumptions["basis_gates"] == ["h", "cx", "measure"]
    assert report.target_assumptions["connectivity_map"] == [[0, 1]]
    assert report.target_assumptions["transpile_constraint_fields"] == ["basis_gates", "connectivity_map"]
    assert "coupling" in report.error.lower() or "connected" in report.error.lower()


def test_validate_target_constraints_skipped_does_not_claim_transpiled_metrics() -> None:
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    qspec.constraints.max_depth = None
    qspec.constraints.basis_gates = None
    qspec.constraints.connectivity_map = None

    report = validate_target_constraints(qspec)

    assert report.status == "skipped"
    assert report.benchmark_mode == "structural_only"
    assert report.comparable is False
    assert report.transpiled_depth is None
    assert report.transpiled_two_qubit_gates is None
    assert report.coupling_insertions is None
    assert report.target_assumptions["basis_gates"] == []
    assert report.target_assumptions["connectivity_map"] == []
    assert report.target_assumptions["max_depth"] is None
    assert report.target_assumptions["constraint_fields"] == []
    assert report.target_assumptions["transpile_constraint_fields"] == []
    assert report.target_assumptions["validation_constraint_fields"] == []
    assert any("skipped" in warning.lower() for warning in report.warnings)


def test_validate_target_constraints_max_depth_only_is_not_target_aware() -> None:
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    qspec.constraints.basis_gates = None
    qspec.constraints.connectivity_map = None
    qspec.constraints.max_depth = 64

    report = validate_target_constraints(qspec)

    assert report.status == "ok"
    assert report.benchmark_mode == "structural_only"
    assert report.comparable is False
    assert report.target_assumptions["constraint_fields"] == ["max_depth"]
    assert report.target_assumptions["transpile_constraint_fields"] == []
    assert report.target_assumptions["validation_constraint_fields"] == ["max_depth"]
