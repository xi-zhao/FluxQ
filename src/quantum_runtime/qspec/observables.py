"""Observable helpers for parameterized workflow semantics."""

from __future__ import annotations

from typing import Any


def build_maxcut_cost_observable(cost_edges: list[list[int]]) -> dict[str, Any]:
    """Return a normalized MaxCut cost observable as a weighted Pauli sum."""
    return {
        "name": "maxcut_cost",
        "kind": "pauli_sum",
        "objective": "maximize",
        "constant": float(len(cost_edges)) / 2.0,
        "source": "qaoa_maxcut",
        "terms": [
            {
                "pauli": "ZZ",
                "qubits": [int(left), int(right)],
                "coefficient": -0.5,
            }
            for left, right in cost_edges
        ],
    }


def normalize_observable_specs(value: object) -> list[dict[str, Any]]:
    """Normalize user-declared observable specs into a stable IR shape."""
    if value is None:
        return []
    if not isinstance(value, list):
        raise TypeError("observables must be a list of observable objects")

    normalized: list[dict[str, Any]] = []
    for observable in value:
        if not isinstance(observable, dict):
            raise TypeError("observable entries must be objects")
        result = dict(observable)
        result["name"] = str(result.get("name", "")).strip()
        result["kind"] = str(result.get("kind", "pauli_sum")).strip().lower()
        objective = result.get("objective")
        if objective is not None:
            result["objective"] = str(objective).strip().lower()
        constant = result.get("constant")
        if constant is not None:
            result["constant"] = float(constant)
        terms = result.get("terms", [])
        if not isinstance(terms, list):
            raise TypeError("observable terms must be a list")
        normalized_terms: list[dict[str, Any]] = []
        for term in terms:
            if not isinstance(term, dict):
                raise TypeError("observable terms must be objects")
            normalized_terms.append(
                {
                    "pauli": str(term.get("pauli", "")).strip().upper(),
                    "qubits": [int(qubit) for qubit in term.get("qubits", [])],
                    "coefficient": float(term.get("coefficient", 1.0)),
                }
            )
        result["terms"] = normalized_terms
        normalized.append(result)
    return normalized
