"""Local Qiskit simulation diagnostics."""

from __future__ import annotations

import time
from typing import Any, Literal

from pydantic import BaseModel, Field
from qiskit import transpile
from qiskit_aer import AerSimulator
from qiskit.quantum_info import SparsePauliOp, Statevector

from quantum_runtime.lowering.qiskit_emitter import build_qiskit_circuit
from quantum_runtime.qspec import QSpec
from quantum_runtime.qspec.parameter_workflow import summarize_parameter_workflow


class SimulationReport(BaseModel):
    """Structured local simulation result."""

    status: str
    shots: int
    counts: dict[str, int] = Field(default_factory=dict)
    parameter_mode: str = "defaults"
    representative_bindings: dict[str, float] = Field(default_factory=dict)
    representative_point_label: str = "defaults"
    observables: list[dict[str, Any]] = Field(default_factory=list)
    expectation_values: list[dict[str, Any]] = Field(default_factory=list)
    parameter_points: list[dict[str, Any]] = Field(default_factory=list)
    best_point: dict[str, Any] | None = None
    error: str | None = None
    elapsed_ms: int


def run_local_simulation(qspec: QSpec, shots: int = 1024) -> SimulationReport:
    """Simulate a QSpec on the local Aer simulator."""
    start = time.perf_counter()
    try:
        points = _parameter_points(qspec)
        observable_specs = [dict(observable) for observable in qspec.observables]
        evaluated_points = [
            _evaluate_parameter_point(
                qspec,
                label=point["label"],
                source=point["source"],
                bindings=point["bindings"],
                observables=observable_specs,
            )
            for point in points
        ]
        representative = _representative_point(evaluated_points)
        circuit = build_qiskit_circuit(qspec, parameter_bindings=representative["bindings"])
        backend = AerSimulator()
        compiled = transpile(circuit, backend)
        result = backend.run(compiled, shots=shots).result()
        counts = dict(sorted(result.get_counts().items()))
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return SimulationReport(
            status="ok",
            shots=shots,
            counts=counts,
            parameter_mode=str(representative.get("workflow_mode", "defaults")),
            representative_bindings=dict(representative.get("bindings", {})),
            representative_point_label=str(representative.get("label", "defaults")),
            observables=observable_specs,
            expectation_values=list(representative.get("expectation_values", [])),
            parameter_points=evaluated_points,
            best_point=_best_point(evaluated_points),
            elapsed_ms=elapsed_ms,
        )
    except Exception as exc:  # pragma: no cover - defensive path
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return SimulationReport(
            status="error",
            shots=shots,
            counts={},
            error=str(exc),
            elapsed_ms=elapsed_ms,
        )


def _parameter_points(qspec: QSpec) -> list[dict[str, Any]]:
    workflow = summarize_parameter_workflow(qspec)
    mode = str(workflow.get("mode", "defaults"))
    if mode == "binding":
        return [
            {
                "label": "bound",
                "source": "binding",
                "workflow_mode": "binding",
                "bindings": dict(workflow.get("bindings", {})),
            }
        ]
    if mode == "sweep":
        points = workflow.get("points", [])
        if isinstance(points, list) and points:
            return [
                {
                    "label": f"sweep_{index:03d}",
                    "source": "sweep",
                    "workflow_mode": "sweep",
                    "bindings": dict(point),
                }
                for index, point in enumerate(points)
                if isinstance(point, dict)
            ]
    return [
        {
            "label": "defaults",
            "source": "defaults",
            "workflow_mode": "defaults",
            "bindings": dict(workflow.get("bindings", {})),
        }
    ]


def _evaluate_parameter_point(
    qspec: QSpec,
    *,
    label: str,
    source: Literal["defaults", "binding", "sweep"] | str,
    bindings: dict[str, float],
    observables: list[dict[str, Any]],
) -> dict[str, Any]:
    circuit = build_qiskit_circuit(qspec, parameter_bindings=bindings)
    state_circuit = circuit.remove_final_measurements(inplace=False)
    statevector = Statevector.from_instruction(state_circuit)
    expectation_values = [
        _evaluate_observable(statevector, observable, num_qubits=state_circuit.num_qubits)
        for observable in observables
    ]
    return {
        "label": label,
        "source": source,
        "workflow_mode": source,
        "bindings": {name: float(value) for name, value in bindings.items()},
        "evaluation_mode": "exact_statevector",
        "expectation_values": expectation_values,
    }


def _evaluate_observable(
    statevector: Statevector,
    observable: dict[str, Any],
    *,
    num_qubits: int,
) -> dict[str, Any]:
    terms = observable.get("terms", [])
    sparse_terms: list[tuple[str, list[int], float]] = []
    for term in terms:
        if not isinstance(term, dict):
            continue
        sparse_terms.append(
            (
                str(term.get("pauli", "")).upper(),
                [int(qubit) for qubit in term.get("qubits", [])],
                float(term.get("coefficient", 1.0)),
            )
        )

    constant = float(observable.get("constant", 0.0))
    value = constant
    if sparse_terms:
        operator = SparsePauliOp.from_sparse_list(sparse_terms, num_qubits=num_qubits)
        value += float(statevector.expectation_value(operator).real)

    return {
        "name": str(observable.get("name", "observable")),
        "kind": str(observable.get("kind", "pauli_sum")),
        "objective": observable.get("objective"),
        "evaluation_mode": "exact_statevector",
        "value": round(value, 10),
        "constant": constant,
        "terms": [dict(term) for term in terms if isinstance(term, dict)],
    }


def _representative_point(points: list[dict[str, Any]]) -> dict[str, Any]:
    best = _best_point(points)
    if best is not None:
        return best
    return points[0] if points else {"label": "defaults", "bindings": {}, "workflow_mode": "defaults"}


def _best_point(points: list[dict[str, Any]]) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_score: float | None = None
    best_direction: str | None = None
    best_observable_name: str | None = None
    for point in points:
        expectation_values = point.get("expectation_values")
        if not isinstance(expectation_values, list):
            continue
        for observable in expectation_values:
            if not isinstance(observable, dict):
                continue
            objective = observable.get("objective")
            if objective not in {"maximize", "minimize"}:
                continue
            value = float(observable.get("value", 0.0))
            if best is None:
                best = {
                    **point,
                    "objective_observable": observable.get("name"),
                    "objective": objective,
                    "objective_value": value,
                }
                best_score = value
                best_direction = str(objective)
                best_observable_name = str(observable.get("name"))
                continue
            if str(objective) != best_direction or str(observable.get("name")) != best_observable_name:
                continue
            if objective == "maximize" and best_score is not None and value > best_score:
                best = {
                    **point,
                    "objective_observable": observable.get("name"),
                    "objective": objective,
                    "objective_value": value,
                }
                best_score = value
            if objective == "minimize" and best_score is not None and value < best_score:
                best = {
                    **point,
                    "objective_observable": observable.get("name"),
                    "objective": objective,
                    "objective_value": value,
                }
                best_score = value
    return best
