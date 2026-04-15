from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_release_docs_cover_runnable_readme_and_release_assets() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text()
    architecture = PROJECT_ROOT / "ARCHITECTURE.md"
    changelog = PROJECT_ROOT / "CHANGELOG.md"
    release_notes = PROJECT_ROOT / "docs" / "releases" / "v0.3.1.md"
    product_strategy = PROJECT_ROOT / "docs" / "product-strategy.md"
    roadmap = PROJECT_ROOT / "docs" / "plans" / "2026-04-02-product-roadmap.md"
    versioning = PROJECT_ROOT / "docs" / "versioning.md"

    assert "# FluxQ" in readme
    assert "![Release]" in readme
    assert "![License]" in readme
    assert "![Python]" in readme
    assert "agent-first quantum runtime CLI" in readme
    assert "Natural language is ingress" in readme
    assert "runtime control plane" in readme
    assert "## Why FluxQ" in readme
    assert "immutable manifests" in readme
    assert "semantic workload comparison" in readme
    assert "## Install" in readme
    assert "uv tool install git+https://github.com/xi-zhao/FluxQ@v0.3.1" in readme
    assert "This public install includes the local `qiskit-local` runtime stack. `classiq` remains optional." in readme
    assert "uv pip install -e '.[dev]'" in readme
    assert "## First Run" in readme
    assert "qrun init --workspace .quantum --json" in readme
    assert "qrun plan --workspace .quantum --intent-file examples/intent-ghz.md --json" in readme
    assert "qrun exec --workspace .quantum --intent-file examples/intent-ghz.md --jsonl" in readme
    assert "qrun baseline set --workspace .quantum --revision rev_000001 --json" in readme
    assert "qrun status --workspace .quantum --json" in readme
    assert "qrun show --workspace .quantum --json" in readme
    assert "qrun compare --workspace .quantum --baseline --fail-on subject_drift --json" in readme
    assert "qrun export --workspace .quantum --report-file .quantum/reports/latest.json --format qasm3 --json" in readme
    assert "qrun bench --workspace .quantum --json" in readme
    assert "qrun doctor --workspace .quantum --json --ci" in readme
    assert "qrun pack-inspect --pack-root .quantum/packs/rev_000001 --json" in readme
    assert "qrun pack-import --pack-root .quantum/packs/rev_000001 --workspace downstream/.quantum --json" in readme
    assert (
        "This first supported path is prompt/resolve -> init/plan/exec -> baseline -> compare -> doctor --ci -> pack -> pack-inspect -> pack-import."
        in readme
    )
    assert "## Runtime Object" in readme
    assert "## Trust And Replay" in readme
    assert "## Decision Loop" in readme
    assert "## Command Reference" in readme
    assert "qrun show --workspace .quantum --revision rev_000001 --json" in readme
    assert "qrun schema manifest" in readme
    assert "docs/product-strategy.md" in readme
    assert "docs/aionrs-integration.md" in readme
    assert "docs/plans/2026-04-02-product-roadmap.md" in readme
    assert "`schema_version`" in readme
    assert "`health`, `reason_codes`, `next_actions`, and `decision` or `gate` blocks" in readme
    assert "`--jsonl` event streams for `qrun exec`, `qrun compare`, `qrun bench`, and `qrun doctor`" in readme
    assert "`source_kind`, `source_revision`, `source_report_path`, and `source_qspec_path`" in readme
    assert "`detached_report_inputs`" in readme
    assert "`replay_integrity`" in readme
    assert "workspace baselines persist approved report/QSpec states" in readme
    assert "`qrun status --json` reports workspace, active artifact, and baseline readiness" in readme
    assert "`replay_integrity_delta`" in readme
    assert "report-backed imports now enforce replay integrity for QSpec identity" in readme
    assert "qrun compare --forbid-replay-integrity-regressions --json" in readme
    assert "Detached copied reports still replay, but `qrun compare --json` degrades with exit code `2`" in readme
    assert "`structural_only`, `target_aware`, and `synthesis_backed`" in readme
    assert "FluxQ does not present Qiskit transpile metrics and Classiq synthesis metrics as directly equivalent by default" in readme
    assert "`benchmark_mode`, `comparable`, `comparability_reason`, `target_parity`, `target_assumptions`, and `fallback_reason`" in readme
    assert "When `--backends` is omitted, `qrun bench` defaults to `qiskit-local` plus any optional backend the active QSpec explicitly requests." in readme
    assert "missing optional backends as advisories unless the active workspace actually depends on them" in readme
    assert "bounded local evaluation" in readme
    assert "not an optimizer, gradient engine, or remote execution story" in readme
    assert "Apache-2.0" in readme
    assert "docs/releases/v0.3.1.md" in readme
    assert "CONTRIBUTING.md" in readme
    assert "SECURITY.md" in readme
    assert "SUPPORT.md" in readme

    assert architecture.exists()
    architecture_text = architecture.read_text()
    assert "Intent" in architecture_text
    assert "QSpec" in architecture_text
    assert "Adapter / Lowering" in architecture_text
    assert "Diagnostics" in architecture_text
    assert "Control Plane" in architecture_text
    assert "manifests/history/<revision>.json" in architecture_text

    assert changelog.exists()
    changelog_text = changelog.read_text()
    assert "Unreleased" in changelog_text
    assert "0.3.1" in changelog_text
    assert "agent-observability release" in changelog_text
    assert "add `--jsonl` event streams for `qrun exec`, `qrun compare`, `qrun bench`, and `qrun doctor`" in changelog_text
    assert "add `health`, `reason_codes`, `next_actions`, and `decision` or `gate` blocks" in changelog_text

    assert release_notes.exists()
    release_notes_text = release_notes.read_text()
    assert "# FluxQ v0.3.1" in release_notes_text
    assert "## Why This Release Matters" in release_notes_text
    assert "## Highlights" in release_notes_text
    assert "## Install" in release_notes_text
    assert "uv tool install git+https://github.com/xi-zhao/FluxQ@v0.3.1" in release_notes_text
    assert "This install includes the local `qiskit-local` runtime dependencies by default. `classiq` remains optional." in release_notes_text
    assert "uv pip install -e '.[dev]'" in release_notes_text
    assert "## What To Try First" in release_notes_text
    assert 'qrun prompt "Build a 4-qubit GHZ circuit and measure all qubits." --json' in release_notes_text
    assert "qrun resolve --workspace .quantum --intent-file examples/intent-ghz.md --json" in release_notes_text
    assert "qrun init --workspace .quantum --json" in release_notes_text
    assert "qrun plan --workspace .quantum --intent-file examples/intent-ghz.md --json" in release_notes_text
    assert "qrun exec --workspace .quantum --intent-file examples/intent-ghz.md --jsonl" in release_notes_text
    assert "qrun baseline set --workspace .quantum --revision rev_000001 --json" in release_notes_text
    assert "qrun compare --workspace .quantum --baseline --fail-on subject_drift --json" in release_notes_text
    assert "qrun doctor --workspace .quantum --json --ci" in release_notes_text
    assert "qrun pack-inspect --pack-root .quantum/packs/rev_000001 --json" in release_notes_text
    assert "qrun pack-import --pack-root .quantum/packs/rev_000001 --workspace downstream/.quantum --json" in release_notes_text
    assert "JSONL event streams" in release_notes_text
    assert "shared decision signals" in release_notes_text

    assert product_strategy.exists()
    product_strategy_text = product_strategy.read_text()
    assert "decision-grade quantum workflow runtime" in product_strategy_text
    assert "workspace-native quantum workflow runtime" in product_strategy_text
    assert "AI-Native Quantum R&D Teams" in product_strategy_text
    assert "teams using AI agents plus CI to iterate on quantum prototypes" in product_strategy_text
    assert "notebooks" in product_strategy_text
    assert "Adoption Ladder" in product_strategy_text
    assert "it does not treat transpile metrics and synthesis metrics as equivalent by default" in product_strategy_text
    assert "benchmark honesty instead of benchmark theater" in product_strategy_text
    assert "If a feature mostly increases backend count, novelty, or demo value" in product_strategy_text

    assert roadmap.exists()
    roadmap_text = roadmap.read_text()
    assert "docs/product-strategy.md" in roadmap_text
    assert "workspace-native quantum workflow runtime" in roadmap_text
    assert "Priority 1: Complete The Import/Load Contract" in roadmap_text

    assert versioning.exists()
    versioning_text = versioning.read_text()
    assert "0.1.x" in versioning_text
    assert "0.2.x" in versioning_text
    assert "0.3.x" in versioning_text
    assert "Released line: `0.3.1`" in versioning_text
    assert "agent-observability surfaces" in versioning_text
    assert "## Stable Runtime Contracts" in versioning_text
    assert "CLI/result/artifact schema_version stays separate from QSpec.version." in versioning_text
    assert "QSpec.version" in versioning_text


def test_readme_and_release_notes_share_one_runtime_quickstart() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text()
    release_notes = (PROJECT_ROOT / "docs" / "releases" / "v0.3.1.md").read_text()

    readme_commands = [
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
    readme_indices = [readme.index(command) for command in readme_commands]

    assert readme_indices == sorted(readme_indices)
    assert (
        readme.index("qrun baseline set --workspace .quantum --revision rev_000001 --json")
        < readme.index("qrun compare --workspace .quantum --baseline --fail-on subject_drift --json")
        < readme.index("qrun doctor --workspace .quantum --json --ci")
    )
    assert readme.index("qrun pack-inspect --pack-root .quantum/packs/rev_000001 --json") < readme.index(
        "qrun pack-import --pack-root .quantum/packs/rev_000001 --workspace downstream/.quantum --json"
    )

    release_commands = readme_commands
    release_indices = [release_notes.index(command) for command in release_commands]

    assert release_indices == sorted(release_indices)
    assert (
        release_notes.index("qrun baseline set --workspace .quantum --revision rev_000001 --json")
        < release_notes.index("qrun compare --workspace .quantum --baseline --fail-on subject_drift --json")
        < release_notes.index("qrun doctor --workspace .quantum --json --ci")
    )
    assert release_notes.index("qrun pack-inspect --pack-root .quantum/packs/rev_000001 --json") < release_notes.index(
        "qrun pack-import --pack-root .quantum/packs/rev_000001 --workspace downstream/.quantum --json"
    )

    assert "docs/fluxq-qaoa-maxcut-case-study.md" in readme
    assert 'qrun prompt "Build a 4-qubit MaxCut QAOA ansatz with 2 layers on a ring graph" --json' not in release_notes
    assert "qrun doctor --workspace .quantum --jsonl --fix" not in release_notes


def test_release_notes_document_runtime_contract_stability() -> None:
    release_notes = (PROJECT_ROOT / "docs" / "releases" / "v0.3.1.md").read_text()

    assert "## Runtime Contract Stability" in release_notes
    assert "Stable runtime contracts:" in release_notes
    assert "Evolving runtime contracts:" in release_notes
    assert "Optional runtime contracts:" in release_notes
    assert "Safe consumption rule:" in release_notes
