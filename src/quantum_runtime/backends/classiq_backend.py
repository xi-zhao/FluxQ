"""Optional Classiq synthesis backend."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Any, Iterator, Literal

from pydantic import BaseModel, Field

from quantum_runtime.lowering.classiq_emitter import write_classiq_program
from quantum_runtime.qspec import QSpec
from quantum_runtime.workspace import WorkspaceHandle


class ClassiqBackendReport(BaseModel):
    """Structured backend report for optional Classiq synthesis."""

    status: Literal["ok", "dependency_missing", "backend_unavailable", "error"]
    reason: str | None = None
    code_path: Path | None = None
    results_path: Path | None = None
    program_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


def run_classiq_backend(qspec: QSpec, workspace: WorkspaceHandle) -> ClassiqBackendReport:
    """Emit Classiq Python and synthesize it when the SDK is available."""
    code_path = workspace.root / "artifacts" / "classiq" / "main.py"

    if "classiq" not in qspec.backend_preferences:
        return ClassiqBackendReport(
            status="backend_unavailable",
            reason="classiq_backend_not_requested",
        )

    emit_result = write_classiq_program(qspec, code_path)
    if emit_result.status != "ok" or emit_result.path is None:
        return ClassiqBackendReport(
            status="backend_unavailable",
            reason=emit_result.reason,
            code_path=emit_result.path,
            details=dict(emit_result.details),
        )

    try:
        classiq_module = _load_classiq_module()
    except ModuleNotFoundError as exc:
        return ClassiqBackendReport(
            status="dependency_missing",
            reason="classiq_not_installed",
            code_path=emit_result.path,
            details={"import_error": str(exc)},
        )

    try:
        constraints = _build_constraints(classiq_module, qspec)
        preferences = _build_preferences(classiq_module, qspec)
        namespace = _load_generated_program(emit_result.path, classiq_module)
        model = classiq_module.create_model(
            namespace["main"],
            constraints=constraints,
            preferences=preferences,
        )
        program = classiq_module.synthesize(
            model,
            constraints=constraints,
            preferences=preferences,
        )
        results_path = emit_result.path.parent / "synthesis.json"
        program.save_results(results_path)
    except Exception as exc:
        return ClassiqBackendReport(
            status="error",
            reason="classiq_synthesis_failed",
            code_path=emit_result.path,
            details={"error": str(exc)},
        )

    return ClassiqBackendReport(
        status="ok",
        code_path=emit_result.path,
        results_path=results_path,
        program_id=getattr(program, "program_id", None),
        warnings=list(getattr(program, "synthesis_warnings", []) or []),
    )


def _load_classiq_module() -> Any:
    return importlib.import_module("classiq")


def _build_constraints(classiq_module: Any, qspec: QSpec) -> Any | None:
    kwargs: dict[str, Any] = {}
    if qspec.constraints.max_width is not None:
        kwargs["max_width"] = qspec.constraints.max_width
    if not kwargs:
        return None
    return classiq_module.Constraints(**kwargs)


def _build_preferences(classiq_module: Any, qspec: QSpec) -> Any | None:
    kwargs: dict[str, Any] = {
        "optimization_level": qspec.constraints.optimization_level,
    }
    if qspec.constraints.backend_provider is not None:
        kwargs["backend_service_provider"] = qspec.constraints.backend_provider
    if qspec.constraints.backend_name is not None:
        kwargs["backend_name"] = qspec.constraints.backend_name
    if not kwargs:
        return None
    return classiq_module.Preferences(**kwargs)


def _load_generated_program(path: Path, classiq_module: Any) -> dict[str, Any]:
    namespace: dict[str, Any] = {"__name__": "quantum_runtime.classiq_program"}
    with _classiq_module_installed(classiq_module):
        exec(compile(path.read_text(), str(path), "exec"), namespace)
    return namespace


@contextmanager
def _classiq_module_installed(classiq_module: Any) -> Iterator[None]:
    previous = sys.modules.get("classiq")
    sys.modules["classiq"] = _coerce_to_module(classiq_module)
    try:
        yield
    finally:
        if previous is None:
            sys.modules.pop("classiq", None)
        else:
            sys.modules["classiq"] = previous


def _coerce_to_module(value: Any) -> ModuleType:
    if isinstance(value, ModuleType):
        return value

    module = ModuleType("classiq")
    for key, attr in vars(value).items():
        setattr(module, key, attr)
    return module
