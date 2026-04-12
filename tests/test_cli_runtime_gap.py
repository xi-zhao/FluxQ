from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.cli import app
from quantum_runtime.intent.parser import parse_intent_file
from quantum_runtime.workspace import acquire_workspace_lock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()


def test_qrun_prompt_json_returns_normalized_intent_payload() -> None:
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
    assert payload["status"] == "ok"
    assert payload["schema_version"] == "0.3.0"
    assert payload["source_kind"] == "prompt_text"
    assert payload["intent"]["goal"] == "Build a 4-qubit GHZ circuit and measure all qubits."
    assert payload["intent"]["exports"] == ["qiskit", "qasm3"]
    assert payload["intent"]["backend_preferences"] == ["qiskit-local"]


def test_qrun_resolve_json_normalizes_structured_intent_and_returns_plan(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    intent_json_path = tmp_path / "intent.json"
    intent_model = parse_intent_file(PROJECT_ROOT / "examples" / "intent-qaoa-maxcut-sweep.md")
    intent_json_path.write_text(intent_model.model_dump_json(indent=2))

    markdown_result = RUNNER.invoke(
        app,
        [
            "resolve",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-qaoa-maxcut-sweep.md"),
            "--json",
        ],
    )
    assert markdown_result.exit_code == 0, markdown_result.stdout
    markdown_payload = json.loads(markdown_result.stdout)

    json_result = RUNNER.invoke(
        app,
        [
            "resolve",
            "--workspace",
            str(workspace),
            "--intent-json-file",
            str(intent_json_path),
            "--json",
        ],
    )

    assert json_result.exit_code == 0, json_result.stdout
    payload = json.loads(json_result.stdout)
    assert payload["status"] == "ok"
    assert payload["schema_version"] == "0.3.0"
    assert payload["intent"]["source_kind"] == "intent_json_file"
    assert payload["qspec"]["pattern"] == "qaoa_ansatz"
    assert payload["qspec"]["semantic_hash"] == markdown_payload["qspec"]["semantic_hash"]
    assert payload["qspec"]["workload_id"].startswith("qaoa_ansatz:")
    assert payload["plan"]["execution"]["selected_backends"] == ["qiskit-local"]
    assert "report" in payload["plan"]["artifacts_expected"]
    assert "manifest" in payload["plan"]["artifacts_expected"]


def test_qrun_exec_json_persists_intent_plan_and_events_runtime_objects(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-text",
            "Build a 4-qubit GHZ circuit and measure all qubits.",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    revision = payload["revision"]

    intent_path = workspace / "intents" / "history" / f"{revision}.json"
    plan_path = workspace / "plans" / "history" / f"{revision}.json"
    events_path = workspace / "events.jsonl"

    assert intent_path.exists()
    assert plan_path.exists()
    assert events_path.exists()

    intent_payload = json.loads(intent_path.read_text())
    plan_payload = json.loads(plan_path.read_text())

    assert intent_payload["schema_version"] == "0.3.0"
    assert intent_payload["intent"]["goal"] == "Build a 4-qubit GHZ circuit and measure all qubits."
    assert plan_payload["schema_version"] == "0.3.0"
    assert plan_payload["execution"]["selected_backends"] == ["qiskit-local"]
    assert any('"event_type": "exec_completed"' in line for line in events_path.read_text().splitlines())


def test_qrun_compare_json_fail_on_subject_drift_returns_failed_gate(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    first = RUNNER.invoke(
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
    assert first.exit_code == 0, first.stdout

    second = RUNNER.invoke(
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
    assert second.exit_code == 0, second.stdout

    result = RUNNER.invoke(
        app,
        [
            "compare",
            "--workspace",
            str(workspace),
            "--left-revision",
            "rev_000001",
            "--right-revision",
            "rev_000002",
            "--fail-on",
            "subject_drift",
            "--json",
        ],
    )

    assert result.exit_code == 2, result.stdout
    payload = json.loads(result.stdout)
    assert payload["verdict"]["status"] == "fail"
    assert payload["verdict"]["failed_checks"] == ["subject_drift"]
    assert payload["gate"]["ready"] is False
    assert payload["gate"]["severity"] == "error"


def test_qrun_compare_detail_includes_human_readable_difference_summary(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    first = RUNNER.invoke(
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
    assert first.exit_code == 0, first.stdout

    second = RUNNER.invoke(
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
    assert second.exit_code == 0, second.stdout

    result = RUNNER.invoke(
        app,
        [
            "compare",
            "--workspace",
            str(workspace),
            "--left-revision",
            "rev_000001",
            "--right-revision",
            "rev_000002",
            "--detail",
        ],
    )

    assert result.exit_code == 2, result.stdout
    assert "differences:" in result.stdout
    assert "semantic_subject_changed" in result.stdout
    assert "reason_codes:" in result.stdout


def test_qrun_export_json_supports_named_profiles(tmp_path: Path) -> None:
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

    result = RUNNER.invoke(
        app,
        [
            "export",
            "--workspace",
            str(workspace),
            "--format",
            "qasm3",
            "--profile",
            "qasm3-generic",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["profile"] == "qasm3-generic"


def test_qrun_pack_json_writes_portable_revision_bundle(tmp_path: Path) -> None:
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

    compare_result = RUNNER.invoke(
        app,
        [
            "compare",
            "--workspace",
            str(workspace),
            "--left-revision",
            "rev_000001",
            "--right-revision",
            "rev_000001",
            "--json",
        ],
    )
    assert compare_result.exit_code == 0, compare_result.stdout

    bench_result = RUNNER.invoke(
        app,
        [
            "bench",
            "--workspace",
            str(workspace),
            "--json",
        ],
    )
    assert bench_result.exit_code == 0, bench_result.stdout

    doctor_result = RUNNER.invoke(
        app,
        [
            "doctor",
            "--workspace",
            str(workspace),
            "--json",
        ],
    )
    assert doctor_result.exit_code == 0, doctor_result.stdout

    result = RUNNER.invoke(
        app,
        [
            "pack",
            "--workspace",
            str(workspace),
            "--revision",
            "rev_000001",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    pack_root = Path(payload["pack_root"])
    assert pack_root.exists()
    assert (pack_root / "intent.json").exists()
    assert (pack_root / "qspec.json").exists()
    assert (pack_root / "plan.json").exists()
    assert (pack_root / "report.json").exists()
    assert (pack_root / "manifest.json").exists()
    assert (pack_root / "events.jsonl").exists()
    assert (pack_root / "exports" / "qasm" / "main.qasm").exists()
    assert (pack_root / "bench.json").exists()
    assert (pack_root / "doctor.json").exists()
    assert (pack_root / "compare.json").exists()
    assert payload["inspection"]["status"] == "ok"


def test_qrun_schema_json_supports_intent_contract() -> None:
    result = RUNNER.invoke(
        app,
        [
            "schema",
            "intent",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["name"] == "intent"
    assert "intent" in payload["schema"]["properties"]


def test_qrun_pack_inspect_json_reports_bundle_health(tmp_path: Path) -> None:
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

    pack_result = RUNNER.invoke(
        app,
        [
            "pack",
            "--workspace",
            str(workspace),
            "--revision",
            "rev_000001",
            "--json",
        ],
    )
    assert pack_result.exit_code == 0, pack_result.stdout
    pack_root = json.loads(pack_result.stdout)["pack_root"]

    inspect_result = RUNNER.invoke(
        app,
        [
            "pack-inspect",
            "--pack-root",
            pack_root,
            "--json",
        ],
    )

    assert inspect_result.exit_code == 0, inspect_result.stdout
    payload = json.loads(inspect_result.stdout)
    assert payload["status"] == "ok"
    assert "exports/" in payload["present"]


def test_qrun_pack_json_reports_workspace_conflict_when_pack_persistence_is_locked(tmp_path: Path) -> None:
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

    with acquire_workspace_lock(workspace, command="pytest pack lock holder"):
        result = RUNNER.invoke(
            app,
            [
                "pack",
                "--workspace",
                str(workspace),
                "--revision",
                "rev_000001",
                "--json",
            ],
        )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["reason"] == "workspace_conflict"


def test_qrun_pack_json_reports_workspace_recovery_required_for_pending_history_backfill_temp(tmp_path: Path) -> None:
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

    intent_history = workspace / "intents" / "history" / "rev_000001.json"
    intent_history.unlink()
    pending = workspace / "intents" / "history" / "rev_000001.json.tmp"
    pending.write_text("pending")

    result = RUNNER.invoke(
        app,
        [
            "pack",
            "--workspace",
            str(workspace),
            "--revision",
            "rev_000001",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["reason"] == "workspace_recovery_required"
    assert str(pending) in payload["details"]["pending_files"]
