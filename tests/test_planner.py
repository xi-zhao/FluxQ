from __future__ import annotations

import json
from pathlib import Path

import pytest

from quantum_runtime.errors import ManualQspecRequiredError
from quantum_runtime.intent.parser import parse_intent_file, parse_intent_text
from quantum_runtime.intent.planner import plan_to_qspec


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_plan_ghz_intent_matches_golden_snapshot() -> None:
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")

    qspec = plan_to_qspec(intent)
    golden = json.loads((PROJECT_ROOT / "tests" / "golden" / "qspec_ghz.json").read_text())

    assert qspec.model_dump(mode="json") == golden


def test_plan_qaoa_intent_matches_golden_snapshot() -> None:
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-qaoa-maxcut.md")

    qspec = plan_to_qspec(intent)
    golden = json.loads((PROJECT_ROOT / "tests" / "golden" / "qspec_qaoa_maxcut.json").read_text())

    assert qspec.model_dump(mode="json") == golden
    assert qspec.observables[0]["name"] == "maxcut_cost"
    assert qspec.observables[0]["kind"] == "pauli_sum"
    assert qspec.observables[0]["objective"] == "maximize"
    assert qspec.observables[0]["constant"] == 2.0
    assert qspec.observables[0]["terms"][0] == {
        "pauli": "ZZ",
        "qubits": [0, 1],
        "coefficient": -0.5,
    }


def test_plan_hardware_efficient_intent_carries_parameterized_structure() -> None:
    intent = parse_intent_text(
        """---
title: HEA Pattern Test
constraints:
  max_width: 3
  layers: 2
---

Generate a 3-qubit hardware efficient ansatz with 2 layers.
"""
    )

    qspec = plan_to_qspec(intent)
    golden = json.loads(
        (PROJECT_ROOT / "tests" / "golden" / "qspec_hardware_efficient_ansatz.json").read_text()
    )
    pattern = qspec.body[0]

    assert qspec.model_dump(mode="json") == golden
    assert pattern.pattern == "hardware_efficient_ansatz"
    assert pattern.args["layers"] == 2
    assert pattern.args["rotation_blocks"] == ["ry", "rz"]
    assert pattern.args["entanglement_edges"] == [[0, 1], [1, 2]]
    assert len(qspec.parameters) == 12
    assert qspec.parameters[0]["name"] == "theta_ry_l0_q0"
    assert qspec.parameters[-1]["name"] == "theta_rz_l1_q2"


def test_plan_hardware_efficient_intent_carries_observables_and_parameter_workflow() -> None:
    intent = parse_intent_text(
        """---
title: HEA Observable Test
constraints:
  max_width: 3
  layers: 2
  parameter_bindings:
    theta_ry_l0_q0: 0.12
    theta_rz_l1_q2: 0.34
  observables:
    - name: z0_plus_z1z2
      kind: pauli_sum
      objective: maximize
      terms:
        - pauli: Z
          qubits: [0]
          coefficient: 1.0
        - pauli: ZZ
          qubits: [1, 2]
          coefficient: -0.5
---

Generate a 3-qubit hardware efficient ansatz with 2 layers.
"""
    )

    qspec = plan_to_qspec(intent)

    assert qspec.metadata["parameter_workflow"]["mode"] == "binding"
    assert qspec.metadata["parameter_workflow"]["bindings"] == {
        "theta_ry_l0_q0": 0.12,
        "theta_rz_l1_q2": 0.34,
    }
    assert qspec.observables == [
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


def test_plan_qaoa_intent_carries_parameter_sweep_workflow() -> None:
    intent = parse_intent_text(
        """---
title: QAOA Sweep
constraints:
  max_width: 4
  qaoa_layers: 2
  parameter_sweep:
    gamma_0: [0.2, 0.4]
    beta_0: [0.1, 0.3]
    gamma_1: [0.45]
    beta_1: [0.35]
---

Build a 4-qubit MaxCut QAOA ansatz.
"""
    )

    qspec = plan_to_qspec(intent)

    assert qspec.metadata["parameter_workflow"]["mode"] == "sweep"
    assert qspec.metadata["parameter_workflow"]["grid"] == {
        "gamma_0": [0.2, 0.4],
        "beta_0": [0.1, 0.3],
        "gamma_1": [0.45],
        "beta_1": [0.35],
    }


@pytest.mark.parametrize(
    ("goal", "expected_pattern", "expected_size"),
    [
        ("Create a Bell pair and measure both qubits.", "bell", 2),
        ("Build a 6-qubit QFT circuit.", "qft", 6),
        ("Generate a 5-qubit hardware efficient ansatz.", "hardware_efficient_ansatz", 5),
        ("Build a 4-qubit MaxCut QAOA ansatz.", "qaoa_ansatz", 4),
    ],
)
def test_plan_supported_patterns(goal: str, expected_pattern: str, expected_size: int) -> None:
    intent = parse_intent_text(
        f"""---
title: Pattern Test
constraints:
  max_width: {expected_size}
---

{goal}
"""
    )

    qspec = plan_to_qspec(intent)

    assert qspec.program_id == f"prog_{expected_pattern}_{expected_size}"
    assert qspec.body[0].pattern == expected_pattern
    assert qspec.registers[0].size == expected_size

    if expected_pattern in {"hardware_efficient_ansatz", "qaoa_ansatz"}:
        assert qspec.parameters
        assert "layers" in qspec.body[0].args


def test_plan_unknown_goal_requires_manual_qspec() -> None:
    intent = parse_intent_text("Design a novel quantum walk experiment.")

    with pytest.raises(ManualQspecRequiredError) as exc:
        plan_to_qspec(intent)

    assert exc.value.code == "manual_qspec_required"
