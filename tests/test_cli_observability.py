from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.cli import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()


def _parse_jsonl(output: str) -> list[dict[str, object]]:
    return [json.loads(line) for line in output.strip().splitlines() if line.strip()]


def test_qrun_status_json_exposes_health_reason_codes_next_actions_and_decision(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    result = RUNNER.invoke(
        app,
        ["status", "--workspace", str(workspace), "--json"],
    )

    assert result.exit_code == 2, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "degraded"
    assert payload["health"]["workspace"]["status"] == "missing"
    assert "workspace_not_initialized" in payload["reason_codes"]
    assert "run_exec" in payload["next_actions"]
    assert payload["decision"]["ready"] is False
    assert payload["decision"]["severity"] == "warning"
    assert payload["decision"]["recommended_action"] == "run_exec"


def test_qrun_show_json_exposes_decision_and_next_actions(tmp_path: Path) -> None:
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
        ["show", "--workspace", str(workspace), "--json"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["health"]["baseline"]["status"] == "not_configured"
    assert "set_baseline" in payload["next_actions"]
    assert payload["decision"]["ready"] is True
    assert payload["decision"]["severity"] == "info"
    assert payload["decision"]["recommended_action"] == "set_baseline"


def test_qrun_inspect_json_exposes_health_and_next_actions_for_replay_degradation(tmp_path: Path) -> None:
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

    latest_manifest = workspace / "manifests" / "latest.json"
    history_manifest = workspace / "manifests" / "history" / "rev_000001.json"
    latest_manifest.write_text('{"broken":')
    history_manifest.write_text('{"broken":')

    result = RUNNER.invoke(
        app,
        ["inspect", "--workspace", str(workspace), "--json"],
    )

    assert result.exit_code == 2, result.stdout
    payload = json.loads(result.stdout)
    assert payload["health"]["replay"]["status"] == "degraded"
    assert any(code.startswith("run_manifest_") for code in payload["reason_codes"])
    assert "run_exec" in payload["next_actions"]
    assert payload["decision"]["ready"] is False
    assert payload["decision"]["severity"] == "warning"


def test_qrun_compare_json_exposes_gate_reason_codes_and_next_actions(tmp_path: Path) -> None:
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
            "--json",
        ],
    )

    assert result.exit_code == 2, result.stdout
    payload = json.loads(result.stdout)
    assert "semantic_subject_changed" in " ".join(payload["reason_codes"])
    assert "review_compare" in payload["next_actions"]
    assert payload["gate"]["ready"] is False
    assert payload["gate"]["severity"] == "warning"
    assert payload["gate"]["recommended_action"] == "review_compare"


def test_qrun_exec_jsonl_emits_event_stream_with_completed_payload(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--jsonl",
        ],
    )

    assert result.exit_code == 0, result.stdout
    events = _parse_jsonl(result.stdout)
    event_types = [event["event_type"] for event in events]
    assert event_types[0] == "run_started"
    assert "input_resolved" in event_types
    assert "qspec_prepared" in event_types
    assert "artifact_written" in event_types
    assert "diagnostic_completed" in event_types
    assert "report_written" in event_types
    assert "manifest_written" in event_types
    assert event_types[-1] == "run_completed"
    assert events[-1]["status"] == "ok"
    assert events[-1]["payload"]["status"] == "ok"
    assert events[-1]["payload"]["schema_version"] == "0.3.0"


def test_qrun_compare_jsonl_emits_resolution_and_completion_events(tmp_path: Path) -> None:
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
            "--jsonl",
        ],
    )

    assert result.exit_code == 2, result.stdout
    events = _parse_jsonl(result.stdout)
    assert [event["event_type"] for event in events] == [
        "compare_started",
        "left_resolved",
        "right_resolved",
        "compare_completed",
    ]
    assert events[-1]["payload"]["status"] == "different_subject"


def test_qrun_bench_jsonl_emits_backend_events(tmp_path: Path) -> None:
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
            "bench",
            "--workspace",
            str(workspace),
            "--backends",
            "qiskit-local",
            "--jsonl",
        ],
    )

    assert result.exit_code == 0, result.stdout
    events = _parse_jsonl(result.stdout)
    assert events[0]["event_type"] == "benchmark_started"
    assert "backend_started" in [event["event_type"] for event in events]
    assert "backend_completed" in [event["event_type"] for event in events]
    assert events[-1]["event_type"] == "benchmark_completed"
    assert events[-1]["payload"]["schema_version"] == "0.3.0"


def test_qrun_bench_jsonl_emits_policy_payload_when_gating_is_requested(tmp_path: Path) -> None:
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

    baseline_result = RUNNER.invoke(
        app,
        [
            "baseline",
            "set",
            "--workspace",
            str(workspace),
            "--revision",
            "rev_000001",
            "--json",
        ],
    )
    assert baseline_result.exit_code == 0, baseline_result.stdout

    baseline_bench = RUNNER.invoke(
        app,
        [
            "bench",
            "--workspace",
            str(workspace),
            "--revision",
            "rev_000001",
            "--backends",
            "qiskit-local",
            "--json",
        ],
    )
    assert baseline_bench.exit_code == 0, baseline_bench.stdout

    second = RUNNER.invoke(
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
    assert second.exit_code == 0, second.stdout

    result = RUNNER.invoke(
        app,
        [
            "bench",
            "--workspace",
            str(workspace),
            "--baseline",
            "--max-depth-regression",
            "0",
            "--jsonl",
        ],
    )

    assert result.exit_code == 0, result.stdout
    events = _parse_jsonl(result.stdout)
    assert events[-1]["event_type"] == "benchmark_completed"
    assert events[-1]["payload"]["schema_version"] == "0.3.0"
    assert events[-1]["payload"]["verdict"]["status"] == "pass"
    assert "reason_codes" in events[-1]["payload"]
    assert "gate" in events[-1]["payload"]


def test_qrun_doctor_jsonl_emits_workspace_and_dependency_events(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    result = RUNNER.invoke(
        app,
        ["doctor", "--workspace", str(workspace), "--jsonl", "--fix"],
    )

    assert result.exit_code == 0, result.stdout
    events = _parse_jsonl(result.stdout)
    assert [event["event_type"] for event in events] == [
        "doctor_started",
        "workspace_checked",
        "dependencies_checked",
        "doctor_completed",
    ]
    assert events[-1]["payload"]["schema_version"] == "0.3.0"


def test_qrun_doctor_ci_jsonl_emits_policy_payload_on_completion(tmp_path: Path) -> None:
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

    report_path = workspace / "reports" / "latest.json"
    report_path.unlink()

    result = RUNNER.invoke(
        app,
        ["doctor", "--workspace", str(workspace), "--jsonl", "--ci"],
    )

    assert result.exit_code == 2, result.stdout
    events = _parse_jsonl(result.stdout)
    assert events[-1]["event_type"] == "doctor_completed"
    assert events[-1]["payload"]["schema_version"] == "0.3.0"
    assert "active_report_missing" in events[-1]["payload"]["blocking_issues"]
    assert events[-1]["payload"]["advisory_issues"] == []
    assert events[-1]["payload"]["verdict"]["status"] == "fail"
    assert events[-1]["payload"]["gate"]["ready"] is False
