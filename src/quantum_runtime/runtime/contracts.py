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
    "baseline_benchmark_missing": (
        "Run `qrun bench --revision <baseline-revision>` to persist saved benchmark evidence before using `qrun bench --baseline ...`."
    ),
    "expected_exactly_one_input": "Provide exactly one supported input selector for the command.",
    "remote_backend_required": "Pass `--backend <name>`; FluxQ requires explicit remote backend selection.",
    "invalid_benchmark_policy": (
        "Use `qrun bench --baseline` with non-negative regression thresholds and valid comparable/status policy options."
    ),
    "workspace_manifest_missing": "Initialize the workspace with `qrun init` or point the command at an existing workspace.",
    "workspace_root_required_for_revision": "Pass `--workspace` when resolving a historical revision.",
    "workspace_root_required_for_report_file": "Pass `--workspace` or use a report file that still carries recoverable workspace provenance.",
    "workspace_conflict": "Wait for the current workspace lease holder to finish, then retry the command or use a different workspace.",
    "workspace_recovery_required": "Run `qrun doctor --fix` or clear the interrupted-write leftovers after validating the last known good revision.",
    "workspace_alias_mismatch": "Review alias_paths, restore the active aliases to one coherent revision, then retry the command.",
    "pack_bundle_invalid": "Run `qrun pack-inspect --pack-root <bundle> --json`, fix the reported bundle verification issues, then retry the import.",
    "pack_revision_conflict": "Import into an empty workspace or remove the conflicting revision history before retrying `qrun pack-import`.",
    "ibm_config_invalid": (
        "Use `qrun ibm configure` with exactly one credential reference: `--token-env` for `env` mode or "
        "`--saved-account-name` for `saved_account` mode."
    ),
    "ibm_instance_required": "Pass `--instance <crn>` to `qrun ibm configure`; FluxQ requires explicit IBM instance selection.",
    "ibm_token_external_required": (
        "Pass `--token-env <ENV_VAR>` and provide the IBM token through that environment variable instead of storing it in `.quantum/qrun.toml`."
    ),
    "ibm_profile_missing": (
        "Run `qrun ibm configure` to persist a non-secret `[remote.ibm]` profile before using IBM readiness checks."
    ),
    "ibm_instance_unset": "Run `qrun ibm configure --instance <crn>` so the workspace pins one explicit IBM instance.",
    "ibm_token_env_missing": (
        "Export the configured IBM token environment variable before running `qrun doctor --ci` for an IBM-enabled workspace."
    ),
    "ibm_saved_account_missing": (
        "Create or refresh the configured IBM saved account outside `.quantum`, then rerun `qrun doctor --ci`."
    ),
    "ibm_runtime_dependency_missing": (
        "Install the optional IBM extra with `uv sync --extra ibm` before running IBM readiness checks."
    ),
    "ibm_backend_lookup_failed": (
        "Use `qrun backend list --workspace <workspace> --json` to confirm the explicit backend name and IBM instance, then retry."
    ),
    "ibm_access_unresolved": (
        "Review the `[remote.ibm]` profile, credential reference, and instance settings, then rerun `qrun doctor --ci`."
    ),
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
    details: Any = Field(default_factory=dict)


class WorkspaceConflictDetails(BaseModel):
    """Structured metadata for a held workspace lease."""

    workspace: str
    lock_path: str
    holder: dict[str, Any] = Field(default_factory=dict)
    reason_codes: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    gate: dict[str, Any] = Field(default_factory=dict)


class WorkspaceConflictErrorPayload(ErrorPayload):
    """Structured machine payload for workspace lease conflicts."""

    reason: Literal["workspace_conflict"] = "workspace_conflict"
    error_code: Literal["workspace_conflict"] = "workspace_conflict"
    details: WorkspaceConflictDetails


class WorkspaceRecoveryRequiredDetails(BaseModel):
    """Structured metadata for interrupted-write recovery state."""

    workspace: str
    pending_files: list[str] = Field(default_factory=list)
    last_valid_revision: str | None = None
    alias_paths: list[str] = Field(default_factory=list)
    recovery_mode: str = "pending_files"
    reason_codes: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    gate: dict[str, Any] = Field(default_factory=dict)


class WorkspaceRecoveryRequiredErrorPayload(ErrorPayload):
    """Structured machine payload for recovery-required workspace failures."""

    reason: Literal["workspace_recovery_required"] = "workspace_recovery_required"
    error_code: Literal["workspace_recovery_required"] = "workspace_recovery_required"
    details: WorkspaceRecoveryRequiredDetails


def remediation_for_error(error_code: str) -> str:
    """Return the best-known remediation for one runtime error code."""
    return REMEDIATIONS.get(error_code, DEFAULT_REMEDIATION)


def workspace_conflict_error_payload(
    *,
    workspace: str,
    lock_path: str,
    holder: dict[str, Any],
    reason_codes: list[str],
    next_actions: list[str],
    gate: dict[str, Any],
) -> WorkspaceConflictErrorPayload:
    """Build a schema-versioned payload for held workspace leases."""
    return WorkspaceConflictErrorPayload(
        remediation=remediation_for_error("workspace_conflict"),
        details=WorkspaceConflictDetails(
            workspace=workspace,
            lock_path=lock_path,
            holder=holder,
            reason_codes=reason_codes,
            next_actions=next_actions,
            gate=gate,
        ),
    )


def workspace_recovery_required_error_payload(
    *,
    workspace: str,
    pending_files: list[str],
    last_valid_revision: str | None,
    alias_paths: list[str],
    recovery_mode: str,
    reason_codes: list[str],
    next_actions: list[str],
    gate: dict[str, Any],
    remediation: str | None = None,
) -> WorkspaceRecoveryRequiredErrorPayload:
    """Build a schema-versioned payload for interrupted-write recovery."""
    return WorkspaceRecoveryRequiredErrorPayload(
        remediation=remediation or remediation_for_error("workspace_recovery_required"),
        details=WorkspaceRecoveryRequiredDetails(
            workspace=workspace,
            pending_files=pending_files,
            last_valid_revision=last_valid_revision,
            alias_paths=alias_paths,
            recovery_mode=recovery_mode,
            reason_codes=reason_codes,
            next_actions=next_actions,
            gate=gate,
        ),
    )


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
