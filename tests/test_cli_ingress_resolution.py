from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.cli import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()
WORKSPACE_ARTIFACT_PATHS = (
    "workspace.json",
    "events.jsonl",
    "trace/events.ndjson",
    "intents/history",
    "plans/history",
    "specs/current.json",
    "reports/latest.json",
)


def _assert_workspace_artifacts_absent(workspace: Path) -> None:
    assert not workspace.exists()
    for relative_path in WORKSPACE_ARTIFACT_PATHS:
        assert not (workspace / relative_path).exists()


def test_qrun_prompt_json_does_not_create_workspace_artifacts(tmp_path: Path) -> None:
    with RUNNER.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        isolated_root = Path(isolated_dir)

        result = RUNNER.invoke(
            app,
            [
                "prompt",
                "Build a 4-qubit GHZ circuit and measure all qubits.",
                "--json",
            ],
        )

        assert result.exit_code == 0, result.stdout
        payload = json.loads(result.stdout)
        assert payload["schema_version"] == "0.3.0"
        assert payload["status"] == "ok"
        assert payload["source_kind"] == "prompt_text"
        assert payload["intent"]["goal"] == "Build a 4-qubit GHZ circuit and measure all qubits."
        assert payload["intent"]["exports"] == ["qiskit", "qasm3"]
        assert payload["intent"]["backend_preferences"] == ["qiskit-local"]
        assert payload["intent"]["constraints"] == {}
        assert payload["intent"]["shots"] == 1024
        _assert_workspace_artifacts_absent(isolated_root / ".quantum")


def test_qrun_resolve_json_is_side_effect_free(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    result = RUNNER.invoke(
        app,
        [
            "resolve",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "ok"
    assert payload["input"]["mode"] == "intent"
    assert payload["qspec"]["pattern"] == "ghz"
    assert payload["qspec"]["workload_id"] == "ghz:4q"
    assert payload["plan"]["execution"]["selected_backends"] == ["qiskit-local"]
    assert "report" in payload["plan"]["artifacts_expected"]
    assert "manifest" in payload["plan"]["artifacts_expected"]
    _assert_workspace_artifacts_absent(workspace)


def test_qrun_plan_json_is_side_effect_free(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    result = RUNNER.invoke(
        app,
        [
            "plan",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "ok"
    assert payload["input"]["mode"] == "intent"
    assert payload["qspec"]["pattern"] == "ghz"
    assert payload["qspec"]["workload_id"] == "ghz:4q"
    assert payload["execution"]["selected_backends"] == ["qiskit-local"]
    assert "report" in payload["artifacts_expected"]
    assert "manifest" in payload["artifacts_expected"]
    _assert_workspace_artifacts_absent(workspace)
