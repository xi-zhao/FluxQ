from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.cli import app
from quantum_runtime.runtime.executor import ExecResult
from quantum_runtime.intent.parser import parse_intent_file
from quantum_runtime.intent.planner import plan_to_qspec


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()


def test_qrun_exec_json_generates_workspace_artifacts_and_report(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    result = RUNNER.invoke(
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

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    revision = payload["revision"]
    assert revision.startswith("rev_")
    assert Path(payload["artifacts"]["qspec"]).exists()
    assert Path(payload["artifacts"]["qiskit_code"]).exists()
    assert Path(payload["artifacts"]["qasm3"]).exists()
    assert Path(payload["artifacts"]["diagram_png"]).exists()
    assert Path(payload["artifacts"]["report"]).exists()
    assert payload["artifacts"]["qspec"].endswith(f"specs/history/{revision}.json")
    assert payload["artifacts"]["qiskit_code"].endswith(f"artifacts/history/{revision}/qiskit/main.py")
    assert payload["artifacts"]["qasm3"].endswith(f"artifacts/history/{revision}/qasm/main.qasm")
    assert payload["artifacts"]["diagram_txt"].endswith(f"artifacts/history/{revision}/figures/circuit.txt")
    assert payload["artifacts"]["diagram_png"].endswith(f"artifacts/history/{revision}/figures/circuit.png")
    assert payload["artifacts"]["report"].endswith(f"reports/history/{revision}.json")
    assert payload["diagnostics"]["simulation"]["status"] == "ok"
    assert payload["diagnostics"]["transpile"]["status"] == "ok"

    report = json.loads((workspace / "reports" / "latest.json").read_text())
    assert report["status"] == "ok"
    assert report["artifacts"]["qiskit_code"].endswith(f"artifacts/history/{revision}/qiskit/main.py")
    assert report["diagnostics"]["resources"]["two_qubit_gates"] == 3

    trace_lines = (workspace / "trace" / "events.ndjson").read_text().strip().splitlines()
    assert any('"event_type": "exec_completed"' in line for line in trace_lines)


def test_qrun_exec_json_accepts_qspec_file_input(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    qspec_path = tmp_path / "ghz-qspec.json"
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    qspec_path.write_text(qspec.model_dump_json(indent=2))

    result = RUNNER.invoke(
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

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert Path(payload["artifacts"]["qspec"]).exists()
    assert Path(payload["artifacts"]["qiskit_code"]).exists()
    assert payload["diagnostics"]["resources"]["two_qubit_gates"] == 3


def test_qrun_exec_json_accepts_report_file_input(tmp_path: Path) -> None:
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

    report_path = source_workspace / "reports" / "latest.json"
    result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(target_workspace),
            "--report-file",
            str(report_path),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert Path(payload["artifacts"]["qspec"]).exists()
    assert Path(payload["artifacts"]["qiskit_code"]).exists()
    assert payload["diagnostics"]["simulation"]["status"] == "ok"


def test_qrun_exec_history_report_pins_revision_qspec_after_later_runs(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    first_result = RUNNER.invoke(
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
    assert first_result.exit_code == 0, first_result.stdout

    second_result = RUNNER.invoke(
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
    assert second_result.exit_code == 0, second_result.stdout

    report = json.loads((workspace / "reports" / "history" / "rev_000001.json").read_text())
    assert report["qspec"]["path"].endswith("specs/history/rev_000001.json")
    assert report["provenance"]["qspec"]["path"].endswith("specs/history/rev_000001.json")


def test_qrun_exec_json_accepts_history_revision_input(tmp_path: Path) -> None:
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
            "exec",
            "--workspace",
            str(workspace),
            "--revision",
            "rev_000001",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert Path(payload["artifacts"]["qspec"]).exists()
    assert Path(payload["artifacts"]["qasm3"]).exists()


def test_qrun_exec_json_accepts_relative_report_qspec_path(tmp_path: Path) -> None:
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

    report_path = source_workspace / "reports" / "latest.json"
    payload = json.loads(report_path.read_text())
    payload["qspec"]["path"] = "specs/current.json"
    report_path.write_text(json.dumps(payload, indent=2))

    result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(target_workspace),
            "--report-file",
            str(report_path),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    exec_payload = json.loads(result.stdout)
    assert exec_payload["status"] == "ok"
    assert Path(exec_payload["artifacts"]["qasm3"]).exists()


def test_qrun_exec_json_returns_exit_code_3_for_invalid_report_input(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    report_path = tmp_path / "broken-report.json"
    report_path.write_text(json.dumps({"status": "ok", "qspec": {}}, indent=2))

    result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--report-file",
            str(report_path),
            "--json",
        ],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["reason"] == "report_qspec_path_missing"


def test_qrun_exec_json_returns_exit_code_3_for_missing_history_revision(
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
            "exec",
            "--workspace",
            str(workspace),
            "--revision",
            "rev_999999",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["reason"] == "report_revision_missing"


def test_qrun_exec_json_requires_exactly_one_input_source(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--json",
        ],
    )

    assert result.exit_code == 3
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["reason"] == "expected_exactly_one_input"


def test_qrun_exec_json_accepts_intent_text_input(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-text",
            "Generate a 4-qubit GHZ circuit and measure all qubits.",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert Path(payload["artifacts"]["qspec"]).exists()
    assert Path(payload["artifacts"]["qiskit_code"]).exists()
    assert payload["diagnostics"]["simulation"]["status"] == "ok"


def test_qrun_exec_json_returns_exit_code_2_for_degraded_result(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / ".quantum"

    monkeypatch.setattr(
        "quantum_runtime.cli.execute_intent_text",
        lambda workspace_root, intent_text: ExecResult(
            status="degraded",
            workspace=str(workspace_root),
            revision="rev_000001",
            summary="degraded execution",
            warnings=["classiq dependency missing"],
            errors=[],
            artifacts={},
            diagnostics={
                "simulation": {"status": "ok"},
                "transpile": {"status": "ok"},
            },
            backend_reports={},
            next_actions=[],
        ),
    )

    result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-text",
            "Generate a 4-qubit GHZ circuit and measure all qubits.",
            "--json",
        ],
    )

    assert result.exit_code == 2, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "degraded"
    assert payload["warnings"] == ["classiq dependency missing"]


def test_qrun_exec_json_returns_exit_code_6_for_simulation_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / ".quantum"
    qspec_path = tmp_path / "ghz-qspec.json"
    intent = parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md")
    qspec = plan_to_qspec(intent)
    qspec_path.write_text(qspec.model_dump_json(indent=2))

    monkeypatch.setattr(
        "quantum_runtime.cli.execute_qspec",
        lambda workspace_root, qspec_file: ExecResult(
            status="error",
            workspace=str(workspace_root),
            revision="rev_000002",
            summary="simulation failed",
            warnings=[],
            errors=[],
            artifacts={},
            diagnostics={
                "simulation": {"status": "error", "error": "Aer unavailable"},
                "transpile": {"status": "ok"},
            },
            backend_reports={},
            next_actions=[],
        ),
    )

    result = RUNNER.invoke(
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

    assert result.exit_code == 6, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["diagnostics"]["simulation"]["status"] == "error"


def test_qrun_exec_json_returns_exit_code_7_for_dependency_missing_backend(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / ".quantum"

    monkeypatch.setattr(
        "quantum_runtime.cli.execute_intent_text",
        lambda workspace_root, intent_text: ExecResult(
            status="degraded",
            workspace=str(workspace_root),
            revision="rev_000003",
            summary="classiq dependency missing",
            warnings=["classiq dependency missing"],
            errors=[],
            artifacts={},
            diagnostics={
                "simulation": {"status": "ok"},
                "transpile": {"status": "ok"},
            },
            backend_reports={
                "classiq": {
                    "status": "dependency_missing",
                    "reason": "classiq_not_installed",
                }
            },
            next_actions=[],
        ),
    )

    result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--intent-text",
            "Generate a 4-qubit GHZ circuit and measure all qubits.",
            "--json",
        ],
    )

    assert result.exit_code == 7, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "degraded"
    assert payload["backend_reports"]["classiq"]["status"] == "dependency_missing"
