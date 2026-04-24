from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from quantum_runtime.qspec import QSpec, summarize_qspec_semantics
from quantum_runtime.runtime.executor import execute_intent
from quantum_runtime.runtime.run_manifest import RunManifestIntegrityError, load_run_manifest
from quantum_runtime.workspace.paths import WorkspacePaths


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _execute_example_intent(*, workspace: Path, name: str):
    return execute_intent(
        workspace_root=workspace,
        intent_file=PROJECT_ROOT / "examples" / name,
    )


def _revision_artifact_paths(*, workspace: Path, revision: str) -> dict[str, Path]:
    paths = WorkspacePaths(root=workspace)
    return {
        "intent": paths.intent_history_json(revision),
        "plan": paths.plan_history_json(revision),
        "qspec": workspace / "specs" / "history" / f"{revision}.json",
        "report": workspace / "reports" / "history" / f"{revision}.json",
        "manifest": paths.manifest_history_json(revision),
        "events_jsonl": paths.event_history_jsonl(revision),
        "trace_ndjson": paths.trace_history_ndjson(revision),
    }


def _load_manifest_payload(path: Path) -> dict[str, object]:
    return json.loads(path.read_text())


def _write_manifest_payload(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2))


def _manifest_block(manifest: dict[str, object], block_name: str) -> dict[str, object]:
    if block_name in {"intent", "plan"}:
        return manifest[block_name]  # type: ignore[index]

    events_block = manifest["events"]  # type: ignore[index]
    assert isinstance(events_block, dict)
    block = events_block[block_name]
    assert isinstance(block, dict)
    return block


def _copy_history_artifact(*, source: Path, redirect_root: Path) -> Path:
    redirect_path = redirect_root / source.name
    redirect_path.parent.mkdir(parents=True, exist_ok=True)
    redirect_path.write_bytes(source.read_bytes())
    return redirect_path


def _validated_manifest(*, workspace: Path, revision: str, artifact_paths: dict[str, Path]) -> dict[str, object]:
    manifest = load_run_manifest(
        workspace_root=workspace,
        revision=revision,
        expected_qspec_path=artifact_paths["qspec"],
        expected_report_path=artifact_paths["report"],
    )
    assert manifest is not None
    return manifest


@pytest.mark.parametrize(
    ("block_name", "expected_mismatch"),
    [
        ("intent", "intent_path"),
        ("plan", "plan_path"),
        ("events_jsonl", "events_jsonl_path"),
        ("trace_ndjson", "trace_ndjson_path"),
    ],
)
def test_run_manifest_rejects_redirected_same_hash_history_artifacts(
    tmp_path: Path,
    block_name: str,
    expected_mismatch: str,
) -> None:
    workspace = tmp_path / ".quantum"
    result = _execute_example_intent(workspace=workspace, name="intent-ghz.md")
    revision = result.revision
    artifact_paths = _revision_artifact_paths(workspace=workspace, revision=revision)
    manifest_path = artifact_paths["manifest"]
    manifest = _load_manifest_payload(manifest_path)

    block = _manifest_block(manifest, block_name)
    source_path = Path(str(block["path"]))
    redirect_path = _copy_history_artifact(
        source=source_path,
        redirect_root=tmp_path / "redirected" / block_name,
    )
    block["path"] = str(redirect_path)
    _write_manifest_payload(manifest_path, manifest)

    with pytest.raises(RunManifestIntegrityError) as exc_info:
        _validated_manifest(
            workspace=workspace,
            revision=revision,
            artifact_paths=artifact_paths,
        )

    assert exc_info.value.mismatches == [expected_mismatch]
    assert exc_info.value.details[f"expected_{block_name}_path"] == str(source_path.resolve())
    assert exc_info.value.details[f"actual_{block_name}_path"] == str(redirect_path.resolve())


@pytest.mark.parametrize(
    ("block_name", "expected_mismatch"),
    [
        ("intent", "intent_hash"),
        ("plan", "plan_hash"),
        ("events_jsonl", "events_jsonl_hash"),
        ("trace_ndjson", "trace_ndjson_hash"),
    ],
)
def test_run_manifest_rejects_hash_drift_at_canonical_history_paths(
    tmp_path: Path,
    block_name: str,
    expected_mismatch: str,
) -> None:
    workspace = tmp_path / ".quantum"
    result = _execute_example_intent(workspace=workspace, name="intent-ghz.md")
    revision = result.revision
    artifact_paths = _revision_artifact_paths(workspace=workspace, revision=revision)
    manifest = _load_manifest_payload(artifact_paths["manifest"])
    block = _manifest_block(manifest, block_name)
    canonical_path = Path(str(block["path"]))

    canonical_path.write_text("tampered\n")

    with pytest.raises(RunManifestIntegrityError) as exc_info:
        _validated_manifest(
            workspace=workspace,
            revision=revision,
            artifact_paths=artifact_paths,
        )

    assert exc_info.value.mismatches == [expected_mismatch]
    assert exc_info.value.details[f"{block_name}_expected_hash"] == str(block["hash"])
    assert exc_info.value.details[f"{block_name}_actual_hash"] == _sha256(canonical_path)


def test_execute_intent_persists_revision_scoped_runtime_artifacts(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    result = _execute_example_intent(workspace=workspace, name="intent-ghz.md")

    assert result.status == "ok"
    revision = result.revision
    artifact_paths = _revision_artifact_paths(workspace=workspace, revision=revision)

    for artifact_path in artifact_paths.values():
        assert artifact_path.exists()
        assert artifact_path.is_file()

    manifest = _validated_manifest(
        workspace=workspace,
        revision=revision,
        artifact_paths=artifact_paths,
    )
    assert result.artifacts["qspec"] == str(artifact_paths["qspec"])
    assert result.artifacts["report"] == str(artifact_paths["report"])
    assert result.artifacts["manifest"] == str(artifact_paths["manifest"])
    assert manifest["revision"] == revision
    assert manifest["intent"] == {
        "path": str(artifact_paths["intent"]),
        "hash": _sha256(artifact_paths["intent"]),
    }
    assert manifest["plan"] == {
        "path": str(artifact_paths["plan"]),
        "hash": _sha256(artifact_paths["plan"]),
    }
    assert manifest["events"] == {
        "events_jsonl": {
            "path": str(artifact_paths["events_jsonl"]),
            "hash": _sha256(artifact_paths["events_jsonl"]),
        },
        "trace_ndjson": {
            "path": str(artifact_paths["trace_ndjson"]),
            "hash": _sha256(artifact_paths["trace_ndjson"]),
        },
    }


def test_run_manifest_stays_readable_when_additive_history_blocks_are_absent(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"
    result = _execute_example_intent(workspace=workspace, name="intent-ghz.md")
    revision = result.revision
    artifact_paths = _revision_artifact_paths(workspace=workspace, revision=revision)
    manifest_path = artifact_paths["manifest"]
    manifest = _load_manifest_payload(manifest_path)

    manifest.pop("intent")
    manifest.pop("plan")
    manifest.pop("events")
    _write_manifest_payload(manifest_path, manifest)

    validated = _validated_manifest(
        workspace=workspace,
        revision=revision,
        artifact_paths=artifact_paths,
    )

    assert validated["revision"] == revision
    assert validated["qspec"]["path"] == str(artifact_paths["qspec"])  # type: ignore[index]
    assert validated["report"]["path"] == str(artifact_paths["report"])  # type: ignore[index]
    assert validated["intent"] == {}
    assert validated["plan"] == {}
    assert validated["events"] == {}


def test_revision_history_artifacts_remain_immutable_after_later_exec(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    first_result = _execute_example_intent(workspace=workspace, name="intent-ghz.md")
    first_revision = first_result.revision
    first_paths = _revision_artifact_paths(workspace=workspace, revision=first_revision)
    first_manifest_before = first_paths["manifest"].read_bytes()
    first_intent_before = first_paths["intent"].read_bytes()
    first_plan_before = first_paths["plan"].read_bytes()
    first_events_before = first_paths["events_jsonl"].read_bytes()
    first_trace_before = first_paths["trace_ndjson"].read_bytes()

    second_result = _execute_example_intent(workspace=workspace, name="intent-qaoa-maxcut.md")
    second_revision = second_result.revision
    second_paths = _revision_artifact_paths(workspace=workspace, revision=second_revision)

    assert second_revision == "rev_000002"
    assert first_paths["manifest"].read_bytes() == first_manifest_before
    assert first_paths["intent"].read_bytes() == first_intent_before
    assert first_paths["plan"].read_bytes() == first_plan_before
    assert first_paths["events_jsonl"].read_bytes() == first_events_before
    assert first_paths["trace_ndjson"].read_bytes() == first_trace_before

    first_manifest = _validated_manifest(
        workspace=workspace,
        revision=first_revision,
        artifact_paths=first_paths,
    )
    second_manifest = _validated_manifest(
        workspace=workspace,
        revision=second_revision,
        artifact_paths=second_paths,
    )

    assert first_manifest["revision"] == "rev_000001"
    assert first_manifest["intent"]["path"].endswith("intents/history/rev_000001.json")  # type: ignore[index]
    assert first_manifest["plan"]["path"].endswith("plans/history/rev_000001.json")  # type: ignore[index]
    assert first_manifest["events"]["events_jsonl"]["path"].endswith(  # type: ignore[index]
        "events/history/rev_000001.jsonl"
    )
    assert first_manifest["events"]["trace_ndjson"]["path"].endswith(  # type: ignore[index]
        "trace/history/rev_000001.ndjson"
    )
    assert second_manifest["revision"] == "rev_000002"
    assert second_manifest["intent"]["path"].endswith("intents/history/rev_000002.json")  # type: ignore[index]
    assert second_manifest["plan"]["path"].endswith("plans/history/rev_000002.json")  # type: ignore[index]


def test_second_exec_keeps_revision_report_and_qspec_semantics_aligned(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    first_result = _execute_example_intent(workspace=workspace, name="intent-ghz.md")
    second_result = _execute_example_intent(workspace=workspace, name="intent-qaoa-maxcut.md")

    first_paths = _revision_artifact_paths(workspace=workspace, revision=first_result.revision)
    second_paths = _revision_artifact_paths(workspace=workspace, revision=second_result.revision)
    first_report = json.loads(first_paths["report"].read_text())
    second_report = json.loads(second_paths["report"].read_text())
    second_qspec = QSpec.model_validate_json(second_paths["qspec"].read_text())
    second_semantics = summarize_qspec_semantics(second_qspec)

    assert second_result.revision == "rev_000002"
    assert first_report["qspec"]["path"] == str(first_paths["qspec"])
    assert second_report["qspec"]["path"] == str(second_paths["qspec"])
    assert first_paths["qspec"].read_bytes() != second_paths["qspec"].read_bytes()
    assert second_report["qspec"]["hash"] == _sha256(second_paths["qspec"])
    assert second_report["qspec"]["semantic_hash"] == second_semantics["semantic_hash"]

    manifest = load_run_manifest(
        workspace_root=workspace,
        revision=second_result.revision,
        expected_qspec_path=second_paths["qspec"],
        expected_report_path=second_paths["report"],
    )

    assert manifest is not None
    assert manifest["qspec"]["path"] == str(second_paths["qspec"])  # type: ignore[index]
    assert manifest["report"]["path"] == str(second_paths["report"])  # type: ignore[index]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"
