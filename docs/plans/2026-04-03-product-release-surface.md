# Product Release Surface Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Raise Quantum Runtime CLI from “technically releasable” to “product-release ready” by shipping a real open-source release surface: product-quality README messaging, Apache-2.0 licensing, contribution/security/support docs, and package metadata suitable for public distribution.

**Architecture:** Keep runtime behavior stable and focus only on release-facing surfaces. Treat README, repository docs, and `pyproject.toml` as the public contract for adoption. Add tests that lock the legal and metadata boundaries so future releases cannot silently regress into an incomplete OSS package.

**Tech Stack:** Python 3.11, setuptools, pytest, Markdown docs

### Task 1: Lock the product README and OSS release contract with tests

**Files:**
- Modify: `tests/test_release_docs.py`
- Create: `tests/test_open_source_release.py`

**Step 1: Write the failing tests**

Add tests that prove:
- README opens with a product-grade value proposition instead of an internal engineering description
- `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, and `SUPPORT.md` exist
- the license is Apache-2.0
- release docs mention the support and contribution surfaces

**Step 2: Run tests to verify they fail**

Run:
`uv run --python 3.11 --extra dev pytest tests/test_release_docs.py tests/test_open_source_release.py -q`

Expected:
- `FAIL` because the project does not yet expose a complete OSS release surface.

**Step 3: Write minimal implementation**

Implement:
- product-grade README intro expectations
- existence checks for the OSS docs
- license checks for Apache-2.0

**Step 4: Run tests to verify they pass**

Run:
`uv run --python 3.11 --extra dev pytest tests/test_release_docs.py tests/test_open_source_release.py -q`

Expected:
- `PASS`

**Step 5: Commit**

```bash
git add tests/test_release_docs.py tests/test_open_source_release.py
git commit -m "test: lock product release surface"
```

### Task 2: Publish the OSS release documents

**Files:**
- Modify: `README.md`
- Create: `LICENSE`
- Create: `CONTRIBUTING.md`
- Create: `SECURITY.md`
- Create: `SUPPORT.md`

**Step 1: Rewrite the README opening**

Make the top section clearly answer:
- what the product is
- who it is for
- why it is different

**Step 2: Add OSS release docs**

Add:
- Apache-2.0 license text
- contributor workflow expectations
- security disclosure guidance
- support boundary and issue-routing guidance

**Step 3: Run doc tests**

Run:
`uv run --python 3.11 --extra dev pytest tests/test_release_docs.py tests/test_open_source_release.py -q`

Expected:
- `PASS`

**Step 4: Commit**

```bash
git add README.md LICENSE CONTRIBUTING.md SECURITY.md SUPPORT.md
git commit -m "docs: add open source release surface"
```

### Task 3: Publish package metadata for distribution

**Files:**
- Modify: `pyproject.toml`
- Modify: `tests/test_packaging_release.py`

**Step 1: Write the failing test**

Extend packaging tests to prove:
- package metadata declares Apache-2.0 licensing
- package metadata includes keywords/classifiers
- package metadata exposes public URLs for docs/issues/changelog

**Step 2: Run tests to verify they fail**

Run:
`uv run --python 3.11 --extra dev pytest tests/test_packaging_release.py -q`

Expected:
- `FAIL` because package metadata is still too thin for a public release.

**Step 3: Write minimal implementation**

Add to `pyproject.toml`:
- `license`
- `keywords`
- `classifiers`
- `project.urls`

**Step 4: Run tests to verify they pass**

Run:
`uv run --python 3.11 --extra dev pytest tests/test_packaging_release.py -q`

Expected:
- `PASS`

**Step 5: Commit**

```bash
git add pyproject.toml tests/test_packaging_release.py
git commit -m "build: add public package metadata"
```

### Task 4: Run the product release gate and capture the slice

**Files:**
- Modify: `README.md`
- Modify: `pyproject.toml`
- Modify: `tests/test_release_docs.py`
- Modify: `tests/test_packaging_release.py`
- Create: `LICENSE`
- Create: `CONTRIBUTING.md`
- Create: `SECURITY.md`
- Create: `SUPPORT.md`
- Create: `tests/test_open_source_release.py`
- Create: `docs/plans/2026-04-03-product-release-surface.md`

**Step 1: Run static checks**

Run:
`uv run --python 3.11 --extra dev ruff check src tests`

Expected:
- `All checks passed`

**Step 2: Run type checks**

Run:
`uv run --python 3.11 --extra dev mypy src`

Expected:
- `Success: no issues found`

**Step 3: Run the full test suite**

Run:
`uv run --python 3.11 --extra dev --extra qiskit pytest -q`

Expected:
- `PASS`

**Step 4: Rebuild release artifacts**

Run:
`uv run --python 3.11 --extra dev python -m build`

Expected:
- wheel and sdist still build cleanly with the new release metadata

**Step 5: Commit the release surface**

```bash
git add README.md pyproject.toml tests/test_release_docs.py tests/test_packaging_release.py LICENSE CONTRIBUTING.md SECURITY.md SUPPORT.md tests/test_open_source_release.py docs/plans/2026-04-03-product-release-surface.md
git commit -m "docs: prepare product release surface"
```
