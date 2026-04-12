from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from quantum_runtime.workspace import (
    WorkspaceLockConflict,
    WorkspaceManager,
    acquire_workspace_lock,
    atomic_write_text,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"


@pytest.mark.parametrize(
    ("relative_path", "replacement"),
    [
        (Path("workspace.json"), '{"workspace_version":"interrupted"}\n'),
        (Path("qrun.toml"), "[workspace]\nhistory_limit = 1\n"),
        (Path("events.jsonl"), '{"event":"interrupted"}\n'),
        (Path("trace/events.ndjson"), '{"event":"interrupted"}\n'),
    ],
)
def test_atomic_write_text_preserves_authoritative_bootstrap_files_on_replace_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative_path: Path,
    replacement: str,
) -> None:
    workspace = tmp_path / ".quantum"
    handle = WorkspaceManager.load_or_init(workspace)
    target = workspace / relative_path
    original = target.read_text()

    def _interrupted_replace(source: str | os.PathLike[str], destination: str | os.PathLike[str]) -> None:
        raise OSError("simulated replace interruption")

    monkeypatch.setattr("quantum_runtime.workspace.manifest.os.replace", _interrupted_replace)

    with pytest.raises(OSError, match="simulated replace interruption"):
        atomic_write_text(target, replacement)

    assert target.read_text() == original

    temp_files = list(target.parent.glob(f".{target.name}.tmp-*"))
    assert temp_files
    assert any(temp_file.read_text() == replacement for temp_file in temp_files)

    reloaded = WorkspaceManager.load_or_init(workspace)
    assert reloaded.manifest.project_id == handle.manifest.project_id
    assert reloaded.manifest.current_revision == handle.manifest.current_revision


def test_acquire_workspace_lock_records_holder_metadata(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    with acquire_workspace_lock(workspace, command="pytest metadata holder") as lock:
        payload = json.loads(Path(lock.lock_path).read_text())

    assert payload["pid"] == lock.pid == os.getpid()
    assert payload["hostname"] == lock.hostname
    assert payload["command"] == "pytest metadata holder"
    assert payload["started_at"] == lock.started_at
    assert payload["lock_path"] == lock.lock_path
    assert lock.lock_path.endswith(".workspace.lock")


def test_load_or_init_fails_fast_with_conflict_metadata_when_workspace_lock_is_held(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / ".quantum"

    with acquire_workspace_lock(workspace, command="pytest bootstrap holder") as lock:
        with pytest.raises(WorkspaceLockConflict) as exc_info:
            WorkspaceManager.load_or_init(workspace)

    conflict = exc_info.value
    assert conflict.code == "workspace_lock_conflict"
    assert conflict.lock_path == lock.lock_path
    assert conflict.holder.pid == lock.pid
    assert conflict.holder.hostname == lock.hostname
    assert conflict.holder.command == "pytest bootstrap holder"
    assert conflict.holder.started_at == lock.started_at
    assert not (workspace / "workspace.json").exists()


def test_reserve_revision_fails_fast_instead_of_advancing_when_writer_lock_is_held(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / ".quantum"
    handle = WorkspaceManager.load_or_init(workspace)

    with acquire_workspace_lock(workspace, command="pytest revision holder") as lock:
        with pytest.raises(WorkspaceLockConflict) as exc_info:
            handle.reserve_revision()

    conflict = exc_info.value
    assert conflict.lock_path == lock.lock_path
    assert conflict.holder.command == "pytest revision holder"

    reloaded = WorkspaceManager.load_or_init(workspace)
    assert reloaded.manifest.current_revision == "rev_000000"


def test_load_or_init_reuses_authoritative_bootstrap_state_after_lock_release(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    with acquire_workspace_lock(workspace, command="pytest transient holder"):
        with pytest.raises(WorkspaceLockConflict):
            WorkspaceManager.load_or_init(workspace)

    first = WorkspaceManager.load_or_init(workspace)
    second = WorkspaceManager.load_or_init(workspace)

    assert second.manifest.project_id == first.manifest.project_id
    assert second.manifest.current_revision == first.manifest.current_revision == "rev_000000"


def start_lock_holder(workspace: Path, *, command: str) -> subprocess.Popen[str]:
    script = f"""
from pathlib import Path
import sys
import time

sys.path.insert(0, {str(SRC_ROOT)!r})

from quantum_runtime.workspace import acquire_workspace_lock

workspace = Path(sys.argv[1])
command = sys.argv[2]

with acquire_workspace_lock(workspace, command=command):
    print("LOCKED", flush=True)
    time.sleep(30)
"""
    process = subprocess.Popen(
        [sys.executable, "-u", "-c", script, str(workspace), command],
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


def stop_lock_holder(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
