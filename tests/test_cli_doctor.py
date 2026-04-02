from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.cli import app


RUNNER = CliRunner()


def test_qrun_doctor_json_reports_workspace_and_dependency_health(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / ".quantum"

    monkeypatch.setattr(
        "quantum_runtime.runtime.doctor._check_import",
        lambda module_name: {
            "module": module_name,
            "available": module_name != "classiq",
            "error": None if module_name != "classiq" else "No module named 'classiq'",
        },
    )

    result = RUNNER.invoke(
        app,
        ["doctor", "--workspace", str(workspace), "--json", "--fix"],
    )

    assert result.exit_code == 7, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "degraded"
    assert payload["workspace_ok"] is True
    assert payload["fix_applied"] is True
    assert payload["workspace"]["required_active_artifacts"] is False
    assert payload["workspace"]["active_spec"]["exists"] is False
    assert payload["workspace"]["active_report"]["exists"] is False
    assert payload["workspace"]["directories"]["reports"]["exists"] is True
    assert payload["dependencies"]["qiskit"]["available"] is True
    assert payload["dependencies"]["qiskit"]["version"]
    assert payload["dependencies"]["qiskit_aer"]["available"] is True
    assert payload["dependencies"]["classiq"]["available"] is False


def test_qrun_doctor_json_returns_exit_code_3_for_missing_workspace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / ".quantum"

    monkeypatch.setattr(
        "quantum_runtime.runtime.doctor._check_import",
        lambda module_name: {
            "module": module_name,
            "available": True,
            "error": None,
        },
    )

    result = RUNNER.invoke(
        app,
        ["doctor", "--workspace", str(workspace), "--json"],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "degraded"
    assert payload["workspace_ok"] is False


def test_qrun_doctor_json_flags_missing_active_report_after_execution(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / ".quantum"

    monkeypatch.setattr(
        "quantum_runtime.runtime.doctor._check_import",
        lambda module_name: {
            "module": module_name,
            "available": True,
            "error": None,
        },
    )

    exec_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(Path(__file__).resolve().parents[1] / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert exec_result.exit_code == 0, exec_result.stdout

    (workspace / "reports" / "latest.json").unlink()

    result = RUNNER.invoke(
        app,
        ["doctor", "--workspace", str(workspace), "--json"],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["workspace"]["required_active_artifacts"] is True
    assert payload["workspace"]["active_spec"]["exists"] is True
    assert payload["workspace"]["active_report"]["exists"] is False
    assert "active_report_missing" in payload["issues"]
