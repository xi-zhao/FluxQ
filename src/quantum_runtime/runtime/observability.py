"""Shared observability contracts for agent-facing CLI output."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from quantum_runtime.runtime.contracts import SCHEMA_VERSION


DecisionSeverity = Literal["info", "warning", "error"]


class JsonlEvent(BaseModel):
    """One machine-readable event emitted by long-running commands."""

    schema_version: str = SCHEMA_VERSION
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    event_type: str
    phase: str
    workspace: str
    status: str
    revision: str | None = None
    error_code: str | None = None
    remediation: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


def phase_for_event_type(event_type: str) -> str:
    """Map a machine event type into a stable phase label."""
    if event_type in {"run_started", "input_resolved", "qspec_prepared", "intent_written", "plan_written"}:
        return "resolve"
    if event_type in {"artifact_written", "report_written", "manifest_written", "run_completed"}:
        return "execute"
    if event_type in {"compare_started", "left_resolved", "right_resolved", "compare_completed"}:
        return "compare"
    if event_type in {"benchmark_started", "benchmark_completed"} or event_type.startswith("backend_"):
        return "benchmark"
    if event_type in {"doctor_started", "workspace_checked", "dependency_checked", "dependencies_checked", "doctor_written", "doctor_completed"}:
        return "doctor"
    if event_type in {"pack_started", "pack_artifact_copied", "pack_completed"}:
        return "pack"
    return "runtime"


def normalize_reason_codes(raw_items: list[str]) -> list[str]:
    """Return stable, de-duplicated reason codes while preserving order."""
    result: list[str] = []
    seen: set[str] = set()
    for raw_item in raw_items:
        item = str(raw_item).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def next_actions_for_reason_codes(reason_codes: list[str]) -> list[str]:
    """Map machine reason codes to short executable next-action hints."""
    actions: list[str] = []
    for code in reason_codes:
        if code in {
            "workspace_not_initialized",
            "active_qspec_missing",
            "active_qspec_invalid",
            "active_report_missing",
            "active_report_invalid",
        }:
            actions.append("run_exec")
        elif code in {
            "active_manifest_missing",
            "active_manifest_invalid",
            "active_manifest_integrity_invalid",
            "current_manifest_history_invalid",
            "current_manifest_history_integrity_invalid",
            "run_manifest_invalid",
            "run_manifest_integrity_invalid",
        }:
            actions.append("run_exec")
        elif code.startswith("baseline_invalid") or code == "baseline_not_configured":
            actions.append("set_baseline")
        elif code.startswith("semantic_subject_changed") or code.startswith("compare_difference"):
            actions.append("review_compare")
        elif code.startswith("replay_") or code.startswith("artifact_outputs_"):
            actions.append("run_exec")
        elif code == "bundle_manifest_missing" or code == "bundle_revision_mismatch":
            actions.append("reject_bundle")
        elif code.startswith("bundle_required_missing") or code.startswith("bundle_digest_mismatch"):
            actions.append("reject_bundle")
        elif code == "ibm_profile_missing" or code == "ibm_instance_unset" or code == "ibm_access_unresolved":
            actions.append("configure_ibm_profile")
        elif code == "ibm_token_env_missing":
            actions.append("set_ibm_token_env")
        elif code == "ibm_saved_account_missing":
            actions.append("verify_ibm_saved_account")
        elif code == "ibm_runtime_dependency_missing":
            actions.append("install_ibm_extra")
        elif code.endswith("_dependency_missing") or code.endswith("_backend_unavailable"):
            actions.append("run_doctor")
    return normalize_reason_codes(actions)


def decision_block(
    *,
    status: str,
    reason_codes: list[str],
    next_actions: list[str],
    ready_when_ok: bool = True,
) -> dict[str, Any]:
    """Build a thin machine decision summary from control-plane state."""
    severity: DecisionSeverity
    if status == "error":
        severity = "error"
    elif status == "degraded":
        severity = "warning"
    else:
        severity = "info"

    ready = ready_when_ok and status == "ok"
    recommended_action = next_actions[0] if next_actions else None
    return {
        "ready": ready,
        "severity": severity,
        "reason_codes": reason_codes,
        "recommended_action": recommended_action,
    }


def gate_block(
    *,
    ready: bool,
    severity: DecisionSeverity,
    reason_codes: list[str],
    next_actions: list[str],
) -> dict[str, Any]:
    """Build a compare/CI gate summary."""
    return {
        "ready": ready,
        "severity": severity,
        "reason_codes": reason_codes,
        "recommended_action": next_actions[0] if next_actions else None,
    }


def workspace_conflict_observability() -> dict[str, Any]:
    """Build machine-readable guidance for a held workspace lease."""
    reason_codes = ["workspace_conflict"]
    next_actions = ["retry_when_workspace_free", "inspect_workspace_lock"]
    return {
        "reason_codes": reason_codes,
        "next_actions": next_actions,
        "gate": gate_block(
            ready=False,
            severity="warning",
            reason_codes=reason_codes,
            next_actions=next_actions,
        ),
    }


def workspace_recovery_required_observability() -> dict[str, Any]:
    """Build machine-readable guidance for interrupted-write recovery."""
    reason_codes = ["workspace_recovery_required"]
    next_actions = ["run_doctor_fix", "review_workspace_recovery"]
    return {
        "reason_codes": reason_codes,
        "next_actions": next_actions,
        "gate": gate_block(
            ready=False,
            severity="error",
            reason_codes=reason_codes,
            next_actions=next_actions,
        ),
    }


def workspace_alias_mismatch_observability() -> dict[str, Any]:
    """Build machine-readable guidance for mixed authoritative alias state."""
    reason_codes = ["workspace_recovery_required", "workspace_alias_mismatch"]
    next_actions = ["review_alias_paths", "restore_active_aliases"]
    return {
        "reason_codes": reason_codes,
        "next_actions": next_actions,
        "gate": gate_block(
            ready=False,
            severity="error",
            reason_codes=reason_codes,
            next_actions=next_actions,
        ),
    }
