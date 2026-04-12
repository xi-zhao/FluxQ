from __future__ import annotations

import json
from pathlib import Path

from quantum_runtime.runtime.executor import execute_intent
from quantum_runtime.workspace.paths import WorkspacePaths


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _execute_example_intent(*, workspace: Path, name: str):
    return execute_intent(
        workspace_root=workspace,
        intent_file=PROJECT_ROOT / "examples" / name,
    )


def test_execute_intent_persists_revision_scoped_runtime_artifacts(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    result = _execute_example_intent(workspace=workspace, name="intent-ghz.md")

    assert result.status == "ok"
    revision = result.revision
    paths = WorkspacePaths(root=workspace)
    expected_paths = {
        "intent": paths.intent_history_json(revision),
        "plan": paths.plan_history_json(revision),
        "qspec": workspace / "specs" / "history" / f"{revision}.json",
        "report": workspace / "reports" / "history" / f"{revision}.json",
        "manifest": paths.manifest_history_json(revision),
        "events": paths.event_history_jsonl(revision),
        "trace": paths.trace_history_ndjson(revision),
    }

    for artifact_path in expected_paths.values():
        assert artifact_path.exists()

    assert result.artifacts["qspec"] == str(expected_paths["qspec"])
    assert result.artifacts["report"] == str(expected_paths["report"])
    assert result.artifacts["manifest"] == str(expected_paths["manifest"])
    assert str(expected_paths["intent"]).endswith(f"intents/history/{revision}.json")
    assert str(expected_paths["plan"]).endswith(f"plans/history/{revision}.json")
    assert str(expected_paths["events"]).endswith(f"events/history/{revision}.jsonl")
    assert str(expected_paths["trace"]).endswith(f"trace/history/{revision}.ndjson")


def test_run_manifest_links_intent_plan_and_event_history(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    result = _execute_example_intent(workspace=workspace, name="intent-ghz.md")

    revision = result.revision
    paths = WorkspacePaths(root=workspace)
    manifest = json.loads(paths.manifest_history_json(revision).read_text())

    assert manifest["intent"] == {
        "path": str(paths.intent_history_json(revision)),
        "hash": _sha256(paths.intent_history_json(revision)),
    }
    assert manifest["plan"] == {
        "path": str(paths.plan_history_json(revision)),
        "hash": _sha256(paths.plan_history_json(revision)),
    }
    assert manifest["events"] == {
        "events_jsonl": {
            "path": str(paths.event_history_jsonl(revision)),
            "hash": _sha256(paths.event_history_jsonl(revision)),
        },
        "trace_ndjson": {
            "path": str(paths.trace_history_ndjson(revision)),
            "hash": _sha256(paths.trace_history_ndjson(revision)),
        },
    }


def test_revision_history_artifacts_remain_immutable_after_later_exec(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    first_result = _execute_example_intent(workspace=workspace, name="intent-ghz.md")
    first_revision = first_result.revision
    paths = WorkspacePaths(root=workspace)
    first_manifest_path = paths.manifest_history_json(first_revision)
    first_events_path = paths.event_history_jsonl(first_revision)
    first_trace_path = paths.trace_history_ndjson(first_revision)
    first_manifest_before = json.loads(first_manifest_path.read_text())
    first_events_before = first_events_path.read_text()
    first_trace_before = first_trace_path.read_text()

    second_result = _execute_example_intent(workspace=workspace, name="intent-qaoa-maxcut.md")

    assert second_result.revision == "rev_000002"

    first_manifest_after = json.loads(first_manifest_path.read_text())
    assert first_manifest_after["revision"] == "rev_000001"
    assert first_manifest_after["intent"]["path"].endswith("intents/history/rev_000001.json")
    assert first_manifest_after["plan"]["path"].endswith("plans/history/rev_000001.json")
    assert first_manifest_after["qspec"]["path"].endswith("specs/history/rev_000001.json")
    assert first_manifest_after["report"]["path"].endswith("reports/history/rev_000001.json")
    assert first_manifest_after["events"]["events_jsonl"]["path"].endswith(
        "events/history/rev_000001.jsonl"
    )
    assert first_manifest_after["events"]["trace_ndjson"]["path"].endswith(
        "trace/history/rev_000001.ndjson"
    )
    assert first_manifest_after == first_manifest_before
    assert first_events_path.read_text() == first_events_before
    assert first_trace_path.read_text() == first_trace_before


def _sha256(path: Path) -> str:
    return "sha256:" + __import__("hashlib").sha256(path.read_bytes()).hexdigest()
