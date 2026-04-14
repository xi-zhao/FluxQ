# Versioning Notes

See also: `docs/plans/2026-04-02-product-roadmap.md` for the current product-level priority order and execution rationale.

## Runtime versions

Released line: `0.3.1`

- `0.1.x`
  Stabilize CLI JSON output, workspace layout, and baseline QSpec fields.

- `0.2.x`
  The released line now covers baseline compare, target-aware benchmark honesty, and bounded local parameter evaluation.
  `0.2.4` tightens the public install contract, makes default benchmark scope follow the active QSpec, and fails export provenance mismatches closed.
  The `0.2.x` line established the trusted local runtime loop.

- `0.3.x`
  `0.3.0` turned FluxQ into an explicit runtime control plane for agents: schema-versioned JSON payloads, immutable per-run manifests, and new `plan` / `status` / `show` / `schema` commands.
  `0.3.1` adds agent-observability surfaces plus the agent-first runtime surface: `prompt`, `resolve`, persisted `intent` / `plan` runtime objects, export profiles, `pack`, `events.jsonl`, `health`, `reason_codes`, `next_actions`, decision or gate blocks, and `--jsonl` event streams for long-running commands.
  Next `0.3.x` work should deepen policy gates and delivery packaging without changing the core runtime truth layers.

## Compatibility rules

- `QSpec.version` must remain explicit in serialized specs.
- CLI/result/artifact `schema_version` is separate from `QSpec.version`.
- CLI JSON responses can add fields, but should not rename or remove released fields.
- Workspace revision history should remain append-only for generated specs, plans, and reports.
