from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.cli import app
from quantum_runtime.workspace import WorkspaceManager


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()


def test_qrun_inspect_json_summarizes_current_workspace_state(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    exec_result = RUNNER.invoke(
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
    assert exec_result.exit_code == 0, exec_result.stdout

    inspect_result = RUNNER.invoke(
        app,
        ["inspect", "--workspace", str(workspace), "--json"],
    )

    assert inspect_result.exit_code == 0, inspect_result.stdout
    payload = json.loads(inspect_result.stdout)
    assert payload["revision"].startswith("rev_")
    assert payload["qspec"]["goal"].lower().startswith("generate a 4-qubit ghz")
    assert payload["qspec"]["pattern"] == "ghz"
    assert payload["qspec"]["parameter_count"] == 0
    assert payload["qspec"]["registers"]["qubits"] == 4
    assert payload["provenance"]["workspace_root"] == str(workspace)
    assert payload["provenance"]["input"]["mode"] == "intent"
    assert payload["provenance"]["input"]["path"].endswith("examples/intent-ghz.md")
    assert payload["provenance"]["subject"]["pattern"] == "ghz"
    assert payload["artifacts"]["qiskit_code"].endswith("artifacts/qiskit/main.py")
    assert payload["diagnostics"]["simulation"]["status"] == "ok"
    assert "qiskit" in payload["backend_capabilities"]


def test_qrun_inspect_json_surfaces_parameterized_ansatz_semantics(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    exec_result = RUNNER.invoke(
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
    assert exec_result.exit_code == 0, exec_result.stdout

    inspect_result = RUNNER.invoke(
        app,
        ["inspect", "--workspace", str(workspace), "--json"],
    )

    assert inspect_result.exit_code == 0, inspect_result.stdout
    payload = json.loads(inspect_result.stdout)
    assert payload["qspec"]["pattern"] == "qaoa_ansatz"
    assert payload["qspec"]["layers"] == 2
    assert payload["qspec"]["parameter_count"] == 4
    assert payload["qspec"]["pattern_args"]["cost_edges"] == [[0, 1], [1, 2], [2, 3], [3, 0]]
    assert payload["provenance"]["subject"]["pattern"] == "qaoa_ansatz"
    assert payload["provenance"]["subject"]["layers"] == 2
    assert payload["provenance"]["subject"]["parameter_count"] == 4


def test_qrun_inspect_json_returns_exit_code_2_for_missing_manifest(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    handle = WorkspaceManager.load_or_init(workspace)
    handle.paths.workspace_json.unlink()

    inspect_result = RUNNER.invoke(
        app,
        ["inspect", "--workspace", str(workspace), "--json"],
    )

    assert inspect_result.exit_code == 2, inspect_result.stdout
    payload = json.loads(inspect_result.stdout)
    assert payload["status"] == "degraded"
    assert "workspace_manifest_missing" in payload["issues"]
    assert payload["qspec"]["status"] == "missing"
    assert payload["workspace"]["current_revision"] == "unknown"
    assert payload["provenance"]["workspace_root"] == str(workspace)
    assert payload["provenance"]["input"]["mode"] == "report"
    assert payload["provenance"]["report"]["path"].endswith("reports/latest.json")


def test_qrun_inspect_json_returns_exit_code_3_for_invalid_qspec_json(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    handle = WorkspaceManager.load_or_init(workspace)
    (handle.root / "specs" / "current.json").write_text("{not valid json")
    (handle.root / "reports" / "latest.json").write_text(
        "{\"artifacts\": {}, \"diagnostics\": {}}"
    )

    inspect_result = RUNNER.invoke(
        app,
        ["inspect", "--workspace", str(workspace), "--json"],
    )

    assert inspect_result.exit_code == 3, inspect_result.stdout
    payload = json.loads(inspect_result.stdout)
    assert payload["status"] == "error"
    assert "active_spec_invalid_json" in payload["errors"]
    assert payload["workspace"]["current_revision"] != ""
    assert payload["provenance"]["workspace_root"] == str(workspace)
    assert payload["provenance"]["input"]["mode"] == "report"
