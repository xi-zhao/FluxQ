from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from quantum_runtime.cli import app
from quantum_runtime.workspace import WorkspaceManager
from quantum_runtime.workspace.manager import DEFAULT_QRUN_TOML


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()


def _workspace_root(tmp_path: Path) -> Path:
    workspace = tmp_path / ".quantum"
    WorkspaceManager.load_or_init(workspace)
    return workspace


def test_ibm_profile_write_persists_only_non_secret_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quantum_runtime.runtime.ibm_access import (
        IbmAccessProfile,
        load_ibm_profile,
        write_ibm_profile,
    )

    workspace = _workspace_root(tmp_path)
    monkeypatch.setenv("QISKIT_IBM_TOKEN", "super-secret-token")

    result = write_ibm_profile(
        workspace_root=workspace,
        profile=IbmAccessProfile(
            credential_mode="env",
            instance="crn:v1:bluemix:public:quantum-computing:us-east:a/test::",
            token_env="QISKIT_IBM_TOKEN",
        ),
    )

    qrun_toml = workspace / "qrun.toml"
    qrun_payload = tomllib.loads(qrun_toml.read_text())
    ibm_profile = qrun_payload["remote"]["ibm"]

    assert result.workspace == str(workspace.resolve())
    assert ibm_profile == {
        "channel": "ibm_quantum_platform",
        "credential_mode": "env",
        "instance": "crn:v1:bluemix:public:quantum-computing:us-east:a/test::",
        "token_env": "QISKIT_IBM_TOKEN",
    }
    assert "super-secret-token" not in qrun_toml.read_text()

    loaded = load_ibm_profile(workspace_root=workspace)
    assert loaded is not None
    assert loaded.channel == "ibm_quantum_platform"
    assert loaded.credential_mode == "env"
    assert loaded.instance == "crn:v1:bluemix:public:quantum-computing:us-east:a/test::"
    assert loaded.token_env == "QISKIT_IBM_TOKEN"
    assert loaded.saved_account_name is None


def test_ibm_resolution_reports_missing_instance_reason_code(tmp_path: Path) -> None:
    from quantum_runtime.runtime.ibm_access import resolve_ibm_access

    workspace = _workspace_root(tmp_path)
    (workspace / "qrun.toml").write_text(
        DEFAULT_QRUN_TOML
        + """

[remote.ibm]
channel = "ibm_quantum_platform"
credential_mode = "env"
token_env = "QISKIT_IBM_TOKEN"
"""
    )

    resolution = resolve_ibm_access(workspace_root=workspace)

    assert resolution.status == "error"
    assert resolution.error_code == "ibm_instance_required"
    assert resolution.channel == "ibm_quantum_platform"
    assert resolution.credential_mode == "env"


def test_ibm_resolution_rejects_invalid_saved_account_profile(tmp_path: Path) -> None:
    from quantum_runtime.runtime.ibm_access import resolve_ibm_access

    workspace = _workspace_root(tmp_path)
    (workspace / "qrun.toml").write_text(
        DEFAULT_QRUN_TOML
        + """

[remote.ibm]
channel = "ibm_quantum_platform"
credential_mode = "saved_account"
token_env = "QISKIT_IBM_TOKEN"
instance = "crn:v1:bluemix:public:quantum-computing:us-east:a/test::"
"""
    )

    resolution = resolve_ibm_access(workspace_root=workspace)

    assert resolution.status == "error"
    assert resolution.error_code == "ibm_config_invalid"
    assert resolution.credential_mode == "saved_account"
    assert resolution.instance == "crn:v1:bluemix:public:quantum-computing:us-east:a/test::"


def test_ibm_resolution_builds_env_service_via_optional_import_seam(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quantum_runtime.runtime.ibm_access import (
        IbmAccessProfile,
        build_ibm_service,
        resolve_ibm_access,
        write_ibm_profile,
    )

    class FakeService:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

    class FakeModule:
        QiskitRuntimeService = FakeService

    workspace = _workspace_root(tmp_path)
    monkeypatch.setenv("QISKIT_IBM_TOKEN", "super-secret-token")
    write_ibm_profile(
        workspace_root=workspace,
        profile=IbmAccessProfile(
            credential_mode="env",
            instance="crn:v1:bluemix:public:quantum-computing:us-east:a/test::",
            token_env="QISKIT_IBM_TOKEN",
        ),
    )
    monkeypatch.setattr(
        "quantum_runtime.runtime.ibm_access.importlib.import_module",
        lambda name: FakeModule,
    )

    resolution = resolve_ibm_access(workspace_root=workspace)
    service = build_ibm_service(resolution=resolution)

    assert resolution.status == "ok"
    assert isinstance(service, FakeService)
    assert service.kwargs == {
        "channel": "ibm_quantum_platform",
        "token": "super-secret-token",
        "instance": "crn:v1:bluemix:public:quantum-computing:us-east:a/test::",
    }


def test_ibm_profile_pyproject_declares_optional_ibm_extra() -> None:
    pyproject_payload = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())

    assert pyproject_payload["project"]["optional-dependencies"]["ibm"] == [
        "qiskit-ibm-runtime~=0.46",
    ]


def test_qrun_ibm_configure_env_json_writes_non_secret_profile_reference(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / ".quantum"
    monkeypatch.setenv("QISKIT_IBM_TOKEN", "super-secret-token")

    result = RUNNER.invoke(
        app,
        [
            "ibm",
            "configure",
            "--workspace",
            str(workspace),
            "--credential-mode",
            "env",
            "--token-env",
            "QISKIT_IBM_TOKEN",
            "--instance",
            "crn:v1:bluemix:public:quantum-computing:us-east:a/test::",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["profile"]["credential_mode"] == "env"
    assert payload["profile"]["token_env"] == "QISKIT_IBM_TOKEN"
    assert payload["profile"]["instance"] == "crn:v1:bluemix:public:quantum-computing:us-east:a/test::"

    qrun_payload = tomllib.loads((workspace / "qrun.toml").read_text())
    assert qrun_payload["remote"]["ibm"] == {
        "channel": "ibm_quantum_platform",
        "credential_mode": "env",
        "instance": "crn:v1:bluemix:public:quantum-computing:us-east:a/test::",
        "token_env": "QISKIT_IBM_TOKEN",
    }
    assert "super-secret-token" not in (workspace / "qrun.toml").read_text()


def test_qrun_ibm_configure_saved_account_json_writes_profile_reference(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    result = RUNNER.invoke(
        app,
        [
            "ibm",
            "configure",
            "--workspace",
            str(workspace),
            "--credential-mode",
            "saved_account",
            "--saved-account-name",
            "fluxq-dev",
            "--instance",
            "crn:v1:bluemix:public:quantum-computing:us-east:a/test::",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["profile"]["credential_mode"] == "saved_account"
    assert payload["profile"]["saved_account_name"] == "fluxq-dev"
    assert "token_env" not in payload["profile"] or payload["profile"]["token_env"] is None

    qrun_payload = tomllib.loads((workspace / "qrun.toml").read_text())
    assert qrun_payload["remote"]["ibm"] == {
        "channel": "ibm_quantum_platform",
        "credential_mode": "saved_account",
        "instance": "crn:v1:bluemix:public:quantum-computing:us-east:a/test::",
        "saved_account_name": "fluxq-dev",
    }


@pytest.mark.parametrize(
    ("args", "reason"),
    [
        (
            [
                "--credential-mode",
                "env",
                "--instance",
                "crn:v1:bluemix:public:quantum-computing:us-east:a/test::",
            ],
            "ibm_token_external_required",
        ),
        (
            [
                "--credential-mode",
                "saved_account",
                "--instance",
                "crn:v1:bluemix:public:quantum-computing:us-east:a/test::",
                "--token-env",
                "QISKIT_IBM_TOKEN",
            ],
            "ibm_config_invalid",
        ),
        (
            [
                "--credential-mode",
                "saved_account",
                "--saved-account-name",
                "fluxq-dev",
            ],
            "ibm_instance_required",
        ),
    ],
)
def test_qrun_ibm_configure_json_rejects_invalid_flags(
    tmp_path: Path,
    args: list[str],
    reason: str,
) -> None:
    workspace = tmp_path / ".quantum"

    result = RUNNER.invoke(
        app,
        [
            "ibm",
            "configure",
            "--workspace",
            str(workspace),
            *args,
            "--json",
        ],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["reason"] == reason
    assert payload["error_code"] == reason
