from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import quantum_runtime.cli as cli_module
from quantum_runtime.cli import app
from quantum_runtime.errors import WorkspaceConflictError, WorkspaceRecoveryRequiredError


RUNNER = CliRunner()


def _write_intent(path: Path) -> None:
    path.write_text(
        """---
title: Workspace safety intent
---

Prepare a GHZ circuit.
"""
    )


def _raise_workspace_error(error: Exception):
    def _raiser(*args: object, **kwargs: object) -> object:
        raise error

    return _raiser


def test_qrun_exec_json_reports_workspace_conflict_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / ".quantum"
    intent_path = tmp_path / "intent.md"
    _write_intent(intent_path)

    monkeypatch.setattr(
        cli_module,
        "execute_intent",
        _raise_workspace_error(
            WorkspaceConflictError(
                workspace=workspace,
                lock_path=workspace / "locks" / "workspace.lock",
                holder={
                    "pid": 4242,
                    "hostname": "ci-runner-7",
                    "operation": "exec",
                    "agent_id": "agent-17",
                    "acquired_at": "2026-04-12T07:08:09Z",
                },
            )
        ),
    )

    result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(intent_path),
            "--json",
        ],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "error"
    assert payload["reason"] == "workspace_conflict"
    assert payload["error_code"] == "workspace_conflict"
    assert payload["remediation"] == (
        "Wait for the current workspace lease holder to finish, then retry the command or use a different workspace."
    )
    assert payload["details"] == {
        "workspace": str(workspace),
        "lock_path": str(workspace / "locks" / "workspace.lock"),
        "holder": {
            "pid": 4242,
            "hostname": "ci-runner-7",
            "operation": "exec",
            "agent_id": "agent-17",
            "acquired_at": "2026-04-12T07:08:09Z",
        },
        "reason_codes": ["workspace_conflict"],
        "next_actions": ["retry_when_workspace_free", "inspect_workspace_lock"],
        "gate": {
            "ready": False,
            "severity": "warning",
            "reason_codes": ["workspace_conflict"],
            "recommended_action": "retry_when_workspace_free",
        },
    }


def test_qrun_exec_json_reports_workspace_recovery_required_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / ".quantum"
    intent_path = tmp_path / "intent.md"
    _write_intent(intent_path)

    pending_files = [
        workspace / "reports" / "latest.json.tmp",
        workspace / "manifests" / "latest.json.tmp",
    ]
    monkeypatch.setattr(
        cli_module,
        "execute_intent",
        _raise_workspace_error(
            WorkspaceRecoveryRequiredError(
                workspace=workspace,
                pending_files=pending_files,
                last_valid_revision="rev_000007",
            )
        ),
    )

    result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(intent_path),
            "--json",
        ],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.3.0"
    assert payload["status"] == "error"
    assert payload["reason"] == "workspace_recovery_required"
    assert payload["error_code"] == "workspace_recovery_required"
    assert payload["remediation"] == (
        "Run `qrun doctor --fix` or clear the interrupted-write leftovers after validating the last known good revision."
    )
    assert payload["details"] == {
        "workspace": str(workspace),
        "pending_files": [str(item) for item in pending_files],
        "last_valid_revision": "rev_000007",
        "alias_paths": [],
        "recovery_mode": "pending_files",
        "reason_codes": ["workspace_recovery_required"],
        "next_actions": ["run_doctor_fix", "review_workspace_recovery"],
        "gate": {
            "ready": False,
            "severity": "error",
            "reason_codes": ["workspace_recovery_required"],
            "recommended_action": "run_doctor_fix",
        },
    }


def test_qrun_exec_json_reports_workspace_recovery_required_alias_mismatch_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / ".quantum"
    intent_path = tmp_path / "intent.md"
    _write_intent(intent_path)
    alias_paths = [
        workspace / "workspace.json",
        workspace / "specs" / "current.json",
        workspace / "reports" / "latest.json",
        workspace / "manifests" / "latest.json",
    ]

    monkeypatch.setattr(
        cli_module,
        "execute_intent",
        _raise_workspace_error(
            WorkspaceRecoveryRequiredError(
                workspace=workspace,
                pending_files=[],
                alias_paths=alias_paths,
                last_valid_revision="rev_000007",
                recovery_mode="alias_mismatch",
            )
        ),
    )

    result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(intent_path),
            "--json",
        ],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["remediation"] == (
        "Review alias_paths, restore the active aliases to one coherent revision, then retry the command."
    )
    assert payload["details"] == {
        "workspace": str(workspace),
        "pending_files": [],
        "last_valid_revision": "rev_000007",
        "alias_paths": [str(item) for item in alias_paths],
        "recovery_mode": "alias_mismatch",
        "reason_codes": ["workspace_recovery_required", "workspace_alias_mismatch"],
        "next_actions": ["review_alias_paths", "restore_active_aliases"],
        "gate": {
            "ready": False,
            "severity": "error",
            "reason_codes": ["workspace_recovery_required", "workspace_alias_mismatch"],
            "recommended_action": "review_alias_paths",
        },
    }


@pytest.mark.parametrize(
    ("error", "expected_parts"),
    [
        (
            WorkspaceConflictError(
                workspace=Path("/tmp/ws"),
                lock_path=Path("/tmp/ws/locks/workspace.lock"),
                holder={
                    "pid": 4242,
                    "hostname": "ci-runner-7",
                    "operation": "exec",
                },
            ),
            [
                "Workspace conflict",
                "ci-runner-7",
                "pid 4242",
                "retry",
            ],
        ),
        (
            WorkspaceRecoveryRequiredError(
                workspace=Path("/tmp/ws"),
                pending_files=[
                    Path("/tmp/ws/reports/latest.json.tmp"),
                    Path("/tmp/ws/manifests/latest.json.tmp"),
                ],
                last_valid_revision="rev_000007",
            ),
            [
                "Workspace recovery required",
                "rev_000007",
                "qrun doctor --fix",
            ],
        ),
    ],
)
def test_qrun_exec_text_reports_workspace_safety_errors_concisely(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_parts: list[str],
) -> None:
    workspace = tmp_path / ".quantum"
    intent_path = tmp_path / "intent.md"
    _write_intent(intent_path)

    monkeypatch.setattr(
        cli_module,
        "execute_intent",
        _raise_workspace_error(error),
    )

    result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(intent_path),
        ],
    )

    assert result.exit_code == 3, result.stdout
    for expected in expected_parts:
        assert expected in result.stdout
