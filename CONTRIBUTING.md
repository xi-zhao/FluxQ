# Contributing

Quantum Runtime CLI is intended to be a stable runtime surface for coding agents and CI systems. Contributions should preserve determinism, machine-readable outputs, and revision-safe workspace behavior.

## Development Workflow

1. Work in an isolated branch or worktree.
2. Add or update tests before changing behavior.
3. Keep changes focused. Avoid mixing runtime behavior, release docs, and refactors without a reason.
4. Update release-facing docs when user-visible behavior changes.

## Local Verification

Run the full local smoke before asking for review:

```bash
uv run --python 3.11 --extra dev ruff check src tests
uv run --python 3.11 --extra dev mypy src
uv run --python 3.11 --extra dev --extra qiskit pytest -q
```

For the Phase 4 local workspace gate, use this exact repo-local sequence:

```bash
./.venv/bin/ruff check src tests
./.venv/bin/python -m mypy src
./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_cli_observability.py tests/test_runtime_policy.py -q --maxfail=1
```

Use this one-shot command to run the broader full local smoke after `.venv` is already installed:

```bash
./scripts/dev-bootstrap.sh verify
```

`./scripts/dev-bootstrap.sh verify` runs `qrun version`, Ruff, module-form MyPy, and full `pytest -q`. It is not the same as the exact Phase 4 local workspace gate above.

If you want one command that bootstraps `.venv` first and then runs the broader full local smoke, use:

```bash
./scripts/dev-bootstrap.sh all
```

For mainland China package mirrors:

```bash
./scripts/dev-bootstrap.sh all --mirror tsinghua
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
