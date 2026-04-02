from __future__ import annotations

from pathlib import Path

from quantum_runtime.runtime import (
    ImportReference,
    compare_import_resolutions,
    execute_intent,
    resolve_import_reference,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_compare_import_resolutions_detects_same_subject_across_workspaces(tmp_path: Path) -> None:
    left_workspace = tmp_path / ".quantum-left"
    right_workspace = tmp_path / ".quantum-right"
    intent_path = PROJECT_ROOT / "examples" / "intent-ghz.md"

    execute_intent(workspace_root=left_workspace, intent_file=intent_path)
    execute_intent(workspace_root=right_workspace, intent_file=intent_path)

    left = resolve_import_reference(ImportReference(workspace_root=left_workspace))
    right = resolve_import_reference(ImportReference(workspace_root=right_workspace))
    result = compare_import_resolutions(left, right)

    assert result.status == "same_subject"
    assert result.same_subject is True
    assert result.same_qspec is True
    assert result.same_report is False
    assert result.left.qspec_summary["pattern"] == "ghz"
    assert result.right.qspec_summary["pattern"] == "ghz"
    assert "report_artifact_changed" in result.differences


def test_compare_import_resolutions_detects_semantic_drift_across_revisions(tmp_path: Path) -> None:
    workspace = tmp_path / ".quantum"

    execute_intent(
        workspace_root=workspace,
        intent_file=PROJECT_ROOT / "examples" / "intent-ghz.md",
    )
    execute_intent(
        workspace_root=workspace,
        intent_file=PROJECT_ROOT / "examples" / "intent-qaoa-maxcut.md",
    )

    left = resolve_import_reference(ImportReference(workspace_root=workspace, revision="rev_000001"))
    right = resolve_import_reference(ImportReference(workspace_root=workspace, revision="rev_000002"))
    result = compare_import_resolutions(left, right)

    assert result.status == "different_subject"
    assert result.same_subject is False
    assert result.same_qspec is False
    assert result.same_report is False
    assert result.semantic_delta["left"]["pattern"] == "ghz"
    assert result.semantic_delta["right"]["pattern"] == "qaoa_ansatz"
    assert "pattern" in result.semantic_delta["changed_fields"]
    assert "parameter_count" in result.semantic_delta["changed_fields"]
    assert any(diff.startswith("semantic_subject_changed") for diff in result.differences)
