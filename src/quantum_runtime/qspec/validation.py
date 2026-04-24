"""Normalization and semantic validation for QSpec models."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from quantum_runtime.errors import StructuredQuantumRuntimeError

from .observables import normalize_observable_specs
from .parameter_workflow import normalize_parameter_workflow
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
    payload["observables"] = normalize_observable_specs(payload.get("observables"))
    metadata = dict(payload.get("metadata", {}))
    if "parameter_workflow" in metadata:
        metadata["parameter_workflow"] = normalize_parameter_workflow(metadata.get("parameter_workflow"))
    payload["metadata"] = metadata

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
    _validate_observables(qspec, issues)
    _validate_parameter_workflow(qspec, issues)
    _validate_parameter_coverage(qspec, issues)

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
        if node.pattern == "bell":
            if size != 2 or qspec.registers[0].size != 2:
                issues.append("bell pattern requires exactly 2 qubits")
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


def _validate_observables(qspec: QSpec, issues: list[str]) -> None:
    qubit_size = qspec.registers[0].size if qspec.registers else 0
    objective_names: list[str] = []
    for index, observable in enumerate(qspec.observables):
        name = str(observable.get("name", "")).strip()
        if not name:
            issues.append(f"observables[{index}].name must be non-empty")
        kind = str(observable.get("kind", "")).strip().lower()
        if kind != "pauli_sum":
            issues.append("observable kind must be pauli_sum")
        terms = observable.get("terms")
        if not isinstance(terms, list) or not terms:
            issues.append("observable terms must be a non-empty list")
            continue
        objective = observable.get("objective")
        if objective is not None and str(objective) not in {"maximize", "minimize"}:
            issues.append("observable objective must be maximize or minimize when provided")
        elif objective is not None:
            objective_names.append(name or f"observables[{index}]")
        for term_index, term in enumerate(terms):
            if not isinstance(term, dict):
                issues.append(f"observables[{index}].terms[{term_index}] must be an object")
                continue
            pauli = str(term.get("pauli", "")).upper()
            qubits = term.get("qubits", [])
            if not pauli or any(axis not in {"X", "Y", "Z"} for axis in pauli):
                issues.append("observable pauli terms must be explicit X/Y/Z Pauli strings")
            if not isinstance(qubits, list) or len(qubits) != len(pauli):
                issues.append("observable qubits must match the pauli arity")
                continue
            for qubit in qubits:
                if int(qubit) < 0 or int(qubit) >= qubit_size:
                    issues.append("observable qubit indices must fit within the qubit register")
            try:
                float(term.get("coefficient", 1.0))
            except (TypeError, ValueError):
                issues.append("observable term coefficients must be numeric")
    if len(objective_names) > 1:
        issues.append("exact local evaluation currently supports at most one objective observable")


def _validate_parameter_workflow(qspec: QSpec, issues: list[str]) -> None:
    workflow = qspec.metadata.get("parameter_workflow")
    if workflow is None:
        return
    if not isinstance(workflow, dict):
        issues.append("metadata.parameter_workflow must be an object")
        return

    mode = str(workflow.get("mode", "")).strip().lower()
    valid_names = {str(parameter.get("name", "")).strip() for parameter in qspec.parameters}
    if mode not in {"binding", "sweep"}:
        issues.append("metadata.parameter_workflow.mode must be binding or sweep")
        return

    bindings = workflow.get("bindings")
    grid = workflow.get("grid")
    if mode == "binding":
        if grid:
            issues.append("metadata.parameter_workflow cannot declare both bindings and grid")
        if not isinstance(bindings, dict) or not bindings:
            issues.append("metadata.parameter_workflow.bindings must be a non-empty object")
            return
        for name, value in bindings.items():
            if str(name) not in valid_names:
                issues.append("metadata.parameter_workflow contains an unknown parameter name")
            try:
                float(value)
            except (TypeError, ValueError):
                issues.append("metadata.parameter_workflow bindings must be numeric")
    if mode == "sweep":
        if bindings:
            issues.append("metadata.parameter_workflow cannot declare both bindings and grid")
        if not isinstance(grid, dict) or not grid:
            issues.append("metadata.parameter_workflow.grid must be a non-empty object")
            return
        point_count = 1
        for name, values in grid.items():
            if str(name) not in valid_names:
                issues.append("metadata.parameter_workflow contains an unknown parameter name")
            if not isinstance(values, list) or not values:
                issues.append("metadata.parameter_workflow.grid entries must be non-empty lists")
                continue
            point_count *= len(values)
            for value in values:
                try:
                    float(value)
                except (TypeError, ValueError):
                    issues.append("metadata.parameter_workflow sweep values must be numeric")
        if point_count > 16:
            issues.append("metadata.parameter_workflow sweep grid must stay at or below 16 points")


def _validate_parameter_coverage(qspec: QSpec, issues: list[str]) -> None:
    workflow = qspec.metadata.get("parameter_workflow")
    covered_names: set[str] = set()
    if isinstance(workflow, dict):
        bindings = workflow.get("bindings")
        if isinstance(bindings, dict):
            covered_names.update(str(name).strip() for name in bindings)
        grid = workflow.get("grid")
        if isinstance(grid, dict):
            covered_names.update(str(name).strip() for name in grid)

    missing_names: list[str] = []
    for parameter in qspec.parameters:
        name = str(parameter.get("name", "")).strip()
        if not name:
            continue
        default = parameter.get("default")
        if default is not None:
            try:
                float(default)
                continue
            except (TypeError, ValueError):
                pass
        if name not in covered_names:
            missing_names.append(name)

    if missing_names:
        issues.append(
            "all declared parameters must have numeric defaults or be covered by metadata.parameter_workflow"
        )


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
