from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.cli import app
from quantum_runtime.intent.parser import parse_intent_file


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QAOA_SWEEP_INTENT_PATH = PROJECT_ROOT / "examples" / "intent-qaoa-maxcut-sweep.md"
RUNNER = CliRunner()
QSPEC_IDENTITY_KEYS = (
    "pattern",
    "width",
    "layers",
    "workload_id",
    "workload_hash",
    "semantic_hash",
)
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


def _invoke_json_command(*args: str) -> dict[str, object]:
    result = RUNNER.invoke(app, [*args, "--json"])
    assert result.exit_code == 0, result.stdout
    return json.loads(result.stdout)


def _write_qaoa_sweep_intent_json(tmp_path: Path) -> Path:
    intent_json_path = tmp_path / "intent-qaoa-maxcut-sweep.json"
    intent_model = parse_intent_file(QAOA_SWEEP_INTENT_PATH)
    intent_json_path.write_text(intent_model.model_dump_json(indent=2))
    return intent_json_path


def _qaoa_sweep_prompt_text() -> str:
    return QAOA_SWEEP_INTENT_PATH.read_text()


def _qspec_identity_block(payload: dict[str, object]) -> dict[str, object]:
    qspec = payload["qspec"]
    return {key: qspec[key] for key in QSPEC_IDENTITY_KEYS}


def _resolve_parity_block(payload: dict[str, object]) -> dict[str, object]:
    plan_payload = payload["plan"]
    execution = plan_payload["execution"]
    return {
        "qspec": _qspec_identity_block(payload),
        "selected_backends": execution["selected_backends"],
        "artifacts_expected": plan_payload["artifacts_expected"],
    }


def _plan_parity_block(payload: dict[str, object]) -> dict[str, object]:
    execution = payload["execution"]
    return {
        "qspec": _qspec_identity_block(payload),
        "selected_backends": execution["selected_backends"],
        "artifacts_expected": payload["artifacts_expected"],
    }


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


def test_qrun_resolve_json_keeps_prompt_markdown_json_parity(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    intent_json_path = _write_qaoa_sweep_intent_json(tmp_path)

    prompt_payload = _invoke_json_command(
        "resolve",
        "--workspace",
        str(workspace),
        "--intent-text",
        _qaoa_sweep_prompt_text(),
    )
    markdown_payload = _invoke_json_command(
        "resolve",
        "--workspace",
        str(workspace),
        "--intent-file",
        str(QAOA_SWEEP_INTENT_PATH),
    )
    json_payload = _invoke_json_command(
        "resolve",
        "--workspace",
        str(workspace),
        "--intent-json-file",
        str(intent_json_path),
    )

    assert prompt_payload["input"]["mode"] == "intent_text"
    assert markdown_payload["input"]["mode"] == "intent"
    assert json_payload["input"]["mode"] == "intent_json"
    assert (
        _resolve_parity_block(prompt_payload)
        == _resolve_parity_block(markdown_payload)
        == _resolve_parity_block(json_payload)
    )


def test_qrun_plan_json_keeps_prompt_markdown_json_parity(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    intent_json_path = _write_qaoa_sweep_intent_json(tmp_path)

    prompt_payload = _invoke_json_command(
        "plan",
        "--workspace",
        str(workspace),
        "--intent-text",
        _qaoa_sweep_prompt_text(),
    )
    markdown_payload = _invoke_json_command(
        "plan",
        "--workspace",
        str(workspace),
        "--intent-file",
        str(QAOA_SWEEP_INTENT_PATH),
    )
    json_payload = _invoke_json_command(
        "plan",
        "--workspace",
        str(workspace),
        "--intent-json-file",
        str(intent_json_path),
    )

    assert prompt_payload["input"]["mode"] == "intent_text"
    assert markdown_payload["input"]["mode"] == "intent"
    assert json_payload["input"]["mode"] == "intent_json"
    assert (
        _plan_parity_block(prompt_payload)
        == _plan_parity_block(markdown_payload)
        == _plan_parity_block(json_payload)
    )
