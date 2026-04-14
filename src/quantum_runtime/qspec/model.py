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


class CanonicalProblem(BaseModel):
    """Canonical problem definition carried by the runtime IR."""

    kind: str | None = None
    definition: dict[str, Any] = Field(default_factory=dict)


class CanonicalParameterSpace(BaseModel):
    """Canonical parameter-space metadata for the runtime IR."""

    mode: str | None = None
    parameters: list[dict[str, Any]] = Field(default_factory=list)
    workflow: dict[str, Any] = Field(default_factory=dict)


class CanonicalObjective(BaseModel):
    """Canonical objective metadata for the runtime IR."""

    kind: str | None = None
    observable: str | None = None
    goal: str | None = None
    evaluation_method: str | None = None


class ExportRequirements(BaseModel):
    """Requested export formats and profiles for one run."""

    formats: list[str] = Field(default_factory=list)
    profiles: list[str] = Field(default_factory=list)


class PolicyHints(BaseModel):
    """Policy hints that downstream compare or CI loops may use."""

    fail_on: list[str] = Field(default_factory=list)
    compare_expectation: str | None = None
    allow_report_drift: bool = True


class ProvenanceHints(BaseModel):
    """Ingress provenance for one canonical runtime object."""

    ingress_kind: str | None = None
    ingress_source: str | None = None


class RuntimeMetadata(BaseModel):
    """Canonical runtime metadata layered on top of the circuit IR."""

    workload_id: str | None = None
    algorithm_family: str | None = None
    problem: CanonicalProblem = Field(default_factory=CanonicalProblem)
    parameter_space: CanonicalParameterSpace = Field(default_factory=CanonicalParameterSpace)
    objective: CanonicalObjective = Field(default_factory=CanonicalObjective)
    export_requirements: ExportRequirements = Field(default_factory=ExportRequirements)
    policy_hints: PolicyHints = Field(default_factory=PolicyHints)
    provenance: ProvenanceHints = Field(default_factory=ProvenanceHints)


class QSpec(BaseModel):
    """Top-level intermediate representation for deterministic planning."""

    schema_version: str = "0.3.0"
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
    runtime: RuntimeMetadata = Field(default_factory=RuntimeMetadata)
    metadata: dict[str, Any] = Field(default_factory=dict)
