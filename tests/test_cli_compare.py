from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.cli import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()


def test_qrun_compare_json_detects_same_subject_across_current_and_report_file(tmp_path: Path) -> None:
    source_workspace = tmp_path / ".quantum-source"
    target_workspace = tmp_path / ".quantum-target"

    source_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(source_workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert source_result.exit_code == 0, source_result.stdout

    target_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(target_workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert target_result.exit_code == 0, target_result.stdout

    compare_result = RUNNER.invoke(
        app,
        [
            "compare",
            "--workspace",
            str(target_workspace),
            "--left-report-file",
            str(source_workspace / "reports" / "latest.json"),
            "--json",
        ],
    )

    assert compare_result.exit_code == 0, compare_result.stdout
    payload = json.loads(compare_result.stdout)
    assert payload["status"] == "same_subject"
    assert payload["same_subject"] is True
    assert payload["same_qspec"] is True
    assert payload["same_report"] is False
    assert payload["left"]["qspec_summary"]["pattern"] == "ghz"
    assert payload["right"]["qspec_summary"]["pattern"] == "ghz"
    assert payload["left"]["qspec_summary"]["workload_hash"].startswith("sha256:")
    assert payload["left"]["qspec_summary"]["execution_hash"].startswith("sha256:")
    assert payload["left"]["qspec_summary"]["workload_hash"] == payload["right"]["qspec_summary"]["workload_hash"]
    assert payload["left"]["report_summary"]["artifact_output_set_hash"].startswith("sha256:")
    assert (
        payload["left"]["report_summary"]["artifact_output_set_hash"]
        == payload["right"]["report_summary"]["artifact_output_set_hash"]
    )
    assert payload["detached_report_inputs"] == []
    assert payload["verdict"]["status"] == "not_requested"
    assert payload["highlights"][0] == "Same workload identity (ghz) across both inputs."


def test_qrun_compare_json_detects_semantic_drift_across_revisions(tmp_path: Path) -> None:
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

    compare_result = RUNNER.invoke(
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

    assert compare_result.exit_code == 2, compare_result.stdout
    payload = json.loads(compare_result.stdout)
    assert payload["status"] == "different_subject"
    assert payload["same_subject"] is False
    assert payload["semantic_delta"]["left"]["pattern"] == "ghz"
    assert payload["semantic_delta"]["right"]["pattern"] == "qaoa_ansatz"
    assert "semantic_subject_changed:pattern" not in payload["differences"]
    assert any(item.startswith("semantic_subject_changed") for item in payload["differences"])
    assert "artifact_outputs_changed" in payload["differences"]
    assert payload["report_delta"]["artifact_output_names_changed"] == [
        "diagram_png",
        "diagram_txt",
        "qasm3",
        "qiskit_code",
    ]
    assert payload["diagnostic_delta"]["resource_fields_changed"] == [
        "depth",
        "two_qubit_gates",
        "parameter_count",
    ]
    assert payload["verdict"]["status"] == "not_requested"
    assert payload["highlights"][0] == "Different workload identity: ghz -> qaoa_ansatz."


def test_qrun_compare_json_accepts_copied_report_file_via_report_provenance(tmp_path: Path) -> None:
    source_workspace = tmp_path / ".quantum-source"
    target_workspace = tmp_path / ".quantum-target"

    source_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(source_workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert source_result.exit_code == 0, source_result.stdout

    copied_report = tmp_path / "imports" / "copied-rev-1.json"
    copied_report.parent.mkdir(parents=True, exist_ok=True)
    copied_report.write_text((source_workspace / "reports" / "history" / "rev_000001.json").read_text())

    source_mutation = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(source_workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-qaoa-maxcut.md"),
            "--json",
        ],
    )
    assert source_mutation.exit_code == 0, source_mutation.stdout

    target_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(target_workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert target_result.exit_code == 0, target_result.stdout

    compare_result = RUNNER.invoke(
        app,
        [
            "compare",
            "--workspace",
            str(target_workspace),
            "--left-report-file",
            str(copied_report),
            "--json",
        ],
    )

    assert compare_result.exit_code == 2, compare_result.stdout
    payload = json.loads(compare_result.stdout)
    assert payload["status"] == "same_subject"
    assert payload["same_subject"] is True
    assert payload["left"]["revision"] == "rev_000001"
    assert payload["left"]["qspec_path"] == str(source_workspace / "specs" / "history" / "rev_000001.json")
    assert payload["left"]["report_path"] == str(copied_report.resolve())
    assert payload["left"]["report_summary"]["artifact_snapshot_root"] == str(
        source_workspace / "artifacts" / "history" / "rev_000001"
    )
    assert payload["left"]["report_summary"]["artifact_paths"]["qiskit_code"] == str(
        source_workspace / "artifacts" / "history" / "rev_000001" / "qiskit" / "main.py"
    )
    assert payload["detached_report_inputs"] == ["left"]
    assert (
        payload["left"]["report_summary"]["artifact_set_hash"]
        == payload["right"]["report_summary"]["artifact_set_hash"]
    )


def test_qrun_compare_json_returns_exit_code_3_for_conflicting_left_source(tmp_path: Path) -> None:
    report_path = tmp_path / "dummy-report.json"
    report_path.write_text(json.dumps({"status": "ok"}))

    result = RUNNER.invoke(
        app,
        [
            "compare",
            "--workspace",
            str(tmp_path / ".quantum"),
            "--left-report-file",
            str(report_path),
            "--left-revision",
            "rev_000001",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["reason"] == "left_source_conflict"


def test_qrun_compare_json_policy_passes_for_same_subject_without_drift(tmp_path: Path) -> None:
    source_workspace = tmp_path / ".quantum-source"
    target_workspace = tmp_path / ".quantum-target"

    source_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(source_workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert source_result.exit_code == 0, source_result.stdout

    target_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(target_workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert target_result.exit_code == 0, target_result.stdout

    compare_result = RUNNER.invoke(
        app,
        [
            "compare",
            "--workspace",
            str(target_workspace),
            "--left-report-file",
            str(source_workspace / "reports" / "latest.json"),
            "--expect",
            "same-subject",
            "--forbid-report-drift",
            "--json",
        ],
    )

    assert compare_result.exit_code == 0, compare_result.stdout
    payload = json.loads(compare_result.stdout)
    assert payload["verdict"]["status"] == "pass"
    assert payload["report_drift_detected"] is False
    assert "report_drift:clean" in payload["verdict"]["passed_checks"]


def test_qrun_compare_json_policy_fails_for_subject_mismatch(tmp_path: Path) -> None:
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

    compare_result = RUNNER.invoke(
        app,
        [
            "compare",
            "--workspace",
            str(workspace),
            "--left-revision",
            "rev_000001",
            "--right-revision",
            "rev_000002",
            "--expect",
            "same-subject",
            "--json",
        ],
    )

    assert compare_result.exit_code == 2, compare_result.stdout
    payload = json.loads(compare_result.stdout)
    assert payload["verdict"]["status"] == "fail"
    assert "expect:same-subject" in payload["verdict"]["failed_checks"]


def test_qrun_compare_json_policy_passes_for_different_subject_expectation(tmp_path: Path) -> None:
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

    compare_result = RUNNER.invoke(
        app,
        [
            "compare",
            "--workspace",
            str(workspace),
            "--left-revision",
            "rev_000001",
            "--right-revision",
            "rev_000002",
            "--expect",
            "different-subject",
            "--json",
        ],
    )

    assert compare_result.exit_code == 0, compare_result.stdout
    payload = json.loads(compare_result.stdout)
    assert payload["status"] == "different_subject"
    assert payload["verdict"]["status"] == "pass"
    assert "expect:different-subject" in payload["verdict"]["passed_checks"]


def test_qrun_compare_json_returns_exit_code_3_for_invalid_expectation(tmp_path: Path) -> None:
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
            "--expect",
            "not-a-real-policy",
            "--json",
        ],
    )

    assert compare_result.exit_code == 3, compare_result.stdout
    payload = json.loads(compare_result.stdout)
    assert payload["status"] == "error"
    assert payload["reason"] == "invalid_compare_policy"


def test_qrun_compare_json_policy_fails_for_backend_regression(tmp_path: Path) -> None:
    left_workspace = tmp_path / ".quantum-left"
    right_workspace = tmp_path / ".quantum-right"

    left_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(left_workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert left_result.exit_code == 0, left_result.stdout

    left_report_path = left_workspace / "reports" / "latest.json"
    left_report = json.loads(left_report_path.read_text())
    left_report["backend_reports"] = {
        "classiq": {
            "status": "ok",
            "reason": None,
        }
    }
    left_report_path.write_text(json.dumps(left_report, indent=2))

    right_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(right_workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert right_result.exit_code == 0, right_result.stdout

    right_report_path = right_workspace / "reports" / "latest.json"
    right_report = json.loads(right_report_path.read_text())
    right_report["backend_reports"] = {
        "classiq": {
            "status": "dependency_missing",
            "reason": "classiq_not_installed",
        }
    }
    right_report["warnings"] = ["classiq_not_installed"]
    right_report["status"] = "degraded"
    right_report_path.write_text(json.dumps(right_report, indent=2))

    compare_result = RUNNER.invoke(
        app,
        [
            "compare",
            "--workspace",
            str(right_workspace),
            "--left-report-file",
            str(left_report_path),
            "--right-report-file",
            str(right_report_path),
            "--expect",
            "same-subject",
            "--forbid-backend-regressions",
            "--json",
        ],
    )

    assert compare_result.exit_code == 2, compare_result.stdout
    payload = json.loads(compare_result.stdout)
    assert payload["same_subject"] is True
    assert payload["backend_regressions"] == ["classiq"]
    assert payload["verdict"]["status"] == "fail"
    assert "backend_regressions:forbidden" in payload["verdict"]["failed_checks"]


def test_qrun_compare_json_policy_fails_for_replay_integrity_regression(tmp_path: Path) -> None:
    left_workspace = tmp_path / ".quantum-left"
    right_workspace = tmp_path / ".quantum-right"

    left_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(left_workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert left_result.exit_code == 0, left_result.stdout

    right_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(right_workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert right_result.exit_code == 0, right_result.stdout

    right_report_path = right_workspace / "reports" / "latest.json"
    right_report = json.loads(right_report_path.read_text())
    replay_integrity = right_report.get("replay_integrity", {})
    assert isinstance(replay_integrity, dict)
    replay_integrity.pop("artifact_output_digests", None)
    right_report["replay_integrity"] = replay_integrity
    right_report_path.write_text(json.dumps(right_report, indent=2))

    compare_result = RUNNER.invoke(
        app,
        [
            "compare",
            "--workspace",
            str(right_workspace),
            "--left-report-file",
            str(left_workspace / "reports" / "latest.json"),
            "--right-report-file",
            str(right_report_path),
            "--expect",
            "same-subject",
            "--forbid-replay-integrity-regressions",
            "--json",
        ],
    )

    assert compare_result.exit_code == 2, compare_result.stdout
    payload = json.loads(compare_result.stdout)
    assert payload["same_subject"] is True
    assert payload["left"]["replay_integrity"]["status"] == "ok"
    assert payload["right"]["replay_integrity"]["status"] == "legacy"
    assert payload["replay_integrity_delta"]["status_changed"] is True
    assert payload["replay_integrity_regressions"] == ["status:ok->legacy"]
    assert payload["verdict"]["status"] == "fail"
    assert "replay_integrity_regressions:forbidden" in payload["verdict"]["failed_checks"]
    assert "Replay trust changed: ok -> legacy." in payload["highlights"]


def test_qrun_compare_plaintext_surfaces_first_highlight(tmp_path: Path) -> None:
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

    compare_result = RUNNER.invoke(
        app,
        [
            "compare",
            "--workspace",
            str(workspace),
            "--left-revision",
            "rev_000001",
            "--right-revision",
            "rev_000002",
        ],
    )

    assert compare_result.exit_code == 2, compare_result.stdout
    assert "different_subject" in compare_result.stdout
    assert "highlight=Different workload identity: ghz -> qaoa_ansatz." in compare_result.stdout
