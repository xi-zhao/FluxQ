"""Portable revision bundle helpers."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

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
    WorkspaceLockConflict,
    acquire_workspace_lock,
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


BundleManifest.model_rebuild()
PackResult.model_rebuild()
PackInspectionResult.model_rebuild()


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
    from quantum_runtime.workspace import WorkspacePaths

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
