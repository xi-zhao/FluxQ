"""Stable semantic summaries for QSpec payloads."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .model import PatternNode, QSpec


def summarize_qspec_semantics(qspec: QSpec) -> dict[str, Any]:
    """Return a host-friendly semantic summary of the active QSpec."""
    pattern_node = _first_pattern(qspec)
    parameter_records = [_normalize_parameter(parameter) for parameter in qspec.parameters]
    summary: dict[str, Any] = {
        "program_id": qspec.program_id,
        "pattern": pattern_node.pattern,
        "register": str(pattern_node.args.get("register", "q")),
        "width": qspec.registers[0].size if qspec.registers else 0,
        "layers": _optional_int(pattern_node.args.get("layers")),
        "pattern_args": _normalize_value(pattern_node.args),
        "parameter_count": len(parameter_records),
        "parameters": parameter_records,
        "constraints": {
            "max_width": qspec.constraints.max_width,
            "max_depth": qspec.constraints.max_depth,
            "basis_gates": list(qspec.constraints.basis_gates or []),
            "connectivity_map": [list(edge) for edge in qspec.constraints.connectivity_map or []],
            "backend_provider": qspec.constraints.backend_provider,
            "backend_name": qspec.constraints.backend_name,
            "shots": qspec.constraints.shots,
            "optimization_level": qspec.constraints.optimization_level,
        },
        "backend_preferences": list(qspec.backend_preferences),
    }
    summary["semantic_hash"] = _semantic_hash(summary)
    return summary


def _first_pattern(qspec: QSpec) -> PatternNode:
    for node in qspec.body:
        if isinstance(node, PatternNode):
            return node
    raise ValueError("QSpec does not contain a pattern node.")


def _normalize_parameter(parameter: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key in ("name", "kind", "family", "role", "gate", "layer", "qubit", "default"):
        if key not in parameter:
            continue
        value = parameter[key]
        if value is None:
            continue
        normalized[key] = _normalize_value(value)
    return normalized


def _normalize_value(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_normalize_value(item) for item in value]
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _normalize_value(item)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    return value


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, str)):
        return int(value)
    raise TypeError("layers must be an int-compatible value")


def _semantic_hash(summary: dict[str, Any]) -> str:
    payload = {key: value for key, value in summary.items() if key != "semantic_hash"}
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
