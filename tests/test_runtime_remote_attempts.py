from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import quantum_runtime.runtime as runtime_module
from quantum_runtime.errors import WorkspaceRecoveryRequiredError
from quantum_runtime.qspec import QSpec, summarize_qspec_semantics
from quantum_runtime.runtime.resolve import resolve_runtime_input
from quantum_runtime.workspace import WorkspaceManager, WorkspacePaths


PROJECT_ROOT = Path(__file__).resolve().parents[1]


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


def _persist_attempt(tmp_path: Path):
    workspace = tmp_path / ".quantum"
    handle = WorkspaceManager.load_or_init(workspace)
    resolved = resolve_runtime_input(
        workspace_root=workspace,
        intent_file=PROJECT_ROOT / "examples" / "intent-ghz.md",
    )
    semantics = summarize_qspec_semantics(resolved.qspec)
    attempt_id = handle.reserve_attempt()
    record = runtime_module.persist_remote_attempt(
        workspace=handle,
        attempt_id=attempt_id,
        resolved_input=resolved,
        semantic_hashes={
            "semantic_hash": semantics["semantic_hash"],
            "execution_hash": semantics["execution_hash"],
        },
        provider="ibm",
        auth_source="env:QISKIT_IBM_TOKEN",
        backend={
            "name": "ibm_kyiv",
            "instance": "crn:v1:bluemix:public:quantum-computing:us-east:a/test::",
        },
        job={"id": "job-123"},
        decision_block={"status": "open", "summary": "Submission accepted."},
        submit_payload={
            "provider": "ibm",
            "job_id": "job-123",
            "primitive": "sampler",
        },
        reason_codes=["remote_submit_accepted"],
        next_actions=["poll_remote_job"],
    )
    return workspace, handle, resolved, semantics, attempt_id, record


def test_remote_attempt_persistence_does_not_bump_workspace_revision(tmp_path: Path) -> None:
    workspace, handle, _, _, attempt_id, record = _persist_attempt(tmp_path)
    paths = WorkspacePaths(root=workspace)

    assert record.attempt_id == attempt_id
    assert Path(record.artifacts.record_path).exists()
    assert Path(record.artifacts.qspec_path).exists()
    assert Path(record.artifacts.intent_path).exists()
    assert Path(record.artifacts.plan_path).exists()
    assert Path(record.artifacts.submit_payload_path).exists()
    assert paths.remote_attempt_latest_json.exists()
    assert not (workspace / "reports" / "latest.json").exists()
    assert not (workspace / "manifests" / "latest.json").exists()
    assert handle.manifest.current_revision == "rev_000000"

    reloaded = WorkspaceManager.load_or_init(workspace)
    assert reloaded.manifest.current_revision == "rev_000000"
    assert reloaded.manifest.current_attempt == attempt_id


def test_remote_attempt_snapshots_reuse_resolved_qspec_metadata(tmp_path: Path) -> None:
    _, _, _, semantics, _, record = _persist_attempt(tmp_path)

    persisted_qspec = QSpec.model_validate_json(Path(record.artifacts.qspec_path).read_text(encoding="utf-8"))
    persisted_intent = json.loads(Path(record.artifacts.intent_path).read_text(encoding="utf-8"))
    persisted_plan = json.loads(Path(record.artifacts.plan_path).read_text(encoding="utf-8"))
    submit_payload = json.loads(Path(record.artifacts.submit_payload_path).read_text(encoding="utf-8"))
    latest_record = json.loads(Path(record.artifacts.latest_path).read_text(encoding="utf-8"))

    assert summarize_qspec_semantics(persisted_qspec)["semantic_hash"] == semantics["semantic_hash"]
    assert summarize_qspec_semantics(persisted_qspec)["execution_hash"] == semantics["execution_hash"]
    assert persisted_intent["source_kind"] == "intent_file"
    assert persisted_plan["qspec"]["semantic_hash"] == semantics["semantic_hash"]
    assert submit_payload["job_id"] == "job-123"
    assert latest_record["attempt_id"] == record.attempt_id
    assert latest_record["job"]["id"] == "job-123"


def test_load_remote_attempt_returns_saved_provider_handle_and_hashes(tmp_path: Path) -> None:
    workspace, _, _, semantics, attempt_id, _ = _persist_attempt(tmp_path)

    loaded = runtime_module.load_remote_attempt(
        workspace_root=workspace,
        attempt_id=attempt_id,
    )

    assert loaded.attempt_id == attempt_id
    assert loaded.provider == "ibm"
    assert loaded.backend.name == "ibm_kyiv"
    assert loaded.backend.instance == "crn:v1:bluemix:public:quantum-computing:us-east:a/test::"
    assert loaded.job.id == "job-123"
    assert loaded.qspec.semantic_hash == semantics["semantic_hash"]
    assert loaded.qspec.execution_hash == semantics["execution_hash"]


def test_remote_attempt_persistence_fails_closed_on_pending_latest_alias(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    handle = WorkspaceManager.load_or_init(workspace)
    resolved = resolve_runtime_input(
        workspace_root=workspace,
        intent_file=PROJECT_ROOT / "examples" / "intent-ghz.md",
    )
    semantics = summarize_qspec_semantics(resolved.qspec)
    attempt_id = handle.reserve_attempt()
    paths = WorkspacePaths(root=workspace)
    pending_path = paths.remote_attempt_latest_json.parent / f".{paths.remote_attempt_latest_json.name}.tmp-stale"
    pending_path.write_text("stale", encoding="utf-8")

    with pytest.raises(WorkspaceRecoveryRequiredError):
        runtime_module.persist_remote_attempt(
            workspace=handle,
            attempt_id=attempt_id,
            resolved_input=resolved,
            semantic_hashes={
                "semantic_hash": semantics["semantic_hash"],
                "execution_hash": semantics["execution_hash"],
            },
            provider="ibm",
            auth_source="env:QISKIT_IBM_TOKEN",
            backend={
                "name": "ibm_kyiv",
                "instance": "crn:v1:bluemix:public:quantum-computing:us-east:a/test::",
            },
            job={"id": "job-123"},
            decision_block={"status": "open", "summary": "Submission accepted."},
            submit_payload={
                "provider": "ibm",
                "job_id": "job-123",
                "primitive": "sampler",
            },
            reason_codes=["remote_submit_accepted"],
            next_actions=["poll_remote_job"],
        )

    assert not paths.remote_attempt_history_json(attempt_id).exists()
