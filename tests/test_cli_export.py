from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.cli import app
from quantum_runtime.intent.parser import parse_intent_file
from quantum_runtime.intent.planner import plan_to_qspec
from quantum_runtime.workspace import WorkspaceManager


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()


def test_qrun_export_json_writes_requested_qasm3_artifact(tmp_path: Path) -> None:
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    (handle.root / "specs" / "current.json").write_text(qspec.model_dump_json(indent=2))

    result = RUNNER.invoke(
        app,
        [
            "export",
            "--workspace",
            str(handle.root),
            "--format",
            "qasm3",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["format"] == "qasm3"
    assert Path(payload["path"]).exists()
    assert Path(payload["path"]).read_text().startswith("OPENQASM 3.0;")


def test_qrun_export_json_writes_requested_classiq_artifact(tmp_path: Path) -> None:
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    (handle.root / "specs" / "current.json").write_text(qspec.model_dump_json(indent=2))

    result = RUNNER.invoke(
        app,
        [
            "export",
            "--workspace",
            str(handle.root),
            "--format",
            "classiq-python",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["format"] == "classiq-python"
    assert Path(payload["path"]).exists()
    assert "@qfunc" in Path(payload["path"]).read_text()
