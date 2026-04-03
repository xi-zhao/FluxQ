# Release Surface Polish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve FluxQ's public release surface so the README reads like a product homepage with a clearer adoption path and stronger launch positioning.

**Architecture:** Keep scope narrow: reshape README hierarchy, tighten the first-run experience, and align release assertions with the new messaging. Avoid feature changes or packaging changes beyond what the docs explicitly communicate.

**Tech Stack:** Markdown, pytest, release doc assertions

### Task 1: Lock the new homepage contract in tests

**Files:**
- Modify: `tests/test_release_docs.py`

**Step 1: Write the failing test**

Add assertions for a product-oriented README structure:
- launch-oriented opener
- install section with a GitHub-based install path
- value section explaining why FluxQ exists
- short first-run example

**Step 2: Run test to verify it fails**

Run: `uv run --python 3.11 --extra dev pytest tests/test_release_docs.py -q`

Expected: FAIL because the current README does not yet expose the new structure.

**Step 3: Commit**

Do not commit yet. Continue to Task 2.

### Task 2: Rewrite the README for public launch quality

**Files:**
- Modify: `README.md`

**Step 1: Write minimal implementation**

Restructure the top of the README so it includes:
- sharper product positioning
- a `Why FluxQ` section
- install instructions for users and contributors
- a short, credible first-run flow
- a compact trust/integration section

**Step 2: Run test to verify it passes**

Run: `uv run --python 3.11 --extra dev pytest tests/test_release_docs.py -q`

Expected: PASS

### Task 3: Tighten release voice and verify

**Files:**
- Modify: `CHANGELOG.md`
- Test: `tests/test_release_docs.py`

**Step 1: Adjust release phrasing**

Make `0.2.0` read like a product release, not an internal milestone list.

**Step 2: Run verification**

Run:
- `uv run --python 3.11 --extra dev pytest tests/test_release_docs.py tests/test_packaging_release.py tests/test_open_source_release.py -q`
- `uv run --python 3.11 --extra dev ruff check src tests`

Expected: PASS
