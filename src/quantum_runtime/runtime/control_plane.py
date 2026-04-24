"""Agent-first runtime control-plane helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import ConfigDict, Field, ValidationError

from quantum_runtime.qspec import (
    QSpec,
    summarize_qspec_semantics,
)
from quantum_runtime.runtime.compare import compare_import_resolutions
from quantum_runtime.runtime.contracts import SCHEMA_VERSION, SchemaPayload
from quantum_runtime.runtime.doctor import collect_backend_capabilities
from quantum_runtime.runtime.resolve import IntentResolution, ResolveResult, resolve_runtime_input
from quantum_runtime.runtime.observability import (
    decision_block,
    next_actions_for_reason_codes,
    normalize_reason_codes,
)
from quantum_runtime.runtime.imports import (
    ImportReference,
    ImportResolution,
    ImportSourceError,
    resolve_import_reference,
    resolve_workspace_baseline,
)
from quantum_runtime.runtime.run_manifest import (
    RunManifestArtifact,
    RunManifestIntegrityError,
    RunReportArtifact,
    parse_and_validate_run_manifest,
    synthesize_run_manifest,
)
from quantum_runtime.workspace import WorkspaceManifest, WorkspacePaths


class PlanResult(SchemaPayload):
    """Dry-run execution plan for one runtime input."""

    status: Literal["ok", "degraded", "error"]
    workspace: str
    input: dict[str, Any] = Field(default_factory=dict)
    qspec: dict[str, Any] = Field(default_factory=dict)
    execution: dict[str, Any] = Field(default_factory=dict)
    artifacts_expected: list[str] = Field(default_factory=list)
    policy: dict[str, Any] = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    advisories: list[str] = Field(default_factory=list)


class StatusResult(SchemaPayload):
    """Thin workspace status view for agents and CI."""

    status: Literal["ok", "degraded", "error"]
    workspace: dict[str, Any] = Field(default_factory=dict)
    current_revision: str | None = None
    active: dict[str, Any] = Field(default_factory=dict)
    latest_run_status: str | None = None
    baseline: dict[str, Any] = Field(default_factory=dict)
    health: dict[str, Any] = Field(default_factory=dict)
    reason_codes: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    decision: dict[str, Any] = Field(default_factory=dict)
    degraded: bool = False
    issues: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ShowResult(SchemaPayload):
    """Resolved run view for one selected revision."""

    status: Literal["ok", "degraded", "error"]
    revision: str
    selected: dict[str, Any] = Field(default_factory=dict)
    manifest: dict[str, Any] = Field(default_factory=dict)
    report_summary: dict[str, Any] = Field(default_factory=dict)
    qspec_summary: dict[str, Any] = Field(default_factory=dict)
    baseline_relation: dict[str, Any] = Field(default_factory=dict)
    health: dict[str, Any] = Field(default_factory=dict)
    reason_codes: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    decision: dict[str, Any] = Field(default_factory=dict)


class SchemaResult(SchemaPayload):
    """JSON Schema descriptor for one runtime contract."""

    model_config = ConfigDict(populate_by_name=True)

    status: Literal["ok"] = "ok"
    name: str
    schema_document: dict[str, Any] = Field(
        default_factory=dict,
        alias="schema",
        serialization_alias="schema",
    )


def build_execution_plan(
    *,
    workspace_root: Path,
    intent_file: Path | None = None,
    intent_json_file: Path | None = None,
    qspec_file: Path | None = None,
    report_file: Path | None = None,
    revision: str | None = None,
    intent_text: str | None = None,
) -> PlanResult:
    """Build a dry-run execution plan without mutating workspace state."""
    resolved = resolve_runtime_input(
        workspace_root=workspace_root,
        intent_file=intent_file,
        intent_json_file=intent_json_file,
        qspec_file=qspec_file,
        report_file=report_file,
        revision=revision,
        intent_text=intent_text,
    )
    return build_execution_plan_from_resolved(workspace_root=workspace_root, resolved=resolved)


def build_execution_plan_from_resolved(
    *,
    workspace_root: Path,
    resolved: Any,
) -> PlanResult:
    """Build a dry-run execution plan from an already normalized input."""
    qspec = resolved.qspec
    input_data = resolved.input_data
    requested_exports = resolved.requested_exports

    semantics = _plan_qspec_summary(qspec)
    selected_backends = _default_benchmark_backends(qspec)
    capabilities = collect_backend_capabilities()
    blockers, advisories = _backend_findings(capabilities=capabilities, required_backends=set(selected_backends))
    baseline = _baseline_summary(WorkspacePaths(root=workspace_root))
    baseline_is_invalid = baseline.get("status") == "degraded"
    if baseline_is_invalid and baseline.get("reason") is not None:
        advisories.append(f"baseline_invalid:{baseline['reason']}")

    return PlanResult(
        status="degraded" if blockers or baseline_is_invalid else "ok",
        workspace=str(workspace_root.resolve()),
        input=input_data,
        qspec=semantics,
        execution={
            "requested_exports": requested_exports,
            "selected_backends": selected_backends,
            "backend_preferences": list(qspec.backend_preferences),
        },
        artifacts_expected=_artifacts_expected(requested_exports),
        policy={
            "baseline_configured": baseline["configured"],
            "compare_ready": baseline["compare_ready"],
        },
        blockers=blockers,
        advisories=advisories,
    )


def resolve_runtime_object(
    *,
    workspace_root: Path,
    intent_file: Path | None = None,
    intent_json_file: Path | None = None,
    qspec_file: Path | None = None,
    report_file: Path | None = None,
    revision: str | None = None,
    intent_text: str | None = None,
) -> ResolveResult:
    """Resolve one ingress input into canonical intent, qspec, and plan payloads."""
    resolved = resolve_runtime_input(
        workspace_root=workspace_root,
        intent_file=intent_file,
        intent_json_file=intent_json_file,
        qspec_file=qspec_file,
        report_file=report_file,
        revision=revision,
        intent_text=intent_text,
    )
    plan = build_execution_plan_from_resolved(workspace_root=workspace_root, resolved=resolved)
    semantics = summarize_qspec_semantics(resolved.qspec)
    return ResolveResult(
        status=plan.status,
        workspace=str(workspace_root.resolve()),
        input=resolved.input_data,
        intent=resolved.intent_resolution.model_dump(mode="json"),
        qspec=_plan_qspec_summary(resolved.qspec) | {
            "semantic_hash": semantics["semantic_hash"],
            "workload_id": semantics["workload_id"],
            "algorithm_family": semantics["algorithm_family"],
        },
        plan=plan.model_dump(mode="json"),
    )


def workspace_status(*, workspace_root: Path) -> StatusResult:
    """Return a thin, machine-readable workspace status summary."""
    paths = WorkspacePaths(root=workspace_root)
    issues: list[str] = []
    errors: list[str] = []

    workspace_exists = paths.root.exists()
    manifest: WorkspaceManifest | None = None
    if paths.workspace_json.exists():
        try:
            manifest = WorkspaceManifest.load(paths.workspace_json)
        except Exception:
            errors.append("workspace_manifest_invalid")
    elif workspace_exists:
        issues.append("workspace_manifest_missing")

    initialized = manifest is not None
    current_revision = manifest.current_revision if manifest is not None else None
    active_qspec_path = paths.root / manifest.active_spec if manifest is not None else paths.root / "specs" / "current.json"
    active_report_path = paths.root / manifest.active_report if manifest is not None else paths.root / "reports" / "latest.json"
    active_manifest_path = paths.manifests_latest_json
    current_manifest_history_path = None
    if current_revision not in (None, "rev_000000"):
        assert current_revision is not None
        current_manifest_history_path = paths.manifest_history_json(current_revision)
    qspec_health = _qspec_file_status(active_qspec_path)
    report_health = _report_file_status(active_report_path)

    latest_run_status = report_health.get("run_status")
    if initialized and current_revision not in (None, "rev_000000"):
        assert current_revision is not None
        expected_qspec_history_path = paths.root / "specs" / "history" / f"{current_revision}.json"
        expected_report_history_path = paths.root / "reports" / "history" / f"{current_revision}.json"
        if qspec_health["status"] == "missing":
            issues.append("active_qspec_missing")
        elif qspec_health["status"] == "invalid":
            errors.append("active_qspec_invalid")
        if report_health["status"] == "missing":
            issues.append("active_report_missing")
        elif report_health["status"] == "invalid":
            errors.append("active_report_invalid")
        manifest_status = _manifest_file_status(
            active_manifest_path,
            expected_revision=current_revision,
            expected_qspec_path=expected_qspec_history_path,
            expected_report_path=expected_report_history_path,
        )
        if manifest_status == "missing":
            issues.append("active_manifest_missing")
        elif manifest_status == "invalid":
            errors.append("active_manifest_invalid")
        elif manifest_status == "integrity_invalid":
            errors.append("active_manifest_integrity_invalid")
        if current_manifest_history_path is not None:
            history_manifest_status = _manifest_file_status(
                current_manifest_history_path,
                expected_revision=current_revision,
                expected_qspec_path=expected_qspec_history_path,
                expected_report_path=expected_report_history_path,
            )
            if history_manifest_status == "missing":
                issues.append("current_manifest_history_missing")
            elif history_manifest_status == "invalid":
                errors.append("current_manifest_history_invalid")
            elif history_manifest_status == "integrity_invalid":
                errors.append("current_manifest_history_integrity_invalid")
    if latest_run_status == "degraded":
        issues.append("latest_run_degraded")
    elif latest_run_status == "error":
        errors.append("latest_run_error")

    baseline = _baseline_summary(paths)
    if baseline.get("status") == "degraded" and baseline.get("reason") is not None:
        issues.append(f"baseline_invalid:{baseline['reason']}")
    degraded = bool(issues or latest_run_status == "degraded")
    status: Literal["ok", "degraded", "error"]
    if errors:
        status = "error"
    elif not workspace_exists or degraded or not initialized:
        status = "degraded"
    else:
        status = "ok"
    reason_codes = _status_reason_codes(
        workspace_exists=workspace_exists,
        initialized=initialized,
        issues=issues,
        errors=errors,
    )
    next_actions = next_actions_for_reason_codes(reason_codes)
    health = {
        "workspace": {
            "status": "missing" if not workspace_exists else "initialized" if initialized else "degraded",
        },
        "artifacts": {
            "qspec": {"status": qspec_health["status"]},
            "report": {"status": report_health["status"]},
            "manifest": {"status": _active_manifest_status_from_codes(issues=issues, errors=errors)},
        },
        "baseline": {
            "status": _baseline_health_status(baseline),
        },
    }

    return StatusResult(
        status=status,
        workspace={
            "root": str(paths.root),
            "exists": workspace_exists,
            "initialized": initialized,
            "manifest_path": str(paths.workspace_json),
        },
        current_revision=current_revision,
        active={
            "qspec": qspec_health,
            "report": report_health,
            "manifest": {
                "path": str(active_manifest_path),
                "exists": active_manifest_path.exists(),
                "status": _active_manifest_status_from_codes(issues=issues, errors=errors),
            },
        },
        latest_run_status=latest_run_status,
        baseline=baseline,
        health=health,
        reason_codes=reason_codes,
        next_actions=next_actions,
        decision=decision_block(
            status=status,
            reason_codes=reason_codes,
            next_actions=next_actions,
            ready_when_ok=False if "workspace_not_initialized" in reason_codes else True,
        ),
        degraded=degraded or status != "ok",
        issues=issues,
        errors=errors,
    )


def show_run(*, workspace_root: Path, revision: str | None = None) -> ShowResult:
    """Return one resolved run plus baseline relation metadata."""
    reference = (
        ImportReference(workspace_root=workspace_root, revision=revision)
        if revision is not None
        else ImportReference(workspace_root=workspace_root)
    )
    resolution = resolve_import_reference(reference)
    report_payload = resolution.load_report()
    qspec = resolution.load_qspec()
    manifest_path = WorkspacePaths(root=resolution.workspace_root).manifest_history_json(resolution.revision)
    expected_qspec_path = _canonical_history_path(
        report_summary=resolution.report_summary,
        artifact_name="qspec",
        fallback=resolution.qspec_path,
    )
    expected_report_path = _canonical_history_path(
        report_summary=resolution.report_summary,
        artifact_name="report",
        fallback=resolution.report_path,
    )
    manifest_payload = _strict_run_manifest_payload(
        manifest_path,
        expected_revision=resolution.revision,
        expected_qspec_path=expected_qspec_path,
        expected_report_path=expected_report_path,
    )
    if manifest_payload is None:
        if not _is_legacy_report_payload(report_payload):
            raise ImportSourceError(
                "run_manifest_missing",
                source=str(manifest_path),
                details={"revision": resolution.revision},
            )
        manifest_payload = synthesize_run_manifest(
            workspace_root=resolution.workspace_root,
            revision=resolution.revision,
            report_payload=report_payload,
            qspec=qspec,
            qspec_path=expected_qspec_path,
            report_path=expected_report_path,
        )

    baseline_relation = _baseline_relation(workspace_root=resolution.workspace_root, resolution=resolution)
    reason_codes = _show_reason_codes(baseline_relation=baseline_relation)
    next_actions = next_actions_for_reason_codes(reason_codes)
    health = {
        "run": {"status": "ok"},
        "baseline": {"status": _show_baseline_health_status(baseline_relation)},
        "replay": {"status": "ok"},
    }

    return ShowResult(
        status="ok",
        revision=resolution.revision,
        selected={
            "source_kind": resolution.source_kind,
            "source": resolution.source,
            "report_path": str(resolution.report_path),
            "qspec_path": str(resolution.qspec_path),
            "manifest_path": str(manifest_path),
        },
        manifest=manifest_payload,
        report_summary=resolution.report_summary,
        qspec_summary=resolution.qspec_summary,
        baseline_relation=baseline_relation,
        health=health,
        reason_codes=reason_codes,
        next_actions=next_actions,
        decision=decision_block(
            status="ok",
            reason_codes=reason_codes,
            next_actions=next_actions,
        ),
    )


def schema_contract(name: str) -> SchemaResult:
    """Return a JSON Schema envelope for one public runtime contract."""
    registry = {
        "intent": IntentResolution,
        "qspec": QSpec,
        "report": RunReportArtifact,
        "manifest": RunManifestArtifact,
        "compare": __import__("quantum_runtime.runtime.compare", fromlist=["CompareResult"]).CompareResult,
        "plan": PlanResult,
        "resolve": ResolveResult,
        "status": StatusResult,
    }
    if name not in registry:
        raise ValueError(f"unsupported_schema:{name}")

    model = registry[name]
    schema = model.model_json_schema() if hasattr(model, "model_json_schema") else {}
    properties = schema.setdefault("properties", {})
    properties.setdefault(
        "schema_version",
        {
            "default": SCHEMA_VERSION,
            "title": "Schema Version",
            "type": "string",
        },
    )
    return SchemaResult(name=name, schema=schema)

def _default_benchmark_backends(qspec: QSpec) -> list[str]:
    resolved = ["qiskit-local"]
    requested = [str(name) for name in qspec.backend_preferences if name]

    if qspec.constraints.backend_provider == "classiq":
        requested.append("classiq")
    if qspec.constraints.backend_provider == "qiskit":
        requested.append("qiskit-local")
    if qspec.constraints.backend_name in {"classiq", "qiskit-local"}:
        requested.append(str(qspec.constraints.backend_name))

    for backend in requested:
        if backend not in resolved:
            resolved.append(backend)
    return resolved


def _backend_findings(
    *,
    capabilities: dict[str, dict[str, Any]],
    required_backends: set[str],
) -> tuple[list[str], list[str]]:
    known_backends = {name for name in capabilities if name}
    blockers: list[str] = [
        f"unknown backend requested: {backend}"
        for backend in sorted(required_backends - known_backends)
    ]
    advisories: list[str] = []
    for name, details in capabilities.items():
        if details.get("available"):
            continue
        message = f"{name} unavailable: {details.get('reason') or details.get('error') or 'backend_unavailable'}"
        if name in required_backends or not bool(details.get("optional")):
            blockers.append(message)
        else:
            advisories.append(message)
    return blockers, advisories


def _artifacts_expected(requested_exports: list[str]) -> list[str]:
    artifacts = ["qspec", "report", "manifest", "diagram_txt", "diagram_png"]
    if "qiskit" in requested_exports:
        artifacts.append("qiskit_code")
    if "qasm3" in requested_exports:
        artifacts.append("qasm3")
    if "classiq-python" in requested_exports:
        artifacts.append("classiq_code")
    return artifacts


def _plan_qspec_summary(qspec: QSpec) -> dict[str, Any]:
    semantics = summarize_qspec_semantics(qspec)
    return {
        "pattern": semantics["pattern"],
        "workload_id": semantics["workload_id"],
        "algorithm_family": semantics["algorithm_family"],
        "workload_hash": semantics["workload_hash"],
        "execution_hash": semantics["execution_hash"],
        "semantic_hash": semantics["semantic_hash"],
        "parameter_workflow_mode": semantics["parameter_workflow_mode"],
        "parameter_workflow": semantics["parameter_workflow"],
        "width": semantics["width"],
        "layers": semantics["layers"],
        "observable_count": semantics["observable_count"],
        "parameter_count": semantics["parameter_count"],
    }


def _baseline_summary(paths: WorkspacePaths) -> dict[str, Any]:
    baseline_path = paths.baseline_current_json
    if not baseline_path.exists():
        return {
            "configured": False,
            "path": str(baseline_path),
            "revision": None,
            "compare_ready": False,
        }
    try:
        baseline = resolve_workspace_baseline(paths.root)
    except ImportSourceError as exc:
        return {
            "configured": True,
            "path": str(baseline_path),
            "revision": None,
            "status": "degraded",
            "reason": exc.code,
            "compare_ready": False,
        }
    return {
        "configured": True,
        "path": str(baseline_path),
        "revision": baseline.record.revision,
        "compare_ready": True,
    }


def _load_report_status(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    raw_status = payload.get("status")
    return None if raw_status is None else str(raw_status)


def _qspec_file_status(path: Path) -> dict[str, Any]:
    payload = {"path": str(path), "exists": path.exists(), "status": "missing" if not path.exists() else "ok"}
    if not path.exists():
        return payload
    try:
        QSpec.model_validate_json(path.read_text())
    except (ValidationError, json.JSONDecodeError, ValueError):
        payload["status"] = "invalid"
    return payload


def _report_file_status(path: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "status": "missing" if not path.exists() else "ok",
        "run_status": None,
    }
    if not path.exists():
        return payload
    try:
        raw = json.loads(path.read_text())
    except (json.JSONDecodeError, ValueError):
        payload["status"] = "invalid"
        return payload
    if not isinstance(raw, dict):
        payload["status"] = "invalid"
        return payload
    run_status = raw.get("status")
    payload["run_status"] = None if run_status is None else str(run_status)
    return payload


def _manifest_file_status(
    path: Path,
    *,
    expected_revision: str,
    expected_qspec_path: Path,
    expected_report_path: Path,
) -> Literal["ok", "missing", "invalid", "integrity_invalid"]:
    if not path.exists():
        return "missing"
    try:
        parse_and_validate_run_manifest(
            path=path,
            expected_revision=expected_revision,
            expected_qspec_path=expected_qspec_path,
            expected_report_path=expected_report_path,
        )
    except RunManifestIntegrityError:
        return "integrity_invalid"
    except (ValidationError, json.JSONDecodeError, ValueError):
        return "invalid"
    return "ok"


def _strict_run_manifest_payload(
    path: Path,
    *,
    expected_revision: str,
    expected_qspec_path: Path,
    expected_report_path: Path,
) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return parse_and_validate_run_manifest(
            path=path,
            expected_revision=expected_revision,
            expected_qspec_path=expected_qspec_path,
            expected_report_path=expected_report_path,
        )
    except RunManifestIntegrityError as exc:
        raise ImportSourceError(
            "run_manifest_integrity_invalid",
            source=str(path),
            details=exc.details or {"mismatches": exc.mismatches},
        ) from exc
    except (ValidationError, json.JSONDecodeError, ValueError) as exc:
        raise ImportSourceError(
            "run_manifest_invalid",
            source=str(path),
            details={"error": str(exc)},
        ) from exc


def _is_legacy_report_payload(report_payload: dict[str, Any]) -> bool:
    replay_integrity = report_payload.get("replay_integrity")
    if not isinstance(replay_integrity, dict):
        return True
    artifact_output_digests = replay_integrity.get("artifact_output_digests")
    if not isinstance(artifact_output_digests, dict):
        return True
    return not any(
        isinstance(expected_digest, str) and expected_digest.strip()
        for expected_digest in artifact_output_digests.values()
    )


def _canonical_history_path(
    *,
    report_summary: dict[str, Any],
    artifact_name: str,
    fallback: Path,
) -> Path:
    artifact_paths = report_summary.get("artifact_paths") if isinstance(report_summary, dict) else None
    if isinstance(artifact_paths, dict):
        raw_path = artifact_paths.get(artifact_name)
        if isinstance(raw_path, str) and raw_path.strip():
            return Path(raw_path)
    return fallback


def _baseline_relation(*, workspace_root: Path, resolution: ImportResolution) -> dict[str, Any]:
    paths = WorkspacePaths(root=workspace_root)
    if not paths.baseline_current_json.exists():
        return {"configured": False}
    try:
        baseline = resolve_workspace_baseline(workspace_root)
    except ImportSourceError as exc:
        return {
            "configured": True,
            "status": "baseline_invalid",
            "error_code": exc.code,
        }

    compare_result = compare_import_resolutions(baseline.resolution, resolution)
    return {
        "configured": True,
        "baseline_revision": baseline.record.revision,
        "matches_baseline": compare_result.same_report,
        "same_subject": compare_result.same_subject,
        "same_qspec": compare_result.same_qspec,
        "same_report": compare_result.same_report,
    }


def _status_reason_codes(
    *,
    workspace_exists: bool,
    initialized: bool,
    issues: list[str],
    errors: list[str],
) -> list[str]:
    codes: list[str] = []
    if not workspace_exists or not initialized:
        codes.append("workspace_not_initialized")
    codes.extend(errors)
    codes.extend(issues)
    return normalize_reason_codes(codes)


def _active_manifest_status_from_codes(*, issues: list[str], errors: list[str]) -> str:
    if any(code.startswith("active_manifest_") for code in errors):
        return "invalid"
    if any(code.startswith("active_manifest_") for code in issues):
        return "missing"
    return "ok"


def _baseline_health_status(baseline: dict[str, Any]) -> str:
    if not baseline.get("configured"):
        return "not_configured"
    raw_status = baseline.get("status")
    if isinstance(raw_status, str) and raw_status:
        return raw_status
    return "ok"


def _show_reason_codes(*, baseline_relation: dict[str, Any]) -> list[str]:
    if not baseline_relation.get("configured"):
        return ["baseline_not_configured"]
    if baseline_relation.get("status") == "baseline_invalid":
        return [f"baseline_invalid:{baseline_relation.get('error_code', 'unknown')}"]
    if baseline_relation.get("matches_baseline") is False:
        return ["baseline_not_configured"] if baseline_relation.get("baseline_revision") is None else ["baseline_drifted"]
    return []


def _show_baseline_health_status(baseline_relation: dict[str, Any]) -> str:
    if not baseline_relation.get("configured"):
        return "not_configured"
    if baseline_relation.get("status") == "baseline_invalid":
        return "degraded"
    if baseline_relation.get("matches_baseline") is True:
        return "ok"
    return "degraded"
