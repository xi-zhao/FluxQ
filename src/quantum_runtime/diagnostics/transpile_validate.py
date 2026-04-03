"""Target-constrained transpilation validation for Qiskit circuits."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from qiskit import transpile
from qiskit.transpiler import CouplingMap

from quantum_runtime.lowering.qiskit_emitter import build_qiskit_circuit
from quantum_runtime.qspec import QSpec


class TargetValidationReport(BaseModel):
    """Structured metrics for constraint-aware transpilation."""

    status: Literal["ok", "error", "skipped"]
    benchmark_mode: Literal["structural_only", "target_aware"]
    comparable: bool
    target_assumptions: dict[str, object] = Field(default_factory=dict)
    fallback_reason: str | None = None
    error: str | None = None
    original_depth: int
    transpiled_depth: int | None = None
    original_two_qubit_gates: int
    transpiled_two_qubit_gates: int | None = None
    coupling_insertions: int | None = None
    warnings: list[str] = Field(default_factory=list)


def validate_target_constraints(qspec: QSpec) -> TargetValidationReport:
    """Transpile a circuit under target constraints and report structural metrics."""
    circuit = build_qiskit_circuit(qspec)
    original_depth = int(circuit.depth() or 0)
    original_two_qubit_gates = _count_two_qubit_gates(circuit)
    target_assumptions = _target_assumptions(qspec)
    benchmark_mode = _benchmark_mode(target_assumptions)

    if qspec.constraints.max_width is not None and circuit.num_qubits > qspec.constraints.max_width:
        return TargetValidationReport(
            status="error",
            benchmark_mode=benchmark_mode,
            comparable=False,
            target_assumptions=target_assumptions,
            error=(
                f"Circuit width {circuit.num_qubits} exceeds max_width "
                f"{qspec.constraints.max_width}."
            ),
            original_depth=original_depth,
            original_two_qubit_gates=original_two_qubit_gates,
        )

    transpile_kwargs: dict[str, object] = {
        "optimization_level": int(qspec.constraints.optimization_level),
    }
    if qspec.constraints.basis_gates:
        transpile_kwargs["basis_gates"] = list(qspec.constraints.basis_gates)
    if qspec.constraints.connectivity_map:
        transpile_kwargs["coupling_map"] = CouplingMap(qspec.constraints.connectivity_map)

    if len(transpile_kwargs) == 1 and qspec.constraints.max_depth is None:
        return TargetValidationReport(
            status="skipped",
            benchmark_mode="structural_only",
            comparable=False,
            target_assumptions=target_assumptions,
            fallback_reason="no_target_constraints",
            original_depth=original_depth,
            original_two_qubit_gates=original_two_qubit_gates,
            transpiled_depth=None,
            transpiled_two_qubit_gates=None,
            coupling_insertions=None,
            warnings=["Transpilation skipped because no target constraints were provided."],
        )

    try:
        transpiled = transpile(circuit, **transpile_kwargs)
    except Exception as exc:
        return TargetValidationReport(
            status="error",
            benchmark_mode=benchmark_mode,
            comparable=False,
            target_assumptions=target_assumptions,
            error=str(exc),
            original_depth=original_depth,
            original_two_qubit_gates=original_two_qubit_gates,
        )

    transpiled_depth = int(transpiled.depth() or 0)
    transpiled_two_qubit_gates = _count_two_qubit_gates(transpiled)

    if qspec.constraints.max_depth is not None and transpiled_depth > qspec.constraints.max_depth:
        return TargetValidationReport(
            status="error",
            benchmark_mode=benchmark_mode,
            comparable=False,
            target_assumptions=target_assumptions,
            error=(
                f"Transpiled depth {transpiled_depth} exceeds max_depth "
                f"{qspec.constraints.max_depth}."
            ),
            original_depth=original_depth,
            transpiled_depth=transpiled_depth,
            original_two_qubit_gates=original_two_qubit_gates,
            transpiled_two_qubit_gates=transpiled_two_qubit_gates,
            coupling_insertions=max(0, transpiled_two_qubit_gates - original_two_qubit_gates),
        )

    return TargetValidationReport(
        status="ok",
        benchmark_mode=benchmark_mode,
        comparable=benchmark_mode == "target_aware",
        target_assumptions=target_assumptions,
        original_depth=original_depth,
        transpiled_depth=transpiled_depth,
        original_two_qubit_gates=original_two_qubit_gates,
        transpiled_two_qubit_gates=transpiled_two_qubit_gates,
        coupling_insertions=max(0, transpiled_two_qubit_gates - original_two_qubit_gates),
    )


def _count_two_qubit_gates(circuit: object) -> int:
    return sum(
        1
        for item in circuit.data
        if len(item.qubits) == 2 and item.operation.name != "barrier"
    )


def _target_assumptions(qspec: QSpec) -> dict[str, object]:
    basis_gates = list(qspec.constraints.basis_gates or [])
    connectivity_map = (
        [list(edge) for edge in qspec.constraints.connectivity_map]
        if qspec.constraints.connectivity_map
        else []
    )
    constraint_fields: list[str] = []
    transpile_constraint_fields: list[str] = []
    validation_constraint_fields: list[str] = []
    if qspec.constraints.max_depth is not None:
        constraint_fields.append("max_depth")
        validation_constraint_fields.append("max_depth")
    if basis_gates:
        constraint_fields.append("basis_gates")
        transpile_constraint_fields.append("basis_gates")
    if connectivity_map:
        constraint_fields.append("connectivity_map")
        transpile_constraint_fields.append("connectivity_map")
    return {
        "optimization_level": int(qspec.constraints.optimization_level),
        "max_width": qspec.constraints.max_width,
        "max_depth": qspec.constraints.max_depth,
        "basis_gates": basis_gates,
        "connectivity_map": connectivity_map,
        "constraint_fields": constraint_fields,
        "transpile_constraint_fields": transpile_constraint_fields,
        "validation_constraint_fields": validation_constraint_fields,
    }


def _benchmark_mode(target_assumptions: dict[str, object]) -> Literal["structural_only", "target_aware"]:
    fields = target_assumptions.get("transpile_constraint_fields")
    if isinstance(fields, list) and fields:
        return "target_aware"
    return "structural_only"
