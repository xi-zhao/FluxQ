"""Pydantic models for the v0.1 Quantum Runtime IR."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Register(BaseModel):
    """A named qubit or classical register."""

    kind: Literal["qubit", "cbit"]
    name: str
    size: int


class Constraints(BaseModel):
    """Execution and target constraints carried by QSpec."""

    max_width: int | None = None
    max_depth: int | None = None
    basis_gates: list[str] | None = None
    connectivity_map: list[tuple[int, int]] | None = None
    backend_provider: str | None = None
    backend_name: str | None = None
    shots: int = 1024
    optimization_level: int = 2


class PatternNode(BaseModel):
    """A high-level semantic circuit pattern."""

    kind: Literal["pattern"] = "pattern"
    pattern: Literal[
        "ghz",
        "bell",
        "qft",
        "hardware_efficient_ansatz",
        "qaoa_ansatz",
    ]
    args: dict[str, Any] = Field(default_factory=dict)


class MeasureNode(BaseModel):
    """Measure qubits into classical bits."""

    kind: Literal["measure"] = "measure"
    qubits: list[str]
    cbits: list[str]


class QSpec(BaseModel):
    """Top-level intermediate representation for deterministic planning."""

    version: str = "0.1"
    program_id: str
    title: str | None = None
    goal: str
    entrypoint: str = "main"
    registers: list[Register]
    parameters: list[dict[str, Any]] = Field(default_factory=list)
    body: list[PatternNode | MeasureNode]
    observables: list[dict[str, Any]] = Field(default_factory=list)
    constraints: Constraints = Field(default_factory=Constraints)
    backend_preferences: list[str] = Field(default_factory=lambda: ["qiskit-local"])
    metadata: dict[str, Any] = Field(default_factory=dict)
