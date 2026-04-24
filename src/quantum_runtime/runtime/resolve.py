"""Intent normalization and execution-input resolution helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from quantum_runtime.errors import ManualQspecRequiredError
from quantum_runtime.intent import (
    IntentModel,
    parse_intent_file,
    parse_intent_json_file,
    parse_intent_text,
)
from quantum_runtime.qspec import (
    QSpec,
    QSpecValidationError,
    normalize_qspec,
    summarize_qspec_semantics,
    validate_qspec,
)
from quantum_runtime.runtime.contracts import SchemaPayload
from quantum_runtime.runtime.imports import ImportReference, ImportSourceError, resolve_import_reference
from quantum_runtime.workspace import WorkspaceManifest, WorkspacePaths


IntentSourceKind = Literal[
    "prompt_text",
    "intent_file",
    "intent_json_file",
    "qspec_file",
    "report_file",
    "report_revision",
]


class IntentResolution(SchemaPayload):
    """Normalized intent payload that agents can consume before execution."""

    status: Literal["ok"] = "ok"
    source_kind: IntentSourceKind
    source: str
    intent: dict[str, Any] = Field(default_factory=dict)


class ResolveResult(SchemaPayload):
    """Resolved ingress payload including canonical QSpec and execution plan."""

    status: Literal["ok", "degraded", "error"]
    workspace: str
    input: dict[str, Any] = Field(default_factory=dict)
    intent: dict[str, Any] = Field(default_factory=dict)
    qspec: dict[str, Any] = Field(default_factory=dict)
    plan: dict[str, Any] = Field(default_factory=dict)


class ResolvedRuntimeInput(BaseModel):
    """Internal normalized execution input shared by plan and exec flows."""

    source_kind: IntentSourceKind
    source: str
    input_data: dict[str, str]
    intent_model: IntentModel
    intent_resolution: IntentResolution
    qspec: QSpec
    requested_exports: list[str]


def resolve_runtime_input(
    *,
    workspace_root: Path,
    intent_file: Path | None = None,
    intent_json_file: Path | None = None,
    qspec_file: Path | None = None,
    report_file: Path | None = None,
    revision: str | None = None,
    intent_text: str | None = None,
) -> ResolvedRuntimeInput:
    """Resolve one runtime input into normalized intent plus canonical QSpec."""
    inputs_provided = sum(
        value is not None
        for value in (intent_file, intent_json_file, qspec_file, report_file, revision, intent_text)
    )
    if inputs_provided != 1:
        raise ValueError("expected_exactly_one_input")

    if intent_file is not None:
        intent = _parse_plannable_intent(parse_intent_file, intent_file, source=str(intent_file))
        return _resolved_from_intent(
            source_kind="intent_file",
            source=str(intent_file),
            input_data={"mode": "intent", "path": str(intent_file)},
            intent=intent,
        )
    if intent_json_file is not None:
        intent = _parse_plannable_intent(parse_intent_json_file, intent_json_file, source=str(intent_json_file))
        return _resolved_from_intent(
            source_kind="intent_json_file",
            source=str(intent_json_file),
            input_data={"mode": "intent_json", "path": str(intent_json_file)},
            intent=intent,
        )
    if intent_text is not None:
        intent = _parse_plannable_intent(parse_intent_text, intent_text, source="<inline>")
        return _resolved_from_intent(
            source_kind="prompt_text",
            source="<inline>",
            input_data={"mode": "intent_text", "path": "<inline>"},
            intent=intent,
        )
    if qspec_file is not None:
        try:
            qspec = _validated_qspec(QSpec.model_validate_json(qspec_file.read_text()), source=str(qspec_file))
        except ValidationError as exc:
            raise ImportSourceError(
                "invalid_qspec",
                source=str(qspec_file),
                details={"error": str(exc)},
            ) from exc
        exports = _exports_from_qspec(qspec, workspace_root=workspace_root)
        intent = _intent_from_qspec(
            qspec=qspec,
            source_kind="qspec_file",
            source=str(qspec_file),
            requested_exports=exports,
        )
        return ResolvedRuntimeInput(
            source_kind="qspec_file",
            source=str(qspec_file),
            input_data={"mode": "qspec", "path": str(qspec_file)},
            intent_model=intent,
            intent_resolution=IntentResolution(
                source_kind="qspec_file",
                source=str(qspec_file),
                intent=_intent_payload(intent=intent, source_kind="qspec_file", source=str(qspec_file)),
            ),
            qspec=qspec,
            requested_exports=exports,
        )

    resolution = resolve_import_reference(
        ImportReference(
            workspace_root=workspace_root,
            report_file=report_file,
            revision=revision,
        )
    )
    qspec = _validated_qspec(resolution.load_qspec(), source=str(resolution.qspec_path))
    source_kind: IntentSourceKind = "report_revision" if revision is not None else "report_file"
    source = str(resolution.report_path) if report_file is not None else str(revision)
    intent = _intent_from_qspec(
        qspec=qspec,
        source_kind=source_kind,
        source=source,
        requested_exports=_requested_exports_from_resolution(resolution, workspace_root=workspace_root),
    )
    return ResolvedRuntimeInput(
        source_kind=source_kind,
        source=source,
        input_data={"mode": "report", "path": str(resolution.report_path)},
        intent_model=intent,
        intent_resolution=IntentResolution(
            source_kind=source_kind,
            source=source,
            intent=_intent_payload(intent=intent, source_kind=source_kind, source=source),
        ),
        qspec=qspec,
        requested_exports=_requested_exports_from_resolution(resolution, workspace_root=workspace_root),
    )


def intent_resolution_from_prompt(text: str) -> IntentResolution:
    """Normalize one prompt string into an intent payload without planning."""
    intent = _parse_plannable_intent(parse_intent_text, text, source="<inline>")
    return IntentResolution(
        source_kind="prompt_text",
        source="<inline>",
        intent=_intent_payload(intent=intent, source_kind="prompt_text", source="<inline>"),
    )


def _resolved_from_intent(
    *,
    source_kind: IntentSourceKind,
    source: str,
    input_data: dict[str, str],
    intent: IntentModel,
) -> ResolvedRuntimeInput:
    from quantum_runtime.intent.planner import plan_to_qspec

    try:
        qspec = _validated_qspec(plan_to_qspec(intent), source=source)
    except ManualQspecRequiredError as exc:
        raise ImportSourceError(
            "manual_qspec_required",
            source=source,
            details={"error": str(exc)},
        ) from exc
    return ResolvedRuntimeInput(
        source_kind=source_kind,
        source=source,
        input_data=input_data,
        intent_model=intent,
        intent_resolution=IntentResolution(
            source_kind=source_kind,
            source=source,
            intent=_intent_payload(intent=intent, source_kind=source_kind, source=source),
        ),
        qspec=qspec,
        requested_exports=list(intent.exports),
    )


def _parse_plannable_intent(parser: Any, value: Any, *, source: str) -> IntentModel:
    try:
        return parser(value)
    except ManualQspecRequiredError as exc:
        raise ImportSourceError(
            "manual_qspec_required",
            source=source,
            details={"error": str(exc)},
        ) from exc
    except (QSpecValidationError, ValidationError, ValueError) as exc:
        raise ImportSourceError(
            "invalid_intent",
            source=source,
            details={"error": str(exc)},
        ) from exc


def _intent_from_qspec(
    *,
    qspec: QSpec,
    source_kind: IntentSourceKind,
    source: str,
    requested_exports: list[str],
) -> IntentModel:
    constraints = summarize_qspec_semantics(qspec)["constraints"]
    return IntentModel(
        title=qspec.title,
        goal=qspec.goal,
        exports=list(requested_exports),
        backend_preferences=list(qspec.backend_preferences),
        constraints=constraints,
        shots=int(qspec.constraints.shots),
        notes=f"Derived from {source_kind}.",
    )


def _intent_payload(*, intent: IntentModel, source_kind: IntentSourceKind, source: str) -> dict[str, Any]:
    payload = intent.model_dump(mode="json")
    payload["source_kind"] = source_kind
    payload["source"] = source
    return payload


def _validated_qspec(qspec: QSpec, *, source: str) -> QSpec:
    try:
        return validate_qspec(normalize_qspec(qspec))
    except (QSpecValidationError, ValidationError, ValueError) as exc:
        raise ImportSourceError(
            "invalid_qspec",
            source=source,
            details={"error": str(exc)},
        ) from exc


def _default_exports(workspace_root: Path) -> list[str]:
    paths = WorkspacePaths(root=workspace_root)
    if not paths.workspace_json.exists():
        return ["qiskit", "qasm3"]
    try:
        return WorkspaceManifest.load(paths.workspace_json).default_exports
    except Exception:
        return ["qiskit", "qasm3"]


def _exports_from_qspec(qspec: QSpec, *, workspace_root: Path) -> list[str]:
    formats = [str(item) for item in qspec.runtime.export_requirements.formats if item]
    return formats or _default_exports(workspace_root)


def _requested_exports_from_resolution(resolution: Any, *, workspace_root: Path) -> list[str]:
    report_payload = resolution.load_report()
    artifacts = report_payload.get("artifacts") if isinstance(report_payload, dict) else {}
    requested_exports: list[str] = []
    if isinstance(artifacts, dict):
        if isinstance(artifacts.get("qiskit_code"), str):
            requested_exports.append("qiskit")
        if isinstance(artifacts.get("qasm3"), str):
            requested_exports.append("qasm3")
        if isinstance(artifacts.get("classiq_code"), str):
            requested_exports.append("classiq-python")
    return requested_exports or _default_exports(workspace_root)
