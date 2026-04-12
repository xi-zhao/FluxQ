"""Portable revision bundle helpers."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

from quantum_runtime.errors import WorkspaceConflictError, WorkspaceRecoveryRequiredError
from quantum_runtime.workspace import (
    WorkspaceLockConflict,
    acquire_workspace_lock,
    atomic_write_text,
    pending_atomic_write_files,
)

if TYPE_CHECKING:
    from quantum_runtime.workspace import WorkspacePaths

PACK_BUNDLE_REQUIRED_ENTRIES = (
    "intent.json",
    "qspec.json",
    "plan.json",
    "report.json",
    "manifest.json",
    "events.jsonl",
    "exports/",
)


class PackResult(BaseModel):
    """Machine-readable result for `qrun pack`."""

    status: Literal["ok", "error"]
    workspace: str
    revision: str
    pack_root: str
    files: dict[str, str] = Field(default_factory=dict)
    inspection: dict[str, Any] = Field(default_factory=dict)


class PackInspectionResult(BaseModel):
    """Inspection result for a portable revision bundle."""

    status: Literal["ok", "error"]
    pack_root: str
    required: list[str] = Field(default_factory=lambda: list(PACK_BUNDLE_REQUIRED_ENTRIES))
    present: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)


PackResult.model_rebuild()
PackInspectionResult.model_rebuild()


def inspect_pack_bundle(pack_root: Path) -> PackInspectionResult:
    """Inspect one pack bundle for the required runtime objects and exports."""
    root = pack_root.resolve()
    present: list[str] = []
    missing: list[str] = []

    for entry in PACK_BUNDLE_REQUIRED_ENTRIES:
        candidate = root / entry.rstrip("/")
        exists = candidate.is_dir() if entry.endswith("/") else candidate.is_file()
        if exists:
            present.append(entry)
        else:
            missing.append(entry)

    return PackInspectionResult(
        status="ok" if not missing else "error",
        pack_root=str(root),
        present=present,
        missing=missing,
    )


def pack_revision(*, workspace_root: Path, revision: str) -> PackResult:
    """Package one revision into a portable runtime bundle directory."""
    from quantum_runtime.workspace import WorkspacePaths

    paths = WorkspacePaths(root=workspace_root)
    pack_root = paths.pack_revision_dir(revision)
    staged_root = paths.packs_dir / f".{revision}.tmp"

    try:
        with acquire_workspace_lock(paths.root, command=f"qrun pack {revision}"):
            _guard_pack_backfill_paths(paths=paths, revision=revision)
            if staged_root.exists():
                shutil.rmtree(staged_root)
            if pack_root.exists():
                shutil.rmtree(pack_root)
            staged_root.mkdir(parents=True, exist_ok=True)

            core_files = {
                "intent": _resolve_intent_json(paths=paths, revision=revision),
                "qspec": paths.root / "specs" / "history" / f"{revision}.json",
                "plan": _resolve_plan_json(paths=paths, revision=revision),
                "report": paths.root / "reports" / "history" / f"{revision}.json",
                "manifest": paths.manifest_history_json(revision),
            }
            copied_files: dict[str, str] = {}
            destination_names = {
                "intent": "intent.json",
                "qspec": "qspec.json",
                "plan": "plan.json",
                "report": "report.json",
                "manifest": "manifest.json",
            }
            for name, source_path in core_files.items():
                destination_path = staged_root / destination_names[name]
                _copy_file(source_path, destination_path)
                copied_files[name] = str(destination_path)

            events_path = _write_revision_events(paths=paths, revision=revision, destination=staged_root / "events.jsonl")
            copied_files["events"] = str(events_path)

            artifact_root = paths.root / "artifacts" / "history" / revision
            exports_root = staged_root / "exports"
            exports_root.mkdir(parents=True, exist_ok=True)
            if artifact_root.exists():
                for child in artifact_root.iterdir():
                    destination = exports_root / child.name
                    if child.is_dir():
                        shutil.copytree(child, destination, dirs_exist_ok=True)
                    else:
                        _copy_file(child, destination)
            copied_files["exports"] = str(exports_root)
            _copy_optional_artifacts(paths=paths, revision=revision, pack_root=staged_root, copied_files=copied_files)

            inspection = inspect_pack_bundle(staged_root)
            if inspection.status != "ok":
                raise RuntimeError(f"packed bundle verification failed: {inspection.missing}")

            os.replace(staged_root, pack_root)
            copied_files = {
                name: value.replace(str(staged_root), str(pack_root))
                for name, value in copied_files.items()
            }
            return PackResult(
                status="ok",
                workspace=str(paths.root),
                revision=revision,
                pack_root=str(pack_root),
                files=copied_files,
                inspection=inspection.model_dump(mode="json"),
            )
    except WorkspaceLockConflict as exc:
        raise WorkspaceConflictError(
            workspace=paths.root,
            lock_path=Path(exc.lock_path),
            holder=exc.holder.model_dump(mode="json"),
        ) from exc
    finally:
        if staged_root.exists():
            shutil.rmtree(staged_root)


def _resolve_intent_json(*, paths: WorkspacePaths, revision: str) -> Path:
    from quantum_runtime.runtime.resolve import resolve_runtime_input

    candidate = paths.intent_history_json(revision)
    if candidate.exists():
        return candidate
    _guard_pending_backfill_file(candidate, workspace_root=paths.root)
    resolution = resolve_runtime_input(
        workspace_root=paths.root,
        report_file=paths.root / "reports" / "history" / f"{revision}.json",
    )
    payload = resolution.intent_resolution.model_dump_json(indent=2)
    atomic_write_text(candidate, payload)
    return candidate


def _resolve_plan_json(*, paths: WorkspacePaths, revision: str) -> Path:
    from quantum_runtime.runtime.control_plane import build_execution_plan

    candidate = paths.plan_history_json(revision)
    if candidate.exists():
        return candidate

    _guard_pending_backfill_file(candidate, workspace_root=paths.root)
    payload = build_execution_plan(
        workspace_root=paths.root,
        report_file=paths.root / "reports" / "history" / f"{revision}.json",
    ).model_dump_json(indent=2)
    atomic_write_text(candidate, payload)
    return candidate


def _write_revision_events(*, paths: WorkspacePaths, revision: str, destination: Path) -> Path:
    source = paths.events_jsonl if paths.events_jsonl.exists() else paths.trace_events
    selected: list[str] = []
    if source.exists():
        for line in source.read_text().splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(payload.get("revision")) == revision:
                selected.append(json.dumps(payload, ensure_ascii=True))
    atomic_write_text(destination, "\n".join(selected) + ("\n" if selected else ""))
    return destination


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _copy_optional_artifacts(
    *,
    paths: WorkspacePaths,
    revision: str,
    pack_root: Path,
    copied_files: dict[str, str],
) -> None:
    optional_sources = {
        "bench": paths.benchmark_history_json(revision),
        "doctor": paths.doctor_history_json(revision),
    }
    compare_candidate = _compare_artifact_for_revision(paths=paths, revision=revision)
    if compare_candidate is not None:
        optional_sources["compare"] = compare_candidate

    for name, source in optional_sources.items():
        if not source.exists():
            continue
        destination = pack_root / f"{name}.json"
        _copy_file(source, destination)
        copied_files[name] = str(destination)


def _compare_artifact_for_revision(*, paths: WorkspacePaths, revision: str) -> Path | None:
    latest = paths.compare_latest_json
    if not latest.exists():
        return None
    try:
        payload = json.loads(latest.read_text())
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    left = payload.get("left") if isinstance(payload.get("left"), dict) else {}
    right = payload.get("right") if isinstance(payload.get("right"), dict) else {}
    if revision not in {str(left.get("revision", "")), str(right.get("revision", ""))}:
        return None
    return latest


def _guard_pending_backfill_file(candidate: Path, *, workspace_root: Path) -> None:
    pending_files = pending_atomic_write_files(candidate)
    if not pending_files:
        return
    raise WorkspaceRecoveryRequiredError(
        workspace=workspace_root.resolve(),
        pending_files=pending_files,
        last_valid_revision=candidate.stem,
    )


def _guard_pack_backfill_paths(*, paths: WorkspacePaths, revision: str) -> None:
    pending_files = sorted(
        {
            pending
            for candidate in (
                paths.intent_history_json(revision),
                paths.plan_history_json(revision),
            )
            for pending in pending_atomic_write_files(candidate)
        }
    )
    if not pending_files:
        return
    raise WorkspaceRecoveryRequiredError(
        workspace=paths.root,
        pending_files=pending_files,
        last_valid_revision=revision,
    )
