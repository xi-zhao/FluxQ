from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path

import pytest
from pydantic import ValidationError

import quantum_runtime.runtime as runtime_module
from quantum_runtime.workspace import WorkspaceManager, WorkspacePaths


def _load_remote_attempts_module():
    spec = importlib.util.find_spec("quantum_runtime.runtime.remote_attempts")
    assert spec is not None, "quantum_runtime.runtime.remote_attempts must exist"
    return importlib.import_module("quantum_runtime.runtime.remote_attempts")


def test_workspace_attempt_sequencing_is_separate_from_revision(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    handle = WorkspaceManager.load_or_init(workspace)

    assert handle.manifest.current_revision == "rev_000000"
    assert handle.manifest.current_attempt == "attempt_000000"

    attempt_id = handle.reserve_attempt()

    assert attempt_id == "attempt_000001"
    assert handle.manifest.current_revision == "rev_000000"
    assert handle.manifest.current_attempt == "attempt_000001"

    reloaded = WorkspaceManager.load_or_init(workspace)
    assert reloaded.manifest.current_revision == "rev_000000"
    assert reloaded.manifest.current_attempt == "attempt_000001"


def test_workspace_paths_seed_remote_attempt_skeleton(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    WorkspaceManager.load_or_init(workspace)
    paths = WorkspacePaths(root=workspace)

    assert paths.remote_attempts_history_dir.exists()
    assert paths.remote_attempt_latest_json == workspace / "remote" / "attempts" / "latest.json"
    assert paths.remote_artifacts_history_dir.exists()
    assert paths.remote_events_dir.exists()
    assert paths.remote_events_history_dir.exists()
    assert paths.remote_trace_dir.exists()
    assert paths.remote_trace_history_dir.exists()


def test_remote_attempt_record_rejects_secret_bearing_fields() -> None:
    module = _load_remote_attempts_module()

    with pytest.raises(ValidationError):
        module.RemoteAttemptRecord(
            attempt_id="attempt_000001",
            provider="ibm",
            auth_source="env:QISKIT_IBM_TOKEN",
            backend={
                "name": "ibm_kyiv",
                "instance": "crn:v1:bluemix:public:quantum-computing:us-east:a/test::",
            },
            job={"id": "job-123"},
            input={
                "source_kind": "intent_file",
                "source": "examples/intent-ghz.md",
            },
            qspec={
                "semantic_hash": "semantic:123",
                "execution_hash": "execution:123",
            },
            artifacts={
                "record_path": "/tmp/.quantum/remote/attempts/history/attempt_000001.json",
                "latest_path": "/tmp/.quantum/remote/attempts/latest.json",
                "qspec_path": "/tmp/.quantum/remote/artifacts/history/attempt_000001/qspec.json",
                "intent_path": "/tmp/.quantum/remote/artifacts/history/attempt_000001/intent.json",
                "plan_path": "/tmp/.quantum/remote/artifacts/history/attempt_000001/plan.json",
                "submit_payload_path": "/tmp/.quantum/remote/artifacts/history/attempt_000001/submit_payload.json",
            },
            reason_codes=["remote_submit_ready"],
            next_actions=["poll_remote_job"],
            gate={"status": "open"},
            token="secret-token",
        )


def test_runtime_exports_remote_attempt_helpers() -> None:
    assert hasattr(runtime_module, "RemoteAttemptRecord")
    assert hasattr(runtime_module, "RemoteAttemptBackend")
    assert hasattr(runtime_module, "RemoteAttemptJob")
    assert hasattr(runtime_module, "reserve_attempt_id")
