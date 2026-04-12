"""Minimal end-to-end execution flow for intent-driven runs."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field

from quantum_runtime.backends import run_classiq_backend
from quantum_runtime.diagnostics import (
    estimate_resources,
    run_local_simulation,
    validate_target_constraints,
    write_diagrams,
)
from quantum_runtime.lowering import (
    write_classiq_program,
    write_qasm3_program,
    write_qiskit_program,
)
from quantum_runtime.qspec.parameter_workflow import (
    representative_bindings as qspec_representative_bindings,
)
from quantum_runtime.reporters import summarize_report, write_report
from quantum_runtime.qspec import QSpec, normalize_qspec, validate_qspec
from quantum_runtime.runtime.control_plane import build_execution_plan_from_resolved
from quantum_runtime.runtime.resolve import ResolvedRuntimeInput, resolve_runtime_input
from quantum_runtime.runtime.run_manifest import write_run_manifest
from quantum_runtime.runtime.imports import ImportSourceError, resolve_report_file
from quantum_runtime.workspace import WorkspaceManager


EventSink = Callable[[str, dict[str, Any], str | None, str], None]


class ReportImportError(ValueError):
    """Raised when a report cannot be used as an execution input."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


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


def execute_intent(*, workspace_root: Path, intent_file: Path, event_sink: EventSink | None = None) -> ExecResult:
    """Execute the deterministic generation pipeline for an intent file."""
    handle = WorkspaceManager.load_or_init(workspace_root)
    resolved = resolve_runtime_input(workspace_root=workspace_root, intent_file=intent_file)
    revision = handle.reserve_revision()
    if event_sink is not None:
        event_sink("run_started", {"mode": "intent", "path": str(intent_file)}, revision, "ok")
    handle.trace.append(
        "exec_started",
        {"intent_file": str(intent_file)},
        revision=revision,
    )
    latest_intent_path = handle.root / "intents" / "latest.md"
    latest_intent_path.write_text(intent_file.read_text())
    (handle.root / "intents" / "history" / f"{revision}.md").write_text(intent_file.read_text())
    _persist_runtime_objects(handle=handle, revision=revision, resolved=resolved)
    if event_sink is not None:
        event_sink("input_resolved", {"mode": "intent", "path": str(intent_file)}, revision, "ok")
        event_sink(
            "qspec_prepared",
            {
                "program_id": resolved.qspec.program_id,
                "pattern": resolved.qspec.body[0].pattern if resolved.qspec.body else "unknown",
            },
            revision,
            "ok",
        )
        event_sink("intent_written", {"path": str(handle.paths.intent_history_json(revision))}, revision, "ok")
        event_sink("plan_written", {"path": str(handle.paths.plan_history_json(revision))}, revision, "ok")

    return _execute_resolved(
        handle=handle,
        revision=revision,
        resolved=resolved,
        event_sink=event_sink,
    )


def execute_intent_text(*, workspace_root: Path, intent_text: str, event_sink: EventSink | None = None) -> ExecResult:
    """Execute the deterministic generation pipeline for inline intent text."""
    handle = WorkspaceManager.load_or_init(workspace_root)
    resolved = resolve_runtime_input(workspace_root=workspace_root, intent_text=intent_text)
    revision = handle.reserve_revision()
    if event_sink is not None:
        event_sink("run_started", {"mode": "intent_text", "path": "<inline>"}, revision, "ok")
    handle.trace.append(
        "exec_started",
        {"intent_text": intent_text},
        revision=revision,
    )
    latest_intent_path = handle.root / "intents" / "latest.md"
    latest_intent_path.write_text(intent_text)
    (handle.root / "intents" / "history" / f"{revision}.md").write_text(intent_text)
    _persist_runtime_objects(handle=handle, revision=revision, resolved=resolved)
    if event_sink is not None:
        event_sink("input_resolved", {"mode": "intent_text", "path": "<inline>"}, revision, "ok")
        event_sink(
            "qspec_prepared",
            {
                "program_id": resolved.qspec.program_id,
                "pattern": resolved.qspec.body[0].pattern if resolved.qspec.body else "unknown",
            },
            revision,
            "ok",
        )
        event_sink("intent_written", {"path": str(handle.paths.intent_history_json(revision))}, revision, "ok")
        event_sink("plan_written", {"path": str(handle.paths.plan_history_json(revision))}, revision, "ok")

    return _execute_resolved(
        handle=handle,
        revision=revision,
        resolved=resolved,
        event_sink=event_sink,
    )


def execute_intent_json(*, workspace_root: Path, intent_json_file: Path, event_sink: EventSink | None = None) -> ExecResult:
    """Execute the deterministic generation pipeline for a structured JSON intent file."""
    handle = WorkspaceManager.load_or_init(workspace_root)
    resolved = resolve_runtime_input(workspace_root=workspace_root, intent_json_file=intent_json_file)
    revision = handle.reserve_revision()
    if event_sink is not None:
        event_sink("run_started", {"mode": "intent_json", "path": str(intent_json_file)}, revision, "ok")
    handle.trace.append(
        "exec_started",
        {"intent_json_file": str(intent_json_file)},
        revision=revision,
    )
    _persist_runtime_objects(handle=handle, revision=revision, resolved=resolved)
    if event_sink is not None:
        event_sink("input_resolved", {"mode": "intent_json", "path": str(intent_json_file)}, revision, "ok")
        event_sink(
            "qspec_prepared",
            {
                "program_id": resolved.qspec.program_id,
                "pattern": resolved.qspec.body[0].pattern if resolved.qspec.body else "unknown",
            },
            revision,
            "ok",
        )
        event_sink("intent_written", {"path": str(handle.paths.intent_history_json(revision))}, revision, "ok")
        event_sink("plan_written", {"path": str(handle.paths.plan_history_json(revision))}, revision, "ok")
    return _execute_resolved(
        handle=handle,
        revision=revision,
        resolved=resolved,
        event_sink=event_sink,
    )


def execute_qspec(*, workspace_root: Path, qspec_file: Path, event_sink: EventSink | None = None) -> ExecResult:
    """Execute the deterministic generation pipeline for a serialized QSpec file."""
    handle = WorkspaceManager.load_or_init(workspace_root)
    resolved = resolve_runtime_input(workspace_root=workspace_root, qspec_file=qspec_file)
    revision = handle.reserve_revision()
    if event_sink is not None:
        event_sink("run_started", {"mode": "qspec", "path": str(qspec_file)}, revision, "ok")
    handle.trace.append(
        "exec_started",
        {"qspec_file": str(qspec_file)},
        revision=revision,
    )
    _persist_runtime_objects(handle=handle, revision=revision, resolved=resolved)
    if event_sink is not None:
        event_sink("input_resolved", {"mode": "qspec", "path": str(qspec_file)}, revision, "ok")
        event_sink(
            "qspec_prepared",
            {
                "program_id": resolved.qspec.program_id,
                "pattern": resolved.qspec.body[0].pattern if resolved.qspec.body else "unknown",
            },
            revision,
            "ok",
        )
        event_sink("intent_written", {"path": str(handle.paths.intent_history_json(revision))}, revision, "ok")
        event_sink("plan_written", {"path": str(handle.paths.plan_history_json(revision))}, revision, "ok")
    return _execute_resolved(
        handle=handle,
        revision=revision,
        resolved=resolved,
        event_sink=event_sink,
    )


def execute_report(*, workspace_root: Path, report_file: Path, event_sink: EventSink | None = None) -> ExecResult:
    """Execute the deterministic generation pipeline using a previously written report."""
    handle = WorkspaceManager.load_or_init(workspace_root)
    resolved = resolve_runtime_input(workspace_root=workspace_root, report_file=report_file)
    revision = handle.reserve_revision()
    if event_sink is not None:
        event_sink("run_started", {"mode": "report", "path": str(report_file)}, revision, "ok")
    handle.trace.append(
        "exec_started",
        {"report_file": str(report_file)},
        revision=revision,
    )
    _persist_runtime_objects(handle=handle, revision=revision, resolved=resolved)
    if event_sink is not None:
        event_sink("input_resolved", {"mode": "report", "path": str(report_file)}, revision, "ok")
        event_sink(
            "qspec_prepared",
            {
                "program_id": resolved.qspec.program_id,
                "pattern": resolved.qspec.body[0].pattern if resolved.qspec.body else "unknown",
            },
            revision,
            "ok",
        )
        event_sink("intent_written", {"path": str(handle.paths.intent_history_json(revision))}, revision, "ok")
        event_sink("plan_written", {"path": str(handle.paths.plan_history_json(revision))}, revision, "ok")
    return _execute_resolved(
        handle=handle,
        revision=revision,
        resolved=resolved,
        event_sink=event_sink,
    )


def _execute_resolved(
    *,
    handle: Any,
    revision: str,
    resolved: ResolvedRuntimeInput,
    event_sink: EventSink | None = None,
) -> ExecResult:
    return _execute_qspec(
        handle=handle,
        revision=revision,
        qspec=resolved.qspec,
        requested_exports=set(resolved.requested_exports),
        input_data=resolved.input_data,
        shots=int(resolved.intent_model.shots),
        event_sink=event_sink,
    )


def _execute_qspec(
    *,
    handle: Any,
    revision: str,
    qspec: QSpec,
    requested_exports: set[str],
    input_data: dict[str, str],
    shots: int,
    event_sink: EventSink | None = None,
) -> ExecResult:
    """Persist QSpec, emit artifacts, run diagnostics, and write reports."""

    qspec_path = handle.root / "specs" / "current.json"
    qspec_history_path = handle.root / "specs" / "history" / f"{revision}.json"
    qspec_text = qspec.model_dump_json(indent=2)
    qspec_path.write_text(qspec_text)
    qspec_history_path.write_text(qspec_text)
    if event_sink is not None:
        event_sink("artifact_written", {"kind": "qspec", "path": str(qspec_history_path)}, revision, "ok")

    artifacts: dict[str, str] = {
        "qspec": str(qspec_history_path),
    }
    warnings: list[str] = []
    errors: list[str] = []
    backend_reports: dict[str, Any] = {}
    simulation = run_local_simulation(qspec, shots=shots)
    if event_sink is not None:
        event_sink("diagnostic_completed", {"kind": "simulation", "status": simulation.status}, revision, simulation.status)
    representative_bindings = (
        dict(simulation.representative_bindings)
        if simulation.status == "ok"
        else dict(qspec_representative_bindings(qspec))
    )
    if not representative_bindings:
        representative_bindings = None
    export_context = {
        "point_label": simulation.representative_point_label,
        "parameter_mode": simulation.parameter_mode,
        "bindings": dict(representative_bindings or {}),
    }
    if "qiskit" in requested_exports:
        qiskit_path = write_qiskit_program(
            qspec,
            handle.root / "artifacts" / "qiskit" / "main.py",
            parameter_bindings=representative_bindings,
        )
        artifacts["qiskit_code"] = str(
            _snapshot_artifact(
                qiskit_path,
                handle.root / "artifacts" / "history" / revision / "qiskit" / "main.py",
            )
        )
        if event_sink is not None:
            event_sink("artifact_written", {"kind": "qiskit_code", "path": artifacts["qiskit_code"]}, revision, "ok")
    if "qasm3" in requested_exports:
        qasm_path = write_qasm3_program(
            qspec,
            handle.root / "artifacts" / "qasm" / "main.qasm",
            parameter_bindings=representative_bindings,
        )
        artifacts["qasm3"] = str(
            _snapshot_artifact(
                qasm_path,
                handle.root / "artifacts" / "history" / revision / "qasm" / "main.qasm",
            )
        )
        if event_sink is not None:
            event_sink("artifact_written", {"kind": "qasm3", "path": artifacts["qasm3"]}, revision, "ok")
    if "classiq-python" in requested_exports:
        classiq_emit = write_classiq_program(
            qspec,
            handle.root / "artifacts" / "classiq" / "main.py",
            parameter_bindings=representative_bindings,
        )
        if classiq_emit.status == "ok" and classiq_emit.path is not None:
            artifacts["classiq_code"] = str(
                _snapshot_artifact(
                    classiq_emit.path,
                    handle.root / "artifacts" / "history" / revision / "classiq" / "main.py",
                )
            )
            if event_sink is not None:
                event_sink("artifact_written", {"kind": "classiq_code", "path": artifacts["classiq_code"]}, revision, "ok")
        elif classiq_emit.reason is not None:
            warnings.append(classiq_emit.reason)

    diagrams = write_diagrams(qspec, handle, parameter_bindings=representative_bindings)
    resources = estimate_resources(qspec, parameter_bindings=representative_bindings)
    transpile = validate_target_constraints(qspec, parameter_bindings=representative_bindings)
    if event_sink is not None:
        event_sink("diagnostic_completed", {"kind": "resources", "status": "ok"}, revision, "ok")
        event_sink("diagnostic_completed", {"kind": "transpile", "status": transpile.status}, revision, transpile.status)
    diagnostics = {
        "simulation": simulation.model_dump(mode="json"),
        "exports": export_context,
        "resources": resources.model_dump(mode="json"),
        "diagram": {
            "text_path": "",
            "png_path": "",
        },
        "transpile": transpile.model_dump(mode="json"),
    }
    artifacts["diagram_txt"] = str(
        _snapshot_artifact(
            diagrams.text_path,
            handle.root / "artifacts" / "history" / revision / "figures" / "circuit.txt",
        )
    )
    artifacts["diagram_png"] = str(
        _snapshot_artifact(
            diagrams.png_path,
            handle.root / "artifacts" / "history" / revision / "figures" / "circuit.png",
        )
    )
    diagnostics["diagram"]["text_path"] = artifacts["diagram_txt"]
    diagnostics["diagram"]["png_path"] = artifacts["diagram_png"]
    if event_sink is not None:
        event_sink("artifact_written", {"kind": "diagram_txt", "path": artifacts["diagram_txt"]}, revision, "ok")
        event_sink("artifact_written", {"kind": "diagram_png", "path": artifacts["diagram_png"]}, revision, "ok")
        event_sink("diagnostic_completed", {"kind": "diagram", "status": "ok"}, revision, "ok")

    if "classiq" in qspec.backend_preferences:
        classiq_backend_report = run_classiq_backend(
            qspec,
            handle,
            parameter_bindings=representative_bindings,
        )
        classiq_backend_payload = classiq_backend_report.model_dump(mode="json")
        if classiq_backend_report.code_path is not None and classiq_backend_report.code_path.exists():
            classiq_code_snapshot = handle.root / "artifacts" / "history" / revision / "classiq" / "main.py"
            classiq_code_path = _snapshot_artifact(classiq_backend_report.code_path, classiq_code_snapshot)
            artifacts.setdefault("classiq_code", str(classiq_code_path))
            classiq_backend_payload["code_path"] = str(classiq_code_path)
        if classiq_backend_report.results_path is not None and classiq_backend_report.results_path.exists():
            classiq_results_snapshot = handle.root / "artifacts" / "history" / revision / "classiq" / "synthesis.json"
            classiq_results_path = _snapshot_artifact(classiq_backend_report.results_path, classiq_results_snapshot)
            artifacts["classiq_results"] = str(classiq_results_path)
            classiq_backend_payload["results_path"] = str(classiq_results_path)
        backend_reports["classiq"] = classiq_backend_payload
        if classiq_backend_report.status == "dependency_missing":
            warnings.append(classiq_backend_report.reason or "classiq_dependency_missing")
        elif classiq_backend_report.status == "error":
            errors.append(classiq_backend_report.reason or "classiq_backend_error")
        if event_sink is not None:
            event_sink(
                "diagnostic_completed",
                {"kind": "classiq_backend", "status": classiq_backend_report.status},
                revision,
                classiq_backend_report.status,
            )

    report = write_report(
        workspace=handle,
        revision=revision,
        input_data=input_data,
        qspec=qspec,
        qspec_path=qspec_history_path,
        artifacts=artifacts,
        diagnostics=diagnostics,
        backend_reports=backend_reports,
        warnings=warnings,
        errors=errors,
    )
    report_path = handle.root / "reports" / "latest.json"
    report_history_path = handle.root / "reports" / "history" / f"{revision}.json"
    artifacts["report"] = str(report_history_path)
    report["artifacts"]["report"] = str(report_history_path)
    serialized_report = json.dumps(report, indent=2, ensure_ascii=True)
    report_path.write_text(serialized_report)
    report_history_path.write_text(serialized_report)
    if event_sink is not None:
        event_sink("report_written", {"path": str(report_history_path), "status": report["status"]}, revision, str(report["status"]))

    handle.trace.append(
        "exec_completed",
        {"status": str(report["status"]), "report": str(report_history_path)},
        revision=revision,
    )
    event_history_path, trace_history_path = _write_revision_event_snapshots(
        handle=handle,
        revision=revision,
    )
    write_run_manifest(
        workspace_root=handle.root,
        revision=revision,
        report_payload=report,
        qspec=qspec,
        qspec_path=qspec_history_path,
        report_path=report_history_path,
        intent_path=handle.paths.intent_history_json(revision),
        plan_path=handle.paths.plan_history_json(revision),
        event_history_path=event_history_path,
        trace_history_path=trace_history_path,
    )
    manifest_history_path = handle.paths.manifest_history_json(revision)
    artifacts["manifest"] = str(manifest_history_path)
    if event_sink is not None:
        event_sink("manifest_written", {"path": str(manifest_history_path)}, revision, "ok")
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
    if event_sink is not None:
        event_sink("run_completed", result.model_dump(mode="json"), revision, result.status)
    return result


def _snapshot_artifact(source_path: Path, snapshot_path: Path) -> Path:
    """Copy a mutable current artifact into a revision-stable snapshot path."""
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, snapshot_path)
    return snapshot_path


def _prepare_qspec(qspec: QSpec) -> QSpec:
    """Canonicalize and validate a QSpec before any workspace side effects."""
    prepared = normalize_qspec(qspec)
    return validate_qspec(prepared)


def _persist_runtime_objects(*, handle: Any, revision: str, resolved: ResolvedRuntimeInput) -> None:
    intent_history_path = handle.paths.intent_history_json(revision)
    plan_history_path = handle.paths.plan_history_json(revision)
    intent_payload = resolved.intent_resolution.model_dump_json(indent=2)
    intent_history_path.write_text(intent_payload)
    handle.paths.intents_latest_json.write_text(intent_payload)

    plan = build_execution_plan_from_resolved(workspace_root=handle.root, resolved=resolved)
    plan_payload = plan.model_dump_json(indent=2)
    plan_history_path.write_text(plan_payload)
    handle.paths.plans_latest_json.write_text(plan_payload)


def _write_revision_event_snapshots(*, handle: Any, revision: str) -> tuple[Path, Path]:
    event_history_path = handle.paths.event_history_jsonl(revision)
    trace_history_path = handle.paths.trace_history_ndjson(revision)
    _snapshot_revision_events(
        source_path=handle.paths.events_jsonl,
        snapshot_path=event_history_path,
        revision=revision,
    )
    _snapshot_revision_events(
        source_path=handle.paths.trace_events,
        snapshot_path=trace_history_path,
        revision=revision,
    )
    return event_history_path, trace_history_path


def _snapshot_revision_events(*, source_path: Path, snapshot_path: Path, revision: str) -> None:
    lines: list[str] = []
    for raw_line in source_path.read_text().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("revision") == revision:
            lines.append(f"{line}\n")
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text("".join(lines))


def load_qspec_from_report(report_file: Path) -> QSpec:
    """Load, normalize, and validate a QSpec referenced by a report artifact."""
    try:
        resolution = resolve_report_file(report_file)
    except ImportSourceError as exc:
        raise ReportImportError(exc.code) from exc

    try:
        return _prepare_qspec(QSpec.model_validate_json(resolution.qspec_path.read_text()))
    except FileNotFoundError as exc:
        raise ReportImportError("report_qspec_missing") from exc
    except json.JSONDecodeError as exc:
        raise ReportImportError("report_qspec_invalid_json") from exc
    except Exception as exc:
        raise ReportImportError("report_qspec_invalid") from exc


def _load_report_payload(report_file: Path) -> dict[str, Any]:
    try:
        payload = json.loads(report_file.read_text())
    except FileNotFoundError as exc:
        raise ReportImportError("report_file_missing") from exc
    except json.JSONDecodeError as exc:
        raise ReportImportError("report_file_invalid_json") from exc

    if not isinstance(payload, dict):
        raise ReportImportError("report_file_invalid_payload")
    return payload


def _requested_exports_from_report(payload: dict[str, Any], default_exports: list[str]) -> set[str]:
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        return set(default_exports)

    requested_exports: set[str] = set()
    if isinstance(artifacts.get("qiskit_code"), str):
        requested_exports.add("qiskit")
    if isinstance(artifacts.get("qasm3"), str):
        requested_exports.add("qasm3")
    if isinstance(artifacts.get("classiq_code"), str):
        requested_exports.add("classiq-python")

    return requested_exports or set(default_exports)
