"""Rule-based intent to QSpec planner."""

from __future__ import annotations

import re
from typing import Any

from quantum_runtime.errors import ManualQspecRequiredError
from quantum_runtime.intent.structured import IntentModel
from quantum_runtime.qspec import Constraints, MeasureNode, PatternNode, QSpec, Register
from quantum_runtime.qspec.observables import (
    build_maxcut_cost_observable,
    normalize_observable_specs,
)


def plan_to_qspec(intent: IntentModel) -> QSpec:
    """Lower a parsed intent into the v0.1 QSpec IR."""
    pattern = _detect_pattern(intent.goal)
    size = _infer_size(intent, pattern)
    pattern_args, parameters, observables, metadata = _build_pattern_semantics(intent, pattern, size)

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
        parameters=parameters,
        observables=observables,
        body=[
            PatternNode(pattern=pattern, args=pattern_args),
            MeasureNode(
                qubits=[f"q[{index}]" for index in range(size)],
                cbits=[f"c[{index}]" for index in range(size)],
            ),
        ],
        constraints=constraints,
        backend_preferences=list(intent.backend_preferences),
        metadata={"source": "intent", **metadata},
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


def _build_pattern_semantics(
    intent: IntentModel,
    pattern: str,
    size: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    args: dict[str, Any] = {"register": "q", "size": size}
    parameters: list[dict[str, Any]] = []
    observables: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}

    if pattern == "hardware_efficient_ansatz":
        layers = _infer_layer_count(intent, default=2)
        rotation_blocks = _infer_rotation_blocks(intent)
        entanglement, entanglement_edges = _infer_entanglement(intent, size)
        args.update(
            {
                "layers": layers,
                "rotation_blocks": rotation_blocks,
                "entanglement": entanglement,
                "entanglement_edges": entanglement_edges,
            }
        )
        parameters.extend(
            _build_hea_parameters(
                size=size,
                layers=layers,
                rotation_blocks=rotation_blocks,
            )
        )
    elif pattern == "qaoa_ansatz":
        layers = _infer_qaoa_layers(intent)
        cost_edges = _infer_problem_graph(intent, size)
        args.update(
            {
                "layers": layers,
                "problem": "maxcut",
                "cost_operator": "zz",
                "mixer": "rx",
                "initial_state": "hadamard_all",
                "cost_edges": cost_edges,
            }
        )
        parameters.extend(
            _build_qaoa_parameters(
                layers=layers,
                gamma_defaults=_infer_angle_defaults(
                    intent.constraints.get("gamma_init"),
                    layers=layers,
                    base=0.4,
                    step=0.05,
                ),
                beta_defaults=_infer_angle_defaults(
                    intent.constraints.get("beta_init"),
                    layers=layers,
                    base=0.3,
                    step=0.04,
                ),
            )
        )
        observables.append(build_maxcut_cost_observable(cost_edges))

    parameter_workflow = _infer_parameter_workflow(intent)
    if parameter_workflow:
        metadata["parameter_workflow"] = parameter_workflow

    explicit_observables = normalize_observable_specs(intent.constraints.get("observables"))
    if explicit_observables:
        observables = explicit_observables

    return args, parameters, observables, metadata


def _infer_layer_count(intent: IntentModel, *, default: int) -> int:
    for key in ("layers", "layer_count", "repetitions", "depth_layers"):
        value = intent.constraints.get(key)
        if value is not None:
            return max(1, int(value))

    goal = intent.goal.lower()
    patterns = (
        r"(\d+)\s*-\s*layer",
        r"(\d+)\s+layer",
        r"layers?\s*[:=]?\s*(\d+)",
        r"p\s*=\s*(\d+)",
    )
    for pattern in patterns:
        match = re.search(pattern, goal)
        if match is not None:
            return max(1, int(match.group(1)))
    return default


def _infer_qaoa_layers(intent: IntentModel) -> int:
    for key in ("qaoa_layers", "p", "layers", "layer_count"):
        value = intent.constraints.get(key)
        if value is not None:
            return max(1, int(value))
    return _infer_layer_count(intent, default=1)


def _infer_problem_graph(intent: IntentModel, size: int) -> list[list[int]]:
    for key in ("maxcut_edges", "problem_graph", "cost_edges"):
        value = intent.constraints.get(key)
        if value is not None:
            return _normalize_edge_lists(value)

    connectivity_map = intent.constraints.get("connectivity_map")
    if connectivity_map is not None:
        return _normalize_edge_lists(connectivity_map)

    if size <= 2:
        return [[0, 1]]

    return [[index, (index + 1) % size] for index in range(size)]


def _infer_rotation_blocks(intent: IntentModel) -> list[str]:
    value = intent.constraints.get("rotation_blocks")
    if value is None:
        return ["ry", "rz"]
    if not isinstance(value, list) or not value:
        raise ValueError("rotation_blocks must be a non-empty list.")
    return [str(item).strip().lower() for item in value if str(item).strip()]


def _infer_entanglement(intent: IntentModel, size: int) -> tuple[str, list[list[int]]]:
    explicit_edges = intent.constraints.get("entanglement_edges")
    if explicit_edges is not None:
        return "custom", _normalize_edge_lists(explicit_edges)

    connectivity_map = intent.constraints.get("connectivity_map")
    if connectivity_map is not None:
        return "connectivity_map", _normalize_edge_lists(connectivity_map)

    entanglement = str(intent.constraints.get("entanglement", "linear")).strip().lower()
    if entanglement == "ring":
        return "ring", _ring_edges(size)
    return "linear", _linear_edges(size)


def _normalize_edge_lists(value: object) -> list[list[int]]:
    if not isinstance(value, list):
        raise ValueError("Expected a list of edge pairs for the problem graph.")

    edges: list[list[int]] = []
    for item in value:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("Each problem graph edge must contain exactly two indices.")
        edges.append([int(item[0]), int(item[1])])
    return edges


def _linear_edges(size: int) -> list[list[int]]:
    return [[index, index + 1] for index in range(size - 1)]


def _ring_edges(size: int) -> list[list[int]]:
    if size <= 2:
        return _linear_edges(size)
    return [[index, (index + 1) % size] for index in range(size)]


def _build_hea_parameters(
    *,
    size: int,
    layers: int,
    rotation_blocks: list[str],
) -> list[dict[str, Any]]:
    parameters: list[dict[str, Any]] = []
    for layer in range(layers):
        for qubit in range(size):
            for block in rotation_blocks:
                parameters.append(
                    {
                        "name": f"theta_{block}_l{layer}_q{qubit}",
                        "kind": "angle",
                        "family": "hardware_efficient_ansatz",
                        "gate": block,
                        "layer": layer,
                        "qubit": qubit,
                        "default": _default_hea_angle(block=block, layer=layer, qubit=qubit),
                    }
                )
    return parameters


def _build_qaoa_parameters(
    *,
    layers: int,
    gamma_defaults: list[float],
    beta_defaults: list[float],
) -> list[dict[str, Any]]:
    parameters: list[dict[str, Any]] = []
    for layer in range(layers):
        parameters.append(
            {
                "name": f"gamma_{layer}",
                "kind": "angle",
                "family": "qaoa_ansatz",
                "role": "cost",
                "layer": layer,
                "default": gamma_defaults[layer],
            }
        )
        parameters.append(
            {
                "name": f"beta_{layer}",
                "kind": "angle",
                "family": "qaoa_ansatz",
                "role": "mixer",
                "layer": layer,
                "default": beta_defaults[layer],
            }
        )
    return parameters


def _infer_angle_defaults(
    value: object,
    *,
    layers: int,
    base: float,
    step: float,
) -> list[float]:
    if isinstance(value, list) and value:
        defaults = [float(item) for item in value[:layers]]
        if len(defaults) < layers:
            defaults.extend(round(base + (step * index), 3) for index in range(len(defaults), layers))
        return defaults
    return [round(base + (step * index), 3) for index in range(layers)]


def _default_hea_angle(*, block: str, layer: int, qubit: int) -> float:
    base_by_gate = {
        "rx": 0.38,
        "ry": 0.5,
        "rz": 0.25,
    }
    base = base_by_gate.get(block, 0.2)
    return round(base + (0.05 * layer) + (0.02 * qubit), 3)


def _as_optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _infer_parameter_workflow(intent: IntentModel) -> dict[str, Any]:
    bindings = intent.constraints.get("parameter_bindings")
    sweep = intent.constraints.get("parameter_sweep")
    if bindings is not None:
        return {
            "mode": "binding",
            "bindings": {
                str(name).strip(): float(value)
                for name, value in dict(bindings).items()
            },
        }
    if sweep is not None:
        return {
            "mode": "sweep",
            "grid": {
                str(name).strip(): [float(item) for item in values]
                for name, values in dict(sweep).items()
            },
        }
    return {}


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
