from __future__ import annotations

from pathlib import Path

import pytest

from quantum_runtime.runtime.executor import execute_intent
from quantum_runtime.runtime.imports import (
    ImportReference,
    ImportSourceError,
    resolve_import_reference,
    resolve_report_file,
    resolve_report_revision,
    resolve_workspace_current,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_resolve_workspace_current_returns_structured_provenance(tmp_path: Path) -> None:
    workspace = _seed_workspace(tmp_path)

    resolution = resolve_workspace_current(workspace)

    assert resolution.source_kind == "workspace_current"
    assert resolution.revision == "rev_000001"
    assert resolution.report_path == workspace / "reports" / "latest.json"
    assert resolution.qspec_path == workspace / "specs" / "current.json"
    assert resolution.qspec_summary["goal"].lower().startswith("generate a 4-qubit ghz")
    assert resolution.report_summary["status"] == "ok"
    assert resolution.provenance["workspace_source"] == "manifest"
    assert resolution.load_qspec().program_id == resolution.qspec_summary["program_id"]


def test_resolve_report_file_infers_workspace_and_summarizes_source(tmp_path: Path) -> None:
    workspace = _seed_workspace(tmp_path)
    report_file = workspace / "reports" / "latest.json"

    resolution = resolve_report_file(report_file)

    assert resolution.source_kind == "report_file"
    assert resolution.report_path == report_file
    assert resolution.qspec_path == workspace / "specs" / "history" / "rev_000001.json"
    assert resolution.report_summary["input_mode"] == "intent"
    assert resolution.report_summary["artifact_snapshot_root"] == str(
        workspace / "artifacts" / "history" / "rev_000001"
    )
    assert resolution.report_summary["artifact_names"][-1] == "report"
    assert resolution.artifacts["report"] == str(workspace / "reports" / "history" / "rev_000001.json")
    assert resolution.provenance["workspace_source"] == "inferred_from_report_path"
    assert resolution.provenance["artifacts"]["paths"]["report"] == str(
        workspace / "reports" / "history" / "rev_000001.json"
    )
    assert resolution.provenance["artifacts"]["paths"]["qspec"] == str(
        workspace / "specs" / "history" / "rev_000001.json"
    )
    assert resolution.provenance["artifacts"]["current_aliases"]["qiskit_code"] == str(
        workspace / "artifacts" / "qiskit" / "main.py"
    )
    assert resolution.provenance["artifacts"]["current_aliases"]["report"] == str(
        workspace / "reports" / "latest.json"
    )
    assert resolution.provenance["artifacts"]["current_aliases"]["qspec"] == str(
        workspace / "specs" / "current.json"
    )
    assert resolution.load_report()["revision"] == "rev_000001"


def test_resolve_report_revision_uses_history_paths_and_generic_reference(
    tmp_path: Path,
) -> None:
    workspace = _seed_workspace(tmp_path)

    resolution = resolve_import_reference(ImportReference(workspace_root=workspace, revision="rev_000001"))

    assert resolution.source_kind == "report_revision"
    assert resolution.report_path == workspace / "reports" / "history" / "rev_000001.json"
    assert resolution.qspec_path == workspace / "specs" / "history" / "rev_000001.json"
    assert resolution.provenance["report_revision"] == "rev_000001"
    assert resolution.provenance["qspec_resolution_source"] == "workspace_history"
    assert resolution.qspec_summary["program_id"].startswith("prog_")


def test_resolve_report_revision_rejects_invalid_revision_format(tmp_path: Path) -> None:
    workspace = _seed_workspace(tmp_path)

    with pytest.raises(ImportSourceError) as excinfo:
        resolve_report_revision(workspace, "not-a-rev")

    assert excinfo.value.code == "invalid_revision"


def test_resolve_report_file_rejects_missing_report_path(tmp_path: Path) -> None:
    with pytest.raises(ImportSourceError) as excinfo:
        resolve_report_file(tmp_path / "missing-report.json")

    assert excinfo.value.code == "report_file_missing"


def test_resolve_report_file_supports_relative_workspace_roots(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    workspace = Path("tmp-review-relative-workspace")

    result = execute_intent(workspace_root=workspace, intent_file=PROJECT_ROOT / "examples" / "intent-ghz.md")

    assert result.status == "ok"
    report_file = workspace / "reports" / "latest.json"
    resolution = resolve_report_file(report_file)

    assert resolution.workspace_root.is_absolute()
    assert resolution.report_path.is_absolute()
    assert resolution.qspec_path.is_absolute()
    assert resolution.qspec_path == resolution.workspace_root / "specs" / "history" / "rev_000001.json"
    assert resolution.load_report()["artifacts"]["report"] == str(
        resolution.workspace_root / "reports" / "history" / "rev_000001.json"
    )


def _seed_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / ".quantum"
    result = execute_intent(workspace_root=workspace, intent_file=PROJECT_ROOT / "examples" / "intent-ghz.md")
    assert result.status == "ok"
    return workspace
