from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_open_source_release_files_exist_and_match_apache_2() -> None:
    license_path = PROJECT_ROOT / "LICENSE"
    contributing_path = PROJECT_ROOT / "CONTRIBUTING.md"
    security_path = PROJECT_ROOT / "SECURITY.md"
    support_path = PROJECT_ROOT / "SUPPORT.md"

    assert license_path.exists()
    assert contributing_path.exists()
    assert security_path.exists()
    assert support_path.exists()

    license_text = license_path.read_text()
    assert "Apache License" in license_text
    assert "Version 2.0, January 2004" in license_text

    contributing_text = contributing_path.read_text()
    assert "Development Workflow" in contributing_text
    assert "uv run --python 3.11 --extra dev --extra qiskit pytest -q" in contributing_text

    security_text = security_path.read_text()
    assert "Reporting a Vulnerability" in security_text
    assert "do not post exploit details in a public issue" in security_text.lower()

    support_text = support_path.read_text()
    assert "Support Scope" in support_text
    assert "bug reports" in support_text.lower()
