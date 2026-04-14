from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from quantum_runtime.cli import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()


def test_qrun_pack_import_json_imports_verified_bundle_into_target_workspace(tmp_path: Path) -> None:
    source_workspace = tmp_path / "source" / ".quantum"
    target_workspace = tmp_path / "target" / ".quantum"
    bundle_root = _copied_pack_bundle(source_workspace=source_workspace)
    shutil.rmtree(source_workspace)

    result = RUNNER.invoke(
        app,
        [
            "pack-import",
            "--pack-root",
            str(bundle_root),
            "--workspace",
            str(target_workspace),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["revision"] == "rev_000001"

    for relative_path in (
        "reports/history/rev_000001.json",
        "specs/history/rev_000001.json",
        "manifests/history/rev_000001.json",
        "events/history/rev_000001.jsonl",
        "trace/history/rev_000001.ndjson",
    ):
        assert (target_workspace / relative_path).exists()

    show_result = RUNNER.invoke(
        app,
        [
            "show",
            "--workspace",
            str(target_workspace),
            "--revision",
            "rev_000001",
            "--json",
        ],
    )
    assert show_result.exit_code == 0, show_result.stdout
    show_payload = json.loads(show_result.stdout)
    assert show_payload["revision"] == "rev_000001"
    assert show_payload["report_summary"]["replay_integrity_status"] == "ok"

    inspect_result = RUNNER.invoke(
        app,
        [
            "inspect",
            "--workspace",
            str(target_workspace),
            "--json",
        ],
    )
    assert inspect_result.exit_code == 0, inspect_result.stdout
    inspect_payload = json.loads(inspect_result.stdout)
    assert inspect_payload["revision"] == "rev_000001"
    assert inspect_payload["replay_integrity"]["status"] == "ok"


def test_qrun_pack_import_json_rejects_invalid_bundle_before_writing_workspace(tmp_path: Path) -> None:
    source_workspace = tmp_path / "source" / ".quantum"
    target_workspace = tmp_path / "target" / ".quantum"
    bundle_root = _copied_pack_bundle(source_workspace=source_workspace)
    qspec_path = bundle_root / "qspec.json"
    qspec_payload = json.loads(qspec_path.read_text())
    qspec_payload["tampered"] = True
    qspec_path.write_text(json.dumps(qspec_payload, indent=2))

    result = RUNNER.invoke(
        app,
        [
            "pack-import",
            "--pack-root",
            str(bundle_root),
            "--workspace",
            str(target_workspace),
            "--json",
        ],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["reason"] == "pack_bundle_invalid"
    assert not target_workspace.exists()
    assert not (target_workspace / "reports" / "history" / "rev_000001.json").exists()
    assert not (target_workspace / "specs" / "history" / "rev_000001.json").exists()
    assert not (target_workspace / "manifests" / "history" / "rev_000001.json").exists()


def test_qrun_pack_import_json_rejects_conflicting_existing_revision(tmp_path: Path) -> None:
    source_workspace = tmp_path / "source" / ".quantum"
    target_workspace = tmp_path / "target" / ".quantum"
    bundle_root = _copied_pack_bundle(source_workspace=source_workspace)

    conflicting_exec = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(target_workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-qaoa-maxcut.md"),
            "--json",
        ],
    )
    assert conflicting_exec.exit_code == 0, conflicting_exec.stdout
    before_snapshot = _workspace_file_snapshot(target_workspace)

    result = RUNNER.invoke(
        app,
        [
            "pack-import",
            "--pack-root",
            str(bundle_root),
            "--workspace",
            str(target_workspace),
            "--json",
        ],
    )

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["reason"] == "pack_revision_conflict"
    assert _workspace_file_snapshot(target_workspace) == before_snapshot


def _copied_pack_bundle(*, source_workspace: Path) -> Path:
    exec_result = RUNNER.invoke(
        app,
        [
            "exec",
            "--workspace",
            str(source_workspace),
            "--intent-file",
            str(PROJECT_ROOT / "examples" / "intent-ghz.md"),
            "--json",
        ],
    )
    assert exec_result.exit_code == 0, exec_result.stdout
    revision = json.loads(exec_result.stdout)["revision"]

    pack_result = RUNNER.invoke(
        app,
        [
            "pack",
            "--workspace",
            str(source_workspace),
            "--revision",
            revision,
            "--json",
        ],
    )
    assert pack_result.exit_code == 0, pack_result.stdout
    pack_root = Path(json.loads(pack_result.stdout)["pack_root"])
    copied_bundle = source_workspace.parent / "copied-bundle"
    shutil.copytree(pack_root, copied_bundle)
    return copied_bundle


def _workspace_file_snapshot(workspace_root: Path) -> dict[str, bytes]:
    return {
        candidate.relative_to(workspace_root).as_posix(): candidate.read_bytes()
        for candidate in sorted(workspace_root.rglob("*"))
        if candidate.is_file()
    }
