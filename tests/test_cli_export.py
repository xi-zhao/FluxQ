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


def test_qrun_export_json_accepts_history_revision_input(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    initial_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
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
            str(workspace),
            "--revision",
            "rev_000001",
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


def test_qrun_export_json_accepts_copied_report_file_via_report_provenance(tmp_path: Path) -> None:
    source_workspace = tmp_path / ".quantum-source"
    target_workspace = tmp_path / ".quantum-target"

    first_result = RUNNER.invoke(
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
    assert first_result.exit_code == 0, first_result.stdout

    copied_report = tmp_path / "imports" / "copied-rev-1.json"
    copied_report.parent.mkdir(parents=True, exist_ok=True)
    copied_report.write_text((source_workspace / "reports" / "history" / "rev_000001.json").read_text())

    second_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(source_workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-qaoa-maxcut.md"),
            "--json",
        ],
    )
    assert second_result.exit_code == 0, second_result.stdout

    result = RUNNER.invoke(
        app,
        [
            "export",
            "--workspace",
            str(target_workspace),
            "--report-file",
            str(copied_report),
            "--format",
            "qasm3",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["format"] == "qasm3"
    exported_qasm = Path(payload["path"]).read_text()
    assert "OPENQASM 3.0;" in exported_qasm
    assert "h q[0];" in exported_qasm
    assert "cx q[0], q[1];" in exported_qasm
    assert "ry(" not in exported_qasm


def test_qrun_export_json_returns_exit_code_3_for_tampered_report_qspec_fallback(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / ".quantum"

    initial_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert initial_result.exit_code == 0, initial_result.stdout

    current_qspec = workspace / "specs" / "current.json"
    history_qspec = workspace / "specs" / "history" / "rev_000001.json"
    mutated_qspec = plan_to_qspec(parse_intent_file(PROJECT_ROOT / "examples" / "intent-qaoa-maxcut.md"))
    current_qspec.write_text(mutated_qspec.model_dump_json(indent=2))
    history_qspec.unlink()

    result = RUNNER.invoke(
        app,
        [
            "export",
            "--workspace",
            str(workspace),
            "--report-file",
            str(workspace / "reports" / "latest.json"),
            "--format",
            "qasm3",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["reason"] == "report_qspec_hash_mismatch"


def test_qrun_export_json_reports_replay_source_for_revision_input(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    first_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert first_result.exit_code == 0, first_result.stdout

    second_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-qaoa-maxcut.md"),
            "--json",
        ],
    )
    assert second_result.exit_code == 0, second_result.stdout

    result = RUNNER.invoke(
        app,
        [
            "export",
            "--workspace",
            str(workspace),
            "--revision",
            "rev_000001",
            "--format",
            "qasm3",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["source_kind"] == "report_revision"
    assert payload["source_revision"] == "rev_000001"
    assert payload["source_report_path"] == str(workspace / "reports" / "history" / "rev_000001.json")
    assert payload["source_qspec_path"] == str(workspace / "specs" / "history" / "rev_000001.json")
    exported_qasm = Path(payload["path"]).read_text()
    assert "h q[0];" in exported_qasm
    assert "cx q[0], q[1];" in exported_qasm
    assert "ry(" not in exported_qasm


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
