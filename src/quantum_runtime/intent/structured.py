"""Structured models for parsed intent files."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class IntentModel(BaseModel):
    """Normalized intent data consumed by later planning stages."""

    title: str | None = None
    goal: str
    exports: list[str] = Field(default_factory=lambda: ["qiskit", "qasm3"])
    backend_preferences: list[str] = Field(default_factory=lambda: ["qiskit-local"])
    constraints: dict[str, Any] = Field(default_factory=dict)
    shots: int = 1024
    notes: str | None = None
