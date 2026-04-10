from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_release_docs_cover_runnable_readme_and_release_assets() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text()
    architecture = PROJECT_ROOT / "ARCHITECTURE.md"
    changelog = PROJECT_ROOT / "CHANGELOG.md"
    release_notes = PROJECT_ROOT / "docs" / "releases" / "v0.2.4.md"
    product_strategy = PROJECT_ROOT / "docs" / "product-strategy.md"
    roadmap = PROJECT_ROOT / "docs" / "plans" / "2026-04-02-product-roadmap.md"
    versioning = PROJECT_ROOT / "docs" / "versioning.md"

    assert "# FluxQ" in readme
    assert "![Release]" in readme
    assert "![License]" in readme
    assert "![Python]" in readme
    assert "workspace-native quantum workflow runtime" in readme
    assert "coding agents and CI systems can trust" in readme
    assert "## Why FluxQ" in readme
    assert "replayable reports" in readme
    assert "semantic workload comparison" in readme
    assert "## Install" in readme
    assert "uv tool install git+https://github.com/xi-zhao/FluxQ@v0.2.4" in readme
    assert "This public install includes the local `qiskit-local` runtime stack. `classiq` remains optional." in readme
    assert "uv pip install -e '.[dev]'" in readme
    assert "## First Run" in readme
    assert "qrun init --workspace .quantum --json" in readme
    assert "qrun exec --workspace .quantum --intent-file examples/intent-ghz.md --json" in readme
    assert "qrun baseline set --workspace .quantum --revision rev_000001 --json" in readme
    assert "qrun inspect --workspace .quantum --json" in readme
    assert "qrun compare --workspace .quantum --baseline --json" in readme
    assert "qrun export --workspace .quantum --format qasm3 --json" in readme
    assert "qrun bench --workspace .quantum --json" in readme
    assert "qrun doctor --workspace .quantum --json --fix" in readme
    assert "## Trust And Replay" in readme
    assert "## Decision Loop" in readme
    assert "## Command Reference" in readme
    assert "qrun compare --workspace .quantum --left-revision rev_000001 --right-revision rev_000002 --expect same-subject --json" in readme
    assert "docs/product-strategy.md" in readme
    assert "docs/aionrs-integration.md" in readme
    assert "docs/plans/2026-04-02-product-roadmap.md" in readme
    assert "`source_kind`, `source_revision`, `source_report_path`, and `source_qspec_path`" in readme
    assert "`detached_report_inputs`" in readme
    assert "`replay_integrity`" in readme
    assert "workspace baselines persist approved report/QSpec states" in readme
    assert "`baseline` block" in readme
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
    assert "docs/releases/v0.2.4.md" in readme
    assert "CONTRIBUTING.md" in readme
    assert "SECURITY.md" in readme
    assert "SUPPORT.md" in readme

    assert architecture.exists()
    architecture_text = architecture.read_text()
    assert "Intent" in architecture_text
    assert "QSpec" in architecture_text
    assert "Lowering" in architecture_text
    assert "Diagnostics" in architecture_text

    assert changelog.exists()
    changelog_text = changelog.read_text()
    assert "Unreleased" in changelog_text
    assert "0.2.4" in changelog_text
    assert "decision-grade release" in changelog_text
    assert "emit replay provenance fields from `qrun export --json`" in changelog_text
    assert "surface `detached_report_inputs` in `qrun compare --json`" in changelog_text
    assert "surface `replay_integrity` in `qrun inspect --json`" in changelog_text
    assert "add replay-trust deltas and `--forbid-replay-integrity-regressions` to `qrun compare`" in changelog_text
    assert "add workspace baseline persistence with `qrun baseline set/show/clear`" in changelog_text
    assert "add `qrun compare --baseline`" in changelog_text
    assert "label benchmark entries as `structural_only`, `target_aware`, or `synthesis_backed`" in changelog_text
    assert "separate target-aware transpile provenance from Classiq synthesis-backed provenance" in changelog_text
    assert "treat missing optional backends as advisories unless the active workspace requests them" in changelog_text
    assert "bound parameterized expectation workflows to local evaluation" in changelog_text

    assert release_notes.exists()
    release_notes_text = release_notes.read_text()
    assert "# FluxQ v0.2.4" in release_notes_text
    assert "## Why This Release Matters" in release_notes_text
    assert "## Highlights" in release_notes_text
    assert "## Install" in release_notes_text
    assert "uv tool install git+https://github.com/xi-zhao/FluxQ@v0.2.4" in release_notes_text
    assert "This install includes the local `qiskit-local` runtime dependencies by default. `classiq` remains optional." in release_notes_text
    assert "uv pip install -e '.[dev]'" in release_notes_text
    assert "## What To Try First" in release_notes_text
    assert "qrun exec --workspace .quantum --intent-file examples/intent-ghz.md --json" in release_notes_text
    assert "qrun baseline set --workspace .quantum --revision rev_000001 --json" in release_notes_text
    assert "qrun compare --workspace .quantum --baseline --json" in release_notes_text
    assert "qrun bench --workspace .quantum --json" in release_notes_text
    assert "qrun doctor --workspace .quantum --json --fix" in release_notes_text
    assert "By default, `qrun bench` runs `qiskit-local` and only adds optional backends that the active QSpec explicitly requests." in release_notes_text
    assert "optional backends stay advisory until a workspace actually depends on them" in release_notes_text
    assert "parameter workflows are bounded local expectation evaluation, not a general optimizer" in release_notes_text

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
    assert "Released line: `0.2.4`" in versioning_text
    assert "baseline compare, target-aware benchmark honesty, and bounded local parameter evaluation" in versioning_text
    assert "QSpec.version" in versioning_text
