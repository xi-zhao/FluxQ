# Contributing

Quantum Runtime CLI is intended to be a stable runtime surface for coding agents and CI systems. Contributions should preserve determinism, machine-readable outputs, and revision-safe workspace behavior.

## Development Workflow

1. Work in an isolated branch or worktree.
2. Add or update tests before changing behavior.
3. Keep changes focused. Avoid mixing runtime behavior, release docs, and refactors without a reason.
4. Update release-facing docs when user-visible behavior changes.

## Local Verification

Run the full local gate before asking for review:

```bash
uv run --python 3.11 --extra dev ruff check src tests
uv run --python 3.11 --extra dev mypy src
uv run --python 3.11 --extra dev --extra qiskit pytest -q
```

If your change affects packaging or release behavior, also run:

```bash
uv run --python 3.11 --extra dev python -m build
```

## Contribution Guidelines

- Preserve CLI JSON compatibility. Additive fields are acceptable; renames and removals are not.
- Keep workspace history append-only.
- Do not weaken replay-integrity or compare guardrails without explicit release notes.
- Prefer small commits with a clear product or runtime boundary.

## Pull Request Checklist

- Tests added or updated for behavior changes
- Docs updated for release-facing changes
- No unrelated file churn
- Verification commands run successfully
