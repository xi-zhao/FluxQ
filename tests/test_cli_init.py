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


def _start_lock_holder(
    workspace: Path,
    *,
    command: str,
    sleep_seconds: float = 1.5,
) -> subprocess.Popen[str]:
    script = f"""
from pathlib import Path
import sys
import time

sys.path.insert(0, {str(SRC_ROOT)!r})

from quantum_runtime.workspace import acquire_workspace_lock

workspace = Path(sys.argv[1])
command = sys.argv[2]
sleep_seconds = float(sys.argv[3])

with acquire_workspace_lock(workspace, command=command):
    print("LOCKED", flush=True)
    time.sleep(sleep_seconds)
"""
    process = subprocess.Popen(
        [sys.executable, "-u", "-c", script, str(workspace), command, str(sleep_seconds)],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    ready = process.stdout.readline().strip() if process.stdout is not None else ""
    if ready != "LOCKED":
        stderr = process.stderr.read() if process.stderr is not None else ""
        process.kill()
        raise AssertionError(f"failed to start lock holder: stdout={ready!r} stderr={stderr!r}")

    return process


def _stop_lock_holder(process: subprocess.Popen[str]) -> None:
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


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


def test_init_reports_lock_conflict_before_bootstrap_and_then_reuses_authoritative_state(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / ".quantum"
    holder = _start_lock_holder(workspace, command="pytest cli init holder")

    try:
        blocked = run_cli("init", "--workspace", str(workspace), "--json")
    finally:
        _stop_lock_holder(holder)

    blocked_output = blocked.stdout + blocked.stderr
    assert blocked.returncode != 0
    assert "workspace_lock_conflict" in blocked_output
    assert ".workspace.lock" in blocked_output

    first = run_cli("init", "--workspace", str(workspace), "--json")
    assert first.returncode == 0, first.stderr
    first_payload = json.loads(first.stdout)

    second = run_cli("init", "--workspace", str(workspace), "--json")
    assert second.returncode == 0, second.stderr
    second_payload = json.loads(second.stdout)

    assert second_payload["project_id"] == first_payload["project_id"]
    assert second_payload["current_revision"] == first_payload["current_revision"] == "rev_000000"


def test_init_ignores_interrupted_bootstrap_temp_files(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    initial = run_cli("init", "--workspace", str(workspace), "--json")
    assert initial.returncode == 0, initial.stderr
    initial_payload = json.loads(initial.stdout)

    workspace_json = workspace / "workspace.json"
    qrun_toml = workspace / "qrun.toml"
    events_jsonl = workspace / "events.jsonl"
    trace_events = workspace / "trace" / "events.ndjson"

    original_workspace_json = workspace_json.read_text()
    original_qrun_toml = qrun_toml.read_text()
    original_events_jsonl = events_jsonl.read_text()
    original_trace_events = trace_events.read_text()

    (workspace / ".workspace.json.tmp-interrupted").write_text('{"project_id":"proj_shadow"}')
    (workspace / ".qrun.toml.tmp-interrupted").write_text("[workspace]\nhistory_limit = 1\n")
    (workspace / ".events.jsonl.tmp-interrupted").write_text('{"event":"shadow"}\n')
    (workspace / "trace" / ".events.ndjson.tmp-interrupted").write_text('{"event":"shadow"}\n')

    reloaded = run_cli("init", "--workspace", str(workspace), "--json")
    assert reloaded.returncode == 0, reloaded.stderr
    reloaded_payload = json.loads(reloaded.stdout)

    assert reloaded_payload["project_id"] == initial_payload["project_id"]
    assert reloaded_payload["current_revision"] == initial_payload["current_revision"] == "rev_000000"
    assert workspace_json.read_text() == original_workspace_json
    assert qrun_toml.read_text() == original_qrun_toml
    assert events_jsonl.read_text() == original_events_jsonl
    assert trace_events.read_text() == original_trace_events


def test_version_command_prints_semver() -> None:
    result = run_cli("version")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "0.3.1"
