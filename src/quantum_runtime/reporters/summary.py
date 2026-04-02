"""Compact report summaries for agent hosts."""

from __future__ import annotations


def summarize_report(report: dict[str, object]) -> str:
    """Compress a report into a short, agent-friendly summary."""
    revision = report.get("revision", "unknown")
    qspec_path = report.get("qspec", {}).get("path", "unknown")  # type: ignore[union-attr]
    diagnostics = report.get("diagnostics", {})  # type: ignore[assignment]
    simulation = diagnostics.get("simulation", {}) if isinstance(diagnostics, dict) else {}
    simulation_status = simulation.get("status", "unknown") if isinstance(simulation, dict) else "unknown"
    warnings = len(report.get("warnings", [])) if isinstance(report.get("warnings", []), list) else 0
    errors = len(report.get("errors", [])) if isinstance(report.get("errors", []), list) else 0

    summary = (
        f"revision={revision}; qspec={qspec_path}; simulation={simulation_status}; "
        f"warnings={warnings}; errors={errors}."
    )
    return summary[:1200]
