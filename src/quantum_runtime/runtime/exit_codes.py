"""Centralized CLI exit-code mapping."""

from __future__ import annotations

from typing import Any


EXIT_OK = 0
EXIT_DEGRADED = 2
EXIT_INVALID_INPUT = 3
EXIT_UNSUPPORTED = 4
EXIT_COMPILE_FAILURE = 5
EXIT_SIMULATION_FAILURE = 6
EXIT_DEPENDENCY_MISSING = 7


def exit_code_for_exec(result: Any) -> int:
    """Map an exec result payload to the documented CLI exit codes."""
    diagnostics = _as_mapping(getattr(result, "diagnostics", None))
    backend_reports = _as_mapping(getattr(result, "backend_reports", None))
    warnings = list(getattr(result, "warnings", []) or [])
    errors = list(getattr(result, "errors", []) or [])
    status = str(getattr(result, "status", "ok"))

    if _has_status(diagnostics.get("simulation"), "error") or _has_status(diagnostics.get("transpile"), "error"):
        return EXIT_SIMULATION_FAILURE
    if _any_backend_status(backend_reports, "dependency_missing"):
        return EXIT_DEPENDENCY_MISSING
    if _any_backend_status(backend_reports, "backend_unavailable"):
        return EXIT_UNSUPPORTED
    if status == "error" or errors:
        return EXIT_COMPILE_FAILURE
    if status == "degraded" or warnings:
        return EXIT_DEGRADED
    return EXIT_OK


def exit_code_for_benchmark(result: Any) -> int:
    """Map a benchmark report to the documented CLI exit codes."""
    backends = _as_mapping(getattr(result, "backends", None))
    statuses = {_status_of(report) for report in backends.values()}
    statuses.discard(None)
    status = str(getattr(result, "status", "ok"))

    if "dependency_missing" in statuses:
        return EXIT_DEPENDENCY_MISSING
    if "backend_unavailable" in statuses:
        return EXIT_UNSUPPORTED
    if "error" in statuses or status == "error":
        return EXIT_COMPILE_FAILURE
    if status == "degraded" or statuses - {"ok"}:
        return EXIT_DEGRADED
    return EXIT_OK


def exit_code_for_doctor(result: Any) -> int:
    """Map a doctor report to the documented CLI exit codes."""
    issues = list(getattr(result, "issues", []) or [])
    workspace_ok = bool(getattr(result, "workspace_ok", True))

    if not issues:
        return EXIT_OK
    if not workspace_ok or any(_is_workspace_issue(issue) for issue in issues):
        return EXIT_INVALID_INPUT
    if any("unavailable" in issue for issue in issues):
        return EXIT_DEPENDENCY_MISSING
    return EXIT_DEGRADED


def exit_code_for_export(result: Any) -> int:
    """Map an export result to the documented CLI exit codes."""
    status = str(getattr(result, "status", "ok"))
    if status == "ok":
        return EXIT_OK
    if status == "unsupported":
        return EXIT_UNSUPPORTED
    return EXIT_COMPILE_FAILURE


def exit_code_for_inspect(result: Any) -> int:
    """Map an inspect report to the documented CLI exit codes."""
    status = str(getattr(result, "status", "ok"))
    issues = list(getattr(result, "issues", []) or [])
    errors = list(getattr(result, "errors", []) or [])

    if status == "ok" and not issues and not errors:
        return EXIT_OK
    if errors:
        return EXIT_INVALID_INPUT
    return EXIT_DEGRADED


def exit_code_for_compare(result: Any) -> int:
    """Map a compare report to the documented CLI exit codes."""
    verdict = _as_mapping(getattr(result, "verdict", None))
    verdict_status = str(verdict.get("status")) if verdict else None
    if verdict_status == "pass":
        return EXIT_OK
    if verdict_status == "fail":
        return EXIT_DEGRADED
    status = str(getattr(result, "status", "different_subject"))
    if status == "same_subject":
        return EXIT_OK
    return EXIT_DEGRADED


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _has_status(value: Any, expected: str) -> bool:
    return _status_of(value) == expected


def _any_backend_status(backends: dict[str, Any], expected: str) -> bool:
    return any(_status_of(report) == expected for report in backends.values())


def _is_workspace_issue(issue: str) -> bool:
    return (
        issue == "workspace_root_missing"
        or issue == "workspace_manifest_missing"
        or issue == "workspace_manifest_invalid"
        or issue == "active_spec_missing"
        or issue == "active_spec_invalid"
        or issue == "active_report_missing"
        or issue == "active_report_invalid"
        or issue.startswith("missing_directories:")
    )


def _status_of(value: Any) -> str | None:
    if isinstance(value, dict):
        raw = value.get("status")
    else:
        raw = getattr(value, "status", None)
    if raw is None:
        return None
    return str(raw)
