"""Rule-based intent to QSpec planner."""

from __future__ import annotations

import re

from quantum_runtime.errors import ManualQspecRequiredError
from quantum_runtime.intent.structured import IntentModel
from quantum_runtime.qspec import Constraints, MeasureNode, PatternNode, QSpec, Register


def plan_to_qspec(intent: IntentModel) -> QSpec:
    """Lower a parsed intent into the v0.1 QSpec IR."""
    pattern = _detect_pattern(intent.goal)
    size = _infer_size(intent, pattern)

    constraints = Constraints(
        max_width=_as_optional_int(intent.constraints.get("max_width")),
        max_depth=_as_optional_int(intent.constraints.get("max_depth")),
        basis_gates=_as_optional_string_list(intent.constraints.get("basis_gates")),
        connectivity_map=_as_optional_connectivity_map(intent.constraints.get("connectivity_map")),
        backend_provider=_as_optional_str(intent.constraints.get("backend_provider")),
        backend_name=_as_optional_str(intent.constraints.get("backend_name")),
        shots=int(intent.shots),
        optimization_level=_as_int(intent.constraints.get("optimization_level"), default=2),
    )

    return QSpec(
        program_id=f"prog_{pattern}_{size}",
        title=intent.title,
        goal=intent.goal,
        registers=[
            Register(kind="qubit", name="q", size=size),
            Register(kind="cbit", name="c", size=size),
        ],
        body=[
            PatternNode(pattern=pattern, args={"register": "q", "size": size}),
            MeasureNode(
                qubits=[f"q[{index}]" for index in range(size)],
                cbits=[f"c[{index}]" for index in range(size)],
            ),
        ],
        constraints=constraints,
        backend_preferences=list(intent.backend_preferences),
        metadata={"source": "intent"},
    )


def _detect_pattern(goal: str) -> str:
    normalized = goal.lower()
    if "ghz" in normalized:
        return "ghz"
    if "bell" in normalized:
        return "bell"
    if "qft" in normalized:
        return "qft"
    if "hardware efficient ansatz" in normalized or "hardware-efficient ansatz" in normalized or "hea" in normalized:
        return "hardware_efficient_ansatz"
    if "qaoa" in normalized and "maxcut" in normalized:
        return "qaoa_ansatz"
    raise ManualQspecRequiredError(
        "Unable to infer a supported pattern from intent. Provide a manual QSpec."
    )


def _infer_size(intent: IntentModel, pattern: str) -> int:
    goal_match = re.search(r"(\d+)\s*-\s*qubit|(\d+)\s+qubit|(\d+)\s*-\s*qubits|(\d+)\s+qubits", intent.goal.lower())
    if goal_match:
        for group in goal_match.groups():
            if group is not None:
                return int(group)

    max_width = intent.constraints.get("max_width")
    if max_width is not None:
        return int(max_width)

    if pattern == "bell":
        return 2
    return 4


def _as_optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _as_int(value: object, default: int) -> int:
    if value is None:
        return default
    return int(value)


def _as_optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _as_optional_string_list(value: object) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("Expected a list of strings in intent constraints.")
    return [str(item) for item in value]


def _as_optional_connectivity_map(value: object) -> list[tuple[int, int]] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("Expected a list of edge pairs in intent constraints.")
    edges: list[tuple[int, int]] = []
    for item in value:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("Each connectivity edge must contain exactly two qubit indices.")
        edges.append((int(item[0]), int(item[1])))
    return edges
