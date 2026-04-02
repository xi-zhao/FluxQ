from __future__ import annotations

from pathlib import Path

import pytest

from quantum_runtime.artifact_provenance import (
    ArtifactProvenanceMismatch,
    canonicalize_artifact_provenance,
)


def test_canonicalize_artifact_provenance_normalizes_relative_alias_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    workspace = Path("relative-workspace")
    revision = "rev_000001"

    provenance = canonicalize_artifact_provenance(
        workspace_root=workspace,
        revision=revision,
        artifacts={
            "qspec": "specs/current.json",
            "report": "reports/latest.json",
            "qiskit_code": "artifacts/qiskit/main.py",
        },
        stored_provenance={
            "snapshot_root": f"artifacts/history/{revision}",
            "current_root": "artifacts",
            "paths": {},
            "current_aliases": {
                "qiskit_code": "artifacts/qiskit/main.py",
            },
        },
    )

    absolute_workspace = (tmp_path / workspace).resolve()
    assert provenance["snapshot_root"] == str(absolute_workspace / "artifacts" / "history" / revision)
    assert provenance["current_root"] == str(absolute_workspace / "artifacts")
    assert provenance["paths"]["qspec"] == str(absolute_workspace / "specs" / "history" / f"{revision}.json")
    assert provenance["paths"]["report"] == str(absolute_workspace / "reports" / "history" / f"{revision}.json")
    assert provenance["paths"]["qiskit_code"] == str(
        absolute_workspace / "artifacts" / "history" / revision / "qiskit" / "main.py"
    )
    assert provenance["current_aliases"]["qspec"] == str(absolute_workspace / "specs" / "current.json")
    assert provenance["current_aliases"]["report"] == str(absolute_workspace / "reports" / "latest.json")
    assert provenance["current_aliases"]["qiskit_code"] == str(
        absolute_workspace / "artifacts" / "qiskit" / "main.py"
    )


def test_canonicalize_artifact_provenance_repairs_partial_legacy_payloads(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    revision = "rev_000001"

    provenance = canonicalize_artifact_provenance(
        workspace_root=workspace,
        revision=revision,
        artifacts={"qasm3": str(workspace / "artifacts" / "qasm" / "main.qasm")},
        stored_provenance={
            "paths": {},
            "current_aliases": {},
        },
    )

    assert provenance["paths"]["qspec"] == str(workspace / "specs" / "history" / f"{revision}.json")
    assert provenance["paths"]["report"] == str(workspace / "reports" / "history" / f"{revision}.json")
    assert provenance["paths"]["qasm3"] == str(workspace / "artifacts" / "history" / revision / "qasm" / "main.qasm")
    assert provenance["current_aliases"]["qspec"] == str(workspace / "specs" / "current.json")
    assert provenance["current_aliases"]["report"] == str(workspace / "reports" / "latest.json")
    assert provenance["current_aliases"]["qasm3"] == str(workspace / "artifacts" / "qasm" / "main.qasm")


def test_canonicalize_artifact_provenance_accepts_workspace_prefixed_legacy_relative_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    workspace = Path("tmp-review-old-bug-report")
    revision = "rev_000001"

    provenance = canonicalize_artifact_provenance(
        workspace_root=workspace,
        revision=revision,
        artifacts={
            "qspec": "tmp-review-old-bug-report/specs/current.json",
            "report": "tmp-review-old-bug-report/reports/latest.json",
            "qiskit_code": "tmp-review-old-bug-report/artifacts/qiskit/main.py",
        },
        stored_provenance={
            "snapshot_root": f"tmp-review-old-bug-report/artifacts/history/{revision}",
            "current_root": "tmp-review-old-bug-report/artifacts",
            "paths": {
                "qspec": "tmp-review-old-bug-report/specs/current.json",
                "report": "tmp-review-old-bug-report/reports/latest.json",
            },
            "current_aliases": {
                "qiskit_code": "tmp-review-old-bug-report/artifacts/qiskit/main.py",
            },
        },
    )

    absolute_workspace = (tmp_path / workspace).resolve()
    assert provenance["snapshot_root"] == str(absolute_workspace / "artifacts" / "history" / revision)
    assert provenance["current_root"] == str(absolute_workspace / "artifacts")
    assert provenance["paths"]["qspec"] == str(absolute_workspace / "specs" / "history" / f"{revision}.json")
    assert provenance["paths"]["report"] == str(absolute_workspace / "reports" / "history" / f"{revision}.json")
    assert provenance["paths"]["qiskit_code"] == str(
        absolute_workspace / "artifacts" / "history" / revision / "qiskit" / "main.py"
    )
    assert provenance["current_aliases"]["qspec"] == str(absolute_workspace / "specs" / "current.json")
    assert provenance["current_aliases"]["report"] == str(absolute_workspace / "reports" / "latest.json")
    assert provenance["current_aliases"]["qiskit_code"] == str(
        absolute_workspace / "artifacts" / "qiskit" / "main.py"
    )


def test_canonicalize_artifact_provenance_accepts_mixed_alias_and_history_inputs(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    revision = "rev_000001"

    provenance = canonicalize_artifact_provenance(
        workspace_root=workspace,
        revision=revision,
        artifacts={"qiskit_code": str(workspace / "artifacts" / "qiskit" / "main.py")},
        stored_provenance={
            "paths": {
                "qiskit_code": str(workspace / "artifacts" / "history" / revision / "qiskit" / "main.py"),
            },
            "current_aliases": {
                "qiskit_code": str(workspace / "artifacts" / "qiskit" / "main.py"),
            },
        },
    )

    assert provenance["paths"]["qiskit_code"] == str(
        workspace / "artifacts" / "history" / revision / "qiskit" / "main.py"
    )
    assert provenance["current_aliases"]["qiskit_code"] == str(workspace / "artifacts" / "qiskit" / "main.py")


def test_canonicalize_artifact_provenance_rejects_other_revision_history_path(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    with pytest.raises(ArtifactProvenanceMismatch) as excinfo:
        canonicalize_artifact_provenance(
            workspace_root=workspace,
            revision="rev_000001",
            artifacts={
                "qiskit_code": str(
                    workspace / "artifacts" / "history" / "rev_000099" / "qiskit" / "main.py"
                ),
            },
        )

    assert excinfo.value.code == "artifact_revision_mismatch"
    assert excinfo.value.details["artifact"] == "qiskit_code"
    assert excinfo.value.details["expected_revision"] == "rev_000001"


def test_canonicalize_artifact_provenance_rejects_malformed_snapshot_root(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    with pytest.raises(ArtifactProvenanceMismatch) as excinfo:
        canonicalize_artifact_provenance(
            workspace_root=workspace,
            revision="rev_000001",
            artifacts={"qiskit_code": "artifacts/qiskit/main.py"},
            stored_provenance={
                "snapshot_root": "artifacts/history",
            },
        )

    assert excinfo.value.code == "artifact_path_invalid"
    assert excinfo.value.details["artifact"] == "snapshot_root"


def test_canonicalize_artifact_provenance_rejects_disagreeing_inputs(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    revision = "rev_000001"

    with pytest.raises(ArtifactProvenanceMismatch) as excinfo:
        canonicalize_artifact_provenance(
            workspace_root=workspace,
            revision=revision,
            artifacts={"qiskit_code": str(workspace / "artifacts" / "qiskit" / "main.py")},
            stored_provenance={
                "paths": {
                    "qiskit_code": str(workspace / "artifacts" / "history" / revision / "qiskit" / "alt.py"),
                }
            },
        )

    assert excinfo.value.code == "artifact_path_mismatch"
    assert excinfo.value.details["artifact"] == "qiskit_code"
