"""Compact report summaries for agent hosts."""

from __future__ import annotations


def summarize_report(report: dict[str, object]) -> str:
    """Compress a report into a short, agent-friendly summary."""
    status = str(report.get("status", "unknown"))
    revision = report.get("revision", "unknown")
    qspec_path = report.get("qspec", {}).get("path", "unknown")  # type: ignore[union-attr]
    semantics = report.get("semantics", {})  # type: ignore[assignment]
    artifacts = report.get("artifacts", {})  # type: ignore[assignment]
    diagnostics = report.get("diagnostics", {})  # type: ignore[assignment]
    backend_reports = report.get("backend_reports", {})  # type: ignore[assignment]
    suggestions = report.get("suggestions", [])  # type: ignore[assignment]
    errors_list = report.get("errors", [])  # type: ignore[assignment]
    simulation = diagnostics.get("simulation", {}) if isinstance(diagnostics, dict) else {}
    simulation_status = simulation.get("status", "unknown") if isinstance(simulation, dict) else "unknown"
    warnings = len(report.get("warnings", [])) if isinstance(report.get("warnings", []), list) else 0
    errors = len(errors_list) if isinstance(errors_list, list) else 0
    pattern = semantics.get("pattern", "unknown") if isinstance(semantics, dict) else "unknown"
    parameter_count = semantics.get("parameter_count", "unknown") if isinstance(semantics, dict) else "unknown"
    artifact_names = ",".join(sorted(str(name) for name in artifacts.keys())[:4]) if isinstance(artifacts, dict) else "none"
    backend_summary = (
        ",".join(
            _format_backend_summary_entry(name, details)
            for name, details in sorted(backend_reports.items())
            if isinstance(details, dict)
        )[:240]
        if isinstance(backend_reports, dict) and backend_reports
        else "none"
    )
    first_error = (
        str(errors_list[0])[:180]
        if isinstance(errors_list, list) and errors_list
        else "none"
    )
    next_step = (
        str(suggestions[0])[:220]
        if isinstance(suggestions, list) and suggestions
        else "none"
    )

    summary = (
        f"status={status}; revision={revision}; pattern={pattern}; params={parameter_count}; qspec={qspec_path}; artifacts={artifact_names}; "
        f"simulation={simulation_status}; backends={backend_summary}; warnings={warnings}; "
        f"errors={errors}; first_error={first_error}; next={next_step}."
    )
    return summary[:1200]


def _format_backend_summary_entry(name: str, details: dict[str, object]) -> str:
    status = str(details.get("status", "unknown"))
    nested_details = details.get("details")
    if not isinstance(nested_details, dict):
        return f"{name}:{status}"

    benchmark_mode = nested_details.get("benchmark_mode")
    target_parity = nested_details.get("target_parity")
    if isinstance(benchmark_mode, str) and isinstance(target_parity, str):
        return f"{name}:{status}[{benchmark_mode},{target_parity}]"
    if isinstance(benchmark_mode, str):
        return f"{name}:{status}[{benchmark_mode}]"
    return f"{name}:{status}"
