from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.cli import app
from quantum_runtime.runtime.backend_registry import BackendCapabilityDescriptor, BackendDependency


RUNNER = CliRunner()


def test_qrun_doctor_json_reports_workspace_and_dependency_health(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / ".quantum"

    monkeypatch.setattr(
        "quantum_runtime.runtime.doctor.collect_backend_capabilities",
        lambda: {
            "qiskit-local": BackendCapabilityDescriptor(
                backend="qiskit-local",
                provider="qiskit",
                available=True,
                module_dependencies=[
                    BackendDependency(
                        module="qiskit",
                        distribution="qiskit",
                        available=True,
                        version="2.3.1",
                        location="/tmp/qiskit/__init__.py",
                        error=None,
                    ),
                    BackendDependency(
                        module="qiskit_aer",
                        distribution="qiskit-aer",
                        available=True,
                        version="0.17.1",
                        location="/tmp/qiskit_aer/__init__.py",
                        error=None,
                    ),
                ],
                capabilities={
                    "simulate_locally": True,
                    "transpile_validation": True,
                    "structural_benchmark": True,
                    "classiq_synthesis": False,
                    "remote_submit": False,
                },
                notes=["Local Qiskit backend"],
            ).model_dump(mode="json"),
            "classiq": BackendCapabilityDescriptor(
                backend="classiq",
                provider="classiq",
                available=False,
                reason="No module named 'classiq'",
                module_dependencies=[
                    BackendDependency(
                        module="classiq",
                        distribution="classiq",
                        available=False,
                        version=None,
                        location=None,
                        error="No module named 'classiq'",
                    )
                ],
                capabilities={
                    "simulate_locally": False,
                    "transpile_validation": False,
                    "structural_benchmark": True,
                    "classiq_synthesis": True,
                    "remote_submit": False,
                },
                notes=["Optional Classiq synthesis backend"],
            ).model_dump(mode="json"),
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
    assert payload["dependencies"]["qiskit-local"]["available"] is True
    assert payload["dependencies"]["qiskit-local"]["provider"] == "qiskit"
    assert payload["dependencies"]["qiskit-local"]["module_dependencies"][0]["module"] == "qiskit"
    assert payload["dependencies"]["classiq"]["available"] is False
    assert payload["dependencies"]["classiq"]["module_dependencies"][0]["module"] == "classiq"


def test_qrun_doctor_json_returns_exit_code_3_for_missing_workspace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / ".quantum"

    monkeypatch.setattr(
        "quantum_runtime.runtime.doctor.collect_backend_capabilities",
        lambda: {
            "qiskit-local": BackendCapabilityDescriptor(
                backend="qiskit-local",
                provider="qiskit",
                available=True,
                module_dependencies=[],
                capabilities={},
                notes=[],
            ).model_dump(mode="json"),
            "classiq": BackendCapabilityDescriptor(
                backend="classiq",
                provider="classiq",
                available=True,
                module_dependencies=[],
                capabilities={},
                notes=[],
            ).model_dump(mode="json"),
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
        "quantum_runtime.runtime.doctor.collect_backend_capabilities",
        lambda: {
            "qiskit-local": BackendCapabilityDescriptor(
                backend="qiskit-local",
                provider="qiskit",
                available=True,
                module_dependencies=[],
                capabilities={},
                notes=[],
            ).model_dump(mode="json"),
            "classiq": BackendCapabilityDescriptor(
                backend="classiq",
                provider="classiq",
                available=True,
                module_dependencies=[],
                capabilities={},
                notes=[],
            ).model_dump(mode="json"),
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
