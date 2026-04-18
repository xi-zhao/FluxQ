from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.cli import app
from quantum_runtime.runtime.backend_registry import BackendCapabilityDescriptor, BackendDependency
from quantum_runtime.runtime.ibm_access import IbmAccessError, IbmAccessResolution


RUNNER = CliRunner()


def _backend_capabilities_fixture() -> dict[str, BackendCapabilityDescriptor]:
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
                "benchmark_target_aware": True,
                "benchmark_synthesis_backed": False,
                "classiq_synthesis": False,
                "remote_submit": False,
            },
            notes=["Local Qiskit backend"],
        ),
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
                "benchmark_target_aware": False,
                "benchmark_synthesis_backed": True,
                "classiq_synthesis": True,
                "remote_submit": False,
            },
            notes=["Optional Classiq synthesis backend"],
        ),
        "ibm-runtime": BackendCapabilityDescriptor(
            backend="ibm-runtime",
            provider="ibm",
            available=False,
            optional=True,
            reason="ibm_runtime_dependency_missing",
            module_dependencies=[],
            capabilities={
                "simulate_locally": False,
                "transpile_validation": False,
                "structural_benchmark": False,
                "benchmark_target_aware": False,
                "benchmark_synthesis_backed": False,
                "classiq_synthesis": False,
                "remote_readiness": True,
                "remote_submit": True,
            },
            notes=["IBM readiness-only inventory surface"],
        ),
    }


def _configured_ibm_resolution() -> IbmAccessResolution:
    return IbmAccessResolution(
        status="ok",
        configured=True,
        channel="ibm_quantum_platform",
        credential_mode="saved_account",
        instance="crn:v1:bluemix:public:quantum-computing:us-east:a/test::",
        saved_account_name="fluxq-dev",
    )


def test_qrun_backend_list_json_reports_known_backends(monkeypatch) -> None:
    monkeypatch.setattr(
        "quantum_runtime.runtime.backend_list.collect_backend_capabilities",
        _backend_capabilities_fixture,
    )

    result = RUNNER.invoke(app, ["backend", "list", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["backends"]["qiskit-local"]["available"] is True
    assert payload["backends"]["qiskit-local"]["provider"] == "qiskit"
    assert payload["backends"]["qiskit-local"]["capabilities"]["simulate_locally"] is True
    assert payload["backends"]["qiskit-local"]["capabilities"]["benchmark_target_aware"] is True
    assert payload["backends"]["qiskit-local"]["capabilities"]["benchmark_synthesis_backed"] is False
    assert payload["backends"]["classiq"]["available"] is False
    assert payload["backends"]["classiq"]["reason"] == "No module named 'classiq'"
    assert payload["backends"]["classiq"]["capabilities"]["benchmark_target_aware"] is False
    assert payload["backends"]["classiq"]["capabilities"]["benchmark_synthesis_backed"] is True


def test_backend_list_json_accepts_workspace_option(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / ".quantum"
    captured: dict[str, Path] = {}

    def _fake_list_backends(*, workspace_root: Path) -> dict[str, object]:
        captured["workspace_root"] = workspace_root
        return {
            "backends": {},
            "remote": {
                "provider": "ibm",
                "configured": False,
                "auth_source": None,
                "instance": None,
                "sdk_available": False,
            },
        }

    monkeypatch.setattr("quantum_runtime.cli.list_backends", _fake_list_backends)

    result = RUNNER.invoke(
        app,
        ["backend", "list", "--json", "--workspace", str(workspace)],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert captured["workspace_root"] == workspace
    assert payload["remote"]["provider"] == "ibm"
    assert payload["remote"]["configured"] is False
    assert payload["remote"]["auth_source"] is None
    assert payload["remote"]["instance"] is None
    assert payload["remote"]["sdk_available"] is False


def test_backend_list_json_reports_ibm_runtime_descriptor(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / ".quantum"

    result = RUNNER.invoke(
        app,
        ["backend", "list", "--json", "--workspace", str(workspace)],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    descriptor = payload["backends"]["ibm-runtime"]
    assert descriptor["provider"] == "ibm"
    assert descriptor["optional"] is True
    assert descriptor["capabilities"]["remote_readiness"] is True
    assert descriptor["capabilities"]["remote_submit"] is True


def test_backend_list_json_omits_auto_selection_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / ".quantum"
    monkeypatch.setattr(
        "quantum_runtime.runtime.backend_list.collect_backend_capabilities",
        _backend_capabilities_fixture,
    )

    result = RUNNER.invoke(
        app,
        ["backend", "list", "--json", "--workspace", str(workspace)],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert "recommended_backend" not in payload
    assert "selected_backend" not in payload
    assert "least_busy" not in payload
    assert "recommended_backend" not in payload["remote"]
    assert "selected_backend" not in payload["remote"]
    assert "least_busy" not in payload["remote"]


def test_backend_list_json_projects_ibm_target_readiness(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / ".quantum"

    class _FakeStatus:
        operational = True
        status_msg = "active"
        pending_jobs = 3

    class _FakeBackend:
        name = "ibm_brisbane"
        backend_version = "2.1.4"
        num_qubits = 127

        def status(self) -> _FakeStatus:
            return _FakeStatus()

    class _FakeService:
        def backends(self) -> list[_FakeBackend]:
            return [_FakeBackend()]

    monkeypatch.setattr(
        "quantum_runtime.runtime.backend_list.collect_backend_capabilities",
        _backend_capabilities_fixture,
    )
    monkeypatch.setattr(
        "quantum_runtime.runtime.backend_list.resolve_ibm_access",
        lambda *, workspace_root: _configured_ibm_resolution(),
    )
    monkeypatch.setattr(
        "quantum_runtime.runtime.backend_list.build_ibm_service",
        lambda *, resolution: _FakeService(),
    )

    result = RUNNER.invoke(
        app,
        ["backend", "list", "--json", "--workspace", str(workspace)],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    remote = payload["remote"]
    target = remote["targets"][0]
    assert target["name"] == "ibm_brisbane"
    assert target["operational"] is True
    assert target["status_msg"] == "active"
    assert target["pending_jobs"] == 3
    assert target["num_qubits"] == 127
    assert target["backend_version"] == "2.1.4"
    assert target["readiness"]["status"] == "ready"
    assert target["readiness"]["reason_codes"] == []
    assert target["readiness"]["next_actions"] == []


def test_backend_list_json_returns_blocked_remote_state_when_ibm_service_unavailable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / ".quantum"

    monkeypatch.setattr(
        "quantum_runtime.runtime.backend_list.collect_backend_capabilities",
        _backend_capabilities_fixture,
    )
    monkeypatch.setattr(
        "quantum_runtime.runtime.backend_list.resolve_ibm_access",
        lambda *, workspace_root: _configured_ibm_resolution(),
    )

    def _service_unavailable(*, resolution: IbmAccessResolution) -> object:
        raise IbmAccessError("ibm_runtime_dependency_missing")

    monkeypatch.setattr(
        "quantum_runtime.runtime.backend_list.build_ibm_service",
        _service_unavailable,
    )

    result = RUNNER.invoke(
        app,
        ["backend", "list", "--json", "--workspace", str(workspace)],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    remote = payload["remote"]
    assert remote["readiness"]["status"] == "blocked"
    assert "ibm_runtime_dependency_missing" in remote["readiness"]["reason_codes"]
    assert remote["targets"] == []
    assert "recommended_backend" not in payload
    assert "selected_backend" not in payload
    assert "least_busy" not in payload
