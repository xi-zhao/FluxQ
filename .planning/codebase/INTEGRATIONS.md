# External Integrations

**Analysis Date:** 2026-04-18

## APIs & External Services

**Quantum Provider Readiness:**
- IBM Quantum Platform - Optional readiness-only remote inventory surface. `qrun ibm configure` persists a non-secret workspace profile, `build_ibm_service()` instantiates `QiskitRuntimeService`, and `qrun backend list` projects target status from `service.backends()`; current capability registry marks `remote_submit = False` in `src/quantum_runtime/runtime/backend_registry.py`.
  - SDK/Client: `qiskit-ibm-runtime` from `pyproject.toml`; integration code in `src/quantum_runtime/runtime/ibm_access.py`, `src/quantum_runtime/runtime/backend_list.py`, and `src/quantum_runtime/runtime/doctor.py`
  - Auth: Workspace `qrun.toml` `[remote.ibm]` profile plus either `token_env` (typically `QISKIT_IBM_TOKEN`) or `saved_account_name`, validated in `src/quantum_runtime/runtime/ibm_access.py`
- Classiq - Optional synthesis/export backend for `classiq-python` emission and synthesis-backed metrics. FluxQ emits Python, optionally calls `classiq.create_model()` / `classiq.synthesize()`, and persists `artifacts/classiq/synthesis.json` via `src/quantum_runtime/backends/classiq_backend.py`.
  - SDK/Client: `classiq` from `pyproject.toml`; emit path in `src/quantum_runtime/lowering/classiq_emitter.py`
  - Auth: Not defined in repo config; authentication is delegated to the installed Classiq SDK environment

**Host Agent Integration:**
- aionrs host workflow - FluxQ ships host integration docs/examples rather than a custom sidecar plugin. The intended flow is documented in `docs/aionrs-integration.md` with example `CLAUDE.md` and hook files in `integrations/aionrs/`.
  - SDK/Client: Shell-driven host integration only; no dedicated Python SDK
  - Auth: Not applicable for FluxQ itself; host authentication lives in the adjacent `aionrs/` project

**Adjacent Sidecar Providers:**
- Anthropic - `aionrs` supports direct API-key auth and Claude.ai OAuth, with HTTP calls in `aionrs/src/provider/anthropic.rs` and device flow in `aionrs/src/auth.rs`.
  - SDK/Client: `reqwest` HTTP client in `aionrs/src/provider/anthropic.rs`
  - Auth: `API_KEY` / `ANTHROPIC_API_KEY` fallback in `aionrs/src/config.rs`, or OAuth credentials in `~/.config/aionrs/auth.json` via `aionrs/src/auth.rs`
- OpenAI-compatible APIs - `aionrs` supports OpenAI plus compatible bases such as DeepSeek or Ollama-style endpoints through configurable `base_url` and API path handling in `aionrs/src/provider/openai.rs` and `aionrs/src/provider/compat.rs`.
  - SDK/Client: `reqwest` in `aionrs/src/provider/openai.rs`
  - Auth: `API_KEY` / `OPENAI_API_KEY` or config file values in `aionrs/src/config.rs`
- AWS Bedrock - `aionrs` supports Claude-over-Bedrock with SigV4 signing and AWS credential resolution in `aionrs/src/provider/bedrock.rs`.
  - SDK/Client: `aws-sigv4`, `aws-config`, `aws-credential-types`, and `reqwest` from `aionrs/Cargo.toml`
  - Auth: Explicit config, `AWS_PROFILE`, or AWS env credential chain per `aionrs/docs/providers.md` and `aionrs/src/provider/bedrock.rs`
- Google Vertex AI - `aionrs` supports Claude-over-Vertex with service account, Application Default Credentials, or metadata server auth in `aionrs/src/provider/vertex.rs`.
  - SDK/Client: `reqwest` plus `jsonwebtoken` in `aionrs/src/provider/vertex.rs`
  - Auth: `credentials_file`, GCP ADC, metadata server, or env such as `GOOGLE_APPLICATION_CREDENTIALS`, `VERTEX_PROJECT_ID`, and `VERTEX_REGION` per `aionrs/docs/providers.md` and `aionrs/docs/json-stream-protocol.md`

**Tool Federation:**
- MCP servers - The adjacent `aionrs` sidecar can federate external tool servers over `stdio`, `sse`, and `streamable-http`, configured in `aionrs/src/mcp/config.rs` and documented in `aionrs/docs/mcp.md`.
  - SDK/Client: `aionrs/src/mcp/manager.rs`, `aionrs/src/mcp/tool_proxy.rs`, `aionrs/src/mcp/transport/stdio.rs`, `aionrs/src/mcp/transport/sse.rs`, and `aionrs/src/mcp/transport/streamable_http.rs`
  - Auth: Per-server `env` or `headers` blocks in the sidecar config, shown in `aionrs/docs/mcp.md`

## Data Storage

**Databases:**
- Not detected. The Python runtime does not include an ORM or database client under `src/quantum_runtime/`.

**File Storage:**
- Local filesystem only. FluxQ stores workspace state, manifests, specs, reports, artifacts, packs, and event logs under the workspace paths defined in `src/quantum_runtime/workspace/paths.py`.
- Classiq synthesis outputs are persisted as local files such as `artifacts/classiq/main.py` and `artifacts/classiq/synthesis.json` via `src/quantum_runtime/backends/classiq_backend.py`.
- The adjacent `aionrs` sidecar stores config and OAuth credentials under the local config directory paths built in `aionrs/src/config.rs` and `aionrs/src/auth.rs`.

**Caching:**
- No remote cache service is detected in FluxQ. The runtime has a local `cache/` workspace directory via `src/quantum_runtime/workspace/paths.py`.
- `aionrs` supports provider-side prompt caching behavior, but this is a request-mode feature rather than a separate cache service, per `aionrs/README.md` and provider implementations in `aionrs/src/provider/`.

## Authentication & Identity

**Auth Provider:**
- FluxQ main runtime uses IBM Quantum Platform credential references only. The workspace stores non-secret identity/config fields in `qrun.toml`, then resolves either an environment variable token or a Qiskit saved account name in `src/quantum_runtime/runtime/ibm_access.py`.
  - Implementation: `qrun ibm configure` in `src/quantum_runtime/cli.py` writes `[remote.ibm]`, `resolve_ibm_access()` validates it, and doctor/backend-list only evaluate IBM readiness when that block exists in `src/quantum_runtime/runtime/doctor.py`
- Classiq authentication is delegated to the installed SDK; this repo does not define secret storage or login flows for it in `src/quantum_runtime/`.
  - Implementation: Runtime import-and-call pattern in `src/quantum_runtime/backends/classiq_backend.py`
- The adjacent `aionrs` sidecar supports API-key, OAuth, AWS SigV4, and GCP OAuth2 identity modes in `aionrs/src/config.rs`, `aionrs/src/auth.rs`, `aionrs/src/provider/bedrock.rs`, and `aionrs/src/provider/vertex.rs`.
  - Implementation: Config merge in `aionrs/src/config.rs` plus provider-specific auth flows in `aionrs/src/provider/`

## Monitoring & Observability

**Error Tracking:**
- None detected. Neither FluxQ nor the adjacent `aionrs` sidecar is wired to a SaaS error-tracking service in the repository.

**Logs:**
- FluxQ emits schema-versioned JSON payloads and append-only workspace event streams at `events.jsonl` and `trace/events.ndjson`, implemented in `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/workspace/trace.py`, and `src/quantum_runtime/runtime/executor.py`.
- `qrun doctor`, `qrun compare`, `qrun bench`, `qrun exec`, `qrun status`, and `qrun show` expose `health`, `reason_codes`, `next_actions`, `decision`, or `gate` blocks described in `README.md`, `docs/versioning.md`, and runtime code under `src/quantum_runtime/runtime/`.
- The adjacent `aionrs` sidecar exposes a `--json-stream` host protocol in `aionrs/docs/json-stream-protocol.md` and `aionrs/src/output/protocol_sink.rs`.

## CI/CD & Deployment

**Hosting:**
- FluxQ ships as a local Python CLI package, not a hosted service, per `pyproject.toml` and `.github/workflows/ci.yml`.
- The adjacent `aionrs` sidecar ships as release binaries from `aionrs/.github/workflows/release.yml`.

**CI Pipeline:**
- GitHub Actions runs Python lint, MyPy, pytest, and package builds in `.github/workflows/ci.yml`.
- Optional Classiq-only coverage runs in `.github/workflows/classiq.yml`.
- The sidecar has its own Rust release workflow in `aionrs/.github/workflows/release.yml`.

## Environment Configuration

**Required env vars:**
- FluxQ runtime:
  - `QISKIT_IBM_TOKEN` or another env var name referenced by `[remote.ibm].token_env` when IBM credential mode is `env`, per `src/quantum_runtime/runtime/ibm_access.py` and `tests/test_cli_ibm_config.py`
  - `PYTHON_BIN`, `PIP_TIMEOUT`, and `PIP_INDEX_URL` are bootstrap-time variables for `scripts/dev-bootstrap.sh`
- Adjacent `aionrs` sidecar:
  - `API_KEY`, `ANTHROPIC_API_KEY`, and `OPENAI_API_KEY` fallback chain in `aionrs/src/config.rs`
  - `AWS_REGION`, `AWS_DEFAULT_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, and `AWS_PROFILE` for Bedrock flows in `aionrs/src/provider/mod.rs`, `aionrs/src/provider/bedrock.rs`, and `aionrs/docs/providers.md`
  - `GOOGLE_APPLICATION_CREDENTIALS`, `VERTEX_PROJECT_ID`, and `VERTEX_REGION` for Vertex flows in `aionrs/docs/json-stream-protocol.md` and `aionrs/src/provider/vertex.rs`
  - Per-MCP-server secrets can be passed in config `env` or `headers` blocks in `aionrs/src/mcp/config.rs` and `aionrs/docs/mcp.md`

**Secrets location:**
- FluxQ stores non-secret IBM profile references in the workspace `qrun.toml`; token values stay in environment variables or external Qiskit saved-account storage, per `src/quantum_runtime/runtime/ibm_access.py` and `tests/test_cli_ibm_config.py`.
- The adjacent `aionrs` sidecar stores config in `~/.config/aionrs/config.toml`, OAuth credentials in `~/.config/aionrs/auth.json`, and optional project overrides in `.aionrs.toml`, per `aionrs/src/config.rs` and `aionrs/src/auth.rs`.

## Webhooks & Callbacks

**Incoming:**
- None detected for the FluxQ Python runtime; it has no HTTP server or webhook endpoint under `src/quantum_runtime/`.
- The adjacent `aionrs` sidecar can connect to remote MCP servers over `sse` and `streamable-http`, but these are client transport modes, not webhook receiver endpoints, per `aionrs/src/mcp/config.rs` and `aionrs/docs/mcp.md`.

**Outgoing:**
- IBM readiness calls go through `QiskitRuntimeService` and `service.backends()` in `src/quantum_runtime/runtime/ibm_access.py` and `src/quantum_runtime/runtime/backend_list.py`.
- Classiq synthesis calls go through `classiq.create_model()` and `classiq.synthesize()` in `src/quantum_runtime/backends/classiq_backend.py`.
- The adjacent `aionrs` sidecar makes outbound HTTPS calls to Anthropic (`aionrs/src/provider/anthropic.rs`), OpenAI-compatible endpoints (`aionrs/src/provider/openai.rs`), AWS Bedrock (`aionrs/src/provider/bedrock.rs`), Google Vertex AI (`aionrs/src/provider/vertex.rs`), Claude.ai OAuth endpoints (`aionrs/src/auth.rs`), and configured MCP servers (`aionrs/src/mcp/transport/stdio.rs`, `aionrs/src/mcp/transport/sse.rs`, `aionrs/src/mcp/transport/streamable_http.rs`).

---

*Integration audit: 2026-04-18*
