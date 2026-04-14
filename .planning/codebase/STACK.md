# Technology Stack

**Analysis Date:** 2026-04-14

## Languages

**Primary:**
- Python 3.11 - Main CLI/runtime package in `pyproject.toml`, `src/quantum_runtime/`, `tests/`, and `scripts/dev-bootstrap.sh`

**Secondary:**
- TOML/JSON/YAML/Markdown - Package config, machine-readable runtime contracts, and intent/workspace formats in `pyproject.toml`, `mypy.ini`, `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/workspace/manager.py`, `src/quantum_runtime/intent/markdown.py`, and `docs/`
- Rust edition 2024 - Adjacent agent sidecar crate in `aionrs/Cargo.toml` and `aionrs/src/`; root `.gitignore` ignores `/aionrs/`, and `pyproject.toml` packages only `src`, so the Rust tree is not part of the Python distribution

## Runtime

**Environment:**
- CPython 3.11 - Required by `pyproject.toml` (`requires-python = ">=3.11,<3.12"`), `mypy.ini`, `.github/workflows/ci.yml`, `.github/workflows/classiq.yml`, and `scripts/dev-bootstrap.sh`

**Package Manager:**
- `uv` - Standard developer workflow in `README.md`, `CONTRIBUTING.md`, and `uv.lock`; the repo does not pin a specific `uv` binary version
- `pip` - CI/bootstrap installer in `.github/workflows/ci.yml`, `.github/workflows/classiq.yml`, and `scripts/dev-bootstrap.sh`
- Lockfile: present in `uv.lock`

## Frameworks

**Core:**
- Typer 0.24.1 - CLI entrypoint and command tree in `src/quantum_runtime/cli.py`; declared in `pyproject.toml`, locked in `uv.lock`
- Pydantic 2.12.5 - Schema-versioned runtime payloads and models in `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/qspec/model.py`, and `src/quantum_runtime/workspace/manifest.py`
- Qiskit 2.3.1 - Circuit construction, transpilation, and OpenQASM export in `src/quantum_runtime/lowering/qiskit_emitter.py`, `src/quantum_runtime/diagnostics/transpile_validate.py`, and `src/quantum_runtime/lowering/qasm3_emitter.py`
- Qiskit Aer 0.17.2 - Local simulator in `src/quantum_runtime/diagnostics/simulate.py`
- Classiq 1.7.0 - Optional synthesis/export backend in `src/quantum_runtime/backends/classiq_backend.py` and `src/quantum_runtime/lowering/classiq_emitter.py`

**Testing:**
- pytest 9.0.2 - Test runner configured in `pyproject.toml` and executed in `.github/workflows/ci.yml` and `.github/workflows/classiq.yml`

**Build/Dev:**
- Ruff 0.15.8 - Lint gate configured in `pyproject.toml` and run in `.github/workflows/ci.yml`
- MyPy 1.20.0 - Static checking configured in `mypy.ini` and run in `.github/workflows/ci.yml`
- build 1.3.0 - Wheel/sdist builder invoked by `.github/workflows/ci.yml`
- setuptools `>=69` plus `wheel` - Build backend declared in `pyproject.toml`

## Key Dependencies

**Critical:**
- `typer` 0.24.1 - Exposes the `qrun` command surface in `src/quantum_runtime/cli.py`
- `pydantic` 2.12.5 - Keeps machine-readable outputs stable in `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/runtime/observability.py`, and `src/quantum_runtime/reporters/writer.py`
- `qiskit` 2.3.1 - Canonical lowering target for circuit generation and transpile validation in `src/quantum_runtime/lowering/qiskit_emitter.py` and `src/quantum_runtime/diagnostics/transpile_validate.py`
- `qiskit-aer` 0.17.2 - Local execution backend for `src/quantum_runtime/diagnostics/simulate.py`

**Infrastructure:**
- `pyyaml` 6.0.3 - YAML front matter parsing for markdown intents in `src/quantum_runtime/intent/markdown.py`
- `matplotlib` 3.10.8 - Diagram rendering in `src/quantum_runtime/diagnostics/diagrams.py`
- `classiq` 1.7.0 - Optional extra only; enabled through `.[classiq]` in `pyproject.toml` and `.github/workflows/classiq.yml`
- `build` 1.3.0 - Release artifact construction in `.github/workflows/ci.yml`
- `ruff` 0.15.8, `mypy` 1.20.0, and `pytest` 9.0.2 - Local and CI verification tooling from `pyproject.toml`, `mypy.ini`, and `.github/workflows/ci.yml`

## Configuration

**Environment:**
- Runtime configuration is workspace-file based, not env-driven: `qrun init` seeds `qrun.toml`, `workspace.json`, `events.jsonl`, and `trace/events.ndjson` via `src/quantum_runtime/workspace/manager.py` and `src/quantum_runtime/workspace/paths.py`
- No Python-runtime API key or secret env vars are read in `src/quantum_runtime/`; a focused scan found only bootstrap env vars in `scripts/dev-bootstrap.sh`
- Developer/bootstrap overrides are `PYTHON_BIN`, `PIP_TIMEOUT`, and `PIP_INDEX_URL` in `scripts/dev-bootstrap.sh`
- Optional provider auth in the adjacent sidecar lives in `aionrs/src/config.rs` and `aionrs/src/auth.rs`; it is not part of the `quantum-runtime` package loaded from `src/`

**Build:**
- Package metadata, dependency groups, pytest config, and Ruff config live in `pyproject.toml`
- Type-check configuration lives in `mypy.ini`
- CI/build automation lives in `.github/workflows/ci.yml` and `.github/workflows/classiq.yml`
- setuptools discovers only `src/` packages via `[tool.setuptools.packages.find]` in `pyproject.toml`
- Release artifacts are built into `dist/` by `python -m build` in `.github/workflows/ci.yml`; root `.gitignore` excludes `dist/`, `.venv/`, `.quantum/`, and `/aionrs/`

## Platform Requirements

**Development:**
- Python 3.11 with virtualenv support is required by `pyproject.toml` and `scripts/dev-bootstrap.sh`
- Local runtime validation expects the Qiskit stack from the base install or `.[qiskit]`, and the contributor gate uses `.[dev]` or `.[dev,qiskit]` per `CONTRIBUTING.md` and `.github/workflows/ci.yml`
- Optional Classiq work requires `.[classiq]` or `.[dev,classiq]` per `pyproject.toml` and `.github/workflows/classiq.yml`
- Rust/Cargo is only required when working inside the adjacent `aionrs/` crate in `aionrs/Cargo.toml`

**Production:**
- Deployment target is a local CLI package, not a long-running service; the entrypoint is `qrun = "quantum_runtime.cli:main"` in `pyproject.toml`
- Distribution model is wheel/sdist packaging built by `python -m build` and installable from GitHub refs or release artifacts as shown in `README.md`
- Runtime persistence target is the local workspace directory managed by `src/quantum_runtime/workspace/paths.py` and `src/quantum_runtime/workspace/manager.py`

---

*Stack analysis: 2026-04-14*
