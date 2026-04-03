"""Structural backend benchmarking for generated quantum programs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from quantum_runtime.backends import run_classiq_backend
from quantum_runtime.diagnostics.resources import estimate_resources
from quantum_runtime.diagnostics.transpile_validate import validate_target_constraints
from quantum_runtime.qspec import QSpec, summarize_qspec_semantics
from quantum_runtime.workspace import WorkspaceHandle


class BackendBenchmark(BaseModel):
    """Normalized structural benchmark result for a single backend."""

    backend: str
    status: Literal["ok", "dependency_missing", "backend_unavailable", "error"]
    width: int | None = None
    depth: int | None = None
    transpiled_depth: int | None = None
    two_qubit_gates: int | None = None
    transpiled_two_qubit_gates: int | None = None
    measure_count: int | None = None
    reason: str | None = None
    notes: list[str] = Field(default_factory=list)
    details: dict[str, object] = Field(default_factory=dict)


class BenchmarkReport(BaseModel):
    """Aggregate benchmark report across requested backends."""

    status: Literal["ok", "degraded", "error"]
    backends: dict[str, BackendBenchmark]
    subject: dict[str, Any] = Field(default_factory=dict)


def run_structural_benchmark(
    qspec: QSpec,
    workspace: WorkspaceHandle,
    backends: list[str],
) -> BenchmarkReport:
    """Compare structural backend outputs without making hardware claims."""
    subject = summarize_qspec_semantics(qspec)
    entries: dict[str, BackendBenchmark] = {}
    for backend in backends:
        normalized = backend.strip()
        if not normalized:
            continue
        if normalized == "qiskit-local":
            resources = estimate_resources(qspec)
            transpile_report = validate_target_constraints(qspec)
            notes = ["Local Qiskit structural benchmark"]
            if transpile_report.status == "skipped":
                notes.append("Transpile metrics were skipped because no target constraints were provided.")
            if transpile_report.status == "error":
                notes.append("Target validation failed, so target-aware benchmark parity is unavailable.")
            entries[normalized] = BackendBenchmark(
                backend=normalized,
                status="error" if transpile_report.status == "error" else "ok",
                width=resources.width,
                depth=resources.depth,
                transpiled_depth=transpile_report.transpiled_depth,
                two_qubit_gates=resources.two_qubit_gates,
                transpiled_two_qubit_gates=transpile_report.transpiled_two_qubit_gates,
                measure_count=resources.measure_count,
                reason="target_validation_failed" if transpile_report.status == "error" else None,
                notes=notes,
                details={
                    "resource_source": "qiskit_local",
                    "benchmark_mode": transpile_report.benchmark_mode,
                    "comparable": transpile_report.comparable,
                    "comparability_reason": _qiskit_comparability_reason(transpile_report),
                    "transpile_status": transpile_report.status,
                    "transpile_performed": transpile_report.status != "skipped",
                    "target_assumptions": transpile_report.target_assumptions,
                    "fallback_reason": transpile_report.fallback_reason,
                    "error": transpile_report.error,
                    "parameter_count": resources.parameter_count,
                    "parameter_names": resources.parameter_names,
                    "semantic_hash": subject["semantic_hash"],
                },
            )
            continue

        if normalized == "classiq":
            classiq_report = run_classiq_backend(qspec, workspace)
            if classiq_report.status == "ok":
                resources = estimate_resources(qspec)
                synthesis_metrics = _synthesis_metrics_from_report(classiq_report)
                if synthesis_metrics:
                    benchmark = _benchmark_from_synthesis_metrics(
                        backend=normalized,
                        classiq_report=classiq_report,
                        synthesis_metrics=synthesis_metrics,
                        baseline_resources=resources,
                        subject=subject,
                    )
                else:
                    benchmark = BackendBenchmark(
                        backend=normalized,
                        status="ok",
                        width=resources.width,
                        depth=resources.depth,
                        transpiled_depth=resources.depth,
                        two_qubit_gates=resources.two_qubit_gates,
                        transpiled_two_qubit_gates=resources.two_qubit_gates,
                        measure_count=resources.measure_count,
                        notes=[
                            "Classiq benchmark used fallback QSpec baseline resources because synthesis metrics were unavailable",
                        ],
                        details=_augment_contract(
                            {
                                "resource_source": "qspec_baseline",
                                "target_assumptions": _classiq_target_assumptions(classiq_report),
                                "parameter_count": resources.parameter_count,
                                "parameter_names": resources.parameter_names,
                                "semantic_hash": subject["semantic_hash"],
                            },
                            benchmark_mode="structural_only",
                            comparable=False,
                            fallback_reason="missing_synthesis_metrics",
                            target_parity="unavailable",
                            comparability_reason="missing_synthesis_metrics",
                        ),
                    )
                entries[normalized] = benchmark
            else:
                entries[normalized] = BackendBenchmark(
                    backend=normalized,
                    status=classiq_report.status,
                    reason=classiq_report.reason,
                    notes=["Dependency or backend availability issue blocked Classiq benchmarking"],
                    details=_augment_contract(
                        dict(classiq_report.details),
                        benchmark_mode="unavailable",
                        comparable=False,
                        fallback_reason=classiq_report.reason,
                        target_parity="unavailable",
                        comparability_reason=classiq_report.reason or "backend_unavailable",
                    ),
                )
            continue

        entries[normalized] = BackendBenchmark(
            backend=normalized,
            status="backend_unavailable",
            reason="unknown_backend",
            notes=["Backend is not recognized by this runtime build"],
            details=_augment_contract(
                {},
                benchmark_mode="unavailable",
                comparable=False,
                fallback_reason="unknown_backend",
                target_parity="unavailable",
                comparability_reason="unknown_backend",
            ),
        )

    return BenchmarkReport(
        status=_derive_status(entries),
        backends=entries,
        subject=subject,
    )


def _derive_status(backends: dict[str, BackendBenchmark]) -> Literal["ok", "degraded", "error"]:
    statuses = {entry.status for entry in backends.values()}
    if "error" in statuses:
        return "error"
    if statuses - {"ok"}:
        return "degraded"
    return "ok"


def _synthesis_metrics_from_report(classiq_report: object) -> dict[str, int]:
    metrics = getattr(classiq_report, "synthesis_metrics", None)
    if isinstance(metrics, dict) and metrics:
        return _normalize_metrics(metrics)

    details = getattr(classiq_report, "details", None)
    if isinstance(details, dict):
        nested = details.get("synthesis_metrics")
        if isinstance(nested, dict) and nested:
            return _normalize_metrics(nested)

    return {}


def _benchmark_from_synthesis_metrics(
    *,
    backend: str,
    classiq_report: object,
    synthesis_metrics: dict[str, int],
    baseline_resources: Any,
    subject: dict[str, Any],
) -> BackendBenchmark:
    width = synthesis_metrics.get("width")
    depth = synthesis_metrics.get("depth")
    two_qubit_gates = synthesis_metrics.get("two_qubit_gates")
    measure_count = synthesis_metrics.get("measure_count")

    fallback_used = any(
        value is None
        for value in (width, depth, two_qubit_gates, measure_count)
    )
    width = width if width is not None else baseline_resources.width
    depth = depth if depth is not None else baseline_resources.depth
    two_qubit_gates = two_qubit_gates if two_qubit_gates is not None else baseline_resources.two_qubit_gates
    measure_count = measure_count if measure_count is not None else baseline_resources.measure_count

    notes = ["Classiq benchmark used synthesis metrics from synthesis.json"]
    if fallback_used:
        notes.append("Missing synthesis fields fell back to QSpec baseline resources.")

    target_assumptions = _classiq_target_assumptions(classiq_report)
    return BackendBenchmark(
        backend=backend,
        status="ok",
        width=width,
        depth=depth,
        transpiled_depth=depth,
        two_qubit_gates=two_qubit_gates,
        transpiled_two_qubit_gates=two_qubit_gates,
        measure_count=measure_count,
        notes=notes,
        details=_augment_contract(
            {
                "resource_source": "classiq_synthesis",
                "synthesis_metrics": synthesis_metrics,
                "target_assumptions": target_assumptions,
                "parameter_count": baseline_resources.parameter_count,
                "parameter_names": baseline_resources.parameter_names,
                "semantic_hash": subject["semantic_hash"],
            },
            benchmark_mode="synthesis_backed",
            comparable=False,
            fallback_reason="partial_synthesis_metrics" if fallback_used else None,
            target_parity=_classiq_target_parity(target_assumptions),
            comparability_reason=_classiq_comparability_reason(target_assumptions),
        ),
    )


def _normalize_metrics(metrics: dict[str, int]) -> dict[str, int]:
    normalized: dict[str, int] = {}
    for key in ("width", "depth", "two_qubit_gates", "measure_count"):
        value = metrics.get(key)
        if isinstance(value, int):
            normalized[key] = value
    return normalized


def _classiq_target_assumptions(classiq_report: object) -> dict[str, object]:
    details = getattr(classiq_report, "details", None)
    if not isinstance(details, dict):
        return {
            "applied_constraints": {},
            "applied_preferences": {},
            "unsupported_constraints": [],
        }
    assumptions = details.get("target_assumptions")
    if isinstance(assumptions, dict):
        return assumptions
    return {
        "applied_constraints": {},
        "applied_preferences": {},
        "unsupported_constraints": [],
    }


def _augment_contract(
    details: dict[str, object],
    *,
    benchmark_mode: str,
    comparable: bool,
    fallback_reason: str | None,
    target_parity: str | None = None,
    comparability_reason: str | None = None,
) -> dict[str, object]:
    contract: dict[str, object] = {
        **details,
        "benchmark_mode": benchmark_mode,
        "comparable": comparable,
        "fallback_reason": fallback_reason,
    }
    if target_parity is not None:
        contract["target_parity"] = target_parity
    if comparability_reason is not None:
        contract["comparability_reason"] = comparability_reason
    return contract


def _qiskit_comparability_reason(transpile_report: object) -> str:
    comparable = getattr(transpile_report, "comparable", False)
    fallback_reason = getattr(transpile_report, "fallback_reason", None)
    if comparable:
        return "target_aware_transpile"
    if isinstance(fallback_reason, str) and fallback_reason:
        return fallback_reason
    return "structural_only"


def _classiq_target_parity(target_assumptions: dict[str, object]) -> str:
    unsupported_constraints = target_assumptions.get("unsupported_constraints")
    applied_constraints = target_assumptions.get("applied_constraints")
    if isinstance(unsupported_constraints, list) and unsupported_constraints:
        return "partial"
    if isinstance(applied_constraints, dict) and applied_constraints:
        return "partial"
    return "unavailable"


def _classiq_comparability_reason(target_assumptions: dict[str, object]) -> str:
    target_parity = _classiq_target_parity(target_assumptions)
    if target_parity == "partial":
        return "partial_target_parity"
    return "no_target_parity"
