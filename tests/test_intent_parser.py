from __future__ import annotations

from pathlib import Path

from quantum_runtime.intent.parser import parse_intent_file, parse_intent_text


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_parse_intent_file_reads_example_defaults() -> None:
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")

    assert intent.title == "GHZ circuit"
    assert intent.goal == "Generate a 4-qubit GHZ circuit and measure all qubits."
    assert intent.exports == ["qiskit", "qasm3"]
    assert intent.backend_preferences == ["qiskit-local"]
    assert intent.constraints == {"max_width": 4, "max_depth": 64}
    assert intent.shots == 1024
    assert intent.notes is None


def test_parse_intent_text_reads_section_blocks() -> None:
    intent = parse_intent_text(
        """---
title: Bell Pair
exports:
  - qiskit
---

# Goal
Prepare a Bell pair and measure both qubits.

# Inputs
None

# Outputs
Measurement counts

# Notes
Prefer minimal educational code.
"""
    )

    assert intent.title == "Bell Pair"
    assert intent.goal == "Prepare a Bell pair and measure both qubits."
    assert intent.exports == ["qiskit"]
    assert intent.backend_preferences == ["qiskit-local"]
    assert intent.notes == "Prefer minimal educational code."
