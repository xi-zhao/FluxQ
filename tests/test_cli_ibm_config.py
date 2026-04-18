from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from quantum_runtime.workspace import WorkspaceManager
from quantum_runtime.workspace.manager import DEFAULT_QRUN_TOML


PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
