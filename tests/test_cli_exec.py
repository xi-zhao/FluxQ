from __future__ import annotations

import hashlib
import json
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.cli import app
from quantum_runtime.intent.parser import parse_intent_file
from quantum_runtime.intent.planner import plan_to_qspec
from quantum_runtime.qspec import QSpec, summarize_qspec_semantics
from quantum_runtime.runtime.executor import ExecResult


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()


def _fmt(value: float) -> str:
    rendered = f"{value:.6f}".rstrip("0").rstrip(".")
    return rendered or "0"


def _write_intent(path: Path, *, title: str, goal: str) -> Path:
    path.write_text(
        f"""---
title: {title}
---

{goal}
"""
    )
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _assert_report_matches_qspec(*, report_path: Path, qspec_path: Path) -> dict[str, object]:
    report = json.loads(report_path.read_text())
    qspec = QSpec.model_validate_json(qspec_path.read_text())
    semantics = summarize_qspec_semantics(qspec)

    assert report["qspec"]["path"] == str(qspec_path.resolve())
    assert report["qspec"]["hash"] == _sha256(qspec_path)
    assert report["qspec"]["semantic_hash"] == semantics["semantic_hash"]
    assert report["provenance"]["qspec"]["path"] == str(qspec_path.resolve())
    assert report["provenance"]["qspec"]["hash"] == _sha256(qspec_path)
    assert report["provenance"]["qspec"]["semantic_hash"] == semantics["semantic_hash"]
    return report


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
    assert report["qspec"]["path"].endswith(f"specs/history/{revision}.json")
    assert report["artifacts"]["qiskit_code"].endswith(f"artifacts/history/{revision}/qiskit/main.py")
    assert report["diagnostics"]["diagram"]["text_path"].endswith(
        f"artifacts/history/{revision}/figures/circuit.txt"
    )
    assert report["diagnostics"]["diagram"]["png_path"].endswith(
        f"artifacts/history/{revision}/figures/circuit.png"
    )
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


def test_qrun_exec_json_persists_parameterized_expectation_diagnostics(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    qspec_path = tmp_path / "qaoa-sweep-qspec.json"
    qspec = plan_to_qspec(parse_intent_file(PROJECT_ROOT / "examples" / "intent-qaoa-maxcut.md"))
    qspec.metadata["parameter_workflow"] = {
        "mode": "sweep",
        "grid": {
            "gamma_0": [0.2, 0.4],
            "beta_0": [0.1, 0.3],
            "gamma_1": [0.45],
            "beta_1": [0.35],
        },
    }
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
    assert payload["diagnostics"]["simulation"]["parameter_mode"] == "sweep"
    assert payload["diagnostics"]["simulation"]["best_point"]["objective_observable"] == "maxcut_cost"
    assert payload["diagnostics"]["simulation"]["observables"][0]["name"] == "maxcut_cost"

    report = json.loads((workspace / "reports" / "latest.json").read_text())
    assert report["semantics"]["observable_count"] == 1
    assert report["semantics"]["parameter_workflow_mode"] == "sweep"
    assert report["semantics"]["parameter_workflow"]["point_count"] == 4
    assert report["diagnostics"]["simulation"]["best_point"]["objective"] == "maximize"


def test_qrun_exec_json_accepts_binding_only_parameter_workflow_qspec(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    qspec_path = tmp_path / "qaoa-binding-qspec.json"
    qspec = _binding_only_qaoa_qspec()
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
    assert payload["diagnostics"]["resources"]["two_qubit_gates"] == 16
    assert payload["diagnostics"]["transpile"]["status"] == "ok"
    qiskit_code = Path(payload["artifacts"]["qiskit_code"]).read_text()
    assert "qc.rz(0.4, 1)" in qiskit_code
    assert "qc.rx(0.7, 0)" in qiskit_code


def test_qrun_exec_qiskit_export_uses_representative_parameter_point(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    qspec_path = tmp_path / "qaoa-sweep-qspec.json"
    qspec = plan_to_qspec(parse_intent_file(PROJECT_ROOT / "examples" / "intent-qaoa-maxcut.md"))
    qspec.metadata["parameter_workflow"] = {
        "mode": "sweep",
        "grid": {
            "gamma_0": [0.2, 0.4],
            "beta_0": [0.1, 0.3],
            "gamma_1": [0.45],
            "beta_1": [0.35],
        },
    }
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
    report = json.loads((workspace / "reports" / "latest.json").read_text())
    representative_bindings = report["diagnostics"]["simulation"]["representative_bindings"]
    qiskit_code = Path(payload["artifacts"]["qiskit_code"]).read_text()

    assert f"qc.rz({_fmt(2 * representative_bindings['gamma_0'])}, 1)" in qiskit_code
    assert f"qc.rx({_fmt(2 * representative_bindings['beta_1'])}, 0)" in qiskit_code
    assert "qc.rx(0.68, 0)" not in qiskit_code


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


def test_qrun_exec_json_reports_workspace_recovery_required_for_leftover_commit_temps(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    intent_path = _write_intent(
        tmp_path / "intent-bell.md",
        title="Bell intent",
        goal="Create a Bell pair and measure both qubits.",
    )
    initial = RUNNER.invoke(
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
    assert initial.exit_code == 0, initial.stdout

    pending_report = workspace / "reports" / "latest.json.tmp"
    pending_manifest = workspace / "manifests" / "latest.json.tmp"
    pending_report.write_text("pending")
    pending_manifest.write_text("pending")

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
    assert payload["reason"] == "workspace_recovery_required"
    assert payload["error_code"] == "workspace_recovery_required"
    assert payload["details"]["workspace"] == str(workspace.resolve())
    assert sorted(payload["details"]["pending_files"]) == sorted([str(pending_manifest), str(pending_report)])
    assert payload["details"]["last_valid_revision"] == "rev_000001"


def test_qrun_exec_json_rejects_trusted_report_with_artifact_digest_drift(tmp_path: Path) -> None:
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
    history_qiskit = source_workspace / "artifacts" / "history" / "rev_000001" / "qiskit" / "main.py"
    current_qiskit = source_workspace / "artifacts" / "qiskit" / "main.py"
    history_qiskit.unlink()
    current_qiskit.write_text(current_qiskit.read_text() + "\n# tampered replay alias\n")

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

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["reason"] == "artifact_outputs_mismatched"
    assert payload["error_code"] == "artifact_outputs_mismatched"


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

    first_report = _assert_report_matches_qspec(
        report_path=workspace / "reports" / "history" / "rev_000001.json",
        qspec_path=workspace / "specs" / "history" / "rev_000001.json",
    )

    assert first_report["qspec"]["path"].endswith("specs/history/rev_000001.json")
    assert first_report["provenance"]["qspec"]["path"].endswith("specs/history/rev_000001.json")


def test_qrun_exec_second_revision_report_matches_revision_qspec_semantics(tmp_path: Path) -> None:
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

    first_qspec = workspace / "specs" / "history" / "rev_000001.json"
    second_qspec = workspace / "specs" / "history" / "rev_000002.json"
    second_report = _assert_report_matches_qspec(
        report_path=workspace / "reports" / "history" / "rev_000002.json",
        qspec_path=second_qspec,
    )

    assert second_result.exit_code == 0, second_result.stdout
    assert second_qspec.read_bytes() != first_qspec.read_bytes()
    assert second_report["qspec"]["path"].endswith("specs/history/rev_000002.json")
    assert second_report["artifacts"]["qspec"].endswith("specs/history/rev_000002.json")
    assert second_report["artifacts"]["report"].endswith("reports/history/rev_000002.json")


def test_qrun_exec_json_accepts_second_history_revision_input_after_later_runs(tmp_path: Path) -> None:
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

    result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(workspace),
            "--revision",
            "rev_000002",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["revision"] == "rev_000003"
    assert payload["diagnostics"]["simulation"]["status"] == "ok"
    assert Path(payload["artifacts"]["qspec"]).exists()


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


def test_qrun_exec_json_rejects_trusted_revision_with_artifact_digest_drift(tmp_path: Path) -> None:
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

    history_qiskit = workspace / "artifacts" / "history" / "rev_000001" / "qiskit" / "main.py"
    current_qiskit = workspace / "artifacts" / "qiskit" / "main.py"
    history_qiskit.unlink()
    current_qiskit.unlink()

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

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["reason"] == "artifact_outputs_missing"
    assert payload["error_code"] == "artifact_outputs_missing"


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
    (source_workspace / "specs" / "current.json").write_text('{"version":"0.1"}')

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


def test_qrun_exec_json_returns_exit_code_3_for_tampered_report_qspec_fallback(
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
            "exec",
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
