# External Integrations

**Analysis Date:** 2026-04-14

## APIs & External Services

**Quantum SDKs and providers:**
- Qiskit local toolchain - Primary execution path for circuit building, transpilation, simulation, and QASM export in `src/quantum_runtime/lowering/qiskit_emitter.py`, `src/quantum_runtime/diagnostics/simulate.py`, and `src/quantum_runtime/diagnostics/transpile_validate.py`
  - SDK/Client: `qiskit`, `qiskit-aer`
  - Auth: None
- Classiq - Optional synthesis/export backend used only when requested by the active `QSpec` or export format in `src/quantum_runtime/runtime/executor.py` and `src/quantum_runtime/runtime/export.py`
  - SDK/Client: `classiq`
  - Auth: Not configured in-repo; the Python runtime only imports the SDK and calls `classiq.create_model()` and `classiq.synthesize()` in `src/quantum_runtime/backends/classiq_backend.py`, so endpoint and credential handling are SDK-managed

**Agent and host integration:**
- aionrs sidecar - File-and-shell integration documented in `docs/aionrs-integration.md` and sample host rules in `integrations/aionrs/CLAUDE.md.example`
  - SDK/Client: shell `qrun` invocations plus `.quantum/intents/latest.md`, `.quantum/reports/latest.json`, and `.quantum/manifests/latest.json`
  - Auth: None on the FluxQ side; if the adjacent `aionrs/` tool is used, its own provider auth is configured in `aionrs/src/config.rs` and `aionrs/src/auth.rs`

## Data Storage

**Databases:**
- None
  - Connection: Not applicable
  - Client: Not applicable

**File Storage:**
- Local filesystem only
  - Workspace state: `.quantum/workspace.json`, `.quantum/qrun.toml`, `.quantum/events.jsonl`, and `.quantum/trace/events.ndjson` via `src/quantum_runtime/workspace/manager.py` and `src/quantum_runtime/workspace/trace.py`
  - Revision history: `.quantum/specs/history/`, `.quantum/reports/history/`, `.quantum/manifests/history/`, and `.quantum/artifacts/history/` via `src/quantum_runtime/workspace/paths.py` and `src/quantum_runtime/reporters/writer.py`
  - Portable revision bundles: `.quantum/packs/<revision>/` via `src/quantum_runtime/runtime/pack.py`
  - Build artifacts: `dist/` via `.github/workflows/ci.yml`

**Caching:**
- Local cache directory only
  - Service: `.quantum/cache/` created by `src/quantum_runtime/workspace/paths.py`

## Authentication & Identity

**Auth Provider:**
- None in the Python CLI/runtime
  - Implementation: `src/quantum_runtime/` does not load runtime API keys or secrets from environment variables; workspace identity is local-only through `project_id` generation in `src/quantum_runtime/workspace/manifest.py`

## Monitoring & Observability

**Error Tracking:**
- None

**Logs:**
- Schema-versioned JSON payloads are emitted by `src/quantum_runtime/runtime/contracts.py`
- Workspace NDJSON event logs are appended by `src/quantum_runtime/workspace/trace.py`
- Revisioned reports and provenance payloads are written by `src/quantum_runtime/reporters/writer.py`
- CI logs come from GitHub Actions workflows in `.github/workflows/ci.yml` and `.github/workflows/classiq.yml`

## CI/CD & Deployment

**Hosting:**
- Local CLI/package delivery only; no deployed service target is defined in the repo

**CI Pipeline:**
- GitHub Actions
  - `.github/workflows/ci.yml` runs lint, type-check, Qiskit-focused pytest, and `python -m build`
  - `.github/workflows/classiq.yml` is a manual Classiq-only workflow using `.[dev,classiq]`
- No publish-to-PyPI or service deployment workflow is detected under `.github/workflows/`

## Environment Configuration

**Required env vars:**
- None for normal `qrun` runtime operation inside `src/quantum_runtime/`
- `PYTHON_BIN`, `PIP_TIMEOUT`, and `PIP_INDEX_URL` are optional bootstrap overrides in `scripts/dev-bootstrap.sh`
- If the adjacent `aionrs/` tool is used, provider secrets may come from CLI flags, config, or env such as `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` according to `aionrs/src/config.rs` and `aionrs/docs/getting-started.md`; that surface is separate from FluxQ's Python runtime

**Secrets location:**
- Not detected for the Python package; this refresh found no repo-local `.env` files, and `src/quantum_runtime/` does not read runtime secrets directly
- Optional sidecar/provider secrets live outside the Python package in user environment or sidecar config; Classiq credentials are not configured anywhere under `src/quantum_runtime/`

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None from the Python runtime
- The only callback-like example is a local shell hook in `integrations/aionrs/hooks.example.toml` that runs `qrun doctor`; it is not an HTTP webhook integration

---

*Integration audit: 2026-04-14*
