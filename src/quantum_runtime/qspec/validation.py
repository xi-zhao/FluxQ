"""Normalization and semantic validation for QSpec models."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from quantum_runtime.errors import StructuredQuantumRuntimeError

from .model import MeasureNode, PatternNode, QSpec


class QSpecValidationError(StructuredQuantumRuntimeError):
    """Raised when a QSpec passes schema validation but fails semantic checks."""

    code = "invalid_qspec"

    def __init__(self, message: str, *, issues: list[str] | None = None) -> None:
        rendered_message = message if not issues else f"{message}: " + "; ".join(issues)
        super().__init__(rendered_message)
        self.issues = issues or []


def normalize_qspec(qspec: QSpec) -> QSpec:
    """Return a canonicalized copy of a QSpec."""
    payload = qspec.model_dump(mode="python")

    payload["program_id"] = _strip_string(payload.get("program_id"))
    payload["title"] = _strip_optional_string(payload.get("title"))
    payload["goal"] = _strip_string(payload.get("goal"))
    payload["entrypoint"] = _strip_string(payload.get("entrypoint"))

    payload["registers"] = [
        {
            **register,
            "name": _strip_string(register.get("name")),
        }
        for register in payload.get("registers", [])
    ]

    payload["backend_preferences"] = _dedupe_strings(
        _strip_optional_string(item) for item in payload.get("backend_preferences", [])
    ) or ["qiskit-local"]

    constraints = dict(payload.get("constraints", {}))
    constraints["basis_gates"] = _dedupe_strings(
        _strip_optional_string(item) for item in constraints.get("basis_gates") or []
    )
    constraints["backend_provider"] = _strip_optional_string(constraints.get("backend_provider"))
    constraints["backend_name"] = _strip_optional_string(constraints.get("backend_name"))
    connectivity_map = constraints.get("connectivity_map")
    if connectivity_map is not None:
        constraints["connectivity_map"] = _normalize_connectivity_map(connectivity_map)
    payload["constraints"] = constraints
    payload["parameters"] = [_normalize_parameter(parameter) for parameter in payload.get("parameters", [])]

    return QSpec.model_validate(payload)


def validate_qspec(qspec: QSpec) -> QSpec:
    """Validate a normalized QSpec for the deterministic runtime pipeline."""
    issues: list[str] = []

    _require_non_empty(qspec.program_id, "program_id", issues)
    _require_non_empty(qspec.goal, "goal", issues)
    _require_non_empty(qspec.entrypoint, "entrypoint", issues)

    if len(qspec.registers) != 2:
        issues.append("expected exactly one qubit register and one cbit register")
    else:
        qubit_register, cbit_register = qspec.registers
        if qubit_register.kind != "qubit":
            issues.append("first register must be a qubit register")
        if cbit_register.kind != "cbit":
            issues.append("second register must be a cbit register")
        _require_positive_int(qubit_register.size, "registers[0].size", issues)
        _require_positive_int(cbit_register.size, "registers[1].size", issues)
        _validate_register_names((qubit_register, cbit_register), issues)

    if not qspec.body:
        issues.append("body must contain at least one semantic pattern and a measure node")
    else:
        _validate_body(qspec, issues)

    _require_positive_int(qspec.constraints.shots, "constraints.shots", issues)
    _validate_optimization_level(qspec.constraints.optimization_level, issues)
    _validate_constraint_bounds(qspec, issues)
    _validate_parameters(qspec, issues)

    if issues:
        raise QSpecValidationError("QSpec validation failed", issues=issues)
    return qspec


def _validate_body(qspec: QSpec, issues: list[str]) -> None:
    patterns = [node for node in qspec.body if isinstance(node, PatternNode)]
    measures = [node for node in qspec.body if isinstance(node, MeasureNode)]

    if not patterns:
        issues.append("body must include at least one pattern node")
    if not measures:
        issues.append("body must include a measure node")
        return

    if not isinstance(qspec.body[-1], MeasureNode):
        issues.append("measure node must be the final node")

    measure = measures[-1]
    qubit_register, cbit_register = qspec.registers
    expected_qubits = [f"{qubit_register.name}[{index}]" for index in range(qubit_register.size)]
    expected_cbits = [f"{cbit_register.name}[{index}]" for index in range(cbit_register.size)]

    if measure.qubits != expected_qubits:
        issues.append("measure node must cover all qubits in register order")
    if measure.cbits != expected_cbits:
        issues.append("measure node must cover all cbits in register order")
    if len(measure.qubits) != len(measure.cbits):
        issues.append("measure node must map each qubit to one classical bit")


def _validate_constraint_bounds(qspec: QSpec, issues: list[str]) -> None:
    qubit_size = qspec.registers[0].size if qspec.registers else 0
    max_width = qspec.constraints.max_width
    if max_width is not None and max_width < qubit_size:
        issues.append("constraints.max_width must be at least the qubit register width")

    max_depth = qspec.constraints.max_depth
    if max_depth is not None and max_depth <= 0:
        issues.append("constraints.max_depth must be positive when provided")

    connectivity_map = qspec.constraints.connectivity_map or []
    for left, right in connectivity_map:
        if left < 0 or right < 0:
            issues.append("connectivity_map indices must be non-negative")
            continue
        if left >= qubit_size or right >= qubit_size:
            issues.append("connectivity_map indices must fit within the qubit register")
        if left == right:
            issues.append("connectivity_map cannot contain self-loops")


def _validate_parameters(qspec: QSpec, issues: list[str]) -> None:
    seen_names: set[str] = set()
    for index, parameter in enumerate(qspec.parameters):
        name = str(parameter.get("name", "")).strip()
        if not name:
            issues.append(f"parameters[{index}].name must be non-empty")
            continue
        if name in seen_names:
            issues.append("parameter names must be unique")
        seen_names.add(name)
        if "default" in parameter:
            try:
                float(parameter["default"])
            except (TypeError, ValueError):
                issues.append(f"parameters[{index}].default must be numeric")

    for node in qspec.body:
        if not isinstance(node, PatternNode):
            continue
        size = int(node.args.get("size", qspec.registers[0].size))
        if node.pattern == "hardware_efficient_ansatz":
            layers = int(node.args.get("layers", 1))
            if layers <= 0:
                issues.append("hardware_efficient_ansatz layers must be positive")
            rotation_blocks = node.args.get("rotation_blocks", [])
            if not isinstance(rotation_blocks, list) or not rotation_blocks:
                issues.append("hardware_efficient_ansatz rotation_blocks must be a non-empty list")
            else:
                invalid_blocks = [
                    str(block)
                    for block in rotation_blocks
                    if str(block) not in {"rx", "ry", "rz"}
                ]
                if invalid_blocks:
                    issues.append("hardware_efficient_ansatz rotation_blocks must be rx, ry, or rz")
            _validate_edge_pairs(
                node.args.get("entanglement_edges", []),
                size=size,
                field_name="hardware_efficient_ansatz entanglement_edges",
                issues=issues,
            )
            expected = layers * size * len(rotation_blocks or [])
            actual = _count_family_parameters(qspec, "hardware_efficient_ansatz")
            if expected and actual != expected:
                issues.append("hardware_efficient_ansatz parameter count does not match layers * qubits * rotation blocks")
        if node.pattern == "qaoa_ansatz":
            layers = int(node.args.get("layers", 1))
            if layers <= 0:
                issues.append("qaoa_ansatz layers must be positive")
            if str(node.args.get("cost_operator", "zz")) != "zz":
                issues.append("qaoa_ansatz cost_operator must be zz")
            if str(node.args.get("mixer", "rx")) != "rx":
                issues.append("qaoa_ansatz mixer must be rx")
            _validate_edge_pairs(
                node.args.get("cost_edges", []),
                size=size,
                field_name="qaoa_ansatz cost_edges",
                issues=issues,
            )
            gamma_count = _count_parameter_role(qspec, family="qaoa_ansatz", role="cost")
            beta_count = _count_parameter_role(qspec, family="qaoa_ansatz", role="mixer")
            if gamma_count != layers or beta_count != layers:
                issues.append("qaoa_ansatz must define one gamma and one beta parameter per layer")


def _validate_edge_pairs(
    value: object,
    *,
    size: int,
    field_name: str,
    issues: list[str],
) -> None:
    if not isinstance(value, list):
        issues.append(f"{field_name} must be a list of edge pairs")
        return

    for edge in value:
        if not isinstance(edge, (list, tuple)) or len(edge) != 2:
            issues.append(f"{field_name} entries must contain exactly two indices")
            continue
        left = int(edge[0])
        right = int(edge[1])
        if left < 0 or right < 0:
            issues.append(f"{field_name} indices must be non-negative")
            continue
        if left >= size or right >= size:
            issues.append(f"{field_name} indices must fit within the qubit register")
        if left == right:
            issues.append(f"{field_name} cannot contain self-loops")


def _validate_register_names(registers: Iterable[Any], issues: list[str]) -> None:
    names = [register.name for register in registers]
    if any(not name for name in names):
        issues.append("register names must be non-empty")
    if len(set(names)) != len(names):
        issues.append("register names must be unique")


def _validate_optimization_level(optimization_level: int, issues: list[str]) -> None:
    if optimization_level < 0 or optimization_level > 3:
        issues.append("constraints.optimization_level must be between 0 and 3")


def _require_non_empty(value: str, field_name: str, issues: list[str]) -> None:
    if not value:
        issues.append(f"{field_name} must be non-empty")


def _require_positive_int(value: int, field_name: str, issues: list[str]) -> None:
    if value <= 0:
        issues.append(f"{field_name} must be positive")


def _strip_string(value: object) -> str:
    return str(value).strip()


def _strip_optional_string(value: object) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


def _dedupe_strings(values: Iterable[str | None]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _normalize_connectivity_map(value: object) -> list[tuple[int, int]]:
    if not isinstance(value, list):
        raise TypeError("connectivity_map must be a list of edges")

    result: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for edge in value:
        if not isinstance(edge, (list, tuple)) or len(edge) != 2:
            raise TypeError("each connectivity edge must contain exactly two indices")
        normalized = (int(edge[0]), int(edge[1]))
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _normalize_parameter(parameter: object) -> dict[str, Any]:
    if not isinstance(parameter, dict):
        raise TypeError("parameter entries must be objects")

    result = dict(parameter)
    if "name" in result:
        result["name"] = _strip_string(result["name"])
    for key in ("kind", "family", "gate", "role"):
        if key in result:
            result[key] = _strip_optional_string(result[key])
    if "default" in result and result["default"] is not None:
        result["default"] = float(result["default"])
    return result


def _count_family_parameters(qspec: QSpec, family: str) -> int:
    return sum(1 for parameter in qspec.parameters if str(parameter.get("family")) == family)


def _count_parameter_role(qspec: QSpec, *, family: str, role: str) -> int:
    return sum(
        1
        for parameter in qspec.parameters
        if str(parameter.get("family")) == family and str(parameter.get("role")) == role
    )
