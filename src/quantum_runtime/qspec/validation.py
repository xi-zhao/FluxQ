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
