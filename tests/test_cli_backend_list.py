from __future__ import annotations

import json

from typer.testing import CliRunner

from quantum_runtime.cli import app
from quantum_runtime.runtime.backend_registry import BackendCapabilityDescriptor, BackendDependency


RUNNER = CliRunner()


def test_qrun_backend_list_json_reports_known_backends(monkeypatch) -> None:
    monkeypatch.setattr(
        "quantum_runtime.runtime.backend_list.collect_backend_capabilities",
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
                    "classiq_synthesis": True,
                    "remote_submit": False,
                },
                notes=["Optional Classiq synthesis backend"],
            ),
        },
    )

    result = RUNNER.invoke(app, ["backend", "list", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["backends"]["qiskit-local"]["available"] is True
    assert payload["backends"]["qiskit-local"]["provider"] == "qiskit"
    assert payload["backends"]["qiskit-local"]["capabilities"]["simulate_locally"] is True
    assert payload["backends"]["classiq"]["available"] is False
    assert payload["backends"]["classiq"]["reason"] == "No module named 'classiq'"
