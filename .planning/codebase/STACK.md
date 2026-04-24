# Technology Stack

**Analysis Date:** 2026-04-18

## Languages

**Primary:**
- Python 3.11 - Main CLI/runtime package declared in `pyproject.toml`, implemented under `src/quantum_runtime/`, and exercised by `tests/`.

**Secondary:**
- TOML - Package/build config in `pyproject.toml`, type config in `mypy.ini`, workspace/runtime config in `src/quantum_runtime/workspace/manager.py` and `src/quantum_runtime/runtime/ibm_access.py`, and sidecar config in `aionrs/src/config.rs`.
- JSON / NDJSON - Machine-readable runtime contracts and event logs in `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/runtime/run_manifest.py`, `src/quantum_runtime/workspace/trace.py`, and the workspace layout documented in `README.md`.
- Markdown - User/agent ingress and integration docs in `src/quantum_runtime/intent/markdown.py`, `docs/aionrs-integration.md`, and `integrations/aionrs/CLAUDE.md.example`.
- OpenQASM 3 - Export surface emitted by `src/quantum_runtime/lowering/qasm3_emitter.py` and written by `src/quantum_runtime/runtime/export.py`.
- Rust edition 2024 - Adjacent `aionrs` CLI sidecar in `aionrs/Cargo.toml` and `aionrs/src/`; excluded from the Python package tree by `/.gitignore`.
- Bash and GitHub Actions YAML - Developer bootstrap in `scripts/dev-bootstrap.sh` and CI/release automation in `.github/workflows/ci.yml`, `.github/workflows/classiq.yml`, and `aionrs/.github/workflows/release.yml`.

## Runtime

**Environment:**
- CPython 3.11 - Enforced by `pyproject.toml` (`requires-python = ">=3.11,<3.12"`), `mypy.ini`, `.github/workflows/ci.yml`, and `scripts/dev-bootstrap.sh`.
- Local filesystem workspace runtime - `qrun` persists state under a workspace root via `src/quantum_runtime/workspace/manager.py` and `src/quantum_runtime/workspace/paths.py`; there is no long-running server entrypoint under `src/quantum_runtime/`.
- Rust toolchain / Cargo - Required only when building or releasing the adjacent `aionrs` sidecar described by `aionrs/Cargo.toml` and `aionrs/.github/workflows/release.yml`.

**Package Manager:**
- `uv` - Primary developer workflow in `README.md`, `CONTRIBUTING.md`, and `uv.lock`.
- `pip` - CI/bootstrap fallback in `.github/workflows/ci.yml` and `scripts/dev-bootstrap.sh`.
- `cargo` - Sidecar dependency/build manager in `aionrs/Cargo.toml`.
- Lockfile: present in `uv.lock`.

## Frameworks

**Core:**
- Typer `0.24.1` - CLI surface in `src/quantum_runtime/cli.py`; declared in `pyproject.toml`, locked in `uv.lock`.
- Pydantic `2.12.5` - Runtime/result schema layer across `src/quantum_runtime/runtime/`, `src/quantum_runtime/qspec/`, `src/quantum_runtime/reporters/`, and `src/quantum_runtime/diagnostics/`.
- Qiskit `2.3.1` - Circuit construction, transpilation, and OpenQASM export in `src/quantum_runtime/lowering/qiskit_emitter.py`, `src/quantum_runtime/diagnostics/transpile_validate.py`, and `src/quantum_runtime/lowering/qasm3_emitter.py`.
- Qiskit Aer `0.17.2` - Local simulation backend in `src/quantum_runtime/diagnostics/simulate.py`.
- Qiskit IBM Runtime `0.46.1` - Optional IBM readiness/discovery extra wired through `src/quantum_runtime/runtime/ibm_access.py`, `src/quantum_runtime/runtime/backend_list.py`, and `src/quantum_runtime/runtime/doctor.py`.
- Classiq `1.7.0` - Optional synthesis/export backend in `src/quantum_runtime/backends/classiq_backend.py` and `src/quantum_runtime/lowering/classiq_emitter.py`.
- Tokio, Reqwest, Clap, and Serde - Adjacent `aionrs` runtime stack in `aionrs/Cargo.toml`, `aionrs/src/main.rs`, and `aionrs/src/provider/`.

**Testing:**
- pytest `9.0.2` - Test runner configured in `pyproject.toml` and used throughout `tests/`.
- `wiremock`, `tokio-test`, `mockall`, and `tempfile` - Sidecar Rust test tooling in `aionrs/Cargo.toml`.

**Build/Dev:**
- `setuptools>=69` plus `wheel` - Python build backend in `pyproject.toml`.
- `build` `1.3.0` - Wheel/sdist builder invoked by `.github/workflows/ci.yml`.
- Ruff `0.15.8` - Lint gate from `pyproject.toml` and `.github/workflows/ci.yml`.
- MyPy `1.20.0` - Static checking configured in `mypy.ini` and run in `.github/workflows/ci.yml`.

## Key Dependencies

**Critical:**
- `qiskit` `2.3.1` - Canonical in-memory circuit generation and transpile-friendly circuit handling in `src/quantum_runtime/lowering/qiskit_emitter.py` and `src/quantum_runtime/diagnostics/transpile_validate.py`.
- `qiskit-aer` `0.17.2` - Local execution and exact-simulation path in `src/quantum_runtime/diagnostics/simulate.py` and emitted runnable programs from `src/quantum_runtime/lowering/qiskit_emitter.py`.
- `pydantic` `2.12.5` - Stable machine payloads in `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/runtime/resolve.py`, `src/quantum_runtime/runtime/executor.py`, and `src/quantum_runtime/runtime/run_manifest.py`.
- `typer` `0.24.1` - `qrun` command tree and JSON/text output control in `src/quantum_runtime/cli.py`.
- `qiskit-ibm-runtime` `0.46.1` - Optional IBM readiness inventory via `QiskitRuntimeService` loading in `src/quantum_runtime/runtime/ibm_access.py`; current backend capability matrix keeps `remote_submit` false in `src/quantum_runtime/runtime/backend_registry.py`.

**Infrastructure:**
- `pyyaml` `6.0.3` - Markdown front matter parsing in `src/quantum_runtime/intent/markdown.py`.
- `matplotlib` `3.10.8` - PNG circuit rendering in `src/quantum_runtime/diagnostics/diagrams.py`.
- `classiq` `1.7.0` - Optional Classiq synthesis and `classiq-python` export surface in `src/quantum_runtime/backends/classiq_backend.py` and `src/quantum_runtime/runtime/export.py`.
- `build` `1.3.0` - Release artifact generation in `.github/workflows/ci.yml` and `tests/test_packaging_release.py`.
- `reqwest`, `aws-sigv4`, `aws-config`, `jsonwebtoken`, and `url` - Sidecar transport/auth stack in `aionrs/Cargo.toml`, `aionrs/src/provider/bedrock.rs`, `aionrs/src/provider/vertex.rs`, and `aionrs/src/auth.rs`.

## Configuration

**Environment:**
- FluxQ runtime state is workspace-file based. `qrun init` seeds `qrun.toml`, `workspace.json`, `events.jsonl`, and `trace/events.ndjson` via `src/quantum_runtime/workspace/manager.py`; paths are centralized in `src/quantum_runtime/workspace/paths.py`.
- Base workspace defaults live in `DEFAULT_QRUN_TOML` inside `src/quantum_runtime/workspace/manager.py`, including `default_exports = ["qiskit", "qasm3"]` and `history_limit = 50`.
- Optional IBM access is configured in the workspace `qrun.toml` `[remote.ibm]` block, parsed and written by `src/quantum_runtime/runtime/ibm_access.py` and exposed through `qrun ibm configure` in `src/quantum_runtime/cli.py`.
- IBM secrets are intentionally external. The repo persists `token_env` or `saved_account_name`, but not the token value, per `src/quantum_runtime/runtime/ibm_access.py` and `tests/test_cli_ibm_config.py`.
- Developer bootstrap honors `PYTHON_BIN`, `PIP_TIMEOUT`, and `PIP_INDEX_URL` in `scripts/dev-bootstrap.sh`.
- No checked-in `.env`, `.env.*`, or `*.env` files were detected by repo scan from the project root.
- Adjacent `aionrs` resolves config from `~/.config/aionrs/config.toml` and project `.aionrs.toml` in `aionrs/src/config.rs`; OAuth credentials are stored in `~/.config/aionrs/auth.json` via `aionrs/src/auth.rs`.

**Build:**
- Python packaging/tool config lives in `pyproject.toml`.
- Type-check configuration lives in `mypy.ini`.
- Primary CI lives in `.github/workflows/ci.yml`; optional Classiq coverage lives in `.github/workflows/classiq.yml`.
- Sidecar release automation lives in `aionrs/.github/workflows/release.yml`.
- Distribution outputs are written to `dist/` and ignored in `/.gitignore`.

## Platform Requirements

**Development:**
- Python 3.11 with virtualenv support is required by `pyproject.toml` and `scripts/dev-bootstrap.sh`.
- The default local runtime install path expects the base dependencies plus dev tooling from `.[dev]`; CI/test paths use `.[dev,qiskit]` in `.github/workflows/ci.yml` and `scripts/dev-bootstrap.sh`.
- IBM readiness work requires the optional `.[ibm]` extra from `pyproject.toml` plus a configured workspace profile in `qrun.toml`; doctor checks only engage when `[remote.ibm]` is present, per `src/quantum_runtime/runtime/doctor.py`.
- Classiq work requires the optional `.[classiq]` extra and the dedicated workflow path in `.github/workflows/classiq.yml`.
- Rust/Cargo is required only for `aionrs/` development and release packaging.

**Production:**
- Primary deployment target is a local CLI/package with `qrun = "quantum_runtime.cli:main"` in `pyproject.toml`.
- Release artifacts are wheel/sdist packages built by `python -m build` in `.github/workflows/ci.yml` and validated by `tests/test_packaging_release.py`.
- Runtime persistence target is the local workspace directory managed by `src/quantum_runtime/workspace/paths.py`, not a database or hosted service.
- The adjacent `aionrs` sidecar is released as platform-specific binaries via `cargo build --release` in `aionrs/.github/workflows/release.yml`; it is not bundled into the Python distribution.

---

*Stack analysis: 2026-04-18*
