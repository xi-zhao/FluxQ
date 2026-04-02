"""Shared artifact provenance normalization for revision-stable workspace artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class ArtifactProvenanceMismatch(ValueError):
    """Raised when untrusted artifact provenance cannot be normalized safely."""

    def __init__(self, code: str, *, details: dict[str, Any] | None = None) -> None:
        self.code = code
        self.details = details or {}
        super().__init__(code)

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, **self.details}


def canonicalize_artifact_provenance(
    *,
    workspace_root: Path,
    revision: str,
    artifacts: Any = None,
    stored_provenance: Any = None,
) -> dict[str, Any]:
    """Normalize artifact provenance into absolute revision-stable paths."""
    normalized_root = Path(workspace_root).resolve()
    snapshot_root = normalized_root / "artifacts" / "history" / revision
    current_root = normalized_root / "artifacts"
    canonical_paths: dict[str, str] = {
        "qspec": str(normalized_root / "specs" / "history" / f"{revision}.json"),
        "report": str(normalized_root / "reports" / "history" / f"{revision}.json"),
    }
    current_aliases: dict[str, str] = {
        "qspec": str(normalized_root / "specs" / "current.json"),
        "report": str(normalized_root / "reports" / "latest.json"),
    }
    seen: dict[str, tuple[Path, Path, str]] = {
        name: (Path(path), Path(current_aliases[name]), "canonical_default")
        for name, path in canonical_paths.items()
    }

    if isinstance(stored_provenance, dict):
        _validate_root_candidate(
            name="snapshot_root",
            raw_path=stored_provenance.get("snapshot_root"),
            expected_path=snapshot_root,
            workspace_root=normalized_root,
            revision=revision,
        )
        _validate_root_candidate(
            name="current_root",
            raw_path=stored_provenance.get("current_root"),
            expected_path=current_root,
            workspace_root=normalized_root,
            revision=revision,
        )

    _collect_candidates(
        seen=seen,
        workspace_root=normalized_root,
        revision=revision,
        snapshot_root=snapshot_root,
        current_root=current_root,
        paths=artifacts if isinstance(artifacts, dict) else None,
        source_name="artifacts",
        from_aliases=False,
    )

    if isinstance(stored_provenance, dict):
        _collect_candidates(
            seen=seen,
            workspace_root=normalized_root,
            revision=revision,
            snapshot_root=snapshot_root,
            current_root=current_root,
            paths=stored_provenance.get("paths"),
            source_name="stored_provenance.paths",
            from_aliases=False,
        )
        _collect_candidates(
            seen=seen,
            workspace_root=normalized_root,
            revision=revision,
            snapshot_root=snapshot_root,
            current_root=current_root,
            paths=stored_provenance.get("current_aliases"),
            source_name="stored_provenance.current_aliases",
            from_aliases=True,
        )

    for name, (canonical_path, alias_path, _) in seen.items():
        canonical_paths[name] = str(canonical_path)
        current_aliases[name] = str(alias_path)

    return {
        "snapshot_root": str(snapshot_root),
        "current_root": str(current_root),
        "paths": canonical_paths,
        "current_aliases": current_aliases,
    }


def select_accessible_artifact_paths(artifact_provenance: dict[str, Any]) -> dict[str, str]:
    """Prefer canonical paths when they exist, otherwise fall back to current aliases."""
    paths = artifact_provenance.get("paths")
    aliases = artifact_provenance.get("current_aliases")
    if not isinstance(paths, dict):
        return {}

    resolved: dict[str, str] = {}
    for name, raw_path in paths.items():
        if not isinstance(raw_path, str):
            continue
        canonical_path = Path(raw_path)
        raw_alias = aliases.get(name) if isinstance(aliases, dict) else None
        alias_path = Path(raw_alias) if isinstance(raw_alias, str) else None
        if canonical_path.exists():
            resolved[name] = str(canonical_path)
        elif alias_path is not None and alias_path.exists():
            resolved[name] = str(alias_path)
        else:
            resolved[name] = str(canonical_path)
    return resolved


def _collect_candidates(
    *,
    seen: dict[str, tuple[Path, Path, str]],
    workspace_root: Path,
    revision: str,
    snapshot_root: Path,
    current_root: Path,
    paths: Any,
    source_name: str,
    from_aliases: bool,
) -> None:
    if not isinstance(paths, dict):
        return

    for raw_name, raw_path in paths.items():
        if not isinstance(raw_name, str):
            continue
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        canonical_path, alias_path = _normalize_candidate(
            name=raw_name,
            raw_path=raw_path,
            workspace_root=workspace_root,
            revision=revision,
            snapshot_root=snapshot_root,
            current_root=current_root,
            from_aliases=from_aliases,
        )
        existing = seen.get(raw_name)
        source = f"{source_name}:{raw_name}"
        if existing is None:
            seen[raw_name] = (canonical_path, alias_path, source)
            continue
        existing_canonical, existing_alias, existing_source = existing
        if existing_canonical != canonical_path or existing_alias != alias_path:
            raise ArtifactProvenanceMismatch(
                "artifact_path_mismatch",
                details={
                    "artifact": raw_name,
                    "source_a": existing_source,
                    "source_b": source,
                    "canonical_a": str(existing_canonical),
                    "canonical_b": str(canonical_path),
                    "alias_a": str(existing_alias),
                    "alias_b": str(alias_path),
                },
            )


def _validate_root_candidate(
    *,
    name: str,
    raw_path: Any,
    expected_path: Path,
    workspace_root: Path,
    revision: str,
) -> None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return
    candidate = _anchor_workspace_path(raw_path, workspace_root)
    if name == "snapshot_root":
        history_root = workspace_root / "artifacts" / "history"
        if candidate.is_relative_to(history_root):
            relative = candidate.relative_to(history_root)
            if len(relative.parts) < 1:
                raise ArtifactProvenanceMismatch(
                    "artifact_path_invalid",
                    details={
                        "artifact": name,
                        "path": str(candidate),
                    },
                )
            candidate_revision = relative.parts[0]
            if candidate_revision != revision:
                raise ArtifactProvenanceMismatch(
                    "artifact_revision_mismatch",
                    details={
                        "artifact": name,
                        "expected_revision": revision,
                        "actual_revision": candidate_revision,
                        "path": str(candidate),
                    },
                )
    if candidate != expected_path:
        raise ArtifactProvenanceMismatch(
            "artifact_root_mismatch",
            details={
                "artifact": name,
                "expected_path": str(expected_path),
                "actual_path": str(candidate),
            },
        )


def _normalize_candidate(
    *,
    name: str,
    raw_path: str,
    workspace_root: Path,
    revision: str,
    snapshot_root: Path,
    current_root: Path,
    from_aliases: bool,
) -> tuple[Path, Path]:
    candidate = _anchor_workspace_path(raw_path, workspace_root)
    if name == "qspec":
        return _normalize_special_candidate(
            name=name,
            candidate=candidate,
            workspace_root=workspace_root,
            revision=revision,
        )
    if name == "report":
        return _normalize_special_candidate(
            name=name,
            candidate=candidate,
            workspace_root=workspace_root,
            revision=revision,
        )

    history_root = workspace_root / "artifacts" / "history"
    figures_root = workspace_root / "figures"
    if candidate.is_relative_to(history_root):
        relative = candidate.relative_to(history_root)
        if len(relative.parts) < 2:
            raise ArtifactProvenanceMismatch(
                "artifact_path_invalid",
                details={"artifact": name, "path": str(candidate)},
            )
        candidate_revision = relative.parts[0]
        if candidate_revision != revision:
            raise ArtifactProvenanceMismatch(
                "artifact_revision_mismatch",
                details={
                    "artifact": name,
                    "expected_revision": revision,
                    "actual_revision": candidate_revision,
                    "path": str(candidate),
                },
            )
        suffix = Path(*relative.parts[1:])
        if suffix.parts and suffix.parts[0] == "figures":
            return candidate, workspace_root / "figures" / Path(*suffix.parts[1:])
        return candidate, current_root / suffix

    if candidate.is_relative_to(current_root):
        relative = candidate.relative_to(current_root)
        if len(relative.parts) >= 2 and relative.parts[0] == "history":
            candidate_revision = relative.parts[1]
            if candidate_revision != revision:
                raise ArtifactProvenanceMismatch(
                    "artifact_revision_mismatch",
                    details={
                        "artifact": name,
                        "expected_revision": revision,
                        "actual_revision": candidate_revision,
                        "path": str(candidate),
                },
            )
            suffix = Path(*relative.parts[2:])
            if suffix.parts and suffix.parts[0] == "figures":
                return current_root / relative, workspace_root / "figures" / Path(*suffix.parts[1:])
            return current_root / relative, current_root / suffix
        if relative.parts and relative.parts[0] == "figures":
            return snapshot_root / "figures" / Path(*relative.parts[1:]), workspace_root / "figures" / Path(
                *relative.parts[1:]
            )
        if from_aliases:
            return snapshot_root / relative, candidate
        return snapshot_root / relative, candidate

    if candidate.is_relative_to(figures_root):
        relative = candidate.relative_to(figures_root)
        return snapshot_root / "figures" / relative, candidate

    raise ArtifactProvenanceMismatch(
        "artifact_path_invalid",
        details={"artifact": name, "path": str(candidate)},
    )


def _normalize_special_candidate(
    *,
    name: str,
    candidate: Path,
    workspace_root: Path,
    revision: str,
) -> tuple[Path, Path]:
    if name == "qspec":
        canonical_path = workspace_root / "specs" / "history" / f"{revision}.json"
        alias_path = workspace_root / "specs" / "current.json"
        history_root = workspace_root / "specs" / "history"
        alias_name = "current.json"
    else:
        canonical_path = workspace_root / "reports" / "history" / f"{revision}.json"
        alias_path = workspace_root / "reports" / "latest.json"
        history_root = workspace_root / "reports" / "history"
        alias_name = "latest.json"

    if candidate == canonical_path or candidate == alias_path:
        return canonical_path, alias_path
    if candidate.is_relative_to(history_root):
        candidate_revision = candidate.stem
        if candidate_revision != revision:
            raise ArtifactProvenanceMismatch(
                "artifact_revision_mismatch",
                details={
                    "artifact": name,
                    "expected_revision": revision,
                    "actual_revision": candidate_revision,
                    "path": str(candidate),
                },
            )
        return canonical_path, alias_path
    if candidate.name == alias_name and candidate.parent == alias_path.parent:
        return canonical_path, alias_path

    raise ArtifactProvenanceMismatch(
        "artifact_path_invalid",
        details={"artifact": name, "path": str(candidate)},
    )


def _anchor_workspace_path(raw_path: str, workspace_root: Path) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    if candidate.parts and candidate.parts[0] == workspace_root.name:
        return (workspace_root.parent / candidate).resolve()
    return (workspace_root / candidate).resolve()
