from __future__ import annotations

from pathlib import Path

import pytest

from quantum_runtime.intent.parser import parse_intent_file
from quantum_runtime.runtime.control_plane import build_execution_plan, resolve_runtime_object
from quantum_runtime.runtime.resolve import resolve_runtime_input


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _equivalent_ingress_inputs(tmp_path: Path) -> tuple[Path, str, Path]:
    markdown_path = PROJECT_ROOT / "examples" / "intent-qaoa-maxcut-sweep.md"
    structured_json_path = tmp_path / "intent-qaoa-maxcut-sweep.json"
    structured_json_path.write_text(
        parse_intent_file(markdown_path).model_dump_json(indent=2),
    )
    return markdown_path, markdown_path.read_text(), structured_json_path


def _identity_fields(payload: dict[str, object]) -> dict[str, object]:
    return {
        "workload_id": payload["workload_id"],
        "workload_hash": payload["workload_hash"],
        "semantic_hash": payload["semantic_hash"],
    }


def test_resolve_runtime_input_keeps_prompt_markdown_json_qspec_parity(tmp_path: Path) -> None:
    workspace_root = tmp_path / "missing-workspace"
    markdown_path, prompt_text, structured_json_path = _equivalent_ingress_inputs(tmp_path)

    assert not workspace_root.exists()

    resolved_inputs = [
        resolve_runtime_input(
            workspace_root=workspace_root,
            intent_file=markdown_path,
        ),
        resolve_runtime_input(
            workspace_root=workspace_root,
            intent_text=prompt_text,
        ),
        resolve_runtime_input(
            workspace_root=workspace_root,
            intent_json_file=structured_json_path,
        ),
    ]

    expected_qspec = resolved_inputs[0].qspec.model_dump(mode="json")
    expected_exports = resolved_inputs[0].requested_exports

    for resolved in resolved_inputs:
        assert resolved.qspec.model_dump(mode="json") == expected_qspec
        assert resolved.requested_exports == expected_exports

    assert not workspace_root.exists()


def test_resolve_runtime_object_and_plan_keep_cross_ingress_identity(tmp_path: Path) -> None:
    workspace_root = tmp_path / "missing-workspace"
    markdown_path, prompt_text, structured_json_path = _equivalent_ingress_inputs(tmp_path)

    assert not workspace_root.exists()

    resolve_results = [
        resolve_runtime_object(
            workspace_root=workspace_root,
            intent_file=markdown_path,
        ),
        resolve_runtime_object(
            workspace_root=workspace_root,
            intent_text=prompt_text,
        ),
        resolve_runtime_object(
            workspace_root=workspace_root,
            intent_json_file=structured_json_path,
        ),
    ]
    plan_results = [
        build_execution_plan(
            workspace_root=workspace_root,
            intent_file=markdown_path,
        ),
        build_execution_plan(
            workspace_root=workspace_root,
            intent_text=prompt_text,
        ),
        build_execution_plan(
            workspace_root=workspace_root,
            intent_json_file=structured_json_path,
        ),
    ]

    expected_identity = _identity_fields(resolve_results[0].qspec)
    expected_backends = resolve_results[0].plan["execution"]["selected_backends"]

    for result in resolve_results:
        assert _identity_fields(result.qspec) == expected_identity
        assert result.plan["execution"]["selected_backends"] == expected_backends

    for result in plan_results:
        assert _identity_fields(result.qspec) == expected_identity
        assert result.execution["selected_backends"] == expected_backends

    assert not workspace_root.exists()


def test_resolve_runtime_input_requires_exactly_one_input(tmp_path: Path) -> None:
    workspace_root = tmp_path / "missing-workspace"

    with pytest.raises(ValueError) as no_input_error:
        resolve_runtime_input(workspace_root=workspace_root)

    assert str(no_input_error.value) == "expected_exactly_one_input"

    with pytest.raises(ValueError) as multi_input_error:
        resolve_runtime_input(
            workspace_root=workspace_root,
            intent_file=PROJECT_ROOT / "examples" / "intent-ghz.md",
            intent_text="Generate a GHZ circuit.",
        )

    assert str(multi_input_error.value) == "expected_exactly_one_input"
