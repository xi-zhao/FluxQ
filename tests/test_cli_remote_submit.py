from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from quantum_runtime.errors import WorkspaceConflictError, WorkspaceRecoveryRequiredError
from quantum_runtime.cli import app
from quantum_runtime.intent.parser import parse_intent_file
from quantum_runtime.intent.planner import plan_to_qspec
from quantum_runtime.qspec import QSpec, summarize_qspec_semantics
from quantum_runtime.runtime import load_remote_attempt
from quantum_runtime.workspace import WorkspacePaths


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()


def _load_remote_submit_module():
    spec = importlib.util.find_spec("quantum_runtime.runtime.remote_submit")
    assert spec is not None, "quantum_runtime.runtime.remote_submit must exist"
    return importlib.import_module("quantum_runtime.runtime.remote_submit")


def _load_ibm_remote_submit_module():
    spec = importlib.util.find_spec("quantum_runtime.runtime.ibm_remote_submit")
    assert spec is not None, "quantum_runtime.runtime.ibm_remote_submit must exist"
    return importlib.import_module("quantum_runtime.runtime.ibm_remote_submit")


def _ghz_qspec() -> QSpec:
    return plan_to_qspec(parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md"))


def _intent_json_path(tmp_path: Path) -> Path:
    path = tmp_path / "intent-ghz.json"
    path.write_text(
        parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md").model_dump_json(indent=2),
        encoding="utf-8",
    )
    return path


def _qspec_path(tmp_path: Path) -> Path:
    path = tmp_path / "ghz-qspec.json"
    path.write_text(_ghz_qspec().model_dump_json(indent=2), encoding="utf-8")
    return path


def _report_sources(tmp_path: Path) -> tuple[Path, Path, str]:
    source_workspace = tmp_path / ".quantum-source"
    result = RUNNER.invoke(
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
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    return source_workspace, source_workspace / "reports" / "latest.json", payload["revision"]


def _submit_kwargs_for_source(tmp_path: Path, source_kind: str) -> tuple[Path, dict[str, object], QSpec]:
    expected_qspec = _ghz_qspec()
    if source_kind == "intent_file":
        workspace = tmp_path / ".quantum"
        return (
            workspace,
            {"intent_file": PROJECT_ROOT / "examples" / "intent-ghz.md"},
            expected_qspec,
        )
    if source_kind == "intent_json_file":
        workspace = tmp_path / ".quantum"
        return (
            workspace,
            {"intent_json_file": _intent_json_path(tmp_path)},
            expected_qspec,
        )
    if source_kind == "qspec_file":
        workspace = tmp_path / ".quantum"
        return (
            workspace,
            {"qspec_file": _qspec_path(tmp_path)},
            expected_qspec,
        )
    if source_kind == "prompt_text":
        workspace = tmp_path / ".quantum"
        return (
            workspace,
            {"intent_text": "Generate a 4-qubit GHZ circuit and measure all qubits."},
            expected_qspec,
        )
    source_workspace, report_path, revision = _report_sources(tmp_path)
    if source_kind == "report_file":
        target_workspace = tmp_path / ".quantum-target"
        return target_workspace, {"report_file": report_path}, expected_qspec
    if source_kind == "report_revision":
        return source_workspace, {"revision": revision}, expected_qspec
    raise AssertionError(f"unsupported source kind: {source_kind}")


def _fake_ibm_resolution():
    from quantum_runtime.runtime.ibm_access import IbmAccessResolution

    return IbmAccessResolution(
        status="ok",
        configured=True,
        channel="ibm_quantum_platform",
        credential_mode="saved_account",
        instance="crn:v1:bluemix:public:quantum-computing:us-east:a/test::",
        saved_account_name="fluxq-dev",
    )


@pytest.mark.parametrize(
    "source_kind",
    [
        "intent_file",
        "intent_json_file",
        "qspec_file",
        "prompt_text",
        "report_file",
        "report_revision",
    ],
)
def test_submit_remote_input_accepts_canonical_sources_and_persists_attempt(
    tmp_path: Path,
    monkeypatch,
    source_kind: str,
) -> None:
    module = _load_remote_submit_module()
    workspace, input_kwargs, expected_qspec = _submit_kwargs_for_source(tmp_path, source_kind)
    captured: dict[str, object] = {}

    def _fake_submit_ibm_job(*, service, backend_name: str, qspec: QSpec, shots: int):
        captured["backend_name"] = backend_name
        semantics = summarize_qspec_semantics(qspec)
        captured["semantic_hash"] = semantics["semantic_hash"]
        captured["execution_hash"] = semantics["execution_hash"]
        captured["shots"] = shots
        return {
            "job_id": "job-123",
            "job_status": "QUEUED",
        }

    monkeypatch.setattr(module, "resolve_ibm_access", lambda *, workspace_root: _fake_ibm_resolution())
    monkeypatch.setattr(module, "build_ibm_service", lambda *, resolution: object())
    monkeypatch.setattr(module, "submit_ibm_job", _fake_submit_ibm_job)

    result = module.submit_remote_input(
        workspace_root=workspace,
        backend_name="ibm_brisbane",
        **input_kwargs,
    )

    assert result.attempt_id.startswith("attempt_")
    assert result.job.id == "job-123"
    assert result.job.status == "QUEUED"
    assert result.backend.name == "ibm_brisbane"
    assert result.backend.instance == "crn:v1:bluemix:public:quantum-computing:us-east:a/test::"
    assert result.qspec.semantic_hash == captured["semantic_hash"]
    assert result.qspec.execution_hash == captured["execution_hash"]
    assert captured["backend_name"] == "ibm_brisbane"
    assert captured["shots"] == expected_qspec.constraints.shots

    persisted = load_remote_attempt(workspace_root=workspace, attempt_id=result.attempt_id)
    assert persisted.attempt_id == result.attempt_id
    assert persisted.job.id == "job-123"
    assert persisted.job.status == "QUEUED"
    assert persisted.backend.name == "ibm_brisbane"
    assert persisted.backend.instance == "crn:v1:bluemix:public:quantum-computing:us-east:a/test::"
    assert persisted.qspec.semantic_hash == captured["semantic_hash"]
    assert persisted.qspec.execution_hash == captured["execution_hash"]


def test_submit_remote_input_requires_explicit_backend_name(tmp_path: Path) -> None:
    module = _load_remote_submit_module()

    with pytest.raises(ValueError, match="remote_backend_required"):
        module.submit_remote_input(
            workspace_root=tmp_path / ".quantum",
            backend_name="   ",
            intent_text="Generate a 4-qubit GHZ circuit and measure all qubits.",
        )


def test_submit_remote_input_checks_workspace_recovery_before_provider_submit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_remote_submit_module()
    workspace = tmp_path / ".quantum"
    handle = module.WorkspaceManager.load_or_init(workspace)
    paths = WorkspacePaths(root=workspace)
    pending_path = paths.remote_attempt_latest_json.parent / f".{paths.remote_attempt_latest_json.name}.tmp-stale"
    pending_path.write_text("stale", encoding="utf-8")

    submit_called = False

    def _fake_submit_ibm_job(*, service, backend_name: str, qspec: QSpec, shots: int):
        nonlocal submit_called
        submit_called = True
        return {"job_id": "job-123", "job_status": "QUEUED"}

    monkeypatch.setattr(module, "resolve_ibm_access", lambda *, workspace_root: _fake_ibm_resolution())
    monkeypatch.setattr(module, "build_ibm_service", lambda *, resolution: object())
    monkeypatch.setattr(module, "submit_ibm_job", _fake_submit_ibm_job)

    with pytest.raises(WorkspaceRecoveryRequiredError):
        module.submit_remote_input(
            workspace_root=handle.root,
            backend_name="ibm_brisbane",
            intent_text="Generate a 4-qubit GHZ circuit and measure all qubits.",
        )

    assert submit_called is False


def test_submit_ibm_job_uses_explicit_backend_lookup_and_sampler_job_mode(monkeypatch) -> None:
    module = _load_ibm_remote_submit_module()
    qspec = _ghz_qspec()
    captured: dict[str, object] = {}

    class _FakeBackend:
        name = "ibm_brisbane"

        def run(self, *args, **kwargs):
            raise AssertionError("backend.run should not be used for remote submit")

    class _FakeJob:
        def job_id(self) -> str:
            return "job-123"

        def status(self) -> str:
            return "QUEUED"

    class _FakeSampler:
        def __init__(self, *, mode, options=None) -> None:
            captured["mode"] = mode
            captured["options"] = options

        def run(self, pubs, *, shots=None):
            captured["pubs"] = pubs
            captured["shots"] = shots
            return _FakeJob()

    class _FakeService:
        def backend(self, backend_name: str) -> _FakeBackend:
            captured["backend_lookup"] = backend_name
            return _FakeBackend()

        def least_busy(self):
            raise AssertionError("least_busy should not be used for remote submit")

    monkeypatch.setattr(module, "SamplerV2", _FakeSampler)
    monkeypatch.setattr(module, "transpile", lambda circuit, backend: "transpiled-circuit")

    result = module.submit_ibm_job(
        service=_FakeService(),
        backend_name="ibm_brisbane",
        qspec=qspec,
        shots=512,
    )

    assert captured["backend_lookup"] == "ibm_brisbane"
    assert isinstance(captured["mode"], _FakeBackend)
    assert captured["pubs"] == ["transpiled-circuit"]
    assert captured["shots"] == 512
    assert result.job_id == "job-123"
    assert result.job_status == "QUEUED"


def test_backend_registry_reports_ibm_remote_submit_capability() -> None:
    from quantum_runtime.runtime.backend_registry import collect_backend_capabilities

    capabilities = collect_backend_capabilities()

    assert capabilities["ibm-runtime"].capabilities["remote_submit"] is True


def _patch_real_remote_submit(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_remote_submit_module()

    def _fake_submit_ibm_job(*, service, backend_name: str, qspec: QSpec, shots: int):
        return {
            "job_id": "job-123",
            "job_status": "QUEUED",
            "primitive": "sampler_v2",
        }

    monkeypatch.setattr(module, "resolve_ibm_access", lambda *, workspace_root: _fake_ibm_resolution())
    monkeypatch.setattr(module, "build_ibm_service", lambda *, resolution: object())
    monkeypatch.setattr(module, "submit_ibm_job", _fake_submit_ibm_job)


def _assert_remote_submit_payload(payload: dict[str, object]) -> None:
    assert payload["status"] == "ok"
    assert str(payload["attempt_id"]).startswith("attempt_")
    assert payload["job"]["id"] == "job-123"
    assert payload["job"]["status"] == "QUEUED"
    assert payload["backend"]["name"] == "ibm_brisbane"
    assert payload["backend"]["instance"] == "crn:v1:bluemix:public:quantum-computing:us-east:a/test::"


def test_qrun_remote_submit_json_requires_exactly_one_input_source(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    result = RUNNER.invoke(
        app,
        [
            "remote",
            "submit",
            "--workspace",
            str(workspace),
            "--backend",
            "ibm_brisbane",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["reason"] == "expected_exactly_one_input"


def test_qrun_remote_submit_json_accepts_intent_text_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / ".quantum"
    _patch_real_remote_submit(monkeypatch)

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
    _assert_remote_submit_payload(json.loads(result.stdout))


def test_qrun_remote_submit_json_accepts_report_file_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_workspace, report_path, _ = _report_sources(tmp_path)
    target_workspace = tmp_path / ".quantum-target"
    assert source_workspace.exists()
    _patch_real_remote_submit(monkeypatch)

    result = RUNNER.invoke(
        app,
        [
            "remote",
            "submit",
            "--workspace",
            str(target_workspace),
            "--backend",
            "ibm_brisbane",
            "--report-file",
            str(report_path),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    _assert_remote_submit_payload(json.loads(result.stdout))


def test_qrun_remote_submit_json_accepts_revision_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, _, revision = _report_sources(tmp_path)
    _patch_real_remote_submit(monkeypatch)

    result = RUNNER.invoke(
        app,
        [
            "remote",
            "submit",
            "--workspace",
            str(workspace),
            "--backend",
            "ibm_brisbane",
            "--revision",
            revision,
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    _assert_remote_submit_payload(json.loads(result.stdout))


def test_qrun_remote_submit_json_rejects_blank_backend_name(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    result = RUNNER.invoke(
        app,
        [
            "remote",
            "submit",
            "--workspace",
            str(workspace),
            "--backend",
            "   ",
            "--intent-text",
            "Generate a 4-qubit GHZ circuit and measure all qubits.",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["reason"] == "remote_backend_required"


def test_qrun_remote_submit_preserves_latest_report_and_manifest_aliases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / ".quantum"
    _patch_real_remote_submit(monkeypatch)

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

    report_latest = workspace / "reports" / "latest.json"
    manifest_latest = workspace / "manifests" / "latest.json"
    assert str(report_latest).endswith("reports/latest.json")
    assert str(manifest_latest).endswith("manifests/latest.json")
    report_before = report_latest.read_text(encoding="utf-8")
    manifest_before = manifest_latest.read_text(encoding="utf-8")

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
    assert report_latest.read_text(encoding="utf-8") == report_before
    assert manifest_latest.read_text(encoding="utf-8") == manifest_before


@pytest.mark.parametrize(
    "error_factory",
    [
        lambda workspace: WorkspaceConflictError(
            workspace=workspace,
            lock_path=workspace / ".lease",
            holder={"hostname": "builder", "pid": 99, "operation": "qrun exec"},
        ),
        lambda workspace: WorkspaceRecoveryRequiredError(
            workspace=workspace,
            pending_files=[workspace / "reports" / ".latest.json.tmp-stale"],
            last_valid_revision="rev_000001",
        ),
    ],
)
def test_qrun_remote_submit_json_uses_workspace_safety_helpers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error_factory,
) -> None:
    workspace = tmp_path / ".quantum"

    def _raise_error(**kwargs):
        raise error_factory(workspace)

    monkeypatch.setattr("quantum_runtime.cli.submit_remote_input", _raise_error)

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

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["reason"] in {"workspace_conflict", "workspace_recovery_required"}
