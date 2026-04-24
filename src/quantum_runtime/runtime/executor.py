"""Minimal end-to-end execution flow for intent-driven runs."""

from __future__ import annotations

import json
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
from quantum_runtime.errors import WorkspaceConflictError, WorkspaceRecoveryRequiredError
from quantum_runtime.lowering import (
    write_classiq_program,
    write_qasm3_program,
    write_qiskit_program,
)
from quantum_runtime.qspec import QSpec, normalize_qspec, validate_qspec
from quantum_runtime.qspec.parameter_workflow import (
    representative_bindings as qspec_representative_bindings,
)
from quantum_runtime.reporters import summarize_report, write_report
from quantum_runtime.runtime.control_plane import build_execution_plan_from_resolved
from quantum_runtime.runtime.imports import ImportSourceError, resolve_report_file
from quantum_runtime.runtime.resolve import ResolvedRuntimeInput, resolve_runtime_input
from quantum_runtime.runtime.run_manifest import write_run_manifest
from quantum_runtime.workspace import (
    TraceEvent,
    WorkspaceLockConflict,
    WorkspaceManager,
    acquire_workspace_lock,
    atomic_copy_file,
    atomic_write_text,
    pending_atomic_write_files,
)
from quantum_runtime.workspace.manifest import WorkspaceManifest
from quantum_runtime.workspace.trace import append_trace_log, write_trace_snapshot


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
    resolved = resolve_runtime_input(workspace_root=workspace_root, intent_file=intent_file)
    return _execute_runtime_input(
        workspace_root=workspace_root,
        resolved=resolved,
        run_payload={"mode": "intent", "path": str(intent_file)},
        trace_payload={"intent_file": str(intent_file)},
        intent_markdown=intent_file.read_text(),
        event_sink=event_sink,
    )


def execute_intent_text(*, workspace_root: Path, intent_text: str, event_sink: EventSink | None = None) -> ExecResult:
    """Execute the deterministic generation pipeline for inline intent text."""
    resolved = resolve_runtime_input(workspace_root=workspace_root, intent_text=intent_text)
    return _execute_runtime_input(
        workspace_root=workspace_root,
        resolved=resolved,
        run_payload={"mode": "intent_text", "path": "<inline>"},
        trace_payload={"intent_text": intent_text},
        intent_markdown=intent_text,
        event_sink=event_sink,
    )


def execute_intent_json(*, workspace_root: Path, intent_json_file: Path, event_sink: EventSink | None = None) -> ExecResult:
    """Execute the deterministic generation pipeline for a structured JSON intent file."""
    resolved = resolve_runtime_input(workspace_root=workspace_root, intent_json_file=intent_json_file)
    return _execute_runtime_input(
        workspace_root=workspace_root,
        resolved=resolved,
        run_payload={"mode": "intent_json", "path": str(intent_json_file)},
        trace_payload={"intent_json_file": str(intent_json_file)},
        event_sink=event_sink,
    )


def execute_qspec(*, workspace_root: Path, qspec_file: Path, event_sink: EventSink | None = None) -> ExecResult:
    """Execute the deterministic generation pipeline for a serialized QSpec file."""
    resolved = resolve_runtime_input(workspace_root=workspace_root, qspec_file=qspec_file)
    return _execute_runtime_input(
        workspace_root=workspace_root,
        resolved=resolved,
        run_payload={"mode": "qspec", "path": str(qspec_file)},
        trace_payload={"qspec_file": str(qspec_file)},
        event_sink=event_sink,
    )


def execute_report(*, workspace_root: Path, report_file: Path, event_sink: EventSink | None = None) -> ExecResult:
    """Execute the deterministic generation pipeline using a previously written report."""
    resolved = resolve_runtime_input(workspace_root=workspace_root, report_file=report_file)
    return _execute_runtime_input(
        workspace_root=workspace_root,
        resolved=resolved,
        run_payload={"mode": "report", "path": str(report_file)},
        trace_payload={"report_file": str(report_file)},
        event_sink=event_sink,
    )


def _execute_runtime_input(
    *,
    workspace_root: Path,
    resolved: ResolvedRuntimeInput,
    run_payload: dict[str, str],
    trace_payload: dict[str, str],
    intent_markdown: str | None = None,
    event_sink: EventSink | None = None,
) -> ExecResult:
    try:
        handle = WorkspaceManager.load_or_init(workspace_root)
    except WorkspaceLockConflict as exc:
        raise _workspace_conflict_error(workspace_root=workspace_root, conflict=exc) from exc

    plan_payload = build_execution_plan_from_resolved(
        workspace_root=handle.root,
        resolved=resolved,
    ).model_dump_json(indent=2)
    intent_payload = resolved.intent_resolution.model_dump_json(indent=2)

    try:
        with acquire_workspace_lock(handle.root, command=f"qrun exec {run_payload['mode']}"):
            manifest = WorkspaceManifest.load(handle.paths.workspace_json)
            handle.manifest = manifest
            _guard_exec_commit_paths(
                handle=handle,
                manifest_revision=_last_valid_revision(manifest.current_revision),
            )
            previous_revision = manifest.current_revision
            revision = handle.reserve_revision(assume_locked=True)

            if event_sink is not None:
                event_sink("run_started", run_payload, revision, "ok")
                event_sink("input_resolved", run_payload, revision, "ok")
                event_sink(
                    "qspec_prepared",
                    {
                        "program_id": resolved.qspec.program_id,
                        "pattern": resolved.qspec.body[0].pattern if resolved.qspec.body else "unknown",
                    },
                    revision,
                    "ok",
                )

            staged_events = [
                _serialize_exec_event("exec_started", trace_payload, revision=revision),
            ]
            try:
                return _execute_qspec(
                    handle=handle,
                    revision=revision,
                    qspec=resolved.qspec,
                    requested_exports=set(resolved.requested_exports),
                    input_data=resolved.input_data,
                    shots=int(resolved.intent_model.shots),
                    intent_payload=intent_payload,
                    plan_payload=plan_payload,
                    intent_markdown=intent_markdown,
                    staged_events=staged_events,
                    event_sink=event_sink,
                )
            except Exception:
                _restore_workspace_revision(handle=handle, revision=previous_revision)
                raise
    except WorkspaceLockConflict as exc:
        raise _workspace_conflict_error(workspace_root=handle.root, conflict=exc) from exc


def _execute_qspec(
    *,
    handle: Any,
    revision: str,
    qspec: QSpec,
    requested_exports: set[str],
    input_data: dict[str, str],
    shots: int,
    intent_payload: str,
    plan_payload: str,
    intent_markdown: str | None,
    staged_events: list[str],
    event_sink: EventSink | None = None,
) -> ExecResult:
    """Persist QSpec, emit artifacts, run diagnostics, and promote one revision coherently."""

    qspec_history_path = handle.root / "specs" / "history" / f"{revision}.json"
    atomic_write_text(qspec_history_path, qspec.model_dump_json(indent=2))

    intent_history_path = handle.paths.intent_history_json(revision)
    plan_history_path = handle.paths.plan_history_json(revision)
    atomic_write_text(intent_history_path, intent_payload)
    atomic_write_text(plan_history_path, plan_payload)

    intent_markdown_history_path: Path | None = None
    if intent_markdown is not None:
        intent_markdown_history_path = handle.root / "intents" / "history" / f"{revision}.md"
        atomic_write_text(intent_markdown_history_path, intent_markdown)

    if event_sink is not None:
        event_sink("intent_written", {"path": str(intent_history_path)}, revision, "ok")
        event_sink("plan_written", {"path": str(plan_history_path)}, revision, "ok")
        event_sink("artifact_written", {"kind": "qspec", "path": str(qspec_history_path)}, revision, "ok")

    artifacts: dict[str, str] = {"qspec": str(qspec_history_path)}
    warnings: list[str] = []
    errors: list[str] = []
    backend_reports: dict[str, Any] = {}

    simulation = run_local_simulation(qspec, shots=shots)
    if event_sink is not None:
        event_sink(
            "diagnostic_completed",
            {"kind": "simulation", "status": simulation.status},
            revision,
            simulation.status,
        )

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
    history_root = handle.root / "artifacts" / "history" / revision

    if "qiskit" in requested_exports:
        qiskit_path = write_qiskit_program(
            qspec,
            history_root / "qiskit" / "main.py",
            parameter_bindings=representative_bindings,
        )
        artifacts["qiskit_code"] = str(qiskit_path)
        if event_sink is not None:
            event_sink("artifact_written", {"kind": "qiskit_code", "path": artifacts["qiskit_code"]}, revision, "ok")

    if "qasm3" in requested_exports:
        qasm_path = write_qasm3_program(
            qspec,
            history_root / "qasm" / "main.qasm",
            parameter_bindings=representative_bindings,
        )
        artifacts["qasm3"] = str(qasm_path)
        if event_sink is not None:
            event_sink("artifact_written", {"kind": "qasm3", "path": artifacts["qasm3"]}, revision, "ok")

    if "classiq-python" in requested_exports:
        classiq_emit = write_classiq_program(
            qspec,
            history_root / "classiq" / "main.py",
            parameter_bindings=representative_bindings,
        )
        if classiq_emit.status == "ok" and classiq_emit.path is not None:
            artifacts["classiq_code"] = str(classiq_emit.path)
            if event_sink is not None:
                event_sink(
                    "artifact_written",
                    {"kind": "classiq_code", "path": artifacts["classiq_code"]},
                    revision,
                    "ok",
                )
        elif classiq_emit.reason is not None:
            warnings.append(classiq_emit.reason)

    diagrams = write_diagrams(
        qspec,
        handle,
        parameter_bindings=representative_bindings,
        output_dir=history_root / "figures",
    )
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
    diagram_text_history = _ensure_history_artifact(
        source_path=diagrams.text_path,
        history_path=history_root / "figures" / "circuit.txt",
    )
    diagram_png_history = _ensure_history_artifact(
        source_path=diagrams.png_path,
        history_path=history_root / "figures" / "circuit.png",
    )
    artifacts["diagram_txt"] = str(diagram_text_history)
    artifacts["diagram_png"] = str(diagram_png_history)
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
            output_dir=history_root / "classiq",
        )
        classiq_backend_payload = classiq_backend_report.model_dump(mode="json")
        if classiq_backend_report.code_path is not None and classiq_backend_report.code_path.exists():
            artifacts.setdefault("classiq_code", str(classiq_backend_report.code_path))
            classiq_backend_payload["code_path"] = str(classiq_backend_report.code_path)
        if classiq_backend_report.results_path is not None and classiq_backend_report.results_path.exists():
            artifacts["classiq_results"] = str(classiq_backend_report.results_path)
            classiq_backend_payload["results_path"] = str(classiq_backend_report.results_path)
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

    canonical_artifacts = dict(artifacts)
    canonical_artifacts["qspec"] = str(qspec_history_path)

    report = write_report(
        workspace=handle,
        revision=revision,
        input_data=input_data,
        qspec=qspec,
        qspec_path=qspec_history_path,
        artifacts=canonical_artifacts,
        diagnostics=diagnostics,
        backend_reports=backend_reports,
        warnings=warnings,
        errors=errors,
        promote_latest=False,
    )
    report_history_path = handle.root / "reports" / "history" / f"{revision}.json"
    artifacts["report"] = str(report_history_path)
    report["artifacts"]["report"] = str(report_history_path)
    if event_sink is not None:
        event_sink(
            "report_written",
            {"path": str(report_history_path), "status": report["status"]},
            revision,
            str(report["status"]),
        )

    staged_events.append(
        _serialize_exec_event(
            "exec_completed",
            {"status": str(report["status"]), "report": str(report_history_path)},
            revision=revision,
            status=str(report["status"]),
        )
    )
    staged_event_log = _write_staged_events(handle=handle, revision=revision, events=staged_events)
    try:
        event_history_path, trace_history_path = _write_revision_event_snapshots(
            handle=handle,
            revision=revision,
            staged_event_log=staged_event_log,
        )
        write_run_manifest(
            workspace_root=handle.root,
            revision=revision,
            report_payload=report,
            qspec=qspec,
            qspec_path=qspec_history_path,
            report_path=report_history_path,
            intent_path=intent_history_path,
            plan_path=plan_history_path,
            event_history_path=event_history_path,
            trace_history_path=trace_history_path,
            promote_latest=False,
        )
        manifest_history_path = handle.paths.manifest_history_json(revision)
        artifacts["manifest"] = str(manifest_history_path)
        if event_sink is not None:
            event_sink("manifest_written", {"path": str(manifest_history_path)}, revision, "ok")

        append_trace_log(source_path=staged_event_log, destination_path=handle.paths.events_jsonl)
        append_trace_log(source_path=staged_event_log, destination_path=handle.paths.trace_events)
        _promote_exec_aliases(
            handle=handle,
            qspec_history_path=qspec_history_path,
            intent_markdown_history_path=intent_markdown_history_path,
            intent_history_path=intent_history_path,
            plan_history_path=plan_history_path,
            report_history_path=report_history_path,
            manifest_history_path=manifest_history_path,
            artifacts=artifacts,
        )
    finally:
        staged_event_log.unlink(missing_ok=True)

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


def _prepare_qspec(qspec: QSpec) -> QSpec:
    """Canonicalize and validate a QSpec before any workspace side effects."""
    prepared = normalize_qspec(qspec)
    return validate_qspec(prepared)


def _ensure_history_artifact(*, source_path: Path, history_path: Path) -> Path:
    if source_path.resolve() == history_path.resolve():
        return history_path
    atomic_copy_file(source_path, history_path)
    return history_path


def _serialize_exec_event(
    event_type: str,
    payload: dict[str, Any],
    *,
    revision: str,
    status: str = "ok",
    error_code: str | None = None,
) -> str:
    event = TraceEvent(
        event_type=event_type,
        phase="execute",
        status=status,
        revision=revision,
        error_code=error_code,
        payload=payload,
    )
    return json.dumps(event.model_dump(mode="json"), ensure_ascii=True) + "\n"


def _write_staged_events(*, handle: Any, revision: str, events: list[str]) -> Path:
    staged_event_log = handle.root / "cache" / f"{revision}.events.staged"
    atomic_write_text(staged_event_log, "".join(events))
    return staged_event_log


def _write_revision_event_snapshots(*, handle: Any, revision: str, staged_event_log: Path) -> tuple[Path, Path]:
    event_history_path = handle.paths.event_history_jsonl(revision)
    trace_history_path = handle.paths.trace_history_ndjson(revision)
    write_trace_snapshot(source_path=staged_event_log, snapshot_path=event_history_path)
    write_trace_snapshot(source_path=staged_event_log, snapshot_path=trace_history_path)
    return event_history_path, trace_history_path


def _promote_exec_aliases(
    *,
    handle: Any,
    qspec_history_path: Path,
    intent_markdown_history_path: Path | None,
    intent_history_path: Path,
    plan_history_path: Path,
    report_history_path: Path,
    manifest_history_path: Path,
    artifacts: dict[str, str],
) -> None:
    for source_path, alias_path in _exec_alias_pairs(
        handle=handle,
        qspec_history_path=qspec_history_path,
        intent_markdown_history_path=intent_markdown_history_path,
        intent_history_path=intent_history_path,
        plan_history_path=plan_history_path,
        report_history_path=report_history_path,
        manifest_history_path=manifest_history_path,
        artifacts=artifacts,
    ):
        atomic_copy_file(source_path, alias_path)


def _guard_exec_commit_paths(*, handle: Any, manifest_revision: str | None) -> None:
    pending_files = sorted(
        {
            candidate
            for path in _exec_alias_target_paths(handle=handle)
            for candidate in pending_atomic_write_files(path)
        }
    )
    if pending_files:
        last_valid_revision = _coherent_active_revision(handle=handle)
        raise WorkspaceRecoveryRequiredError(
            workspace=handle.root,
            pending_files=pending_files,
            last_valid_revision=last_valid_revision,
        )

    last_valid_revision = _coherent_active_revision(handle=handle)
    alias_paths = _mismatched_exec_alias_paths(
        handle=handle,
        manifest_revision=manifest_revision,
        last_valid_revision=last_valid_revision,
    )
    if alias_paths:
        raise WorkspaceRecoveryRequiredError(
            workspace=handle.root,
            pending_files=[],
            last_valid_revision=last_valid_revision,
            alias_paths=alias_paths,
            recovery_mode="alias_mismatch",
        )


def _exec_alias_pairs(
    *,
    handle: Any,
    qspec_history_path: Path,
    intent_markdown_history_path: Path | None,
    intent_history_path: Path,
    plan_history_path: Path,
    report_history_path: Path,
    manifest_history_path: Path,
    artifacts: dict[str, str],
) -> list[tuple[Path, Path]]:
    alias_pairs: list[tuple[Path, Path]] = [
        (report_history_path, handle.root / "reports" / "latest.json"),
        (manifest_history_path, handle.paths.manifests_latest_json),
        (qspec_history_path, handle.root / "specs" / "current.json"),
    ]

    # Promote the revision-bearing surface first. Convenience aliases like latest
    # intent/plan should never outrun the coherent report/manifest/qspec set.
    if intent_markdown_history_path is not None:
        alias_pairs.append((intent_markdown_history_path, handle.root / "intents" / "latest.md"))

    alias_pairs.extend(
        [
            (intent_history_path, handle.paths.intents_latest_json),
            (plan_history_path, handle.paths.plans_latest_json),
        ]
    )

    artifact_aliases = {
        "qiskit_code": handle.root / "artifacts" / "qiskit" / "main.py",
        "qasm3": handle.root / "artifacts" / "qasm" / "main.qasm",
        "classiq_code": handle.root / "artifacts" / "classiq" / "main.py",
        "classiq_results": handle.root / "artifacts" / "classiq" / "synthesis.json",
        "diagram_txt": handle.root / "figures" / "circuit.txt",
        "diagram_png": handle.root / "figures" / "circuit.png",
    }
    for artifact_name, alias_path in artifact_aliases.items():
        raw_source = artifacts.get(artifact_name)
        if raw_source is None:
            continue
        alias_pairs.append((Path(raw_source), alias_path))

    return alias_pairs


def _exec_alias_target_paths(*, handle: Any) -> list[Path]:
    return [
        handle.root / "intents" / "latest.md",
        handle.paths.intents_latest_json,
        handle.paths.plans_latest_json,
        handle.root / "reports" / "latest.json",
        handle.paths.manifests_latest_json,
        handle.root / "specs" / "current.json",
        handle.root / "artifacts" / "qiskit" / "main.py",
        handle.root / "artifacts" / "qasm" / "main.qasm",
        handle.root / "artifacts" / "classiq" / "main.py",
        handle.root / "artifacts" / "classiq" / "synthesis.json",
        handle.root / "figures" / "circuit.txt",
        handle.root / "figures" / "circuit.png",
    ]


def _mismatched_exec_alias_paths(
    *,
    handle: Any,
    manifest_revision: str | None,
    last_valid_revision: str | None,
) -> list[Path]:
    workspace_json = handle.paths.workspace_json
    report_alias = handle.root / "reports" / "latest.json"
    manifest_alias = handle.paths.manifests_latest_json
    qspec_alias = handle.root / "specs" / "current.json"
    alias_paths = [
        workspace_json,
        qspec_alias,
        report_alias,
        manifest_alias,
    ]

    if manifest_revision is None:
        # A fresh workspace can legitimately seed specs/current.json before the first exec.
        # The recovery hole we are guarding here is "report or manifest alias exists
        # without an authoritative committed revision", not "any active qspec exists".
        if report_alias.exists() or manifest_alias.exists():
            return alias_paths
        return []

    if last_valid_revision == manifest_revision:
        return []
    return alias_paths


def _coherent_active_revision(*, handle: Any) -> str | None:
    report_alias = handle.root / "reports" / "latest.json"
    manifest_alias = handle.paths.manifests_latest_json
    qspec_alias = handle.root / "specs" / "current.json"

    report_revision = _load_alias_revision(report_alias)
    manifest_revision = _load_alias_revision(manifest_alias)
    if report_revision is None or manifest_revision is None or report_revision != manifest_revision:
        return None

    expected_qspec_path = handle.root / "specs" / "history" / f"{report_revision}.json"
    if not (
        expected_qspec_path.exists()
        and qspec_alias.exists()
        and qspec_alias.read_bytes() == expected_qspec_path.read_bytes()
    ):
        return None
    return report_revision


def _load_alias_revision(path: Path) -> str | None:
    try:
        payload = json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    if not isinstance(payload, dict):
        return None
    revision = payload.get("revision")
    if isinstance(revision, str):
        return revision
    return None


def _workspace_conflict_error(*, workspace_root: Path, conflict: WorkspaceLockConflict) -> WorkspaceConflictError:
    return WorkspaceConflictError(
        workspace=workspace_root.resolve(),
        lock_path=Path(conflict.lock_path),
        holder=conflict.holder.model_dump(mode="json"),
    )


def _last_valid_revision(revision: str | None) -> str | None:
    if revision in {None, "", "rev_000000"}:
        return None
    return revision


def _restore_workspace_revision(*, handle: Any, revision: str) -> None:
    manifest = WorkspaceManifest.load(handle.paths.workspace_json)
    manifest.current_revision = revision
    manifest.save(handle.paths.workspace_json)


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
