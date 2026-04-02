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


def test_qrun_export_json_accepts_report_file_input(tmp_path: Path) -> None:
    source_workspace = tmp_path / ".quantum-source"
    target_workspace = tmp_path / ".quantum-target"

    initial_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(source_workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert initial_result.exit_code == 0, initial_result.stdout

    result = RUNNER.invoke(
        app,
        [
            "export",
            "--workspace",
            str(target_workspace),
            "--report-file",
            str(source_workspace / "reports" / "latest.json"),
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


def test_qrun_export_returns_exit_code_4_for_unsupported_format(tmp_path: Path) -> None:
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
            "not-a-format",
        ],
    )

    assert result.exit_code == 4, result.stdout
    assert "unsupported_export_format" in result.stdout


def test_qrun_export_json_returns_exit_code_3_for_invalid_report_input(tmp_path: Path) -> None:
    report_path = tmp_path / "broken-report.json"
    report_path.write_text(json.dumps({"status": "ok", "qspec": {}}, indent=2))

    result = RUNNER.invoke(
        app,
        [
            "export",
            "--workspace",
            str(tmp_path / ".quantum"),
            "--report-file",
            str(report_path),
            "--format",
            "qasm3",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["reason"] == "report_qspec_path_missing"
