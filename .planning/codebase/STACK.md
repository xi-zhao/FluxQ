# Technology Stack

**Analysis Date:** 2026-04-12

## Languages

**Primary:**
- Python 3.11 - Main CLI/runtime package in `pyproject.toml`, `src/quantum_runtime/`, and `tests/`
- JSON/TOML/YAML/Markdown - Runtime contracts and workspace/config formats in `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/workspace/manager.py`, and `src/quantum_runtime/intent/markdown.py`

**Secondary:**
- Rust edition 2024 - Adjacent agent CLI sidecar in `aionrs/Cargo.toml` and `aionrs/src/`; root `.gitignore` excludes `/aionrs/`, so it is not part of the Python package build in `pyproject.toml`

## Runtime

**Environment:**
- CPython 3.11 - Required by `pyproject.toml` (`requires-python = ">=3.11,<3.12"`), `mypy.ini`, `.github/workflows/ci.yml`, and `scripts/dev-bootstrap.sh`

**Package Manager:**
- `uv` - Developer install/test flow in `README.md`, `CONTRIBUTING.md`, and `uv.lock`
- `pip` - CI/bootstrap install path in `.github/workflows/ci.yml` and `scripts/dev-bootstrap.sh`
- `cargo` - Only for the adjacent `aionrs/` crate in `aionrs/Cargo.toml`
- Lockfile: present in `uv.lock`

## Frameworks

**Core:**
- Typer `0.24.1` - CLI command surface in `src/quantum_runtime/cli.py`; declared in `pyproject.toml`, locked in `uv.lock`
- Pydantic `2.12.5` - Schema and result models across `src/quantum_runtime/runtime/`, `src/quantum_runtime/qspec/`, and `src/quantum_runtime/diagnostics/`
- Qiskit `2.3.1` - Circuit construction, transpilation, and OpenQASM export in `src/quantum_runtime/lowering/qiskit_emitter.py`, `src/quantum_runtime/diagnostics/transpile_validate.py`, and `src/quantum_runtime/lowering/qasm3_emitter.py`
- Qiskit Aer `0.17.2` - Local execution backend in `src/quantum_runtime/diagnostics/simulate.py`
- Classiq `1.7.0` - Optional synthesis/export backend in `src/quantum_runtime/backends/classiq_backend.py` and `src/quantum_runtime/lowering/classiq_emitter.py`

**Testing:**
- pytest `9.0.2` - Test runner configured in `pyproject.toml` and used throughout `tests/`

**Build/Dev:**
- setuptools `>=69` + `wheel` - Build backend in `pyproject.toml`
- build `1.3.0` - Release artifact builder used by `.github/workflows/ci.yml`
- Ruff `0.15.8` - Linting configured in `pyproject.toml`
- MyPy `1.20.0` - Static checking configured in `mypy.ini`

## Key Dependencies

**Critical:**
- `qiskit` `2.3.1` - In-memory circuit generation and backend-facing export logic in `src/quantum_runtime/lowering/qiskit_emitter.py`
- `qiskit-aer` `0.17.2` - Local simulator used by `src/quantum_runtime/diagnostics/simulate.py`
- `pydantic` `2.12.5` - Stable machine-readable payloads in `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/runtime/observability.py`, and `src/quantum_runtime/reporters/writer.py`
- `typer` `0.24.1` - User-facing `qrun` CLI in `src/quantum_runtime/cli.py`
- `pyyaml` `6.0.3` - YAML front matter parsing for markdown intents in `src/quantum_runtime/intent/markdown.py`
- `matplotlib` `3.10.8` - PNG circuit rendering in `src/quantum_runtime/diagnostics/diagrams.py`

**Infrastructure:**
- `pytest` `9.0.2` - Release and behavior checks in `tests/test_packaging_release.py`, `tests/test_open_source_release.py`, and the broader `tests/` suite
- `ruff` `0.15.8` - Lint gate in `.github/workflows/ci.yml`
- `mypy` `1.20.0` - Type gate in `.github/workflows/ci.yml` and `mypy.ini`
- `classiq` `1.7.0` - Optional extra only; enabled via `.[classiq]` in `.github/workflows/classiq.yml`

## Configuration

**Environment:**
- Runtime workspace config is file-based, not env-driven: `qrun init` creates `qrun.toml`, `workspace.json`, `events.jsonl`, and `trace/events.ndjson` via `src/quantum_runtime/workspace/manager.py` and `src/quantum_runtime/workspace/paths.py`
- Main Python runtime does not declare required runtime secrets or API-key env vars in `src/quantum_runtime/`
- Developer bootstrap honors `PYTHON_BIN`, `PIP_TIMEOUT`, and `PIP_INDEX_URL` in `scripts/dev-bootstrap.sh`
- Optional sidecar provider config lives outside the package in `aionrs/src/config.rs` and `aionrs/src/auth.rs`

**Build:**
- Package metadata and tool configuration live in `pyproject.toml`
- Type-check configuration lives in `mypy.ini`
- CI/build automation lives in `.github/workflows/ci.yml` and `.github/workflows/classiq.yml`
- Release artifacts are built into `dist/` and validated by `tests/test_packaging_release.py`

## Platform Requirements

**Development:**
- Python 3.11 with virtualenv support is required by `pyproject.toml` and `scripts/dev-bootstrap.sh`
- Local Qiskit workflows need base dependencies from `pyproject.toml`
- Classiq work needs the optional extra and dedicated workflow path from `.github/workflows/classiq.yml`
- Rust/Cargo is only required when working inside the adjacent `aionrs/` tree described by `aionrs/Cargo.toml`

**Production:**
- Deployment target is a local CLI/package, not a long-running service; entrypoint is `qrun = "quantum_runtime.cli:main"` in `pyproject.toml`
- Distribution model is wheel/sdist packaging built by `python -m build` in `.github/workflows/ci.yml` and stored in `dist/`
- Runtime persistence target is the local workspace directory managed by `src/quantum_runtime/workspace/paths.py`

---

*Stack analysis: 2026-04-12*
