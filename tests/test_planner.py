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


def test_plan_unknown_goal_requires_manual_qspec() -> None:
    intent = parse_intent_text("Design a novel quantum walk experiment.")

    with pytest.raises(ManualQspecRequiredError) as exc:
        plan_to_qspec(intent)

    assert exc.value.code == "manual_qspec_required"
