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


def _equivalent_qaoa_sweep_qspecs() -> list[QSpec]:
    markdown_path = PROJECT_ROOT / "examples" / "intent-qaoa-maxcut-sweep.md"
    markdown_text = markdown_path.read_text()
    structured_json_text = parse_intent_file(markdown_path).model_dump_json(indent=2)
    return [
        plan_to_qspec(parse_intent_file(markdown_path)),
        plan_to_qspec(parse_intent_text(markdown_text)),
        plan_to_qspec(parse_intent_json_text(structured_json_text)),
    ]


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
