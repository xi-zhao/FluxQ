"""Structural backend benchmarking for generated quantum programs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from quantum_runtime.backends import run_classiq_backend
from quantum_runtime.diagnostics.resources import estimate_resources
from quantum_runtime.diagnostics.transpile_validate import validate_target_constraints
from quantum_runtime.qspec import QSpec
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


def run_structural_benchmark(
    qspec: QSpec,
    workspace: WorkspaceHandle,
    backends: list[str],
) -> BenchmarkReport:
    """Compare structural backend outputs without making hardware claims."""
    entries: dict[str, BackendBenchmark] = {}
    for backend in backends:
        normalized = backend.strip()
        if not normalized:
            continue
        if normalized == "qiskit-local":
            resources = estimate_resources(qspec)
            transpile_report = validate_target_constraints(qspec)
            entries[normalized] = BackendBenchmark(
                backend=normalized,
                status="ok",
                width=resources.width,
                depth=resources.depth,
                transpiled_depth=transpile_report.transpiled_depth,
                two_qubit_gates=resources.two_qubit_gates,
                transpiled_two_qubit_gates=transpile_report.transpiled_two_qubit_gates,
                measure_count=resources.measure_count,
                notes=["Local Qiskit structural benchmark"],
            )
            continue

        if normalized == "classiq":
            classiq_report = run_classiq_backend(qspec, workspace)
            if classiq_report.status == "ok":
                resources = estimate_resources(qspec)
                entries[normalized] = BackendBenchmark(
                    backend=normalized,
                    status="ok",
                    width=resources.width,
                    depth=resources.depth,
                    transpiled_depth=resources.depth,
                    two_qubit_gates=resources.two_qubit_gates,
                    transpiled_two_qubit_gates=resources.two_qubit_gates,
                    measure_count=resources.measure_count,
                    notes=["Classiq benchmark uses QSpec baseline resources until richer synthesis metrics land"],
                    details={"resource_source": "qspec_baseline"},
                )
            else:
                entries[normalized] = BackendBenchmark(
                    backend=normalized,
                    status=classiq_report.status,
                    reason=classiq_report.reason,
                    notes=["Dependency or backend availability issue blocked Classiq benchmarking"],
                    details=dict(classiq_report.details),
                )
            continue

        entries[normalized] = BackendBenchmark(
            backend=normalized,
            status="backend_unavailable",
            reason="unknown_backend",
            notes=["Backend is not recognized by this runtime build"],
        )

    return BenchmarkReport(
        status=_derive_status(entries),
        backends=entries,
    )


def _derive_status(backends: dict[str, BackendBenchmark]) -> Literal["ok", "degraded", "error"]:
    statuses = {entry.status for entry in backends.values()}
    if "error" in statuses:
        return "error"
    if statuses - {"ok"}:
        return "degraded"
    return "ok"
