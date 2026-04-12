from __future__ import annotations

import json
from pathlib import Path

from quantum_runtime.runtime.executor import execute_intent
from quantum_runtime.runtime.imports import resolve_report_file, resolve_workspace_baseline
from quantum_runtime.workspace import WorkspaceBaseline, WorkspaceManager, WorkspacePaths


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_workspace_baseline_round_trips_current_record(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    WorkspaceManager.load_or_init(workspace)
    paths = WorkspacePaths(root=workspace)

    baseline = WorkspaceBaseline(
        source_kind="report_revision",
        source="report_revision:rev_000001",
        workspace_root=str(paths.root),
        workspace_project_id="proj_test",
        revision="rev_000001",
        report_path=str(paths.root / "reports" / "history" / "rev_000001.json"),
        qspec_path=str(paths.root / "specs" / "history" / "rev_000001.json"),
        report_hash="sha256:report",
        qspec_hash="sha256:qspec",
        report_status="ok",
        qspec_summary={
            "pattern": "ghz",
            "workload_hash": "sha256:workload",
            "execution_hash": "sha256:execution",
            "parameter_count": 0,
        },
    )

    baseline.save(paths.baseline_current_json)
    loaded = WorkspaceBaseline.load(paths.baseline_current_json)

    assert paths.baselines_dir == paths.root / "baselines"
    assert paths.baseline_current_json == paths.baselines_dir / "current.json"
    assert loaded == baseline
    assert loaded.source_kind == "report_revision"
    assert loaded.revision == "rev_000001"
    assert loaded.report_path.endswith("reports/history/rev_000001.json")
    assert loaded.qspec_path.endswith("specs/history/rev_000001.json")
    assert loaded.report_hash == "sha256:report"
    assert loaded.qspec_hash == "sha256:qspec"
    assert loaded.qspec_summary["pattern"] == "ghz"


def test_workspace_baseline_accepts_legacy_compatible_report_resolution(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    result = execute_intent(workspace_root=workspace, intent_file=PROJECT_ROOT / "examples" / "intent-ghz.md")
    assert result.status == "ok"

    latest_report = workspace / "reports" / "latest.json"
    history_report = workspace / "reports" / "history" / "rev_000001.json"
    _remove_artifact_output_digests(latest_report)
    _remove_artifact_output_digests(history_report)
    (workspace / "manifests" / "latest.json").unlink()
    (workspace / "manifests" / "history" / "rev_000001.json").unlink()

    resolution = resolve_report_file(latest_report)
    paths = WorkspacePaths(root=workspace)
    WorkspaceBaseline.from_import_resolution(resolution).save(paths.baseline_current_json)

    baseline_resolution = resolve_workspace_baseline(workspace)

    assert baseline_resolution.record.revision == "rev_000001"
    assert baseline_resolution.record.report_path.endswith("reports/history/rev_000001.json")
    assert baseline_resolution.resolution.replay_integrity["status"] == "legacy"
    assert baseline_resolution.resolution.report_summary["replay_integrity_status"] == "legacy"


def _remove_artifact_output_digests(report_path: Path) -> None:
    payload = json.loads(report_path.read_text())
    replay_integrity = payload.get("replay_integrity")
    assert isinstance(replay_integrity, dict)
    replay_integrity.pop("artifact_output_digests", None)
    replay_integrity.pop("artifact_output_missing", None)
    replay_integrity.pop("artifact_output_set_hash", None)
    replay_integrity.pop("artifact_set_hash", None)
    report_path.write_text(json.dumps(payload, indent=2))
