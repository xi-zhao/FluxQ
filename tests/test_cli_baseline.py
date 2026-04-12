from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.cli import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()


def test_qrun_baseline_set_show_and_clear_json(tmp_path: Path) -> None:
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

    set_result = RUNNER.invoke(
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

    assert set_result.exit_code == 0, set_result.stdout
    set_payload = json.loads(set_result.stdout)
    baseline_path = workspace / "baselines" / "current.json"
    assert baseline_path.exists()
    assert set_payload["source_kind"] == "report_revision"
    assert set_payload["revision"] == "rev_000001"
    assert set_payload["report_path"].endswith("reports/history/rev_000001.json")
    assert set_payload["qspec_path"].endswith("specs/history/rev_000001.json")
    assert set_payload["qspec_summary"]["pattern"] == "ghz"
    assert set_payload["qspec_summary"]["workload_hash"].startswith("sha256:")

    show_result = RUNNER.invoke(
        app,
        [
            "baseline",
            "show",
            "--workspace",
            str(workspace),
            "--json",
        ],
    )

    assert show_result.exit_code == 0, show_result.stdout
    show_payload = json.loads(show_result.stdout)
    assert show_payload == set_payload

    clear_result = RUNNER.invoke(
        app,
        [
            "baseline",
            "clear",
            "--workspace",
            str(workspace),
            "--json",
        ],
    )

    assert clear_result.exit_code == 0, clear_result.stdout
    clear_payload = json.loads(clear_result.stdout)
    assert clear_payload["schema_version"] == "0.3.0"
    assert clear_payload["status"] == "ok"
    assert clear_payload["cleared"] is True
    assert clear_payload["path"] == str(baseline_path.resolve())
    assert not baseline_path.exists()


def test_qrun_baseline_set_canonicalizes_copied_report_inputs(tmp_path: Path) -> None:
    source_workspace = tmp_path / ".quantum-source"
    target_workspace = tmp_path / ".quantum-target"

    exec_result = RUNNER.invoke(
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
    assert exec_result.exit_code == 0, exec_result.stdout

    copied_report = tmp_path / "imports" / "copied-rev-1.json"
    copied_report.parent.mkdir(parents=True, exist_ok=True)
    copied_report.write_text((source_workspace / "reports" / "history" / "rev_000001.json").read_text())

    set_result = RUNNER.invoke(
        app,
        [
            "baseline",
            "set",
            "--workspace",
            str(target_workspace),
            "--report-file",
            str(copied_report),
            "--json",
        ],
    )

    assert set_result.exit_code == 0, set_result.stdout
    payload = json.loads(set_result.stdout)
    assert payload["source_kind"] == "report_file"
    assert payload["revision"] == "rev_000001"
    assert payload["workspace_root"] == str(source_workspace)
    assert payload["report_path"] == str(source_workspace / "reports" / "history" / "rev_000001.json")
    assert payload["qspec_path"] == str(source_workspace / "specs" / "history" / "rev_000001.json")
