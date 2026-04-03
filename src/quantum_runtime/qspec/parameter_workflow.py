"""Helpers for parameter binding and sweep workflow metadata."""

from __future__ import annotations

from itertools import product
from typing import Any

from .model import QSpec


MAX_SWEEP_POINTS = 16


def parameter_defaults(qspec: QSpec) -> dict[str, float]:
    """Return the default numeric parameter bindings defined by the QSpec."""
    defaults: dict[str, float] = {}
    for parameter in qspec.parameters:
        name = str(parameter.get("name", "")).strip()
        if not name:
            continue
        default = parameter.get("default")
        if default is None:
            continue
        defaults[name] = float(default)
    return defaults


def parameter_names(qspec: QSpec) -> list[str]:
    """Return the ordered parameter schema names."""
    return list(parameter_defaults(qspec).keys())


def normalize_parameter_workflow(value: object) -> dict[str, Any]:
    """Normalize metadata parameter workflow declarations."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError("parameter_workflow must be an object")

    mode = str(value.get("mode", "")).strip().lower()
    result: dict[str, Any] = {"mode": mode}
    bindings = value.get("bindings")
    if bindings is not None:
        if not isinstance(bindings, dict):
            raise TypeError("parameter_workflow.bindings must be an object")
        result["bindings"] = {
            str(name).strip(): float(raw_value)
            for name, raw_value in bindings.items()
        }
    grid = value.get("grid")
    if grid is not None:
        if not isinstance(grid, dict):
            raise TypeError("parameter_workflow.grid must be an object")
        result["grid"] = {
            str(name).strip(): [float(item) for item in raw_values]
            for name, raw_values in grid.items()
            if isinstance(raw_values, list)
        }
    return result


def summarize_parameter_workflow(qspec: QSpec) -> dict[str, Any]:
    """Return a host-friendly summary of the declared parameter workflow."""
    defaults = parameter_defaults(qspec)
    raw = qspec.metadata.get("parameter_workflow")
    if not isinstance(raw, dict):
        return {
            "mode": "defaults",
            "point_count": 1 if defaults else 0,
            "binding_names": list(defaults.keys()),
            "bindings": defaults,
        }

    mode = str(raw.get("mode", "")).strip().lower()
    if mode == "binding":
        explicit = _coerce_bindings(raw.get("bindings"))
        bindings = {**defaults, **explicit}
        return {
            "mode": "binding",
            "point_count": 1,
            "binding_names": sorted(explicit.keys()),
            "bindings": bindings,
            "explicit_bindings": explicit,
        }

    if mode == "sweep":
        grid = _coerce_grid(raw.get("grid"))
        points = _expand_grid(defaults, grid)
        return {
            "mode": "sweep",
            "point_count": len(points),
            "binding_names": sorted(grid.keys()),
            "grid": grid,
            "points": points,
        }

    return {
        "mode": mode or "unknown",
        "point_count": 0,
        "binding_names": [],
    }


def representative_bindings(qspec: QSpec) -> dict[str, float]:
    """Return the single representative binding set for export/report identity."""
    summary = summarize_parameter_workflow(qspec)
    mode = summary.get("mode")
    if mode == "binding":
        return dict(summary.get("bindings", {}))
    return parameter_defaults(qspec)


def _coerce_bindings(value: object) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    return {
        str(name).strip(): float(raw_value)
        for name, raw_value in value.items()
    }


def _coerce_grid(value: object) -> dict[str, list[float]]:
    if not isinstance(value, dict):
        return {}
    return {
        str(name).strip(): [float(item) for item in raw_values]
        for name, raw_values in value.items()
        if isinstance(raw_values, list)
    }


def _expand_grid(defaults: dict[str, float], grid: dict[str, list[float]]) -> list[dict[str, float]]:
    if not grid:
        return []
    ordered_names = list(grid.keys())
    ordered_values = [grid[name] for name in ordered_names]
    points: list[dict[str, float]] = []
    for combination in product(*ordered_values):
        bindings = dict(defaults)
        for index, name in enumerate(ordered_names):
            bindings[name] = float(combination[index])
        points.append(bindings)
        if len(points) > MAX_SWEEP_POINTS:
            break
    return points
