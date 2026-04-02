from __future__ import annotations

import json
from pathlib import Path

from quantum_runtime.workspace import WorkspaceManager


def test_load_or_init_creates_workspace_handle(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    handle = WorkspaceManager.load_or_init(workspace)

    assert handle.root == workspace
    assert handle.manifest.project_id.startswith("proj_")
    assert handle.paths.workspace_json.exists()
    assert handle.paths.trace_events.exists()


def test_reserve_revision_persists_manifest(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    handle = WorkspaceManager.load_or_init(workspace)
    revision = handle.reserve_revision()

    assert revision == "rev_000001"

    reloaded = WorkspaceManager.load_or_init(workspace)
    assert reloaded.manifest.current_revision == "rev_000001"


def test_trace_append_writes_ndjson_event(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    handle = WorkspaceManager.load_or_init(workspace)
    handle.reserve_revision()
    handle.trace.append(
        event_type="intent_loaded",
        payload={"path": "examples/intent-ghz.md"},
        revision=handle.manifest.current_revision,
    )

    lines = handle.paths.trace_events.read_text().strip().splitlines()
    assert len(lines) == 1

    record = json.loads(lines[0])
    assert record["event_type"] == "intent_loaded"
    assert record["revision"] == "rev_000001"
    assert record["payload"] == {"path": "examples/intent-ghz.md"}
