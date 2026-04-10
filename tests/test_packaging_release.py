from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_release_packaging_contract_is_documented_in_project_files() -> None:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text()
    ci_workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    gitignore = (PROJECT_ROOT / ".gitignore").read_text()

    assert 'version = "0.2.3"' in pyproject
    assert 'license = "Apache-2.0"' in pyproject
    assert 'license-files = ["LICENSE"]' in pyproject
    assert 'description = "Workspace-native quantum workflow runtime for coding agents and CI"' in pyproject
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
