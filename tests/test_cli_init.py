from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_ROOT)
    return subprocess.run(
        [sys.executable, "-m", "quantum_runtime.cli", *args],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def test_init_creates_workspace_layout_and_json_output(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    result = run_cli("init", "--workspace", str(workspace), "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    assert payload["status"] == "ok"
    assert payload["workspace"] == str(workspace)
    assert payload["workspace_version"] == "0.1"

    assert workspace.is_dir()
    assert (workspace / "workspace.json").is_file()
    assert (workspace / "qrun.toml").is_file()
    assert (workspace / "intents" / "history").is_dir()
    assert (workspace / "specs" / "history").is_dir()
    assert (workspace / "artifacts" / "qiskit").is_dir()
    assert (workspace / "artifacts" / "classiq").is_dir()
    assert (workspace / "artifacts" / "qasm").is_dir()
    assert (workspace / "figures").is_dir()
    assert (workspace / "reports" / "history").is_dir()
    assert (workspace / "trace").is_dir()
    assert (workspace / "cache").is_dir()


def test_workspace_json_contains_stable_defaults(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    result = run_cli("init", "--workspace", str(workspace), "--json")

    assert result.returncode == 0, result.stderr

    workspace_json = json.loads((workspace / "workspace.json").read_text())
    assert workspace_json["workspace_version"] == "0.1"
    assert workspace_json["project_id"].startswith("proj_")
    assert workspace_json["current_revision"] == "rev_000000"
    assert workspace_json["active_spec"] == "specs/current.json"
    assert workspace_json["active_report"] == "reports/latest.json"
    assert workspace_json["default_exports"] == ["qiskit", "qasm3"]
    assert workspace_json["history_limit"] == 50


def test_init_is_idempotent(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    first = run_cli("init", "--workspace", str(workspace), "--json")
    assert first.returncode == 0, first.stderr
    first_payload = json.loads(first.stdout)

    second = run_cli("init", "--workspace", str(workspace), "--json")
    assert second.returncode == 0, second.stderr
    second_payload = json.loads(second.stdout)

    assert second_payload["status"] == "ok"
    assert second_payload["workspace"] == str(workspace)
    assert second_payload["project_id"] == first_payload["project_id"]
    assert second_payload["current_revision"] == "rev_000000"


def test_version_command_prints_semver() -> None:
    result = run_cli("version")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "0.2.0"
