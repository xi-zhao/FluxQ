# External Integrations

**Analysis Date:** 2026-04-12

## APIs & External Services

**Quantum SDKs:**
- Qiskit - Local circuit generation, transpilation, simulation, and QASM export
  - SDK/Client: `qiskit` plus `qiskit-aer` from `pyproject.toml` and `uv.lock`
  - Auth: none; the code paths in `src/quantum_runtime/lowering/qiskit_emitter.py`, `src/quantum_runtime/diagnostics/simulate.py`, and `src/quantum_runtime/diagnostics/transpile_validate.py` run locally
- Classiq - Optional synthesis/export backend when a `QSpec` requests `classiq`
  - SDK/Client: `classiq` optional dependency from `pyproject.toml`; runtime entry points in `src/quantum_runtime/backends/classiq_backend.py` and `src/quantum_runtime/lowering/classiq_emitter.py`
  - Auth: not handled in the Python repo; `src/quantum_runtime/backends/classiq_backend.py` imports the installed SDK and delegates any authentication/session handling to that SDK

**Agent Host / Sidecar Integration:**
- aionrs file-based host integration - FluxQ documents shell/file orchestration for an external agent host in `docs/aionrs-integration.md` and sample files under `integrations/aionrs/`
  - SDK/Client: shell calls to `qrun`; no Python import dependency from `src/quantum_runtime/`
  - Auth: none in the FluxQ integration path; the sample hook in `integrations/aionrs/hooks.example.toml` runs a local shell command
- Bundled `aionrs/` sidecar - Separate Rust CLI present in the workspace and ignored by root `.gitignore`; it integrates with multiple remote AI providers and MCP servers from `aionrs/src/provider/` and `aionrs/src/mcp/`
  - SDK/Client: `reqwest`, `aws-sigv4`, `aws-config`, `aws-sdk-sts`, and provider modules in `aionrs/Cargo.toml`
  - Auth: provider/OAuth config in `aionrs/src/config.rs` and `aionrs/src/auth.rs`

## Data Storage

**Databases:**
- None detected in the main Python runtime; no ORM or database client imports appear in `src/quantum_runtime/`

**File Storage:**
- Local filesystem only
  - Workspace state is stored under `.quantum/`-style directories via `src/quantum_runtime/workspace/paths.py`
  - Generated artifacts land in `artifacts/qiskit/`, `artifacts/classiq/`, `artifacts/qasm/`, `figures/`, `reports/`, and `manifests/` from `src/quantum_runtime/workspace/paths.py`
  - Portable revision bundles are copied into `packs/<revision>/` by `src/quantum_runtime/runtime/pack.py`

**Caching:**
- Local workspace cache directory only
  - `src/quantum_runtime/workspace/paths.py` creates `cache/`
  - No Redis, Memcached, or remote cache client is detected in `src/quantum_runtime/`

## Authentication & Identity

**Auth Provider:**
- Main `qrun` runtime: Custom/local only
  - Implementation: no runtime login flow or API-key handling exists under `src/quantum_runtime/`; optional backend availability is checked by import inspection in `src/quantum_runtime/runtime/backend_registry.py`
- Adjacent `aionrs/` sidecar: Provider-specific auth plus Claude OAuth
  - Implementation: Claude device flow in `aionrs/src/auth.rs`; AWS Bedrock credential resolution in `aionrs/src/provider/mod.rs`; Vertex config in `aionrs/src/config.rs` and `aionrs/docs/providers.md`

## Monitoring & Observability

**Error Tracking:**
- None; no Sentry, OpenTelemetry, Datadog, or similar client is detected in `src/quantum_runtime/`

**Logs:**
- Structured local JSON/JSONL events
  - Agent-facing event envelopes are defined in `src/quantum_runtime/runtime/observability.py`
  - Workspace traces are appended to `events.jsonl` and `trace/events.ndjson` by `src/quantum_runtime/workspace/trace.py`
  - Health/dependency reports are written locally by `src/quantum_runtime/runtime/doctor.py`

## CI/CD & Deployment

**Hosting:**
- Not detected for the main runtime; this repo builds a distributable CLI package rather than a deployed web service

**CI Pipeline:**
- GitHub Actions
  - `.github/workflows/ci.yml` runs lint, type-checks, tests, and `python -m build`
  - `.github/workflows/classiq.yml` runs the optional Classiq-only test path with `.[dev,classiq]`

## Environment Configuration

**Required env vars:**
- Main runtime: none required by code under `src/quantum_runtime/`
- Optional developer/bootstrap vars: `PYTHON_BIN`, `PIP_TIMEOUT`, and `PIP_INDEX_URL` in `scripts/dev-bootstrap.sh`
- Optional `aionrs/` sidecar vars: `AWS_REGION` and `AWS_DEFAULT_REGION` in `aionrs/src/provider/mod.rs`; Bedrock docs in `aionrs/docs/providers.md` also reference `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_SESSION_TOKEN`

**Secrets location:**
- Main runtime: not detected; runtime state is file-based and local in `.quantum/` via `src/quantum_runtime/workspace/manager.py`
- `aionrs/` sidecar: config and tokens are stored outside the repo in `~/.config/aionrs/config.toml` and `~/.config/aionrs/auth.json`, as documented in `aionrs/README.md` and implemented in `aionrs/src/auth.rs`

## Webhooks & Callbacks

**Incoming:**
- None; no HTTP server, webhook receiver, or callback endpoint is implemented in `src/quantum_runtime/`

**Outgoing:**
- Main runtime: none required for default `qiskit-local` flows; all core execution paths are local
- Optional Classiq path: outbound behavior is delegated to the installed `classiq` SDK through `src/quantum_runtime/backends/classiq_backend.py`
- `aionrs/` sidecar: outbound HTTP requests exist for Claude OAuth in `aionrs/src/auth.rs`, LLM providers in `aionrs/src/provider/`, and configurable MCP SSE/streamable HTTP endpoints in `aionrs/src/mcp/manager.rs`

---

*Integration audit: 2026-04-12*
