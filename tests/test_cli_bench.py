from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.cli import app
from quantum_runtime.intent.parser import parse_intent_file
from quantum_runtime.intent.planner import plan_to_qspec
from quantum_runtime.workspace import WorkspaceManager, acquire_workspace_lock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()


def _binding_only_qaoa_qspec():
    qspec = plan_to_qspec(parse_intent_file(PROJECT_ROOT / "examples" / "intent-qaoa-maxcut.md"))
    qspec.metadata["parameter_workflow"] = {
        "mode": "binding",
        "bindings": {
            "gamma_0": 0.2,
            "beta_0": 0.1,
            "gamma_1": 0.45,
            "beta_1": 0.35,
        },
    }
    for parameter in qspec.parameters:
        parameter.pop("default", None)
    return qspec


def test_qrun_bench_json_reads_current_qspec_and_emits_structural_report(
    tmp_path: Path,
) -> None:
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    current_qspec = handle.root / "specs" / "current.json"
    current_qspec.write_text(qspec.model_dump_json(indent=2))

    result = RUNNER.invoke(
        app,
        [
            "bench",
            "--workspace",
            str(handle.root),
            "--backends",
            "qiskit-local",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["schema_version"] == "0.3.0"
    assert payload["backends"]["qiskit-local"]["depth"] == 5
    history_path = handle.root / "benchmarks" / "history" / "rev_000000.json"
    latest_path = handle.root / "benchmarks" / "latest.json"
    assert latest_path.exists()
    assert not history_path.exists()
    assert json.loads(latest_path.read_text())["schema_version"] == "0.3.0"


def test_qrun_bench_json_accepts_report_file_input(
    tmp_path: Path,
) -> None:
    source_workspace = tmp_path / ".quantum-source"
    target_workspace = tmp_path / ".quantum-target"

    initial_result = RUNNER.invoke(
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
    assert initial_result.exit_code == 0, initial_result.stdout

    result = RUNNER.invoke(
        app,
        [
            "bench",
            "--workspace",
            str(target_workspace),
            "--report-file",
            str(source_workspace / "reports" / "latest.json"),
            "--backends",
            "qiskit-local",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["schema_version"] == "0.3.0"
    assert payload["backends"]["qiskit-local"]["two_qubit_gates"] == 3
    latest_path = target_workspace / "benchmarks" / "latest.json"
    assert latest_path.exists()
    assert not (target_workspace / "benchmarks" / "history").exists()


def test_qrun_bench_json_returns_exit_code_3_for_tampered_report_qspec_fallback(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / ".quantum"

    initial_result = RUNNER.invoke(
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
    assert initial_result.exit_code == 0, initial_result.stdout

    current_qspec = workspace / "specs" / "current.json"
    history_qspec = workspace / "specs" / "history" / "rev_000001.json"
    mutated_qspec = plan_to_qspec(parse_intent_file(PROJECT_ROOT / "examples" / "intent-qaoa-maxcut.md"))
    current_qspec.write_text(mutated_qspec.model_dump_json(indent=2))
    history_qspec.unlink()

    result = RUNNER.invoke(
        app,
        [
            "bench",
            "--workspace",
            str(workspace),
            "--report-file",
            str(workspace / "reports" / "latest.json"),
            "--json",
        ],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["reason"] == "report_qspec_hash_mismatch"


def test_qrun_bench_json_accepts_history_revision_input(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / ".quantum"

    initial_result = RUNNER.invoke(
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
    assert initial_result.exit_code == 0, initial_result.stdout

    result = RUNNER.invoke(
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

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["backends"]["qiskit-local"]["depth"] == 5
    assert (workspace / "benchmarks" / "history" / "rev_000001.json").exists()


def test_qrun_bench_json_returns_exit_code_7_when_classiq_is_missing(tmp_path: Path) -> None:
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    qspec.backend_preferences.append("classiq")
    current_qspec = handle.root / "specs" / "current.json"
    current_qspec.write_text(qspec.model_dump_json(indent=2))

    result = RUNNER.invoke(
        app,
        [
            "bench",
            "--workspace",
            str(handle.root),
            "--backends",
            "qiskit-local,classiq",
            "--json",
        ],
    )

    assert result.exit_code == 7, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "degraded"
    assert payload["backends"]["qiskit-local"]["details"]["benchmark_mode"] == "structural_only"
    assert payload["backends"]["qiskit-local"]["details"]["comparable"] is False
    assert payload["backends"]["classiq"]["status"] == "dependency_missing"
    assert payload["backends"]["classiq"]["details"]["benchmark_mode"] == "unavailable"
    assert payload["backends"]["classiq"]["details"]["comparable"] is False
    assert payload["backends"]["classiq"]["details"]["fallback_reason"] == "classiq_not_installed"
    assert payload["subject"]["pattern"] == "ghz"
    assert payload["subject"]["parameter_count"] == 0


def test_qrun_bench_json_returns_exit_code_4_for_unknown_backend(
    tmp_path: Path,
) -> None:
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    current_qspec = handle.root / "specs" / "current.json"
    current_qspec.write_text(qspec.model_dump_json(indent=2))

    result = RUNNER.invoke(
        app,
        [
            "bench",
            "--workspace",
            str(handle.root),
            "--backends",
            "qiskit-local,unknown-backend",
            "--json",
        ],
    )

    assert result.exit_code == 4, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "degraded"
    assert payload["backends"]["unknown-backend"]["status"] == "backend_unavailable"


def test_qrun_bench_json_returns_exit_code_3_when_qspec_is_missing(tmp_path: Path) -> None:
    result = RUNNER.invoke(
        app,
        [
            "bench",
            "--workspace",
            str(tmp_path / ".quantum"),
            "--json",
        ],
    )

    assert result.exit_code == 3
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["reason"] == "missing_qspec"


def test_qrun_bench_json_returns_exit_code_3_for_invalid_report_input(tmp_path: Path) -> None:
    report_path = tmp_path / "broken-report.json"
    report_path.write_text(json.dumps({"status": "ok", "qspec": {}}, indent=2))

    result = RUNNER.invoke(
        app,
        [
            "bench",
            "--workspace",
            str(tmp_path / ".quantum"),
            "--report-file",
            str(report_path),
            "--json",
        ],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["reason"] == "report_qspec_path_missing"


def test_qrun_bench_json_defaults_to_qiskit_local_for_qiskit_only_workspace(tmp_path: Path) -> None:
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
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert set(payload["backends"]) == {"qiskit-local"}
    assert payload["schema_version"] == "0.3.0"
    assert (workspace / "benchmarks" / "latest.json").exists()


def test_qrun_bench_json_accepts_binding_only_parameter_workflow_qspec(tmp_path: Path) -> None:
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")
    qspec = _binding_only_qaoa_qspec()
    (handle.root / "specs" / "current.json").write_text(qspec.model_dump_json(indent=2))

    result = RUNNER.invoke(
        app,
        [
            "bench",
            "--workspace",
            str(handle.root),
            "--backends",
            "qiskit-local",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["schema_version"] == "0.3.0"
    assert payload["backends"]["qiskit-local"]["depth"] > 0
    assert payload["backends"]["qiskit-local"]["two_qubit_gates"] == 16
    assert not (handle.root / "benchmarks" / "history").exists()


def test_qrun_bench_json_defaults_include_requested_classiq_backend(tmp_path: Path) -> None:
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    qspec.backend_preferences.append("classiq")
    (handle.root / "specs" / "current.json").write_text(qspec.model_dump_json(indent=2))

    result = RUNNER.invoke(
        app,
        [
            "bench",
            "--workspace",
            str(handle.root),
            "--json",
        ],
    )

    assert result.exit_code == 7, result.stdout
    payload = json.loads(result.stdout)
    assert payload["backends"]["qiskit-local"]["status"] == "ok"
    assert payload["backends"]["classiq"]["status"] == "dependency_missing"
    assert payload["schema_version"] == "0.3.0"


def test_qrun_bench_json_reports_workspace_conflict_when_benchmark_persistence_is_locked(tmp_path: Path) -> None:
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

    with acquire_workspace_lock(workspace, command="pytest bench lock holder"):
        result = RUNNER.invoke(
            app,
            [
                "bench",
                "--workspace",
                str(workspace),
                "--json",
            ],
        )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["reason"] == "workspace_conflict"


def test_qrun_bench_json_reports_workspace_recovery_required_for_pending_benchmark_temp(tmp_path: Path) -> None:
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

    pending = workspace / "benchmarks" / "latest.json.tmp"
    pending.parent.mkdir(parents=True, exist_ok=True)
    pending.write_text("pending")

    result = RUNNER.invoke(
        app,
        [
            "bench",
            "--workspace",
            str(workspace),
            "--json",
        ],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["reason"] == "workspace_recovery_required"
    assert str(pending) in payload["details"]["pending_files"]
