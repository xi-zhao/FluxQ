from __future__ import annotations

import json

from typer.testing import CliRunner

from quantum_runtime.cli import app


RUNNER = CliRunner()


def test_qrun_backend_list_json_reports_known_backends(monkeypatch) -> None:
    monkeypatch.setattr(
        "quantum_runtime.runtime.doctor._check_import",
        lambda module_name: {
            "module": module_name,
            "available": module_name != "classiq",
            "error": None if module_name != "classiq" else "No module named 'classiq'",
        },
    )

    result = RUNNER.invoke(app, ["backend", "list", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["backends"]["qiskit-local"]["available"] is True
    assert payload["backends"]["classiq"]["available"] is False
    assert payload["backends"]["classiq"]["reason"] == "No module named 'classiq'"
