from __future__ import annotations

import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_release_packaging_contract_is_documented_in_project_files() -> None:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text()
    ci_workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    gitignore = (PROJECT_ROOT / ".gitignore").read_text()

    assert 'version = "0.3.1"' in pyproject
    assert 'license = "Apache-2.0"' in pyproject
    assert 'license-files = ["LICENSE"]' in pyproject
    assert 'description = "Agent-first quantum runtime CLI with a runtime control plane for reproducible quantum runs"' in pyproject
    assert "keywords = [" in pyproject
    assert '"Topic :: Software Development :: Code Generators"' in pyproject
    assert "[project.urls]" in pyproject
    assert 'Homepage = "https://github.com/xi-zhao/FluxQ"' in pyproject
    assert 'Repository = "https://github.com/xi-zhao/FluxQ.git"' in pyproject
    assert 'Issues = "https://github.com/xi-zhao/FluxQ/issues"' in pyproject
    assert '"build>=' in pyproject
    assert "python -m build" in ci_workflow
    assert "dist/" in gitignore
    assert "build/" in gitignore


def test_release_packaging_includes_qiskit_runtime_dependencies_in_base_install() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())

    dependencies = pyproject["project"]["dependencies"]

    assert "qiskit" in dependencies
    assert "qiskit-aer" in dependencies
    assert "matplotlib>=3.8" in dependencies


def test_runtime_contract_stability_is_documented_in_versioning_and_packaging_metadata() -> None:
    versioning = (PROJECT_ROOT / "docs" / "versioning.md").read_text()
    changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text()
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text()

    assert "## Stable Runtime Contracts" in versioning
    assert "## Evolving Runtime Contracts" in versioning
    assert "## Optional Runtime Contracts" in versioning
    assert "## Safe Consumption Rules" in versioning
    assert "QSpec.version" in versioning
    assert "schema_version" in versioning
    assert "append-only" in versioning
    assert "pack-inspect" in versioning
    assert "pack-import" in versioning
    assert "reason_codes" in versioning
    assert "next_actions" in versioning
    assert "decision" in versioning
    assert "gate" in versioning
    assert "classiq" in versioning
    assert "aionrs" in versioning
    assert "hooks.example.toml" in versioning

    assert "clarify stable, evolving, and optional runtime contracts for adopters" in changelog
    assert "align packaging metadata with the runtime control plane positioning" in changelog

    assert "control-plane" in pyproject
    assert '"Topic :: Software Development :: Code Generators"' not in pyproject
