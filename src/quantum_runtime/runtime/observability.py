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
    workspace: str
    status: str
    revision: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


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
