"""Write stable report artifacts into the workspace."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from quantum_runtime.workspace.manager import WorkspaceHandle


def write_report(
    *,
    workspace: WorkspaceHandle,
    revision: str,
    input_data: dict[str, Any],
    qspec_path: Path,
    artifacts: dict[str, Any],
    diagnostics: dict[str, Any],
    backend_reports: dict[str, Any],
    warnings: list[str],
    errors: list[str],
) -> dict[str, Any]:
    """Write `reports/latest.json` and a revision history copy."""
    payload: dict[str, Any] = {
        "revision": revision,
        "input": input_data,
        "qspec": {
            "path": str(qspec_path),
            "hash": _sha256_file(qspec_path),
        },
        "artifacts": artifacts,
        "diagnostics": diagnostics,
        "backend_reports": backend_reports,
        "warnings": warnings,
        "errors": errors,
        "suggestions": _build_suggestions(warnings, errors),
    }

    latest_path = workspace.root / "reports" / "latest.json"
    history_path = workspace.root / "reports" / "history" / f"{revision}.json"
    serialized = json.dumps(payload, indent=2, ensure_ascii=True)
    latest_path.write_text(serialized)
    history_path.write_text(serialized)
    return payload


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _build_suggestions(warnings: list[str], errors: list[str]) -> list[str]:
    suggestions = []
    if errors:
        suggestions.append("Inspect the diagnostics errors before attempting export or execution.")
    else:
        suggestions.append("Review the generated artifacts and diagnostics report for the next backend step.")
    if warnings:
        suggestions.append("Resolve warnings before adding target constraints or backend benchmarks.")
    else:
        suggestions.append("Add target constraints or backend benchmarks to deepen validation.")
    return suggestions
