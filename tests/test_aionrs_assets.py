from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
    assert "qrun bench --workspace .quantum --json" in hooks_text

    assert "do not build a custom aionrs tool" in doc_text.lower()
    assert "qrun exec --workspace .quantum --intent-file .quantum/intents/latest.md --json" in doc_text
    assert "qrun bench --workspace .quantum --json" in doc_text
