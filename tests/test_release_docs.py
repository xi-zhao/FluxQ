from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_release_docs_cover_runnable_readme_and_release_assets() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text()
    architecture = PROJECT_ROOT / "ARCHITECTURE.md"
    changelog = PROJECT_ROOT / "CHANGELOG.md"
    versioning = PROJECT_ROOT / "docs" / "versioning.md"

    assert "uv pip install -e '.[dev,qiskit]'" in readme
    assert "qrun init --workspace .quantum --json" in readme
    assert "qrun exec --workspace .quantum --intent-file examples/intent-ghz.md --json" in readme
    assert "qrun bench --workspace .quantum --json" in readme
    assert "docs/aionrs-integration.md" in readme

    assert architecture.exists()
    architecture_text = architecture.read_text()
    assert "Intent" in architecture_text
    assert "QSpec" in architecture_text
    assert "Lowering" in architecture_text
    assert "Diagnostics" in architecture_text

    assert changelog.exists()
    changelog_text = changelog.read_text()
    assert "Unreleased" in changelog_text
    assert "0.1.0" in changelog_text

    assert versioning.exists()
    versioning_text = versioning.read_text()
    assert "0.1.x" in versioning_text
    assert "0.2.x" in versioning_text
    assert "QSpec.version" in versioning_text
