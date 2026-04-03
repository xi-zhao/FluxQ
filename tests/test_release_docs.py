from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_release_docs_cover_runnable_readme_and_release_assets() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text()
    architecture = PROJECT_ROOT / "ARCHITECTURE.md"
    changelog = PROJECT_ROOT / "CHANGELOG.md"
    roadmap = PROJECT_ROOT / "docs" / "plans" / "2026-04-02-product-roadmap.md"
    versioning = PROJECT_ROOT / "docs" / "versioning.md"

    assert "workspace-native runtime for quantum workflows" in readme
    assert "coding agents and CI systems can trust" in readme
    assert "uv pip install -e '.[dev,qiskit]'" in readme
    assert "Current release: `0.2.0`" in readme
    assert "qrun init --workspace .quantum --json" in readme
    assert "qrun exec --workspace .quantum --intent-file examples/intent-ghz.md --json" in readme
    assert "qrun bench --workspace .quantum --json" in readme
    assert "qrun compare --workspace .quantum --left-revision rev_000001 --right-revision rev_000002 --expect same-subject --json" in readme
    assert "docs/aionrs-integration.md" in readme
    assert "docs/plans/2026-04-02-product-roadmap.md" in readme
    assert "`source_kind`, `source_revision`, `source_report_path`, and `source_qspec_path`" in readme
    assert "`detached_report_inputs`" in readme
    assert "`replay_integrity`" in readme
    assert "`replay_integrity_delta`" in readme
    assert "report-backed imports now enforce replay integrity for QSpec identity" in readme
    assert "qrun compare --forbid-replay-integrity-regressions --json" in readme
    assert "Detached copied reports still replay, but `qrun compare --json` degrades with exit code `2`" in readme
    assert "Apache-2.0" in readme
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
    assert "0.2.0" in changelog_text
    assert "agent-facing quantum workflow runtime" in changelog_text
    assert "emit replay provenance fields from `qrun export --json`" in changelog_text
    assert "surface `detached_report_inputs` in `qrun compare --json`" in changelog_text
    assert "surface `replay_integrity` in `qrun inspect --json`" in changelog_text
    assert "add replay-trust deltas and `--forbid-replay-integrity-regressions` to `qrun compare`" in changelog_text

    assert roadmap.exists()
    roadmap_text = roadmap.read_text()
    assert "workspace-native quantum workflow runtime" in roadmap_text
    assert "Priority 1: Complete The Import/Load Contract" in roadmap_text

    assert versioning.exists()
    versioning_text = versioning.read_text()
    assert "0.1.x" in versioning_text
    assert "0.2.x" in versioning_text
    assert "Released baseline: `0.2.0`" in versioning_text
    assert "QSpec.version" in versioning_text
