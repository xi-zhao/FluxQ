from __future__ import annotations

from pathlib import Path

from quantum_runtime.workspace import WorkspaceBaseline, WorkspaceManager, WorkspacePaths


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
