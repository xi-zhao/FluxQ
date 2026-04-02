from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.cli import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()


def test_qrun_exec_json_generates_workspace_artifacts_and_report(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    result = RUNNER.invoke(
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

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["revision"].startswith("rev_")
    assert Path(payload["artifacts"]["qspec"]).exists()
    assert Path(payload["artifacts"]["qiskit_code"]).exists()
    assert Path(payload["artifacts"]["qasm3"]).exists()
    assert Path(payload["artifacts"]["diagram_png"]).exists()
    assert Path(payload["artifacts"]["report"]).exists()
    assert payload["diagnostics"]["simulation"]["status"] == "ok"
    assert payload["diagnostics"]["transpile"]["status"] == "ok"

    report = json.loads((workspace / "reports" / "latest.json").read_text())
    assert report["status"] == "ok"
    assert report["artifacts"]["qiskit_code"].endswith("artifacts/qiskit/main.py")
    assert report["diagnostics"]["resources"]["two_qubit_gates"] == 3

    trace_lines = (workspace / "trace" / "events.ndjson").read_text().strip().splitlines()
    assert any('"event_type": "exec_completed"' in line for line in trace_lines)
