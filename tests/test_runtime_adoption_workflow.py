from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ADOPTION_COMMANDS = [
    'qrun prompt "Build a 4-qubit GHZ circuit and measure all qubits." --json',
    "qrun resolve --workspace .quantum --intent-file examples/intent-ghz.md --json",
    "qrun init --workspace .quantum --json",
    "qrun plan --workspace .quantum --intent-file examples/intent-ghz.md --json",
    "qrun exec --workspace .quantum --intent-file examples/intent-ghz.md --jsonl",
    "qrun baseline set --workspace .quantum --revision rev_000001 --json",
    "qrun compare --workspace .quantum --baseline --fail-on subject_drift --json",
    "qrun doctor --workspace .quantum --json --ci",
    "qrun pack --workspace .quantum --revision rev_000001 --json",
    "qrun pack-inspect --pack-root .quantum/packs/rev_000001 --json",
    "qrun pack-import --pack-root .quantum/packs/rev_000001 --workspace downstream/.quantum --json",
]


def test_agent_ci_adoption_doc_covers_canonical_runtime_loop() -> None:
    adoption_doc = PROJECT_ROOT / "docs" / "agent-ci-adoption.md"

    assert adoption_doc.exists()

    text = adoption_doc.read_text()

    for heading in (
        "# Runtime Adoption Workflow",
        "## Canonical Loop",
        "## Agent Host Loop",
        "## CI Gate",
        "## Delivery Handoff",
    ):
        assert heading in text

    for command in CANONICAL_ADOPTION_COMMANDS:
        assert command in text


def test_qaoa_case_study_covers_policy_and_delivery_handoff() -> None:
    case_study = PROJECT_ROOT / "docs" / "fluxq-qaoa-maxcut-case-study.md"
    text = case_study.read_text()

    assert "## Agent/CI continuation" in text
    assert "## Delivery handoff" in text

    for command in (
        "qrun compare --workspace .quantum --baseline --fail-on subject_drift --json",
        "qrun doctor --workspace .quantum --json --ci",
        "qrun pack --workspace .quantum --revision rev_000001 --json",
        "qrun pack-inspect --pack-root .quantum/packs/rev_000001 --json",
        "qrun pack-import --pack-root .quantum/packs/rev_000001 --workspace downstream/.quantum --json",
    ):
        assert command in text

    assert text.index("pack-inspect") < text.index("pack-import")

    for signal in ("reason_codes", "next_actions", "gate"):
        assert signal in text
