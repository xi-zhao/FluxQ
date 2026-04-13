from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.cli import app
from quantum_runtime.intent.parser import parse_intent_file
from quantum_runtime.intent.planner import plan_to_qspec
from quantum_runtime.runtime.backend_registry import BackendCapabilityDescriptor, BackendDependency
from quantum_runtime.workspace import WorkspaceManager, acquire_workspace_lock


RUNNER = CliRunner()


def _doctor_capabilities(*, classiq_available: bool, classiq_optional: bool = True) -> dict[str, dict[str, object]]:
    return {
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
            available=classiq_available,
            optional=classiq_optional,
            reason=None if classiq_available else "No module named 'classiq'",
            module_dependencies=[
                BackendDependency(
                    module="classiq",
                    distribution="classiq",
                    available=classiq_available,
                    version="1.7.0" if classiq_available else None,
                    location="/tmp/classiq/__init__.py" if classiq_available else None,
                    error=None if classiq_available else "No module named 'classiq'",
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
    }


def test_qrun_doctor_json_reports_workspace_and_dependency_health(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / ".quantum"

    monkeypatch.setattr(
        "quantum_runtime.runtime.doctor.collect_backend_capabilities",
        lambda: _doctor_capabilities(classiq_available=False),
    )

    result = RUNNER.invoke(
        app,
        ["doctor", "--workspace", str(workspace), "--json", "--fix"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["schema_version"] == "0.3.0"
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
    assert payload["issues"] == []
    assert payload["advisories"] == ["classiq unavailable: No module named 'classiq'"]
    assert not (workspace / "doctor").exists()


def test_qrun_doctor_ci_json_reports_advisory_only_findings_as_pass(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / ".quantum"

    monkeypatch.setattr(
        "quantum_runtime.runtime.doctor.collect_backend_capabilities",
        lambda: _doctor_capabilities(classiq_available=False),
    )

    result = RUNNER.invoke(
        app,
        ["doctor", "--workspace", str(workspace), "--json", "--fix", "--ci"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["blocking_issues"] == []
    assert payload["advisory_issues"] == ["classiq unavailable: No module named 'classiq'"]
    assert payload["verdict"]["status"] == "pass"
    assert payload["gate"]["ready"] is True
    assert payload["policy"]["mode"] == "ci"


def test_qrun_doctor_json_flags_missing_optional_backend_when_workspace_requests_it(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / ".quantum"
    handle = WorkspaceManager.load_or_init(workspace)
    qspec = plan_to_qspec(parse_intent_file(Path(__file__).resolve().parents[1] / "examples" / "intent-ghz.md"))
    qspec.backend_preferences = ["classiq"]
    (handle.root / "specs" / "current.json").write_text(qspec.model_dump_json(indent=2))

    monkeypatch.setattr(
        "quantum_runtime.runtime.doctor.collect_backend_capabilities",
        lambda: _doctor_capabilities(classiq_available=False),
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

    qspec_path = workspace / "specs" / "current.json"
    current_qspec = json.loads(qspec_path.read_text())
    current_qspec["backend_preferences"] = ["classiq"]
    qspec_path.write_text(json.dumps(current_qspec, indent=2))

    result = RUNNER.invoke(
        app,
        ["doctor", "--workspace", str(workspace), "--json"],
    )

    assert result.exit_code == 7, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "degraded"
    assert payload["schema_version"] == "0.3.0"
    assert payload["workspace_ok"] is True
    assert payload["issues"] == ["classiq unavailable: No module named 'classiq'"]
    assert payload["advisories"] == []
    assert (workspace / "doctor" / "latest.json").exists()
    assert (workspace / "doctor" / "history" / "rev_000001.json").exists()


def test_qrun_doctor_ci_json_returns_exit_code_2_for_blocking_workspace_findings(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / ".quantum"

    monkeypatch.setattr(
        "quantum_runtime.runtime.doctor.collect_backend_capabilities",
        lambda: _doctor_capabilities(classiq_available=True),
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
        ["doctor", "--workspace", str(workspace), "--json", "--ci"],
    )

    assert result.exit_code == 2, result.stdout
    payload = json.loads(result.stdout)
    assert "active_report_missing" in payload["blocking_issues"]
    assert payload["advisory_issues"] == []
    assert payload["verdict"]["status"] == "fail"
    assert payload["gate"]["ready"] is False
    assert payload["policy"]["block_on_issues"] is True
    assert (workspace / "doctor" / "latest.json").exists()
    assert (workspace / "doctor" / "history" / "rev_000001.json").exists()


def test_qrun_doctor_json_returns_exit_code_3_for_missing_workspace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / ".quantum"

    monkeypatch.setattr(
        "quantum_runtime.runtime.doctor.collect_backend_capabilities",
        lambda: _doctor_capabilities(classiq_available=True),
    )

    result = RUNNER.invoke(
        app,
        ["doctor", "--workspace", str(workspace), "--json"],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "degraded"
    assert payload["schema_version"] == "0.3.0"
    assert payload["workspace_ok"] is False
    assert not (workspace / "doctor").exists()


def test_qrun_doctor_json_flags_missing_active_report_after_execution(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / ".quantum"

    monkeypatch.setattr(
        "quantum_runtime.runtime.doctor.collect_backend_capabilities",
        lambda: _doctor_capabilities(classiq_available=True),
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
    assert (workspace / "doctor" / "latest.json").exists()
    assert (workspace / "doctor" / "history" / "rev_000001.json").exists()


def test_qrun_doctor_json_reports_workspace_conflict_when_doctor_persistence_is_locked(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
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

    with acquire_workspace_lock(workspace, command="pytest doctor lock holder"):
        result = RUNNER.invoke(
            app,
            ["doctor", "--workspace", str(workspace), "--json"],
        )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["reason"] == "workspace_conflict"


def test_qrun_doctor_json_reports_workspace_recovery_required_for_pending_doctor_temp(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
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

    pending = workspace / "doctor" / "latest.json.tmp"
    pending.parent.mkdir(parents=True, exist_ok=True)
    pending.write_text("pending")

    result = RUNNER.invoke(
        app,
        ["doctor", "--workspace", str(workspace), "--json"],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["reason"] == "workspace_recovery_required"
    assert str(pending) in payload["details"]["pending_files"]
