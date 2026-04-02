from __future__ import annotations

from pathlib import Path

from quantum_runtime.intent.parser import parse_intent_file, parse_intent_text
from quantum_runtime.intent.planner import plan_to_qspec
from quantum_runtime.lowering.classiq_emitter import (
    emit_classiq_source,
    write_classiq_program,
)
from quantum_runtime.qspec import PatternNode
from quantum_runtime.workspace import WorkspaceManager


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_emit_ghz_classiq_source_matches_golden_snapshot() -> None:
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)

    result = emit_classiq_source(qspec)
    golden = (PROJECT_ROOT / "tests" / "golden" / "classiq_ghz_main.py").read_text()

    assert result.status == "ok"
    assert result.source == golden
    assert result.reason is None


def test_emit_supported_classiq_patterns_without_error() -> None:
    samples = [
        "Create a Bell pair and measure both qubits.",
        "Build a 5-qubit QFT circuit.",
        "Generate a 4-qubit hardware efficient ansatz.",
        "Build a 4-qubit MaxCut QAOA ansatz.",
    ]

    for goal in samples:
        intent = parse_intent_text(goal)
        qspec = plan_to_qspec(intent)
        result = emit_classiq_source(qspec)
        assert result.status == "ok"
        assert result.source is not None
        assert "@qfunc" in result.source
        assert "create_model(main)" in result.source


def test_write_classiq_program_creates_artifact(tmp_path: Path) -> None:
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")

    result = write_classiq_program(qspec, handle.root / "artifacts" / "classiq" / "main.py")

    assert result.status == "ok"
    assert result.path is not None
    assert result.path.exists()
    assert result.path.read_text() == result.source


def test_emit_classiq_returns_structured_unsupported_result() -> None:
    intent = parse_intent_text("Generate a 4-qubit GHZ circuit and measure all qubits.")
    qspec = plan_to_qspec(intent)
    qspec.body[0] = PatternNode.model_construct(
        kind="pattern",
        pattern="custom_oracle",
        args={"register": "q", "size": 4},
    )

    result = emit_classiq_source(qspec)

    assert result.status == "unsupported"
    assert result.source is None
    assert result.reason == "pattern_not_supported_by_classiq_emitter"
    assert result.details == {"pattern": "custom_oracle"}
