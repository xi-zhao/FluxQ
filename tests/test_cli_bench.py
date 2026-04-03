from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.diagnostics.benchmark import BackendBenchmark, BenchmarkReport
from quantum_runtime.cli import app
from quantum_runtime.intent.parser import parse_intent_file
from quantum_runtime.intent.planner import plan_to_qspec
from quantum_runtime.workspace import WorkspaceManager


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()


def test_qrun_bench_json_reads_current_qspec_and_emits_structural_report(
    tmp_path: Path,
    monkeypatch,
) -> None:
    handle = WorkspaceManager.load_or_init(tmp_path / ".quantum")
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    qspec.backend_preferences.append("classiq")
    current_qspec = handle.root / "specs" / "current.json"
    current_qspec.write_text(qspec.model_dump_json(indent=2))

    monkeypatch.setattr(
        "quantum_runtime.cli.run_structural_benchmark",
        lambda qspec, workspace, backends: BenchmarkReport(
            status="degraded",
            backends={
                "qiskit-local": BackendBenchmark(
                    backend="qiskit-local",
                    status="ok",
                    width=4,
                    depth=5,
                    transpiled_depth=5,
                    two_qubit_gates=3,
                    transpiled_two_qubit_gates=3,
                    measure_count=4,
                )
            },
        ),
    )

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

    assert result.exit_code == 2, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "degraded"
    assert payload["backends"]["qiskit-local"]["depth"] == 5


def test_qrun_bench_json_accepts_report_file_input(
    tmp_path: Path,
    monkeypatch,
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

    monkeypatch.setattr(
        "quantum_runtime.cli.run_structural_benchmark",
        lambda qspec, workspace, backends: BenchmarkReport(
            status="ok",
            backends={
                "qiskit-local": BackendBenchmark(
                    backend="qiskit-local",
                    status="ok",
                    width=4,
                    depth=5,
                    transpiled_depth=5,
                    two_qubit_gates=3,
                    transpiled_two_qubit_gates=3,
                    measure_count=4,
                )
            },
        ),
    )

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
    assert payload["backends"]["qiskit-local"]["two_qubit_gates"] == 3


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
    monkeypatch,
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

    monkeypatch.setattr(
        "quantum_runtime.cli.run_structural_benchmark",
        lambda qspec, workspace, backends: BenchmarkReport(
            status="ok",
            backends={
                "qiskit-local": BackendBenchmark(
                    backend="qiskit-local",
                    status="ok",
                    width=4,
                    depth=5,
                    transpiled_depth=5,
                    two_qubit_gates=3,
                    transpiled_two_qubit_gates=3,
                    measure_count=4,
                )
            },
        ),
    )

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
    assert payload["backends"]["classiq"]["status"] == "dependency_missing"
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
