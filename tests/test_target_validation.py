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
    assert report.error is None
    assert report.original_depth == 5
    assert report.transpiled_depth == 5
    assert report.original_two_qubit_gates == 3
    assert report.transpiled_two_qubit_gates == 3
    assert report.coupling_insertions == 0


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
    assert report.error is not None
    assert "coupling" in report.error.lower() or "connected" in report.error.lower()


def test_validate_target_constraints_skipped_does_not_claim_transpiled_metrics() -> None:
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    qspec.constraints.max_depth = None
    qspec.constraints.basis_gates = None
    qspec.constraints.connectivity_map = None

    report = validate_target_constraints(qspec)

    assert report.status == "skipped"
    assert report.transpiled_depth is None
    assert report.transpiled_two_qubit_gates is None
    assert report.coupling_insertions is None
    assert any("skipped" in warning.lower() for warning in report.warnings)
