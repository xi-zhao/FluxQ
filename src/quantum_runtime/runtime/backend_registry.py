"""Unified backend capability registry for runtime host integrations."""

from __future__ import annotations

import importlib
from importlib import metadata
from typing import Any

from pydantic import BaseModel, Field


class BackendDependency(BaseModel):
    """Resolved dependency metadata for a backend."""

    module: str
    distribution: str
    available: bool
    version: str | None = None
    location: str | None = None
    error: str | None = None


class BackendCapabilityDescriptor(BaseModel):
    """Stable machine-readable backend descriptor."""

    backend: str
    provider: str
    available: bool
    reason: str | None = None
    module_dependencies: list[BackendDependency] = Field(default_factory=list)
    capabilities: dict[str, bool] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


def collect_backend_capabilities() -> dict[str, BackendCapabilityDescriptor]:
    """Return the runtime's known backend capability descriptors."""
    qiskit = _dependency_metadata(module_name="qiskit", distribution_name="qiskit")
    qiskit_aer = _dependency_metadata(module_name="qiskit_aer", distribution_name="qiskit-aer")
    classiq = _dependency_metadata(module_name="classiq", distribution_name="classiq")

    qiskit_local_available = qiskit.available and qiskit_aer.available
    classiq_available = classiq.available

    return {
        "qiskit-local": BackendCapabilityDescriptor(
            backend="qiskit-local",
            provider="qiskit",
            available=qiskit_local_available,
            reason=None if qiskit_local_available else (qiskit.error or qiskit_aer.error or "qiskit_unavailable"),
            module_dependencies=[qiskit, qiskit_aer],
            capabilities={
                "simulate_locally": True,
                "transpile_validation": True,
                "structural_benchmark": True,
                "classiq_synthesis": False,
                "remote_submit": False,
            },
            notes=["Local Qiskit backend"],
        ),
        "classiq": BackendCapabilityDescriptor(
            backend="classiq",
            provider="classiq",
            available=classiq_available,
            reason=None if classiq_available else classiq.error or "classiq_not_installed",
            module_dependencies=[classiq],
            capabilities={
                "simulate_locally": False,
                "transpile_validation": False,
                "structural_benchmark": True,
                "classiq_synthesis": True,
                "remote_submit": False,
            },
            notes=["Optional Classiq synthesis backend"],
        ),
    }


def backend_capabilities_as_dict() -> dict[str, dict[str, Any]]:
    """Return JSON-serializable backend capability descriptors."""
    return {name: descriptor.model_dump(mode="json") for name, descriptor in collect_backend_capabilities().items()}


def _dependency_metadata(*, module_name: str, distribution_name: str) -> BackendDependency:
    try:
        importlib.import_module(module_name)
    except Exception as exc:
        return BackendDependency(
            module=module_name,
            distribution=distribution_name,
            available=False,
            version=None,
            location=None,
            error=str(exc),
        )

    return BackendDependency(
        module=module_name,
        distribution=distribution_name,
        available=True,
        version=_dependency_version(distribution_name),
        location=_module_location(module_name),
        error=None,
    )


def _dependency_version(distribution_name: str) -> str | None:
    try:
        return metadata.version(distribution_name)
    except metadata.PackageNotFoundError:
        return None


def _module_location(module_name: str) -> str | None:
    try:
        module = importlib.import_module(module_name)
    except Exception:
        return None
    return getattr(module, "__file__", None)
