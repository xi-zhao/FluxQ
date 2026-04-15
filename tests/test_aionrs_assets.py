from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AIONRS_COMPARE_COMMAND = (
    "qrun compare --workspace .quantum --baseline --fail-on subject_drift --json"
)
AIONRS_DOCTOR_CI_COMMAND = "qrun doctor --workspace .quantum --json --ci"
AIONRS_PACK_COMMAND = "qrun pack --workspace .quantum --revision rev_000001 --json"
AIONRS_PACK_INSPECT_COMMAND = (
    "qrun pack-inspect --pack-root .quantum/packs/rev_000001 --json"
)
AIONRS_PACK_IMPORT_COMMAND = (
    "qrun pack-import --pack-root .quantum/packs/rev_000001 "
    "--workspace downstream/.quantum --json"
)
STOP_ON_GATE_RULE = (
    "If compare or doctor returns a blocking gate, revise the intent and rerun FluxQ; "
    "do not hand-edit generated quantum code to bypass the gate."
)


def test_aionrs_integration_assets_exist_with_runnable_workflow() -> None:
    claude_example = PROJECT_ROOT / "integrations" / "aionrs" / "CLAUDE.md.example"
    hooks_example = PROJECT_ROOT / "integrations" / "aionrs" / "hooks.example.toml"
    integration_doc = PROJECT_ROOT / "docs" / "aionrs-integration.md"

    assert claude_example.exists()
    assert hooks_example.exists()
    assert integration_doc.exists()

    claude_text = claude_example.read_text()
    hooks_text = hooks_example.read_text()
    doc_text = integration_doc.read_text()

    assert "qrun exec --workspace .quantum --intent-file .quantum/intents/latest.md --json" in claude_text
    assert "reports/latest.json" in claude_text
    assert "do not handwrite large quantum programs first" in claude_text.lower()

    assert "[hooks.post_tool_use]" in hooks_text
    assert "qrun doctor --workspace .quantum" in hooks_text

    assert "do not build a custom aionrs tool" in doc_text.lower()
    assert "qrun exec --workspace .quantum --intent-file .quantum/intents/latest.md --json" in doc_text
    assert "qrun doctor --workspace .quantum" in doc_text
    assert "qrun bench --workspace .quantum --json" in doc_text


def test_aionrs_assets_cover_policy_and_delivery_handoff() -> None:
    claude_example = PROJECT_ROOT / "integrations" / "aionrs" / "CLAUDE.md.example"
    hooks_example = PROJECT_ROOT / "integrations" / "aionrs" / "hooks.example.toml"
    integration_doc = PROJECT_ROOT / "docs" / "aionrs-integration.md"

    claude_text = claude_example.read_text()
    hooks_text = hooks_example.read_text()
    doc_text = integration_doc.read_text()

    assert AIONRS_COMPARE_COMMAND in doc_text
    assert AIONRS_DOCTOR_CI_COMMAND in doc_text
    assert AIONRS_PACK_COMMAND in doc_text
    assert AIONRS_PACK_INSPECT_COMMAND in doc_text
    assert AIONRS_PACK_IMPORT_COMMAND in doc_text

    assert AIONRS_COMPARE_COMMAND in claude_text
    assert AIONRS_DOCTOR_CI_COMMAND in claude_text
    assert AIONRS_PACK_COMMAND in claude_text
    assert AIONRS_PACK_INSPECT_COMMAND in claude_text
    assert AIONRS_PACK_IMPORT_COMMAND in claude_text
    assert STOP_ON_GATE_RULE in claude_text

    assert "[hooks.post_tool_use]" in hooks_text
    assert (
        "bash -lc 'if [ -f .quantum/specs/current.json ]; then "
        "qrun doctor --workspace .quantum --json --ci >/dev/null 2>&1 || true; fi'"
    ) in hooks_text
