"""Shared machine-readable runtime contracts."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field


SCHEMA_VERSION = "0.3.0"

DEFAULT_REMEDIATION = (
    "Inspect the error_code and details fields, then correct the input, workspace state, or runtime dependencies."
)

REMEDIATIONS: dict[str, str] = {
    "missing_qspec": "Run `qrun exec` first or point the command at a valid QSpec or report input.",
    "baseline_missing": "Persist a baseline with `qrun baseline set` before requesting baseline-backed operations.",
    "expected_exactly_one_input": "Provide exactly one supported input selector for the command.",
    "workspace_manifest_missing": "Initialize the workspace with `qrun init` or point the command at an existing workspace.",
    "workspace_root_required_for_revision": "Pass `--workspace` when resolving a historical revision.",
    "workspace_root_required_for_report_file": "Pass `--workspace` or use a report file that still carries recoverable workspace provenance.",
}


class SchemaPayload(BaseModel):
    """Base payload for runtime machine-readable responses."""

    schema_version: str = SCHEMA_VERSION


class ErrorPayload(SchemaPayload):
    """Structured machine-readable error payload."""

    status: Literal["error"] = "error"
    reason: str
    error_code: str
    remediation: str = DEFAULT_REMEDIATION
    details: dict[str, Any] = Field(default_factory=dict)


def remediation_for_error(error_code: str) -> str:
    """Return the best-known remediation for one runtime error code."""
    return REMEDIATIONS.get(error_code, DEFAULT_REMEDIATION)


def ensure_schema_payload(value: Any) -> dict[str, Any]:
    """Normalize any model or mapping into a schema-versioned JSON payload."""
    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json", by_alias=True)
    elif isinstance(value, dict):
        payload = dict(value)
    else:
        raise TypeError(f"Unsupported JSON payload type: {type(value)!r}")

    payload.setdefault("schema_version", SCHEMA_VERSION)
    return payload


def dump_schema_payload(value: Any, *, indent: int = 2, exclude_none: bool = False) -> str:
    """Serialize a schema-versioned machine payload."""
    payload = ensure_schema_payload(value)
    if exclude_none:
        payload = {key: item for key, item in payload.items() if item is not None}
    return json.dumps(payload, indent=indent, ensure_ascii=True)
