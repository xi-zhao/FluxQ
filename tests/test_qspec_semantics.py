from __future__ import annotations

from pathlib import Path

from quantum_runtime.intent.parser import (
    parse_intent_file,
    parse_intent_json_text,
    parse_intent_text,
)
from quantum_runtime.intent.planner import plan_to_qspec
from quantum_runtime.qspec import QSpec
from quantum_runtime.qspec.semantics import summarize_qspec_semantics


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_PROMPT_GHZ = "Build a 4-qubit GHZ circuit and measure all qubits."


def _equivalent_qaoa_sweep_qspecs() -> list[QSpec]:
    markdown_path = PROJECT_ROOT / "examples" / "intent-qaoa-maxcut-sweep.md"
    markdown_text = markdown_path.read_text()
    structured_json_text = parse_intent_file(markdown_path).model_dump_json(indent=2)
    return [
        plan_to_qspec(parse_intent_file(markdown_path)),
        plan_to_qspec(parse_intent_text(markdown_text)),
        plan_to_qspec(parse_intent_json_text(structured_json_text)),
    ]


def _equivalent_ghz_qspecs() -> list[QSpec]:
    markdown_path = PROJECT_ROOT / "examples" / "intent-ghz.md"
    markdown_text = markdown_path.read_text()
    structured_json_text = parse_intent_file(markdown_path).model_dump_json(indent=2)
    return [
        plan_to_qspec(parse_intent_file(markdown_path)),
        plan_to_qspec(parse_intent_text(markdown_text)),
        plan_to_qspec(parse_intent_json_text(structured_json_text)),
    ]


def _raw_prompt_ghz_qspec() -> QSpec:
    return plan_to_qspec(parse_intent_text(RAW_PROMPT_GHZ))


def _golden_qspec(name: str) -> QSpec:
    return QSpec.model_validate_json(
        (PROJECT_ROOT / "tests" / "golden" / name).read_text(),
    )


def _identity_block(summary: dict[str, object]) -> dict[str, object]:
    return {
        "workload_id": summary["workload_id"],
        "workload_hash": summary["workload_hash"],
        "execution_hash": summary["execution_hash"],
        "semantic_hash": summary["semantic_hash"],
    }


def test_summarize_qspec_semantics_keeps_equivalent_ingress_hashes_aligned() -> None:
    summaries = [
        summarize_qspec_semantics(qspec)
        for qspec in _equivalent_qaoa_sweep_qspecs()
    ]
    expected_identity = _identity_block(summaries[0])

    for summary in summaries:
        assert _identity_block(summary) == expected_identity


def test_summarize_qspec_semantics_keeps_equivalent_ghz_ingress_hashes_aligned() -> None:
    summaries = [
        summarize_qspec_semantics(qspec)
        for qspec in _equivalent_ghz_qspecs()
    ]
    expected_identity = _identity_block(summaries[0])

    for summary in summaries:
        assert _identity_block(summary) == expected_identity


def test_summarize_qspec_semantics_keeps_raw_prompt_ghz_workload_hashes_aligned() -> None:
    markdown_qspec = _equivalent_ghz_qspecs()[0]
    raw_prompt_qspec = _raw_prompt_ghz_qspec()
    markdown_summary = summarize_qspec_semantics(markdown_qspec)
    raw_prompt_summary = summarize_qspec_semantics(raw_prompt_qspec)

    assert raw_prompt_summary["workload_id"] == markdown_summary["workload_id"]
    assert raw_prompt_summary["workload_hash"] == markdown_summary["workload_hash"]
    assert markdown_qspec.constraints.max_width == 4
    assert markdown_qspec.constraints.max_depth == 64
    assert raw_prompt_qspec.constraints.max_width is None
    assert raw_prompt_qspec.constraints.max_depth is None
    assert raw_prompt_summary["execution_hash"] != markdown_summary["execution_hash"]
    assert raw_prompt_summary["semantic_hash"] != markdown_summary["semantic_hash"]


def test_summarize_qspec_semantics_changes_execution_hash_without_changing_workload_hash() -> None:
    original = _equivalent_ghz_qspecs()[0]
    mutated = original.model_copy(deep=True)
    mutated.backend_preferences = ["qiskit-local", "ionq-local"]
    mutated.constraints.shots = 2048

    original_summary = summarize_qspec_semantics(original)
    mutated_summary = summarize_qspec_semantics(mutated)

    assert mutated_summary["workload_id"] == original_summary["workload_id"]
    assert mutated_summary["workload_hash"] == original_summary["workload_hash"]
    assert mutated_summary["execution_hash"] != original_summary["execution_hash"]
    assert mutated_summary["semantic_hash"] != original_summary["semantic_hash"]


def test_summarize_qspec_semantics_distinguishes_different_workloads() -> None:
    ghz_summary = summarize_qspec_semantics(_golden_qspec("qspec_ghz.json"))
    qaoa_summary = summarize_qspec_semantics(_golden_qspec("qspec_qaoa_maxcut.json"))

    assert ghz_summary["workload_id"] != qaoa_summary["workload_id"]
    assert ghz_summary["workload_hash"] != qaoa_summary["workload_hash"]
    assert ghz_summary["semantic_hash"] != qaoa_summary["semantic_hash"]


def test_semantic_hash_tracks_execution_hash_contract() -> None:
    summaries = [
        summarize_qspec_semantics(_equivalent_qaoa_sweep_qspecs()[0]),
        summarize_qspec_semantics(_golden_qspec("qspec_ghz.json")),
    ]

    for summary in summaries:
        assert summary["semantic_hash"] == summary["execution_hash"]
        assert summary["workload_hash"] != summary["semantic_hash"]
