from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.backends import ClassiqBackendReport
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
        "quantum_runtime.diagnostics.benchmark.run_classiq_backend",
        lambda qspec, workspace: ClassiqBackendReport(
            status="dependency_missing",
            reason="classiq_not_installed",
            code_path=workspace.root / "artifacts" / "classiq" / "main.py",
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

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "degraded"
    assert payload["backends"]["qiskit-local"]["depth"] == 5
    assert payload["backends"]["classiq"]["status"] == "dependency_missing"
