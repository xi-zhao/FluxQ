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


def _exec_intent(*, workspace: Path, intent_name: str) -> dict[str, object]:
    result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / intent_name),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.stdout
    return json.loads(result.stdout)


def _bench(*, workspace: Path, args: list[str]) -> tuple[object, dict[str, object]]:
    result = RUNNER.invoke(
        app,
        [
            "bench",
            "--workspace",
            str(workspace),
            *args,
        ],
    )
    payload = json.loads(result.stdout)
    return result, payload


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
    assert payload["source_kind"] == "report_file"
    assert payload["source_revision"] == "rev_000001"
    latest_path = target_workspace / "benchmarks" / "latest.json"
    history_path = target_workspace / "benchmarks" / "history" / "rev_000001.json"
    assert latest_path.exists()
    assert history_path.exists()
    latest_payload = json.loads(latest_path.read_text())
    persisted_payload = json.loads(history_path.read_text())
    assert latest_payload["source_kind"] == "report_file"
    assert latest_payload["source_revision"] == "rev_000001"
    assert persisted_payload["source_kind"] == "report_file"
    assert persisted_payload["source_revision"] == "rev_000001"


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


def test_qrun_bench_json_persists_imported_revision_history_using_source_revision(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / ".quantum"

    _exec_intent(workspace=workspace, intent_name="intent-ghz.md")
    _exec_intent(workspace=workspace, intent_name="intent-qaoa-maxcut.md")

    result, payload = _bench(
        workspace=workspace,
        args=[
            "--revision",
            "rev_000001",
            "--backends",
            "qiskit-local",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert payload["status"] == "ok"
    assert payload["source_kind"] == "report_revision"
    assert payload["source_revision"] == "rev_000001"
    history_path = workspace / "benchmarks" / "history" / "rev_000001.json"
    wrong_history_path = workspace / "benchmarks" / "history" / "rev_000002.json"
    latest_path = workspace / "benchmarks" / "latest.json"
    assert history_path.exists()
    assert not wrong_history_path.exists()
    latest_payload = json.loads(latest_path.read_text())
    persisted_payload = json.loads(history_path.read_text())
    assert latest_payload["source_kind"] == "report_revision"
    assert latest_payload["source_revision"] == "rev_000001"
    assert persisted_payload["source_kind"] == "report_revision"
    assert persisted_payload["source_revision"] == "rev_000001"


def test_qrun_bench_json_returns_baseline_benchmark_missing_when_saved_evidence_is_absent(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / ".quantum"

    _exec_intent(workspace=workspace, intent_name="intent-ghz.md")

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

    _exec_intent(workspace=workspace, intent_name="intent-ghz.md")

    result, payload = _bench(
        workspace=workspace,
        args=[
            "--baseline",
            "--max-depth-regression",
            "0",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.stdout
    assert payload["status"] == "error"
    assert payload["reason"] == "baseline_benchmark_missing"
    assert payload["error_code"] == "baseline_benchmark_missing"


def test_qrun_bench_json_baseline_policy_fails_when_metrics_regress_from_saved_baseline(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / ".quantum"

    _exec_intent(workspace=workspace, intent_name="intent-ghz.md")

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

    baseline_bench_result, baseline_bench_payload = _bench(
        workspace=workspace,
        args=[
            "--revision",
            "rev_000001",
            "--backends",
            "qiskit-local",
            "--json",
        ],
    )
    assert baseline_bench_result.exit_code == 0, baseline_bench_result.stdout
    baseline_history_path = workspace / "benchmarks" / "history" / "rev_000001.json"
    persisted_baseline = json.loads(baseline_history_path.read_text())
    persisted_baseline["backends"]["qiskit-local"]["depth"] = baseline_bench_payload["backends"]["qiskit-local"]["depth"] - 1
    persisted_baseline["backends"]["qiskit-local"]["two_qubit_gates"] = (
        baseline_bench_payload["backends"]["qiskit-local"]["two_qubit_gates"] - 1
    )
    baseline_history_path.write_text(json.dumps(persisted_baseline, indent=2))

    _exec_intent(workspace=workspace, intent_name="intent-ghz.md")

    result, payload = _bench(
        workspace=workspace,
        args=[
            "--baseline",
            "--max-depth-regression",
            "0",
            "--max-two-qubit-regression",
            "0",
            "--json",
        ],
    )

    assert result.exit_code == 2, result.stdout
    assert payload["status"] == "ok"
    assert payload["baseline"]["revision"] == "rev_000001"
    assert payload["verdict"]["status"] == "fail"
    assert payload["gate"]["ready"] is False
    assert payload["policy"]["max_depth_regression"] == 0
    assert payload["policy"]["max_two_qubit_regression"] == 0
    assert "benchmark_metric_regressed:qiskit-local:depth" in payload["reason_codes"]
    assert "benchmark_metric_regressed:qiskit-local:two_qubit_gates" in payload["reason_codes"]


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
