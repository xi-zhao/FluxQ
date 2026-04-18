from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import quantum_runtime.cli as cli_module
from quantum_runtime.cli import app
from quantum_runtime.errors import WorkspaceConflictError
from quantum_runtime.runtime.contracts import DEFAULT_REMEDIATION, remediation_for_error
from quantum_runtime.runtime.ibm_access import IbmAccessError, IbmAccessResolution
from quantum_runtime.runtime.observability import next_actions_for_reason_codes
from quantum_runtime.workspace import WorkspaceManager
from quantum_runtime.workspace.manager import DEFAULT_QRUN_TOML


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()


def _doctor_capabilities() -> dict[str, dict[str, object]]:
    return {
        "qiskit-local": {
            "backend": "qiskit-local",
            "provider": "qiskit",
            "available": True,
            "optional": False,
            "reason": None,
            "module_dependencies": [],
            "capabilities": {"remote_submit": False},
            "notes": ["Local Qiskit backend"],
        }
    }


def _write_remote_ibm_profile(
    workspace: Path,
    *,
    credential_mode: str = "env",
    token_env: str = "QISKIT_IBM_TOKEN",
    saved_account_name: str = "fluxq-dev",
    instance: str = "crn:v1:bluemix:public:quantum-computing:us-east:a/test::",
) -> None:
    if credential_mode == "env":
        remote_block = f"""

[remote.ibm]
channel = "ibm_quantum_platform"
credential_mode = "env"
token_env = "{token_env}"
instance = "{instance}"
"""
    else:
        remote_block = f"""

[remote.ibm]
channel = "ibm_quantum_platform"
credential_mode = "saved_account"
saved_account_name = "{saved_account_name}"
instance = "{instance}"
"""
    (workspace / "qrun.toml").write_text(DEFAULT_QRUN_TOML + remote_block)


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
    assert all(event["phase"] == "doctor" for event in events)
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
    assert "doctor_written" in [event["event_type"] for event in events]
    assert all(event["phase"] == "doctor" for event in events)
    assert events[-1]["payload"]["schema_version"] == "0.3.0"
    assert "active_report_missing" in events[-1]["payload"]["blocking_issues"]
    assert isinstance(events[-1]["payload"]["advisory_issues"], list)
    assert events[-1]["payload"]["verdict"]["status"] == "fail"
    assert events[-1]["payload"]["gate"]["ready"] is False


def test_qrun_doctor_jsonl_workspace_safety_failure_uses_doctor_completed_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / ".quantum"

    monkeypatch.setattr(
        cli_module,
        "run_doctor",
        lambda **kwargs: (_ for _ in ()).throw(
            WorkspaceConflictError(
                workspace=workspace,
                lock_path=workspace / "locks" / "workspace.lock",
                holder={"pid": 4242, "hostname": "ci-runner"},
            )
        ),
    )

    result = RUNNER.invoke(
        app,
        ["doctor", "--workspace", str(workspace), "--jsonl"],
    )

    assert result.exit_code == 3, result.stdout
    events = _parse_jsonl(result.stdout)
    assert events[-1]["event_type"] == "doctor_completed"
    assert events[-1]["phase"] == "doctor"
    assert events[-1]["payload"]["reason"] == "workspace_conflict"


def test_doctor_jsonl_ci_preserves_ibm_reason_codes_and_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / ".quantum"
    WorkspaceManager.load_or_init(workspace)
    _write_remote_ibm_profile(workspace, credential_mode="env")

    monkeypatch.setattr(
        "quantum_runtime.runtime.doctor.collect_backend_capabilities",
        _doctor_capabilities,
    )
    monkeypatch.setattr(
        "quantum_runtime.runtime.doctor.resolve_ibm_access",
        lambda *, workspace_root: IbmAccessResolution(
            status="error",
            configured=True,
            channel="ibm_quantum_platform",
            credential_mode="env",
            instance="crn:v1:bluemix:public:quantum-computing:us-east:a/test::",
            token_env="QISKIT_IBM_TOKEN",
            error_code="ibm_token_env_missing",
            reason_codes=["ibm_token_env_missing"],
        ),
        raising=False,
    )

    json_result = RUNNER.invoke(
        app,
        ["doctor", "--workspace", str(workspace), "--json", "--ci"],
    )
    assert json_result.exit_code == 2, json_result.stdout
    json_payload = json.loads(json_result.stdout)
    ibm_codes = [code for code in json_payload["reason_codes"] if str(code).startswith("ibm_")]
    assert ibm_codes == ["ibm_token_env_missing"]
    assert all(remediation_for_error(code) != DEFAULT_REMEDIATION for code in ibm_codes)
    assert next_actions_for_reason_codes(ibm_codes) == ["set_ibm_token_env"]

    jsonl_result = RUNNER.invoke(
        app,
        ["doctor", "--workspace", str(workspace), "--jsonl", "--ci"],
    )
    assert jsonl_result.exit_code == 2, jsonl_result.stdout
    events = _parse_jsonl(jsonl_result.stdout)
    completion = events[-1]["payload"]

    assert completion["reason_codes"] == json_payload["reason_codes"]
    assert completion["next_actions"] == json_payload["next_actions"]
    assert completion["gate"] == json_payload["gate"]
    assert completion["gate"]["ready"] is False


def test_doctor_jsonl_ci_redacts_ibm_secret_material(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / ".quantum"
    WorkspaceManager.load_or_init(workspace)
    _write_remote_ibm_profile(workspace, credential_mode="env")
    monkeypatch.setenv("QISKIT_IBM_TOKEN", "super-secret-token")

    monkeypatch.setattr(
        "quantum_runtime.runtime.doctor.collect_backend_capabilities",
        _doctor_capabilities,
    )
    monkeypatch.setattr(
        "quantum_runtime.runtime.doctor.resolve_ibm_access",
        lambda *, workspace_root: IbmAccessResolution(
            status="ok",
            configured=True,
            channel="ibm_quantum_platform",
            credential_mode="env",
            instance="crn:v1:bluemix:public:quantum-computing:us-east:a/test::",
            token_env="QISKIT_IBM_TOKEN",
        ),
        raising=False,
    )
    monkeypatch.setattr(
        "quantum_runtime.runtime.doctor.build_ibm_service",
        lambda *, resolution: (_ for _ in ()).throw(
            IbmAccessError(
                "ibm_token_external_required",
                details={
                    "token_env": "QISKIT_IBM_TOKEN",
                    "authorization": "Bearer super-secret-token",
                },
            )
        ),
        raising=False,
    )

    result = RUNNER.invoke(
        app,
        ["doctor", "--workspace", str(workspace), "--jsonl", "--ci"],
    )

    assert result.exit_code == 2, result.stdout
    assert "super-secret-token" not in result.stdout
    assert "Authorization" not in result.stdout
    assert "Bearer " not in result.stdout

    events = _parse_jsonl(result.stdout)
    completion = events[-1]["payload"]
    assert completion["gate"]["ready"] is False
    assert any(str(code).startswith("ibm_") for code in completion["reason_codes"])


def test_ibm_doctor_jsonl_ci_preserves_ibm_reason_codes_and_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_doctor_jsonl_ci_preserves_ibm_reason_codes_and_gate(tmp_path, monkeypatch)


def test_ibm_doctor_jsonl_ci_redacts_ibm_secret_material(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_doctor_jsonl_ci_redacts_ibm_secret_material(tmp_path, monkeypatch)


def _remote_submit_ibm_resolution() -> IbmAccessResolution:
    return IbmAccessResolution(
        status="ok",
        configured=True,
        channel="ibm_quantum_platform",
        credential_mode="saved_account",
        instance="crn:v1:bluemix:public:quantum-computing:us-east:a/test::",
        saved_account_name="fluxq-dev",
    )


def test_remote_submit_reason_codes_map_to_machine_actions() -> None:
    expected_actions = {
        "remote_backend_required": "choose_explicit_backend",
        "remote_backend_not_ready": "run_backend_list",
        "remote_submit_failed": "retry_submit_when_backend_ready",
        "remote_attempt_persist_failed": "inspect_remote_attempt_store",
        "ibm_profile_missing": "configure_ibm_profile",
        "ibm_runtime_dependency_missing": "install_ibm_extra",
        "ibm_backend_lookup_failed": "run_backend_list",
    }

    for code, action in expected_actions.items():
        assert remediation_for_error(code) != DEFAULT_REMEDIATION
        assert action in next_actions_for_reason_codes([code])


def test_qrun_remote_submit_json_exposes_reason_codes_next_actions_and_decision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / ".quantum"

    monkeypatch.setattr(
        "quantum_runtime.runtime.remote_submit.resolve_ibm_access",
        lambda *, workspace_root: _remote_submit_ibm_resolution(),
        raising=False,
    )
    monkeypatch.setattr(
        "quantum_runtime.runtime.remote_submit.build_ibm_service",
        lambda *, resolution: object(),
        raising=False,
    )
    monkeypatch.setattr(
        "quantum_runtime.runtime.remote_submit.submit_ibm_job",
        lambda *, service, backend_name, qspec, shots: {
            "job_id": "job-123",
            "job_status": "QUEUED",
            "primitive": "sampler_v2",
        },
        raising=False,
    )

    result = RUNNER.invoke(
        app,
        [
            "remote",
            "submit",
            "--workspace",
            str(workspace),
            "--backend",
            "ibm_brisbane",
            "--intent-text",
            "Generate a 4-qubit GHZ circuit and measure all qubits.",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["reason_codes"] == ["remote_submit_persisted"]
    assert payload["next_actions"] == ["inspect_remote_attempt_store"]
    assert payload["decision"]["ready"] is True
    assert payload["decision"]["severity"] == "info"
    assert payload["decision"]["recommended_action"] == "inspect_remote_attempt_store"


def test_qrun_remote_submit_json_blocks_backend_lookup_with_stable_gate_and_redaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / ".quantum"

    monkeypatch.setattr(
        "quantum_runtime.runtime.remote_submit.resolve_ibm_access",
        lambda *, workspace_root: _remote_submit_ibm_resolution(),
        raising=False,
    )
    monkeypatch.setattr(
        "quantum_runtime.runtime.remote_submit.build_ibm_service",
        lambda *, resolution: object(),
        raising=False,
    )
    monkeypatch.setattr(
        "quantum_runtime.runtime.remote_submit.submit_ibm_job",
        lambda *, service, backend_name, qspec, shots: (_ for _ in ()).throw(
            IbmAccessError(
                "ibm_backend_lookup_failed",
                details={
                    "backend_name": backend_name,
                    "authorization": "Bearer super-secret-token",
                },
            )
        ),
        raising=False,
    )

    result = RUNNER.invoke(
        app,
        [
            "remote",
            "submit",
            "--workspace",
            str(workspace),
            "--backend",
            "ibm_brisbane",
            "--intent-text",
            "Generate a 4-qubit GHZ circuit and measure all qubits.",
            "--json",
        ],
    )

    assert result.exit_code == 2, result.stdout
    assert "super-secret-token" not in result.stdout
    assert "Authorization" not in result.stdout
    assert "Bearer " not in result.stdout

    payload = json.loads(result.stdout)
    assert payload["reason_codes"] == ["remote_backend_not_ready", "ibm_backend_lookup_failed"]
    assert payload["next_actions"] == ["run_backend_list", "retry_submit_when_backend_ready"]
    assert payload["gate"]["ready"] is False
    assert payload["gate"]["severity"] == "error"
    assert payload["gate"]["recommended_action"] == "run_backend_list"


def test_qrun_remote_submit_json_blocks_ibm_access_and_provider_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / ".quantum"

    monkeypatch.setattr(
        "quantum_runtime.runtime.remote_submit.resolve_ibm_access",
        lambda *, workspace_root: IbmAccessResolution(
            status="error",
            configured=True,
            channel="ibm_quantum_platform",
            credential_mode="env",
            instance="crn:v1:bluemix:public:quantum-computing:us-east:a/test::",
            token_env="QISKIT_IBM_TOKEN",
            error_code="ibm_token_env_missing",
            reason_codes=["ibm_token_env_missing"],
        ),
        raising=False,
    )

    access_result = RUNNER.invoke(
        app,
        [
            "remote",
            "submit",
            "--workspace",
            str(workspace),
            "--backend",
            "ibm_brisbane",
            "--intent-text",
            "Generate a 4-qubit GHZ circuit and measure all qubits.",
            "--json",
        ],
    )

    assert access_result.exit_code == 2, access_result.stdout
    access_payload = json.loads(access_result.stdout)
    assert access_payload["reason_codes"] == ["ibm_token_env_missing"]
    assert access_payload["next_actions"] == ["set_ibm_token_env"]
    assert access_payload["gate"]["ready"] is False

    monkeypatch.setattr(
        "quantum_runtime.runtime.remote_submit.resolve_ibm_access",
        lambda *, workspace_root: _remote_submit_ibm_resolution(),
        raising=False,
    )
    monkeypatch.setattr(
        "quantum_runtime.runtime.remote_submit.build_ibm_service",
        lambda *, resolution: object(),
        raising=False,
    )
    monkeypatch.setattr(
        "quantum_runtime.runtime.remote_submit.submit_ibm_job",
        lambda *, service, backend_name, qspec, shots: (_ for _ in ()).throw(
            RuntimeError("Authorization: Bearer super-secret-token")
        ),
        raising=False,
    )

    provider_result = RUNNER.invoke(
        app,
        [
            "remote",
            "submit",
            "--workspace",
            str(workspace),
            "--backend",
            "ibm_brisbane",
            "--intent-text",
            "Generate a 4-qubit GHZ circuit and measure all qubits.",
            "--json",
        ],
    )

    assert provider_result.exit_code == 2, provider_result.stdout
    assert "super-secret-token" not in provider_result.stdout
    assert "Authorization" not in provider_result.stdout
    assert "Bearer " not in provider_result.stdout

    provider_payload = json.loads(provider_result.stdout)
    assert provider_payload["reason_codes"] == ["remote_submit_failed"]
    assert provider_payload["next_actions"] == ["retry_submit_when_backend_ready"]
    assert provider_payload["gate"]["ready"] is False
