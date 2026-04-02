from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.backends.classiq_backend import ClassiqBackendReport
from quantum_runtime.cli import app
from quantum_runtime.intent.parser import parse_intent_file
from quantum_runtime.intent.planner import plan_to_qspec
from quantum_runtime.workspace import WorkspaceManager


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()


def test_qrun_inspect_json_summarizes_current_workspace_state(tmp_path: Path) -> None:
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

    inspect_result = RUNNER.invoke(
        app,
        ["inspect", "--workspace", str(workspace), "--json"],
    )

    assert inspect_result.exit_code == 0, inspect_result.stdout
    payload = json.loads(inspect_result.stdout)
    assert payload["revision"].startswith("rev_")
    assert payload["qspec"]["goal"].lower().startswith("generate a 4-qubit ghz")
    assert payload["qspec"]["pattern"] == "ghz"
    assert payload["qspec"]["parameter_count"] == 0
    assert payload["qspec"]["registers"]["qubits"] == 4
    assert payload["provenance"]["workspace_root"] == str(workspace)
    assert payload["provenance"]["input"]["mode"] == "intent"
    assert payload["provenance"]["input"]["path"].endswith("examples/intent-ghz.md")
    assert payload["provenance"]["subject"]["pattern"] == "ghz"
    assert payload["artifacts"]["qiskit_code"].endswith(
        f"artifacts/history/{payload['revision']}/qiskit/main.py"
    )
    assert payload["provenance"]["artifacts"]["snapshot_root"].endswith(
        f"artifacts/history/{payload['revision']}"
    )
    assert payload["provenance"]["artifacts"]["paths"]["qiskit_code"] == payload["artifacts"]["qiskit_code"]
    assert payload["provenance"]["artifacts"]["paths"]["qspec"].endswith(
        f"specs/history/{payload['revision']}.json"
    )
    assert payload["provenance"]["artifacts"]["paths"]["report"].endswith(
        f"reports/history/{payload['revision']}.json"
    )
    assert payload["provenance"]["artifacts"]["current_aliases"]["qiskit_code"].endswith(
        "artifacts/qiskit/main.py"
    )
    assert payload["provenance"]["artifacts"]["current_aliases"]["qspec"].endswith("specs/current.json")
    assert payload["provenance"]["artifacts"]["current_aliases"]["report"].endswith("reports/latest.json")
    assert payload["diagnostics"]["simulation"]["status"] == "ok"
    assert "qiskit" in payload["backend_capabilities"]


def test_qrun_inspect_json_surfaces_parameterized_ansatz_semantics(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    exec_result = RUNNER.invoke(
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
    assert exec_result.exit_code == 0, exec_result.stdout

    inspect_result = RUNNER.invoke(
        app,
        ["inspect", "--workspace", str(workspace), "--json"],
    )

    assert inspect_result.exit_code == 0, inspect_result.stdout
    payload = json.loads(inspect_result.stdout)
    assert payload["qspec"]["pattern"] == "qaoa_ansatz"
    assert payload["qspec"]["layers"] == 2
    assert payload["qspec"]["parameter_count"] == 4
    assert payload["qspec"]["pattern_args"]["cost_edges"] == [[0, 1], [1, 2], [2, 3], [3, 0]]
    assert payload["provenance"]["subject"]["pattern"] == "qaoa_ansatz"
    assert payload["provenance"]["subject"]["layers"] == 2
    assert payload["provenance"]["subject"]["parameter_count"] == 4


def test_qrun_inspect_json_reports_classiq_artifact_snapshot_aliases(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / ".quantum"
    qspec = plan_to_qspec(parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md"))
    qspec.backend_preferences = ["classiq"]
    qspec_path = tmp_path / "classiq-qspec.json"
    qspec_path.write_text(qspec.model_dump_json(indent=2))

    def fake_run_classiq_backend(qspec, workspace_handle):
        code_path = workspace_handle.root / "artifacts" / "classiq" / "main.py"
        results_path = workspace_handle.root / "artifacts" / "classiq" / "synthesis.json"
        code_path.parent.mkdir(parents=True, exist_ok=True)
        code_path.write_text("# classiq program\n")
        results_path.write_text("{\"depth\": 5}")
        return ClassiqBackendReport(
            status="ok",
            code_path=code_path,
            results_path=results_path,
            synthesis_metrics={"depth": 5},
        )

    monkeypatch.setattr("quantum_runtime.runtime.executor.run_classiq_backend", fake_run_classiq_backend)

    exec_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--qspec-file",
            str(qspec_path),
            "--json",
        ],
    )
    assert exec_result.exit_code == 0, exec_result.stdout

    inspect_result = RUNNER.invoke(
        app,
        ["inspect", "--workspace", str(workspace), "--json"],
    )

    assert inspect_result.exit_code == 0, inspect_result.stdout
    payload = json.loads(inspect_result.stdout)
    assert payload["artifacts"]["classiq_code"].endswith(
        f"artifacts/history/{payload['revision']}/classiq/main.py"
    )
    assert payload["artifacts"]["classiq_results"].endswith(
        f"artifacts/history/{payload['revision']}/classiq/synthesis.json"
    )
    assert payload["provenance"]["artifacts"]["current_aliases"]["classiq_code"].endswith(
        "artifacts/classiq/main.py"
    )
    assert payload["provenance"]["artifacts"]["current_aliases"]["classiq_results"].endswith(
        "artifacts/classiq/synthesis.json"
    )


def test_qrun_inspect_json_returns_exit_code_2_for_missing_manifest(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    handle = WorkspaceManager.load_or_init(workspace)
    handle.paths.workspace_json.unlink()

    inspect_result = RUNNER.invoke(
        app,
        ["inspect", "--workspace", str(workspace), "--json"],
    )

    assert inspect_result.exit_code == 2, inspect_result.stdout
    payload = json.loads(inspect_result.stdout)
    assert payload["status"] == "degraded"
    assert "workspace_manifest_missing" in payload["issues"]
    assert payload["qspec"]["status"] == "missing"
    assert payload["workspace"]["current_revision"] == "unknown"
    assert payload["provenance"]["workspace_root"] == str(workspace)
    assert payload["provenance"]["input"]["mode"] == "report"
    assert payload["provenance"]["report"]["path"].endswith("reports/latest.json")


def test_qrun_inspect_json_returns_exit_code_3_for_invalid_qspec_json(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    handle = WorkspaceManager.load_or_init(workspace)
    (handle.root / "specs" / "current.json").write_text("{not valid json")
    (handle.root / "reports" / "latest.json").write_text(
        "{\"artifacts\": {}, \"diagnostics\": {}}"
    )

    inspect_result = RUNNER.invoke(
        app,
        ["inspect", "--workspace", str(workspace), "--json"],
    )

    assert inspect_result.exit_code == 3, inspect_result.stdout
    payload = json.loads(inspect_result.stdout)
    assert payload["status"] == "error"
    assert "active_spec_invalid_json" in payload["errors"]
    assert payload["workspace"]["current_revision"] != ""
    assert payload["provenance"]["workspace_root"] == str(workspace)
    assert payload["provenance"]["input"]["mode"] == "report"
