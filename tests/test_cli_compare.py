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
