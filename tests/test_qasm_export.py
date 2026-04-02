from __future__ import annotations

from pathlib import Path

from quantum_runtime.intent.parser import parse_intent_file
from quantum_runtime.intent.planner import plan_to_qspec
from quantum_runtime.lowering.qasm3_emitter import emit_qasm3_source, write_qasm3_program
from quantum_runtime.workspace import WorkspaceManager


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_emit_ghz_qasm3_matches_golden_snapshot() -> None:
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)

    source = emit_qasm3_source(qspec)
    golden = (PROJECT_ROOT / "tests" / "golden" / "qasm_ghz_main.qasm").read_text()

    assert source == golden


def test_write_qasm3_program_creates_artifact(tmp_path: Path) -> None:
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")

    output_path = write_qasm3_program(qspec, handle.root / "artifacts" / "qasm" / "main.qasm")

    assert output_path.exists()
    assert output_path.read_text().startswith("OPENQASM 3.0;")
