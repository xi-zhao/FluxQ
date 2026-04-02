"""Minimal end-to-end execution flow for intent-driven runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from quantum_runtime.backends import run_classiq_backend
from quantum_runtime.diagnostics import (
    estimate_resources,
    run_local_simulation,
    validate_target_constraints,
    write_diagrams,
)
from quantum_runtime.intent.parser import parse_intent_file, parse_intent_text
from quantum_runtime.intent.planner import plan_to_qspec
from quantum_runtime.lowering import (
    write_classiq_program,
    write_qasm3_program,
    write_qiskit_program,
)
from quantum_runtime.reporters import summarize_report, write_report
from quantum_runtime.qspec import QSpec, normalize_qspec, validate_qspec
from quantum_runtime.workspace import WorkspaceManager


class ExecResult(BaseModel):
    """Machine-readable result returned by `qrun exec --json`."""

    status: Literal["ok", "degraded", "error"]
    workspace: str
    revision: str
    summary: str
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(default_factory=dict)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    backend_reports: dict[str, Any] = Field(default_factory=dict)
    next_actions: list[str] = Field(default_factory=list)


def execute_intent(*, workspace_root: Path, intent_file: Path) -> ExecResult:
    """Execute the deterministic generation pipeline for an intent file."""
    handle = WorkspaceManager.load_or_init(workspace_root)
    intent = parse_intent_file(intent_file)
    qspec = _prepare_qspec(plan_to_qspec(intent))
    revision = handle.reserve_revision()
    handle.trace.append(
        "exec_started",
        {"intent_file": str(intent_file)},
        revision=revision,
    )
    latest_intent_path = handle.root / "intents" / "latest.md"
    latest_intent_path.write_text(intent_file.read_text())
    (handle.root / "intents" / "history" / f"{revision}.md").write_text(intent_file.read_text())

    return _execute_qspec(
        handle=handle,
        revision=revision,
        qspec=qspec,
        requested_exports=set(intent.exports),
        input_data={"mode": "intent", "path": str(intent_file)},
        shots=int(intent.shots),
    )


def execute_intent_text(*, workspace_root: Path, intent_text: str) -> ExecResult:
    """Execute the deterministic generation pipeline for inline intent text."""
    handle = WorkspaceManager.load_or_init(workspace_root)
    intent = parse_intent_text(intent_text)
    qspec = _prepare_qspec(plan_to_qspec(intent))
    revision = handle.reserve_revision()
    handle.trace.append(
        "exec_started",
        {"intent_text": intent_text},
        revision=revision,
    )
    latest_intent_path = handle.root / "intents" / "latest.md"
    latest_intent_path.write_text(intent_text)
    (handle.root / "intents" / "history" / f"{revision}.md").write_text(intent_text)

    return _execute_qspec(
        handle=handle,
        revision=revision,
        qspec=qspec,
        requested_exports=set(intent.exports),
        input_data={"mode": "intent_text", "path": "<inline>"},
        shots=int(intent.shots),
    )


def execute_qspec(*, workspace_root: Path, qspec_file: Path) -> ExecResult:
    """Execute the deterministic generation pipeline for a serialized QSpec file."""
    handle = WorkspaceManager.load_or_init(workspace_root)
    qspec = _prepare_qspec(QSpec.model_validate_json(qspec_file.read_text()))
    revision = handle.reserve_revision()
    handle.trace.append(
        "exec_started",
        {"qspec_file": str(qspec_file)},
        revision=revision,
    )
    return _execute_qspec(
        handle=handle,
        revision=revision,
        qspec=qspec,
        requested_exports=set(handle.manifest.default_exports),
        input_data={"mode": "qspec", "path": str(qspec_file)},
        shots=int(qspec.constraints.shots),
    )


def _execute_qspec(
    *,
    handle: Any,
    revision: str,
    qspec: QSpec,
    requested_exports: set[str],
    input_data: dict[str, str],
    shots: int,
) -> ExecResult:
    """Persist QSpec, emit artifacts, run diagnostics, and write reports."""

    qspec_path = handle.root / "specs" / "current.json"
    qspec_text = qspec.model_dump_json(indent=2)
    qspec_path.write_text(qspec_text)
    (handle.root / "specs" / "history" / f"{revision}.json").write_text(qspec_text)

    artifacts: dict[str, str] = {
        "qspec": str(qspec_path),
    }
    warnings: list[str] = []
    errors: list[str] = []
    backend_reports: dict[str, Any] = {}

    if "qiskit" in requested_exports:
        artifacts["qiskit_code"] = str(
            write_qiskit_program(qspec, handle.root / "artifacts" / "qiskit" / "main.py")
        )
    if "qasm3" in requested_exports:
        artifacts["qasm3"] = str(
            write_qasm3_program(qspec, handle.root / "artifacts" / "qasm" / "main.qasm")
        )
    if "classiq-python" in requested_exports:
        classiq_emit = write_classiq_program(qspec, handle.root / "artifacts" / "classiq" / "main.py")
        if classiq_emit.status == "ok" and classiq_emit.path is not None:
            artifacts["classiq_code"] = str(classiq_emit.path)
        elif classiq_emit.reason is not None:
            warnings.append(classiq_emit.reason)

    diagrams = write_diagrams(qspec, handle)
    simulation = run_local_simulation(qspec, shots=shots)
    resources = estimate_resources(qspec)
    transpile = validate_target_constraints(qspec)
    diagnostics = {
        "simulation": simulation.model_dump(mode="json"),
        "resources": resources.model_dump(mode="json"),
        "diagram": {
            "text_path": str(diagrams.text_path),
            "png_path": str(diagrams.png_path),
        },
        "transpile": transpile.model_dump(mode="json"),
    }
    artifacts["diagram_txt"] = str(diagrams.text_path)
    artifacts["diagram_png"] = str(diagrams.png_path)

    if "classiq" in qspec.backend_preferences:
        classiq_backend_report = run_classiq_backend(qspec, handle)
        backend_reports["classiq"] = classiq_backend_report.model_dump(mode="json")
        if classiq_backend_report.status == "dependency_missing":
            warnings.append(classiq_backend_report.reason or "classiq_dependency_missing")
        elif classiq_backend_report.status == "error":
            errors.append(classiq_backend_report.reason or "classiq_backend_error")

    report = write_report(
        workspace=handle,
        revision=revision,
        input_data=input_data,
        qspec_path=qspec_path,
        artifacts=artifacts,
        diagnostics=diagnostics,
        backend_reports=backend_reports,
        warnings=warnings,
        errors=errors,
    )
    report_path = handle.root / "reports" / "latest.json"
    artifacts["report"] = str(report_path)
    report["artifacts"]["report"] = str(report_path)
    serialized_report = json.dumps(report, indent=2, ensure_ascii=True)
    report_path.write_text(serialized_report)
    (handle.root / "reports" / "history" / f"{revision}.json").write_text(serialized_report)
    summary = summarize_report(report)

    result = ExecResult(
        status=str(report["status"]),
        workspace=str(handle.root),
        revision=revision,
        summary=summary,
        warnings=warnings,
        errors=errors,
        artifacts=artifacts,
        diagnostics=diagnostics,
        backend_reports=backend_reports,
        next_actions=[
            "read .quantum/reports/latest.json",
            "inspect .quantum/artifacts/qiskit/main.py",
        ],
    )

    handle.trace.append(
        "exec_completed",
        {"status": result.status, "report": str(report_path)},
        revision=revision,
    )
    return result


def _prepare_qspec(qspec: QSpec) -> QSpec:
    """Canonicalize and validate a QSpec before any workspace side effects."""
    prepared = normalize_qspec(qspec)
    return validate_qspec(prepared)
