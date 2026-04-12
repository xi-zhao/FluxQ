"""Immutable per-run manifest artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import Field, ValidationError

from quantum_runtime.qspec import QSpec, summarize_qspec_semantics
from quantum_runtime.errors import WorkspaceRecoveryRequiredError
from quantum_runtime.runtime.contracts import SchemaPayload
from quantum_runtime.workspace import WorkspacePaths, atomic_write_text, pending_atomic_write_files


class RunManifestArtifact(SchemaPayload):
    """Immutable join record for one runtime revision."""

    status: str
    revision: str
    input: dict[str, Any] = Field(default_factory=dict)
    intent: dict[str, Any] = Field(default_factory=dict)
    plan: dict[str, Any] = Field(default_factory=dict)
    events: dict[str, Any] = Field(default_factory=dict)
    qspec: dict[str, Any] = Field(default_factory=dict)
    report: dict[str, Any] = Field(default_factory=dict)
    representative_point: dict[str, Any] | None = None
    artifacts: dict[str, dict[str, Any]] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)


class RunReportArtifact(SchemaPayload):
    """Stable top-level report artifact contract."""

    status: str
    revision: str
    input: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    qspec: dict[str, Any] = Field(default_factory=dict)
    semantics: dict[str, Any] = Field(default_factory=dict)
    replay_integrity: dict[str, Any] = Field(default_factory=dict)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    backend_reports: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class RunManifestIntegrityError(ValueError):
    """Raised when a persisted run manifest is structurally valid but inconsistent."""

    def __init__(self, mismatches: list[str], *, details: dict[str, Any] | None = None) -> None:
        super().__init__(", ".join(mismatches))
        self.mismatches = mismatches
        self.details = details or {}


def write_run_manifest(
    *,
    workspace_root: Path,
    revision: str,
    report_payload: dict[str, Any],
    qspec: QSpec,
    qspec_path: Path,
    report_path: Path,
    intent_path: Path | None = None,
    plan_path: Path | None = None,
    event_history_path: Path | None = None,
    trace_history_path: Path | None = None,
    promote_latest: bool = True,
) -> dict[str, Any]:
    """Persist the immutable manifest artifact for one revision."""
    payload = build_run_manifest(
        workspace_root=workspace_root,
        revision=revision,
        report_payload=report_payload,
        qspec=qspec,
        qspec_path=qspec_path,
        report_path=report_path,
        intent_path=intent_path,
        plan_path=plan_path,
        event_history_path=event_history_path,
        trace_history_path=trace_history_path,
    )
    paths = WorkspacePaths(root=workspace_root)
    history_path = paths.manifest_history_json(revision)
    latest_path = paths.manifests_latest_json
    serialized = payload.model_dump_json(indent=2)
    _guard_manifest_latest_path(
        workspace_root=workspace_root,
        latest_path=latest_path,
        last_valid_revision=None,
    )
    atomic_write_text(history_path, serialized)
    if promote_latest:
        atomic_write_text(latest_path, serialized)
    return payload.model_dump(mode="json")


def _guard_manifest_latest_path(
    *,
    workspace_root: Path,
    latest_path: Path,
    last_valid_revision: str | None,
) -> None:
    pending_files = _pending_atomic_write_files(latest_path)
    if not pending_files:
        return
    raise WorkspaceRecoveryRequiredError(
        workspace=workspace_root.resolve(),
        pending_files=pending_files,
        last_valid_revision=last_valid_revision,
    )


def _pending_atomic_write_files(path: Path) -> list[Path]:
    return pending_atomic_write_files(path)


def load_run_manifest(
    *,
    workspace_root: Path,
    revision: str,
    expected_qspec_path: Path,
    expected_report_path: Path,
) -> dict[str, Any] | None:
    """Load one persisted immutable run manifest when available."""
    path = WorkspacePaths(root=workspace_root).manifest_history_json(revision)
    if not path.exists():
        return None
    return parse_and_validate_run_manifest(
        path=path,
        expected_revision=revision,
        expected_qspec_path=expected_qspec_path,
        expected_report_path=expected_report_path,
        workspace_root=workspace_root,
    )


def parse_and_validate_run_manifest(
    *,
    path: Path,
    expected_revision: str,
    expected_qspec_path: Path,
    expected_report_path: Path,
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    """Load a run manifest and verify that it still describes the expected immutable run."""
    try:
        payload = RunManifestArtifact.model_validate_json(path.read_text())
    except (ValidationError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(str(exc)) from exc

    mismatches: list[str] = []
    details: dict[str, Any] = {}

    if payload.revision != expected_revision:
        mismatches.append("revision")
        details["expected_revision"] = expected_revision
        details["actual_revision"] = payload.revision

    qspec_block = payload.qspec if isinstance(payload.qspec, dict) else {}
    report_block = payload.report if isinstance(payload.report, dict) else {}
    intent_block = payload.intent if isinstance(payload.intent, dict) else {}
    plan_block = payload.plan if isinstance(payload.plan, dict) else {}
    events_block = payload.events if isinstance(payload.events, dict) else {}
    qspec_path = Path(str(qspec_block.get("path", ""))).resolve()
    report_path = Path(str(report_block.get("path", ""))).resolve()
    expected_qspec_path = expected_qspec_path.resolve()
    expected_report_path = expected_report_path.resolve()
    workspace_paths = _resolve_workspace_paths(
        manifest_path=path,
        expected_revision=expected_revision,
        expected_qspec_path=expected_qspec_path,
        expected_report_path=expected_report_path,
        workspace_root=workspace_root,
    )
    expected_optional_paths = _expected_optional_artifact_paths(
        revision=expected_revision,
        workspace_paths=workspace_paths,
    )

    if qspec_path != expected_qspec_path:
        mismatches.append("qspec_path")
        details["expected_qspec_path"] = str(expected_qspec_path)
        details["actual_qspec_path"] = str(qspec_path)
    if report_path != expected_report_path:
        mismatches.append("report_path")
        details["expected_report_path"] = str(expected_report_path)
        details["actual_report_path"] = str(report_path)

    qspec_hash = str(qspec_block.get("hash", ""))
    report_hash = str(report_block.get("hash", ""))
    if not qspec_path.exists() or not qspec_path.is_file():
        mismatches.append("qspec_missing")
        details["resolved_qspec_path"] = str(qspec_path)
    elif _sha256_file(qspec_path) != qspec_hash:
        mismatches.append("qspec_hash")
        details["expected_qspec_hash"] = qspec_hash
        details["actual_qspec_hash"] = _sha256_file(qspec_path)
    if not report_path.exists() or not report_path.is_file():
        mismatches.append("report_missing")
        details["resolved_report_path"] = str(report_path)
    elif _sha256_file(report_path) != report_hash:
        mismatches.append("report_hash")
        details["expected_report_hash"] = report_hash
        details["actual_report_hash"] = _sha256_file(report_path)

    mismatches.extend(
        _validate_optional_artifact_block(
            "intent",
            intent_block,
            details=details,
            expected_path=expected_optional_paths.get("intent"),
        ),
    )
    mismatches.extend(
        _validate_optional_artifact_block(
            "plan",
            plan_block,
            details=details,
            expected_path=expected_optional_paths.get("plan"),
        ),
    )
    mismatches.extend(
        _validate_optional_artifact_block(
            "events_jsonl",
            events_block.get("events_jsonl"),
            details=details,
            expected_path=expected_optional_paths.get("events_jsonl"),
        ),
    )
    mismatches.extend(
        _validate_optional_artifact_block(
            "trace_ndjson",
            events_block.get("trace_ndjson"),
            details=details,
            expected_path=expected_optional_paths.get("trace_ndjson"),
        ),
    )

    if mismatches:
        raise RunManifestIntegrityError(mismatches, details=details)

    return payload.model_dump(mode="json")


def build_run_manifest(
    *,
    workspace_root: Path,
    revision: str,
    report_payload: dict[str, Any],
    qspec: QSpec,
    qspec_path: Path,
    report_path: Path,
    intent_path: Path | None = None,
    plan_path: Path | None = None,
    event_history_path: Path | None = None,
    trace_history_path: Path | None = None,
) -> RunManifestArtifact:
    """Build an immutable run manifest from report + qspec truth."""
    paths = WorkspacePaths(root=workspace_root)
    semantics = summarize_qspec_semantics(qspec)
    report_block = report_payload.get("qspec") if isinstance(report_payload, dict) else {}
    artifact_paths = report_payload.get("artifacts") if isinstance(report_payload, dict) else {}
    provenance = report_payload.get("provenance") if isinstance(report_payload, dict) else {}
    diagnostics = report_payload.get("diagnostics") if isinstance(report_payload, dict) else {}
    simulation = diagnostics.get("simulation") if isinstance(diagnostics, dict) else {}
    exports = diagnostics.get("exports") if isinstance(diagnostics, dict) else {}
    resolved_intent_path = intent_path if intent_path is not None else paths.intent_history_json(revision)
    resolved_plan_path = plan_path if plan_path is not None else paths.plan_history_json(revision)
    resolved_event_history_path = (
        event_history_path if event_history_path is not None else paths.event_history_jsonl(revision)
    )
    resolved_trace_history_path = (
        trace_history_path if trace_history_path is not None else paths.trace_history_ndjson(revision)
    )

    return RunManifestArtifact(
        status=str(report_payload.get("status", "unknown")),
        revision=revision,
        input=dict(report_payload.get("input", {}) or {}),
        intent=_manifest_artifact_entry(resolved_intent_path),
        plan=_manifest_artifact_entry(resolved_plan_path),
        events=_manifest_event_entries(
            event_history_path=resolved_event_history_path,
            trace_history_path=resolved_trace_history_path,
        ),
        qspec={
            "path": str(qspec_path),
            "hash": _sha256_file(qspec_path),
            "semantic_hash": _string_or_default(report_block.get("semantic_hash"), semantics["semantic_hash"]),
            "workload_hash": semantics["workload_hash"],
            "execution_hash": semantics["execution_hash"],
            "pattern": semantics["pattern"],
        },
        report={
            "path": str(report_path),
            "hash": _sha256_file(report_path),
            "status": report_payload.get("status"),
        },
        representative_point=_representative_point(simulation=simulation, exports=exports),
        artifacts=_artifact_manifest_entries(artifact_paths),
        provenance={
            "workspace_root": str(workspace_root),
            "report_provenance": provenance,
        },
    )


def synthesize_run_manifest(
    *,
    workspace_root: Path,
    revision: str,
    report_payload: dict[str, Any],
    qspec: QSpec,
    qspec_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    """Return a manifest-shaped payload even for pre-manifest workspaces."""
    return build_run_manifest(
        workspace_root=workspace_root,
        revision=revision,
        report_payload=report_payload,
        qspec=qspec,
        qspec_path=qspec_path,
        report_path=report_path,
    ).model_dump(mode="json")


def _artifact_manifest_entries(raw_artifacts: object) -> dict[str, dict[str, Any]]:
    if not isinstance(raw_artifacts, dict):
        return {}

    payload: dict[str, dict[str, Any]] = {}
    for name, raw_path in sorted(raw_artifacts.items()):
        if name in {"qspec", "report", "manifest"}:
            continue
        if not isinstance(raw_path, str):
            continue
        path = Path(raw_path)
        payload[str(name)] = {
            "path": raw_path,
            "hash": _sha256_file(path) if path.exists() and path.is_file() else None,
        }
    return payload


def _manifest_artifact_entry(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    return {
        "path": str(path),
        "hash": _sha256_file(path),
    }


def _manifest_event_entries(*, event_history_path: Path, trace_history_path: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    event_entry = _manifest_artifact_entry(event_history_path)
    if event_entry:
        payload["events_jsonl"] = event_entry
    trace_entry = _manifest_artifact_entry(trace_history_path)
    if trace_entry:
        payload["trace_ndjson"] = trace_entry
    return payload


def _validate_optional_artifact_block(
    label: str,
    block: object,
    *,
    details: dict[str, Any],
    expected_path: Path | None = None,
) -> list[str]:
    if not isinstance(block, dict) or not block:
        return []

    path_value = block.get("path")
    hash_value = block.get("hash")
    if not isinstance(path_value, str) or not isinstance(hash_value, str):
        details[f"{label}_block"] = block
        return [f"{label}_invalid"]

    path = Path(path_value).resolve()
    resolved_expected_path = expected_path.resolve() if expected_path is not None else None
    if resolved_expected_path is not None and path != resolved_expected_path:
        details[f"expected_{label}_path"] = str(resolved_expected_path)
        details[f"actual_{label}_path"] = str(path)
        return [f"{label}_path"]

    if not path.exists() or not path.is_file():
        details[f"{label}_path"] = str(path)
        return [f"{label}_missing"]

    actual_hash = _sha256_file(path)
    if actual_hash != hash_value:
        details[f"{label}_expected_hash"] = hash_value
        details[f"{label}_actual_hash"] = actual_hash
        return [f"{label}_hash"]

    return []


def _representative_point(*, simulation: object, exports: object) -> dict[str, Any] | None:
    if not isinstance(simulation, dict) and not isinstance(exports, dict):
        return None

    simulation_mapping = simulation if isinstance(simulation, dict) else {}
    exports_mapping = exports if isinstance(exports, dict) else {}
    bindings = _float_mapping(exports_mapping.get("bindings")) or _float_mapping(
        simulation_mapping.get("representative_bindings")
    )
    payload = {
        "label": exports_mapping.get("point_label") or simulation_mapping.get("representative_point_label"),
        "parameter_mode": exports_mapping.get("parameter_mode") or simulation_mapping.get("parameter_mode"),
        "bindings": bindings,
        "bindings_hash": _hash_payload(bindings),
    }
    if payload["label"] is None and payload["parameter_mode"] is None and not payload["bindings"]:
        return None
    return payload


def _float_mapping(value: object) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    payload: dict[str, float] = {}
    for key, raw in value.items():
        try:
            payload[str(key)] = float(raw)
        except (TypeError, ValueError):
            continue
    return payload


def _hash_payload(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _string_or_default(value: object, default: str) -> str:
    if value is None:
        return default
    return str(value)


def _expected_optional_artifact_paths(
    *,
    revision: str,
    workspace_paths: WorkspacePaths | None,
) -> dict[str, Path]:
    if workspace_paths is None:
        return {}

    return {
        "intent": workspace_paths.intent_history_json(revision).resolve(),
        "plan": workspace_paths.plan_history_json(revision).resolve(),
        "events_jsonl": workspace_paths.event_history_jsonl(revision).resolve(),
        "trace_ndjson": workspace_paths.trace_history_ndjson(revision).resolve(),
    }


def _resolve_workspace_paths(
    *,
    manifest_path: Path,
    expected_revision: str,
    expected_qspec_path: Path,
    expected_report_path: Path,
    workspace_root: Path | None,
) -> WorkspacePaths | None:
    if workspace_root is not None:
        return WorkspacePaths(root=workspace_root)

    inferred_root = (
        _workspace_root_from_history_path(
            expected_qspec_path,
            top_level_dir="specs",
            expected_revision=expected_revision,
        )
        or _workspace_root_from_history_path(
            expected_report_path,
            top_level_dir="reports",
            expected_revision=expected_revision,
        )
        or _workspace_root_from_history_path(
            manifest_path.resolve(),
            top_level_dir="manifests",
            expected_revision=expected_revision,
        )
    )
    if inferred_root is None:
        return None
    return WorkspacePaths(root=inferred_root)


def _workspace_root_from_history_path(
    path: Path,
    *,
    top_level_dir: str,
    expected_revision: str,
) -> Path | None:
    resolved_path = path.resolve()
    if resolved_path.stem != expected_revision:
        return None
    if resolved_path.parent.name != "history":
        return None
    if resolved_path.parent.parent.name != top_level_dir:
        return None
    return resolved_path.parent.parent.parent
