"""Portable revision bundle helpers."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from quantum_runtime.errors import WorkspaceConflictError, WorkspaceRecoveryRequiredError
from quantum_runtime.runtime.contracts import SCHEMA_VERSION
from quantum_runtime.runtime.imports import ImportSourceError, validate_revision
from quantum_runtime.runtime.observability import (
    gate_block,
    next_actions_for_reason_codes,
    normalize_reason_codes,
)
from quantum_runtime.workspace import (
    WorkspaceManifest,
    WorkspaceLockConflict,
    WorkspacePaths,
    acquire_workspace_lock,
    atomic_copy_file,
    atomic_write_text,
    pending_atomic_write_files,
)

PACK_BUNDLE_REQUIRED_ENTRIES = (
    "intent.json",
    "qspec.json",
    "plan.json",
    "report.json",
    "manifest.json",
    "bundle_manifest.json",
    "events.jsonl",
    "trace.ndjson",
    "exports/",
)

_BUNDLE_MANIFEST_REQUIRED_PATHS = frozenset(
    {
        "intent.json",
        "qspec.json",
        "plan.json",
        "report.json",
        "manifest.json",
        "events.jsonl",
        "trace.ndjson",
    },
)


class BundleManifestEntry(BaseModel):
    """One bundled file recorded in bundle-local trust metadata."""

    path: str
    required: bool
    digest: str


class BundleManifest(BaseModel):
    """Bundle-local digest manifest for portable runtime bundles."""

    schema_version: str = SCHEMA_VERSION
    revision: str
    entries: list[BundleManifestEntry] = Field(default_factory=list)


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
    revision: str | None = None
    mismatched: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    gate: dict[str, Any] = Field(default_factory=dict)


class PackImportResult(BaseModel):
    """Machine-readable result for `qrun pack-import`."""

    status: Literal["ok", "error"]
    workspace: str
    revision: str
    pack_root: str
    files: dict[str, str] = Field(default_factory=dict)
    inspection: dict[str, Any] = Field(default_factory=dict)


BundleManifest.model_rebuild()
PackResult.model_rebuild()
PackInspectionResult.model_rebuild()
PackImportResult.model_rebuild()


def inspect_pack_bundle(pack_root: Path) -> PackInspectionResult:
    """Inspect one pack bundle for required runtime objects and trusted bundle bytes."""
    root = pack_root.resolve()
    present: list[str] = []
    missing: list[str] = []
    mismatched: list[str] = []
    reason_codes: list[str] = []

    for entry in PACK_BUNDLE_REQUIRED_ENTRIES:
        candidate = root / entry.rstrip("/")
        exists = candidate.is_dir() if entry.endswith("/") else candidate.is_file()
        if exists:
            present.append(entry)
        else:
            missing.append(entry)

    bundle_manifest = _load_bundle_manifest(root)
    revision = bundle_manifest.revision if bundle_manifest is not None else _fallback_bundle_revision(root)

    for item in missing:
        if item == "bundle_manifest.json":
            reason_codes.append("bundle_manifest_missing")
            continue
        reason_codes.append(f"bundle_required_missing:{item}")

    if bundle_manifest is not None:
        missing_from_manifest, mismatched_from_manifest = _verify_bundle_manifest_entries(
            root=root,
            bundle_manifest=bundle_manifest,
        )
        for item in missing_from_manifest:
            if item not in missing:
                missing.append(item)
            reason_codes.append(f"bundle_required_missing:{item}")
        for item in mismatched_from_manifest:
            mismatched.append(item)
            reason_codes.append(f"bundle_digest_mismatch:{item}")
        if _bundle_revision_mismatch(root=root, expected_revision=bundle_manifest.revision):
            reason_codes.append("bundle_revision_mismatch")

    reason_codes = normalize_reason_codes(reason_codes)
    next_actions = next_actions_for_reason_codes(reason_codes)
    status: Literal["ok", "error"] = "ok" if not reason_codes else "error"
    gate = gate_block(
        ready=status == "ok",
        severity="info" if status == "ok" else "error",
        reason_codes=reason_codes,
        next_actions=next_actions,
    )

    return PackInspectionResult(
        status=status,
        pack_root=str(root),
        present=present,
        missing=missing,
        revision=revision,
        mismatched=mismatched,
        reason_codes=reason_codes,
        next_actions=next_actions,
        gate=gate,
    )


def pack_revision(*, workspace_root: Path, revision: str) -> PackResult:
    """Package one revision into a portable runtime bundle directory."""
    paths = WorkspacePaths(root=workspace_root)
    revision = validate_revision(revision, source=revision)
    pack_root, staged_root, backup_root = _pack_roots(paths=paths, revision=revision)

    try:
        with acquire_workspace_lock(paths.root, command=f"qrun pack {revision}"):
            _guard_pack_history_paths(paths=paths, revision=revision)
            _reset_directory(staged_root)
            _reset_directory(backup_root)
            staged_root.mkdir(parents=True, exist_ok=True)

            copied_files: dict[str, str] = {}
            required_sources = {
                "intent": (
                    _required_history_file(
                        paths.intent_history_json(revision),
                        missing_code="pack_intent_history_missing",
                    ),
                    "intent.json",
                ),
                "qspec": (
                    _required_history_file(
                        _qspec_history_json(paths=paths, revision=revision),
                        missing_code="pack_qspec_history_missing",
                    ),
                    "qspec.json",
                ),
                "plan": (
                    _required_history_file(
                        paths.plan_history_json(revision),
                        missing_code="pack_plan_history_missing",
                    ),
                    "plan.json",
                ),
                "report": (
                    _required_history_file(
                        _report_history_json(paths=paths, revision=revision),
                        missing_code="pack_report_history_missing",
                    ),
                    "report.json",
                ),
                "manifest": (
                    _required_history_file(
                        paths.manifest_history_json(revision),
                        missing_code="pack_manifest_history_missing",
                    ),
                    "manifest.json",
                ),
                "events": (
                    _required_history_file(
                        paths.event_history_jsonl(revision),
                        missing_code="pack_events_history_missing",
                    ),
                    "events.jsonl",
                ),
                "trace": (
                    _required_history_file(
                        paths.trace_history_ndjson(revision),
                        missing_code="pack_trace_history_missing",
                    ),
                    "trace.ndjson",
                ),
            }

            for name, (source_path, destination_name) in required_sources.items():
                destination_path = staged_root / destination_name
                _copy_file(source_path, destination_path)
                copied_files[name] = str(destination_path)

            exports_root = staged_root / "exports"
            exports_root.mkdir(parents=True, exist_ok=True)
            _copy_exports(paths=paths, revision=revision, exports_root=exports_root)
            copied_files["exports"] = str(exports_root)

            _copy_optional_artifacts(
                paths=paths,
                revision=revision,
                pack_root=staged_root,
                copied_files=copied_files,
            )

            bundle_manifest_path = _write_bundle_manifest(staged_root=staged_root, revision=revision)
            copied_files["bundle_manifest"] = str(bundle_manifest_path)

            _verify_staged_bundle(staged_root=staged_root, revision=revision)
            _promote_verified_bundle(
                pack_root=pack_root,
                staged_root=staged_root,
                backup_root=backup_root,
            )
            inspection = inspect_pack_bundle(pack_root)
            copied_files = _rewrite_staged_paths(
                copied_files=copied_files,
                staged_root=staged_root,
                pack_root=pack_root,
            )
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
        _reset_directory(staged_root)
        _reset_directory(backup_root)


def import_pack_bundle(*, pack_root: Path, workspace_root: Path) -> PackImportResult:
    """Import one verified pack bundle into a workspace revision."""
    bundle_root = pack_root.resolve()
    inspection = inspect_pack_bundle(bundle_root)
    if inspection.status != "ok" or inspection.revision is None:
        raise ImportSourceError(
            "pack_bundle_invalid",
            source=str(bundle_root),
            details={"inspection": inspection.model_dump(mode="json")},
        )

    revision = validate_revision(inspection.revision, source=inspection.revision)
    paths = WorkspacePaths(root=workspace_root)

    try:
        with acquire_workspace_lock(paths.root, command=f"qrun pack-import {revision}"):
            for directory in paths.required_directories():
                directory.mkdir(parents=True, exist_ok=True)

            manifest = _load_or_create_workspace_manifest(paths)
            _guard_pack_import_paths(
                paths=paths,
                revision=revision,
                last_valid_revision=manifest.current_revision if manifest.current_revision != "rev_000000" else None,
            )

            copied_files = _import_bundle_history(
                bundle_root=bundle_root,
                paths=paths,
                revision=revision,
            )
            copied_files.update(
                _import_optional_bundle_members(
                    bundle_root=bundle_root,
                    paths=paths,
                    revision=revision,
                )
            )
            _promote_import_aliases(paths=paths, revision=revision)

            manifest.current_revision = revision
            manifest.active_spec = "specs/current.json"
            manifest.active_report = "reports/latest.json"
            manifest.save(paths.workspace_json)

            return PackImportResult(
                status="ok",
                workspace=str(paths.root),
                revision=revision,
                pack_root=str(bundle_root),
                files=copied_files,
                inspection=inspection.model_dump(mode="json"),
            )
    except WorkspaceLockConflict as exc:
        raise WorkspaceConflictError(
            workspace=paths.root,
            lock_path=Path(exc.lock_path),
            holder=exc.holder.model_dump(mode="json"),
        ) from exc


def _pack_roots(*, paths: WorkspacePaths, revision: str) -> tuple[Path, Path, Path]:
    validated_revision = validate_revision(revision, source=revision)
    packs_dir = paths.packs_dir.resolve()
    pack_root = paths.pack_revision_dir(validated_revision).resolve()
    staged_root = (paths.packs_dir / f".{validated_revision}.tmp").resolve()
    backup_root = (paths.packs_dir / f".{validated_revision}.bak").resolve()

    for candidate in (pack_root, staged_root, backup_root):
        if candidate.parent != packs_dir:
            raise ImportSourceError(
                "invalid_revision",
                source=revision,
                details={"expected_pattern": "rev_000001"},
            )

    return pack_root, staged_root, backup_root


def _required_history_file(source: Path, *, missing_code: str) -> Path:
    if source.exists():
        return source
    raise ImportSourceError(
        missing_code,
        source=str(source),
        details={"path": str(source)},
    )


def _qspec_history_json(*, paths: WorkspacePaths, revision: str) -> Path:
    return paths.root / "specs" / "history" / f"{revision}.json"


def _report_history_json(*, paths: WorkspacePaths, revision: str) -> Path:
    return paths.root / "reports" / "history" / f"{revision}.json"


def _copy_exports(*, paths: WorkspacePaths, revision: str, exports_root: Path) -> None:
    artifact_root = paths.root / "artifacts" / "history" / revision
    if not artifact_root.exists():
        return
    for child in sorted(artifact_root.iterdir()):
        destination = exports_root / child.name
        if child.is_dir():
            shutil.copytree(child, destination, dirs_exist_ok=True)
            continue
        _copy_file(child, destination)


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
    raw_left = payload.get("left")
    raw_right = payload.get("right")
    left: dict[str, Any] = raw_left if isinstance(raw_left, dict) else {}
    right: dict[str, Any] = raw_right if isinstance(raw_right, dict) else {}
    if revision not in {str(left.get("revision", "")), str(right.get("revision", ""))}:
        return None
    return latest


def _write_bundle_manifest(*, staged_root: Path, revision: str) -> Path:
    entries: list[BundleManifestEntry] = []
    for candidate in sorted(staged_root.rglob("*")):
        if not candidate.is_file():
            continue
        relative_path = candidate.relative_to(staged_root).as_posix()
        if relative_path == "bundle_manifest.json":
            continue
        entries.append(
            BundleManifestEntry(
                path=relative_path,
                required=_bundle_manifest_entry_required(relative_path),
                digest=f"sha256:{_sha256_file(candidate)}",
            ),
        )

    manifest = BundleManifest(revision=revision, entries=entries)
    bundle_manifest_path = staged_root / "bundle_manifest.json"
    bundle_manifest_path.write_text(manifest.model_dump_json(indent=2))
    return bundle_manifest_path


def _bundle_manifest_entry_required(relative_path: str) -> bool:
    return relative_path in _BUNDLE_MANIFEST_REQUIRED_PATHS or relative_path.startswith("exports/")


def _load_bundle_manifest(root: Path) -> BundleManifest | None:
    bundle_manifest_path = root / "bundle_manifest.json"
    if not bundle_manifest_path.is_file():
        return None
    try:
        return BundleManifest.model_validate_json(bundle_manifest_path.read_text())
    except ValueError:
        return None


def _fallback_bundle_revision(root: Path) -> str | None:
    for relative_path in ("manifest.json", "report.json"):
        payload = _load_json_object(root / relative_path)
        if payload is None:
            continue
        revision = _revision_from_payload(payload)
        if revision is not None:
            return revision
    return None


def _verify_bundle_manifest_entries(
    *,
    root: Path,
    bundle_manifest: BundleManifest,
) -> tuple[list[str], list[str]]:
    manifest_paths = {entry.path for entry in bundle_manifest.entries if entry.required}
    missing: list[str] = []
    mismatched: list[str] = []

    for required_path in sorted(_BUNDLE_MANIFEST_REQUIRED_PATHS - manifest_paths):
        missing.append(required_path)

    for entry in bundle_manifest.entries:
        if not entry.required:
            continue
        candidate = root / entry.path
        if not candidate.is_file():
            if entry.path not in missing:
                missing.append(entry.path)
            continue
        actual_digest = f"sha256:{_sha256_file(candidate)}"
        if actual_digest != entry.digest:
            mismatched.append(entry.path)

    return missing, mismatched


def _bundle_revision_mismatch(*, root: Path, expected_revision: str) -> bool:
    for relative_path in ("manifest.json", "report.json"):
        payload = _load_json_object(root / relative_path)
        if payload is None:
            continue
        revision = _revision_from_payload(payload)
        if revision is None:
            continue
        if revision != expected_revision:
            return True
    return False


def _load_json_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _revision_from_payload(payload: dict[str, Any]) -> str | None:
    top_level_revision = payload.get("revision")
    if isinstance(top_level_revision, str) and top_level_revision:
        return top_level_revision
    provenance = payload.get("provenance")
    if isinstance(provenance, dict):
        provenance_revision = provenance.get("revision")
        if isinstance(provenance_revision, str) and provenance_revision:
            return provenance_revision
    return None


def _verify_staged_bundle(*, staged_root: Path, revision: str) -> None:
    inspection = inspect_pack_bundle(staged_root)
    if inspection.status != "ok" or inspection.revision != revision:
        reason_codes = list(inspection.reason_codes)
        if inspection.revision != revision:
            reason_codes.append("bundle_revision_mismatch")
        raise ImportSourceError(
            "pack_bundle_verification_failed",
            source=str(staged_root),
            details={
                "missing": inspection.missing,
                "present": inspection.present,
                "mismatched": inspection.mismatched,
                "expected_revision": revision,
                "actual_revision": inspection.revision,
                "reason_codes": normalize_reason_codes(reason_codes),
            },
        )

    bundle_manifest_path = staged_root / "bundle_manifest.json"
    try:
        bundle_manifest = BundleManifest.model_validate_json(bundle_manifest_path.read_text())
    except ValueError as exc:
        raise ImportSourceError(
            "pack_bundle_verification_failed",
            source=str(bundle_manifest_path),
            details={"error": str(exc)},
        ) from exc

    manifest_paths = {entry.path for entry in bundle_manifest.entries}
    missing_manifest_entries = sorted(_BUNDLE_MANIFEST_REQUIRED_PATHS - manifest_paths)
    missing_files: list[str] = []
    digest_mismatches: list[dict[str, str]] = []

    for entry in bundle_manifest.entries:
        candidate = staged_root / entry.path
        if not candidate.is_file():
            missing_files.append(entry.path)
            continue
        actual_digest = f"sha256:{_sha256_file(candidate)}"
        if actual_digest != entry.digest:
            digest_mismatches.append(
                {
                    "path": entry.path,
                    "expected": entry.digest,
                    "actual": actual_digest,
                },
            )

    if bundle_manifest.revision != revision or missing_manifest_entries or missing_files or digest_mismatches:
        raise ImportSourceError(
            "pack_bundle_verification_failed",
            source=str(bundle_manifest_path),
            details={
                "expected_revision": revision,
                "actual_revision": bundle_manifest.revision,
                "missing_manifest_entries": missing_manifest_entries,
                "missing_files": missing_files,
                "digest_mismatches": digest_mismatches,
            },
        )


def _promote_verified_bundle(*, pack_root: Path, staged_root: Path, backup_root: Path) -> None:
    if backup_root.exists():
        _reset_directory(backup_root)

    try:
        if pack_root.exists():
            os.replace(pack_root, backup_root)
        os.replace(staged_root, pack_root)
    except OSError as exc:
        if backup_root.exists() and not pack_root.exists():
            os.replace(backup_root, pack_root)
        raise ImportSourceError(
            "pack_promotion_failed",
            source=str(pack_root),
            details={"error": str(exc)},
        ) from exc

    if backup_root.exists():
        _reset_directory(backup_root)


def _rewrite_staged_paths(*, copied_files: dict[str, str], staged_root: Path, pack_root: Path) -> dict[str, str]:
    rewritten: dict[str, str] = {}
    staged_root_str = str(staged_root)
    pack_root_str = str(pack_root)
    for name, value in copied_files.items():
        rewritten[name] = value.replace(staged_root_str, pack_root_str)
    return rewritten


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reset_directory(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
        return
    path.unlink()


def _guard_pack_history_paths(*, paths: WorkspacePaths, revision: str) -> None:
    pending_files = sorted(
        {
            pending
            for candidate in (
                paths.intent_history_json(revision),
                _qspec_history_json(paths=paths, revision=revision),
                paths.plan_history_json(revision),
                _report_history_json(paths=paths, revision=revision),
                paths.manifest_history_json(revision),
                paths.event_history_jsonl(revision),
                paths.trace_history_ndjson(revision),
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


def _load_or_create_workspace_manifest(paths: WorkspacePaths) -> WorkspaceManifest:
    if paths.workspace_json.exists():
        return WorkspaceManifest.load(paths.workspace_json)

    manifest = WorkspaceManifest.create_default()
    manifest.save(paths.workspace_json)
    return manifest


def _guard_pack_import_paths(
    *,
    paths: WorkspacePaths,
    revision: str,
    last_valid_revision: str | None,
) -> None:
    pending_files = sorted(
        {
            pending
            for candidate in (
                paths.intent_history_json(revision),
                _qspec_history_json(paths=paths, revision=revision),
                paths.plan_history_json(revision),
                _report_history_json(paths=paths, revision=revision),
                paths.manifest_history_json(revision),
                paths.event_history_jsonl(revision),
                paths.trace_history_ndjson(revision),
                paths.intents_latest_json,
                paths.plans_latest_json,
                paths.root / "specs" / "current.json",
                paths.root / "reports" / "latest.json",
                paths.manifests_latest_json,
                paths.events_jsonl,
                paths.trace_events,
                paths.benchmarks_latest_json,
                paths.doctor_latest_json,
                paths.compare_latest_json,
                paths.root / "artifacts" / "qiskit" / "main.py",
                paths.root / "artifacts" / "qasm" / "main.qasm",
                paths.root / "artifacts" / "classiq" / "main.py",
                paths.root / "artifacts" / "classiq" / "synthesis.json",
                paths.root / "figures" / "circuit.txt",
                paths.root / "figures" / "circuit.png",
            )
            for pending in pending_atomic_write_files(candidate)
        }
    )
    if not pending_files:
        return
    raise WorkspaceRecoveryRequiredError(
        workspace=paths.root,
        pending_files=pending_files,
        last_valid_revision=last_valid_revision,
    )


def _import_bundle_history(
    *,
    bundle_root: Path,
    paths: WorkspacePaths,
    revision: str,
) -> dict[str, str]:
    copied_files: dict[str, str] = {}
    core_pairs = _bundle_core_history_pairs(bundle_root=bundle_root, paths=paths, revision=revision)
    export_pairs = _bundle_export_history_pairs(bundle_root=bundle_root, paths=paths, revision=revision)
    rewritten_payloads = {
        "report_history": _rewritten_report_bytes(bundle_root=bundle_root, workspace_root=paths.root, revision=revision),
        "manifest_history": _rewritten_manifest_bytes(bundle_root=bundle_root, workspace_root=paths.root, revision=revision),
    }

    _ensure_non_conflicting_bundle_pairs(
        core_pairs + export_pairs,
        revision=revision,
        rewritten_payloads=rewritten_payloads,
    )

    for name, source_path, destination_path in core_pairs:
        rewritten_payload = rewritten_payloads.get(name)
        if rewritten_payload is not None:
            atomic_write_text(destination_path, rewritten_payload)
        else:
            atomic_copy_file(source_path, destination_path)
        copied_files[name] = str(destination_path)

    for source_path, destination_path in export_pairs:
        atomic_copy_file(source_path, destination_path)
    if export_pairs:
        copied_files["exports_root"] = str(paths.root / "artifacts" / "history" / revision)

    return copied_files


def _bundle_core_history_pairs(
    *,
    bundle_root: Path,
    paths: WorkspacePaths,
    revision: str,
) -> list[tuple[str, Path, Path]]:
    return [
        ("intent_history", bundle_root / "intent.json", paths.intent_history_json(revision)),
        ("qspec_history", bundle_root / "qspec.json", _qspec_history_json(paths=paths, revision=revision)),
        ("plan_history", bundle_root / "plan.json", paths.plan_history_json(revision)),
        ("report_history", bundle_root / "report.json", _report_history_json(paths=paths, revision=revision)),
        ("manifest_history", bundle_root / "manifest.json", paths.manifest_history_json(revision)),
        ("events_history", bundle_root / "events.jsonl", paths.event_history_jsonl(revision)),
        ("trace_history", bundle_root / "trace.ndjson", paths.trace_history_ndjson(revision)),
    ]


def _bundle_export_history_pairs(
    *,
    bundle_root: Path,
    paths: WorkspacePaths,
    revision: str,
) -> list[tuple[Path, Path]]:
    export_root = bundle_root / "exports"
    destination_root = paths.root / "artifacts" / "history" / revision
    if not export_root.exists():
        return []

    pairs: list[tuple[Path, Path]] = []
    for source_path in sorted(export_root.rglob("*")):
        if not source_path.is_file():
            continue
        relative_path = source_path.relative_to(export_root)
        pairs.append((source_path, destination_root / relative_path))
    return pairs


def _ensure_non_conflicting_bundle_pairs(
    pairs: list[tuple[str, Path, Path]] | list[tuple[Path, Path]],
    *,
    revision: str,
    rewritten_payloads: dict[str, str] | None = None,
) -> None:
    for pair in pairs:
        if len(pair) == 3:
            name, source_path, destination_path = pair
        else:
            name = None
            source_path, destination_path = pair
        if not destination_path.exists():
            continue
        expected_bytes = (
            rewritten_payloads[name].encode("utf-8")
            if rewritten_payloads is not None and name is not None and name in rewritten_payloads
            else source_path.read_bytes()
        )
        if expected_bytes == destination_path.read_bytes():
            continue
        raise ImportSourceError(
            "pack_revision_conflict",
            source=str(destination_path),
            details={
                "revision": revision,
                "pack_path": str(source_path),
                "workspace_path": str(destination_path),
            },
        )


def _promote_import_aliases(*, paths: WorkspacePaths, revision: str) -> None:
    alias_pairs: list[tuple[Path, Path]] = [
        (paths.intent_history_json(revision), paths.intents_latest_json),
        (paths.plan_history_json(revision), paths.plans_latest_json),
        (_qspec_history_json(paths=paths, revision=revision), paths.root / "specs" / "current.json"),
        (_report_history_json(paths=paths, revision=revision), paths.root / "reports" / "latest.json"),
        (paths.manifest_history_json(revision), paths.manifests_latest_json),
        (paths.event_history_jsonl(revision), paths.events_jsonl),
        (paths.trace_history_ndjson(revision), paths.trace_events),
    ]

    history_root = paths.root / "artifacts" / "history" / revision
    artifact_aliases = {
        history_root / "qiskit" / "main.py": paths.root / "artifacts" / "qiskit" / "main.py",
        history_root / "qasm" / "main.qasm": paths.root / "artifacts" / "qasm" / "main.qasm",
        history_root / "classiq" / "main.py": paths.root / "artifacts" / "classiq" / "main.py",
        history_root / "classiq" / "synthesis.json": paths.root / "artifacts" / "classiq" / "synthesis.json",
        history_root / "figures" / "circuit.txt": paths.root / "figures" / "circuit.txt",
        history_root / "figures" / "circuit.png": paths.root / "figures" / "circuit.png",
    }
    for source_path, alias_path in artifact_aliases.items():
        if source_path.exists():
            alias_pairs.append((source_path, alias_path))

    for source_path, alias_path in alias_pairs:
        atomic_copy_file(source_path, alias_path)


def _import_optional_bundle_members(
    *,
    bundle_root: Path,
    paths: WorkspacePaths,
    revision: str,
) -> dict[str, str]:
    copied_files: dict[str, str] = {}

    benchmark_source = bundle_root / "bench.json"
    if benchmark_source.is_file() and _optional_payload_matches_revision(benchmark_source, revision=revision):
        benchmark_history = paths.benchmark_history_json(revision)
        _ensure_non_conflicting_bundle_pairs([(benchmark_source, benchmark_history)], revision=revision)
        atomic_copy_file(benchmark_source, benchmark_history)
        atomic_copy_file(benchmark_source, paths.benchmarks_latest_json)
        copied_files["benchmark_history"] = str(benchmark_history)
        copied_files["benchmark_latest"] = str(paths.benchmarks_latest_json)

    doctor_source = bundle_root / "doctor.json"
    if doctor_source.is_file() and _optional_payload_matches_revision(doctor_source, revision=revision):
        doctor_history = paths.doctor_history_json(revision)
        _ensure_non_conflicting_bundle_pairs([(doctor_source, doctor_history)], revision=revision)
        atomic_copy_file(doctor_source, doctor_history)
        atomic_copy_file(doctor_source, paths.doctor_latest_json)
        copied_files["doctor_history"] = str(doctor_history)
        copied_files["doctor_latest"] = str(paths.doctor_latest_json)

    compare_source = bundle_root / "compare.json"
    compare_payload = _load_json_object(compare_source)
    compare_history = _compare_history_path(paths=paths, payload=compare_payload)
    if (
        compare_source.is_file()
        and compare_payload is not None
        and compare_history is not None
        and _optional_payload_matches_revision(compare_source, revision=revision)
    ):
        _ensure_non_conflicting_bundle_pairs([(compare_source, compare_history)], revision=revision)
        atomic_copy_file(compare_source, compare_history)
        atomic_copy_file(compare_source, paths.compare_latest_json)
        copied_files["compare_history"] = str(compare_history)
        copied_files["compare_latest"] = str(paths.compare_latest_json)

    return copied_files


def _optional_payload_matches_revision(source_path: Path, *, revision: str) -> bool:
    payload = _load_json_object(source_path)
    if payload is None:
        return False

    candidate_revisions: set[str] = set()
    for key in ("revision", "source_revision"):
        raw_value = payload.get(key)
        if isinstance(raw_value, str) and raw_value:
            candidate_revisions.add(raw_value)

    for side_name in ("left", "right"):
        raw_side = payload.get(side_name)
        if not isinstance(raw_side, dict):
            continue
        raw_revision = raw_side.get("revision")
        if isinstance(raw_revision, str) and raw_revision:
            candidate_revisions.add(raw_revision)

    return revision in candidate_revisions


def _compare_history_path(*, paths: WorkspacePaths, payload: dict[str, Any] | None) -> Path | None:
    if payload is None:
        return None

    left = payload.get("left") if isinstance(payload.get("left"), dict) else {}
    right = payload.get("right") if isinstance(payload.get("right"), dict) else {}

    left_revision = left.get("revision") if isinstance(left, dict) else None
    right_revision = right.get("revision") if isinstance(right, dict) else None

    if payload.get("baseline") is not None and isinstance(right_revision, str) and right_revision:
        return paths.compare_dir / "history" / f"baseline__{right_revision}.json"
    if isinstance(left_revision, str) and left_revision and isinstance(right_revision, str) and right_revision:
        return paths.compare_dir / "history" / f"{left_revision}__{right_revision}.json"
    return None


def _rewritten_report_bytes(*, bundle_root: Path, workspace_root: Path, revision: str) -> str:
    payload = _load_json_object(bundle_root / "report.json")
    if payload is None:
        raise ImportSourceError(
            "pack_bundle_invalid",
            source=str(bundle_root / "report.json"),
            details={"path": str(bundle_root / "report.json")},
        )

    artifact_paths = _canonical_artifact_paths(
        workspace_root=workspace_root,
        revision=revision,
        artifact_names=_artifact_names(payload.get("artifacts")),
    )
    artifact_provenance = _canonical_artifact_provenance_block(
        workspace_root=workspace_root,
        revision=revision,
        artifact_paths=artifact_paths,
    )
    qspec_path = artifact_paths["qspec"]
    payload["artifacts"] = artifact_paths
    if isinstance(payload.get("qspec"), dict):
        payload["qspec"]["path"] = qspec_path

    provenance = payload.get("provenance")
    if isinstance(provenance, dict):
        provenance["workspace_root"] = str(workspace_root)
        if isinstance(provenance.get("qspec"), dict):
            provenance["qspec"]["path"] = qspec_path
        provenance["artifacts"] = artifact_provenance

    diagnostics = payload.get("diagnostics")
    if isinstance(diagnostics, dict) and isinstance(diagnostics.get("diagram"), dict):
        diagram = diagnostics["diagram"]
        if "diagram_txt" in artifact_paths:
            diagram["text_path"] = artifact_paths["diagram_txt"]
        if "diagram_png" in artifact_paths:
            diagram["png_path"] = artifact_paths["diagram_png"]

    return json.dumps(payload, indent=2, ensure_ascii=True)


def _rewritten_manifest_bytes(*, bundle_root: Path, workspace_root: Path, revision: str) -> str:
    payload = _load_json_object(bundle_root / "manifest.json")
    if payload is None:
        raise ImportSourceError(
            "pack_bundle_invalid",
            source=str(bundle_root / "manifest.json"),
            details={"path": str(bundle_root / "manifest.json")},
        )

    artifact_paths = _canonical_artifact_paths(
        workspace_root=workspace_root,
        revision=revision,
        artifact_names=_artifact_names(payload.get("artifacts")),
    )
    artifact_provenance = _canonical_artifact_provenance_block(
        workspace_root=workspace_root,
        revision=revision,
        artifact_paths=artifact_paths,
    )

    _rewrite_manifest_path_entry(payload.get("intent"), path=str(workspace_root / "intents" / "history" / f"{revision}.json"))
    _rewrite_manifest_path_entry(payload.get("plan"), path=str(workspace_root / "plans" / "history" / f"{revision}.json"))
    _rewrite_manifest_path_entry(
        payload.get("qspec"),
        path=str(workspace_root / "specs" / "history" / f"{revision}.json"),
    )
    _rewrite_manifest_path_entry(
        payload.get("report"),
        path=str(workspace_root / "reports" / "history" / f"{revision}.json"),
    )
    report_block = payload.get("report")
    if isinstance(report_block, dict):
        report_block["hash"] = _hash_text(_rewritten_report_bytes(bundle_root=bundle_root, workspace_root=workspace_root, revision=revision))

    events_block = payload.get("events")
    if isinstance(events_block, dict):
        _rewrite_manifest_path_entry(
            events_block.get("events_jsonl"),
            path=str(workspace_root / "events" / "history" / f"{revision}.jsonl"),
        )
        _rewrite_manifest_path_entry(
            events_block.get("trace_ndjson"),
            path=str(workspace_root / "trace" / "history" / f"{revision}.ndjson"),
        )

    artifacts_block = payload.get("artifacts")
    if isinstance(artifacts_block, dict):
        for name, details in artifacts_block.items():
            if name in artifact_paths:
                _rewrite_manifest_path_entry(details, path=artifact_paths[name])

    provenance = payload.get("provenance")
    if isinstance(provenance, dict):
        provenance["workspace_root"] = str(workspace_root)
        report_provenance = provenance.get("report_provenance")
        if isinstance(report_provenance, dict):
            _rewrite_report_provenance(
                provenance=report_provenance,
                workspace_root=workspace_root,
                artifact_provenance=artifact_provenance,
                qspec_path=artifact_paths["qspec"],
            )

    return json.dumps(payload, indent=2, ensure_ascii=True)


def _rewrite_manifest_path_entry(entry: Any, *, path: str) -> None:
    if isinstance(entry, dict):
        entry["path"] = path


def _rewrite_report_provenance(
    *,
    provenance: dict[str, Any],
    workspace_root: Path,
    artifact_provenance: dict[str, Any],
    qspec_path: str,
) -> None:
    provenance["workspace_root"] = str(workspace_root)
    if isinstance(provenance.get("qspec"), dict):
        provenance["qspec"]["path"] = qspec_path
    provenance["artifacts"] = artifact_provenance


def _artifact_names(raw_artifacts: Any) -> set[str]:
    if not isinstance(raw_artifacts, dict):
        return {"qspec", "report"}
    return {"qspec", "report", *[name for name in raw_artifacts if isinstance(name, str)]}


def _canonical_artifact_provenance_block(
    *,
    workspace_root: Path,
    revision: str,
    artifact_paths: dict[str, str],
) -> dict[str, Any]:
    alias_paths = _artifact_alias_paths(workspace_root=workspace_root)
    return {
        "snapshot_root": str(workspace_root / "artifacts" / "history" / revision),
        "current_root": str(workspace_root / "artifacts"),
        "paths": artifact_paths,
        "current_aliases": {
            name: alias_paths[name]
            for name in artifact_paths
            if name in alias_paths
        },
    }


def _canonical_artifact_paths(
    *,
    workspace_root: Path,
    revision: str,
    artifact_names: set[str],
) -> dict[str, str]:
    history_root = workspace_root / "artifacts" / "history" / revision
    path_map = {
        "qspec": str(workspace_root / "specs" / "history" / f"{revision}.json"),
        "report": str(workspace_root / "reports" / "history" / f"{revision}.json"),
        "qiskit_code": str(history_root / "qiskit" / "main.py"),
        "qasm3": str(history_root / "qasm" / "main.qasm"),
        "classiq_code": str(history_root / "classiq" / "main.py"),
        "classiq_results": str(history_root / "classiq" / "synthesis.json"),
        "diagram_txt": str(history_root / "figures" / "circuit.txt"),
        "diagram_png": str(history_root / "figures" / "circuit.png"),
    }
    return {name: path_map[name] for name in sorted(artifact_names) if name in path_map}


def _artifact_alias_paths(*, workspace_root: Path) -> dict[str, str]:
    return {
        "qspec": str(workspace_root / "specs" / "current.json"),
        "report": str(workspace_root / "reports" / "latest.json"),
        "qiskit_code": str(workspace_root / "artifacts" / "qiskit" / "main.py"),
        "qasm3": str(workspace_root / "artifacts" / "qasm" / "main.qasm"),
        "classiq_code": str(workspace_root / "artifacts" / "classiq" / "main.py"),
        "classiq_results": str(workspace_root / "artifacts" / "classiq" / "synthesis.json"),
        "diagram_txt": str(workspace_root / "figures" / "circuit.txt"),
        "diagram_png": str(workspace_root / "figures" / "circuit.png"),
    }


def _hash_text(content: str) -> str:
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
