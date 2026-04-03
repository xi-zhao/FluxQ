from __future__ import annotations

import hashlib
import json
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
from quantum_runtime.intent.parser import parse_intent_file
from quantum_runtime.intent.planner import plan_to_qspec
from quantum_runtime.workspace import WorkspaceManager


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
    assert resolution.provenance["workspace_source"] in {
        "report_provenance.workspace_root",
        "inferred_from_report_path",
    }
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


def test_resolve_report_file_uses_one_consistent_payload_when_canonicalizing_latest(
    tmp_path: Path,
) -> None:
    workspace = _seed_workspace(tmp_path)
    latest_report = workspace / "reports" / "latest.json"
    latest_payload = json.loads(latest_report.read_text())
    latest_payload["status"] = "degraded"
    latest_payload["warnings"] = ["edited_latest_only"]
    latest_report.write_text(json.dumps(latest_payload, indent=2))

    resolution = resolve_report_file(latest_report)

    assert resolution.report_summary["status"] == resolution.load_report()["status"]
    assert resolution.report_summary["status"] == "degraded"
    assert resolution.report_path == latest_report


def test_resolve_report_revision_uses_history_paths_and_generic_reference(
    tmp_path: Path,
) -> None:
    workspace = _seed_workspace(tmp_path)

    resolution = resolve_import_reference(ImportReference(workspace_root=workspace, revision="rev_000001"))

    assert resolution.source_kind == "report_revision"
    assert resolution.report_path == workspace / "reports" / "history" / "rev_000001.json"
    assert resolution.qspec_path == workspace / "specs" / "history" / "rev_000001.json"
    assert resolution.provenance["report_revision"] == "rev_000001"
    assert resolution.provenance["qspec_resolution_source"] == "artifact_provenance"
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


def test_resolve_report_file_uses_report_provenance_for_copied_report_files(tmp_path: Path) -> None:
    workspace = _seed_workspace(tmp_path)
    copied_report = tmp_path / "imports" / "copied-rev-1.json"
    copied_report.parent.mkdir(parents=True, exist_ok=True)
    copied_report.write_text((workspace / "reports" / "history" / "rev_000001.json").read_text())

    resolution = resolve_report_file(copied_report)

    assert resolution.workspace_root == workspace
    assert resolution.report_path == copied_report.resolve()
    assert resolution.qspec_path == workspace / "specs" / "history" / "rev_000001.json"
    assert resolution.provenance["workspace_source"] == "report_provenance.workspace_root"
    assert resolution.provenance["artifacts"]["snapshot_root"] == str(
        workspace / "artifacts" / "history" / "rev_000001"
    )
    assert resolution.provenance["replay_integrity"]["status"] == "ok"
    assert resolution.provenance["replay_integrity"]["qspec_hash_matches"] is True
    assert resolution.provenance["replay_integrity"]["qspec_semantic_hash_matches"] is True


def test_resolve_workspace_current_supports_current_only_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    handle = WorkspaceManager.load_or_init(workspace)
    qspec = plan_to_qspec(parse_intent_file(PROJECT_ROOT / "examples" / "intent-ghz.md"))
    current_qspec = handle.root / "specs" / "current.json"
    current_qspec.write_text(qspec.model_dump_json(indent=2))
    latest_report = handle.root / "reports" / "latest.json"
    latest_report.write_text(
        json.dumps(
            {
                "status": "ok",
                "revision": handle.manifest.current_revision,
                "input": {"mode": "qspec", "path": str(current_qspec)},
                "qspec": {"path": "specs/current.json"},
                "artifacts": {
                    "qspec": "specs/current.json",
                    "report": "reports/latest.json",
                },
                "diagnostics": {},
                "backend_reports": {},
                "warnings": [],
                "errors": [],
            },
            indent=2,
        )
    )

    resolution = resolve_workspace_current(workspace)

    assert resolution.report_path == latest_report
    assert resolution.qspec_path == current_qspec
    assert resolution.artifacts["report"] == str(latest_report)
    assert resolution.artifacts["qspec"] == str(current_qspec)
    assert resolution.provenance["artifacts"]["paths"]["report"] == str(
        workspace / "reports" / "history" / f"{handle.manifest.current_revision}.json"
    )


def test_resolve_report_file_normalizes_relative_alias_artifacts(tmp_path: Path) -> None:
    workspace = _seed_workspace(tmp_path)
    report_file = workspace / "reports" / "latest.json"
    payload = json.loads(report_file.read_text())
    payload["qspec"]["path"] = "specs/current.json"
    payload["artifacts"]["qspec"] = "specs/current.json"
    payload["artifacts"]["report"] = "reports/latest.json"
    payload["artifacts"]["qiskit_code"] = "artifacts/qiskit/main.py"
    payload["provenance"]["artifacts"] = {
        "snapshot_root": f"artifacts/history/{payload['revision']}",
        "current_root": "artifacts",
        "paths": {},
        "current_aliases": {},
    }
    report_file.write_text(json.dumps(payload, indent=2))

    resolution = resolve_report_file(report_file)

    assert resolution.qspec_path == workspace / "specs" / "history" / "rev_000001.json"
    assert resolution.provenance["artifacts"]["snapshot_root"] == str(
        workspace / "artifacts" / "history" / "rev_000001"
    )
    assert resolution.provenance["artifacts"]["current_root"] == str(workspace / "artifacts")
    assert resolution.provenance["artifacts"]["paths"]["qspec"] == str(
        workspace / "specs" / "history" / "rev_000001.json"
    )
    assert resolution.provenance["artifacts"]["paths"]["report"] == str(
        workspace / "reports" / "history" / "rev_000001.json"
    )
    assert resolution.provenance["artifacts"]["paths"]["qiskit_code"] == str(
        workspace / "artifacts" / "history" / "rev_000001" / "qiskit" / "main.py"
    )
    assert resolution.artifacts["qspec"] == str(workspace / "specs" / "history" / "rev_000001.json")
    assert resolution.artifacts["report"] == str(workspace / "reports" / "history" / "rev_000001.json")
    assert resolution.artifacts["qiskit_code"] == str(
        workspace / "artifacts" / "history" / "rev_000001" / "qiskit" / "main.py"
    )
    assert resolution.provenance["artifacts"]["current_aliases"]["qiskit_code"] == str(
        workspace / "artifacts" / "qiskit" / "main.py"
    )


def test_resolve_report_file_rejects_revision_inconsistent_artifact_provenance(tmp_path: Path) -> None:
    workspace = _seed_workspace(tmp_path)
    report_file = workspace / "reports" / "latest.json"
    payload = json.loads(report_file.read_text())
    payload["provenance"]["artifacts"]["paths"]["qiskit_code"] = str(
        workspace / "artifacts" / "history" / "rev_000099" / "qiskit" / "main.py"
    )
    report_file.write_text(json.dumps(payload, indent=2))

    with pytest.raises(ImportSourceError) as excinfo:
        resolve_report_file(report_file)

    assert excinfo.value.code == "artifact_provenance_invalid"


def test_resolve_report_file_rejects_mutated_current_qspec_hash_fallback(tmp_path: Path) -> None:
    workspace = _seed_workspace(tmp_path)
    report_file = workspace / "reports" / "latest.json"
    history_qspec = workspace / "specs" / "history" / "rev_000001.json"
    current_qspec = workspace / "specs" / "current.json"

    mutated_qspec = plan_to_qspec(parse_intent_file(PROJECT_ROOT / "examples" / "intent-qaoa-maxcut.md"))
    current_qspec.write_text(mutated_qspec.model_dump_json(indent=2))
    history_qspec.unlink()

    with pytest.raises(ImportSourceError) as excinfo:
        resolve_report_file(report_file)

    assert excinfo.value.code == "report_qspec_hash_mismatch"


def test_resolve_report_file_rejects_mutated_current_qspec_semantic_fallback(tmp_path: Path) -> None:
    workspace = _seed_workspace(tmp_path)
    report_file = workspace / "reports" / "latest.json"
    history_qspec = workspace / "specs" / "history" / "rev_000001.json"
    current_qspec = workspace / "specs" / "current.json"

    mutated_qspec = plan_to_qspec(parse_intent_file(PROJECT_ROOT / "examples" / "intent-qaoa-maxcut.md"))
    current_qspec.write_text(mutated_qspec.model_dump_json(indent=2))
    history_qspec.unlink()

    payload = json.loads(report_file.read_text())
    payload["qspec"]["hash"] = _sha256_file(current_qspec)
    payload["replay_integrity"]["qspec_hash"] = payload["qspec"]["hash"]
    report_file.write_text(json.dumps(payload, indent=2))

    with pytest.raises(ImportSourceError) as excinfo:
        resolve_report_file(report_file)

    assert excinfo.value.code == "report_qspec_semantic_hash_mismatch"


def test_resolve_report_file_marks_artifact_digest_drift_when_snapshot_missing(tmp_path: Path) -> None:
    workspace = _seed_workspace(tmp_path)
    report_file = workspace / "reports" / "latest.json"
    history_qiskit = workspace / "artifacts" / "history" / "rev_000001" / "qiskit" / "main.py"
    current_qiskit = workspace / "artifacts" / "qiskit" / "main.py"

    history_qiskit.unlink()
    current_qiskit.write_text(current_qiskit.read_text() + "\n# tampered replay alias\n")

    resolution = resolve_report_file(report_file)

    assert resolution.provenance["replay_integrity"]["status"] == "degraded"
    assert resolution.provenance["replay_integrity"]["artifact_digests_present"] is True
    assert resolution.provenance["replay_integrity"]["mismatched_artifacts"] == ["qiskit_code"]
    assert resolution.provenance["replay_integrity"]["missing_artifacts"] == []


def test_resolve_report_file_accepts_workspace_prefixed_legacy_relative_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    workspace = Path("tmp-review-old-bug-report")
    result = execute_intent(workspace_root=workspace, intent_file=PROJECT_ROOT / "examples" / "intent-ghz.md")
    assert result.status == "ok"

    absolute_workspace = (tmp_path / workspace).resolve()
    report_file = absolute_workspace / "reports" / "latest.json"
    payload = json.loads(report_file.read_text())
    payload["qspec"]["path"] = "tmp-review-old-bug-report/specs/current.json"
    payload["artifacts"]["qspec"] = "tmp-review-old-bug-report/specs/current.json"
    payload["artifacts"]["report"] = "tmp-review-old-bug-report/reports/latest.json"
    payload["artifacts"]["qiskit_code"] = "tmp-review-old-bug-report/artifacts/qiskit/main.py"
    payload["provenance"]["artifacts"] = {
        "snapshot_root": f"tmp-review-old-bug-report/artifacts/history/{payload['revision']}",
        "current_root": "tmp-review-old-bug-report/artifacts",
        "paths": {
            "qspec": "tmp-review-old-bug-report/specs/current.json",
            "report": "tmp-review-old-bug-report/reports/latest.json",
            "qiskit_code": "tmp-review-old-bug-report/artifacts/qiskit/main.py",
        },
        "current_aliases": {
            "qspec": "tmp-review-old-bug-report/specs/current.json",
            "report": "tmp-review-old-bug-report/reports/latest.json",
            "qiskit_code": "tmp-review-old-bug-report/artifacts/qiskit/main.py",
        },
    }
    report_file.write_text(json.dumps(payload, indent=2))

    resolution = resolve_report_file(report_file)

    assert resolution.qspec_path == absolute_workspace / "specs" / "history" / "rev_000001.json"
    assert resolution.report_path == report_file
    assert resolution.provenance["artifacts"]["snapshot_root"] == str(
        absolute_workspace / "artifacts" / "history" / "rev_000001"
    )
    assert resolution.provenance["artifacts"]["current_root"] == str(absolute_workspace / "artifacts")
    assert resolution.provenance["artifacts"]["current_aliases"]["qspec"] == str(
        absolute_workspace / "specs" / "current.json"
    )
    assert resolution.provenance["artifacts"]["current_aliases"]["report"] == str(
        absolute_workspace / "reports" / "latest.json"
    )
    assert resolution.artifacts["qspec"] == str(absolute_workspace / "specs" / "history" / "rev_000001.json")
    assert resolution.artifacts["report"] == str(absolute_workspace / "reports" / "history" / "rev_000001.json")
    assert resolution.artifacts["qiskit_code"] == str(
        absolute_workspace / "artifacts" / "history" / "rev_000001" / "qiskit" / "main.py"
    )


def _seed_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / ".quantum"
    result = execute_intent(workspace_root=workspace, intent_file=PROJECT_ROOT / "examples" / "intent-ghz.md")
    assert result.status == "ok"
    return workspace


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"
