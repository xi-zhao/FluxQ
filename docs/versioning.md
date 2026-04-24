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

## Stable Runtime Contracts

- QSpec.version remains explicit in serialized specs.
- CLI/result/artifact schema_version stays separate from QSpec.version.
- Workspace revision history remains append-only under .quantum/*/history/.
- Verified delivery handoff runs through qrun pack, qrun pack-inspect, and qrun pack-import.

## Evolving Runtime Contracts

- `reason_codes`, `next_actions`, `decision`, and `gate` are additive machine signals for agents and CI.
- CLI JSON responses can add fields, but should not rename or remove released fields.
- Release-line guidance can keep refining which control-plane surfaces are recommended first, as long as it does not redefine the stable runtime truth layers.
- Export profiles and machine-facing guidance may expand across the `0.3.x` line without changing the meaning of released stable fields.

## Optional Runtime Contracts

- The `classiq` extra remains capability-gated and optional to the base local runtime install.
- `docs/aionrs-integration.md` documents an optional host integration contract rather than a guaranteed base-runtime dependency.
- `integrations/aionrs/hooks.example.toml` is an optional example surface for host hooks and should be consumed only when that integration is enabled.
- Export profiles beyond the core local flow should be treated as optional capabilities that may differ by installed backend support.

## Safe Consumption Rules

- Depend directly on the stable surfaces above when you need released compatibility guarantees.
- Consume evolving JSON or observability fields additively: check for field presence and ignore unknown fields instead of assuming exhaustive schemas.
- Treat optional integrations and capability-specific examples as opt-in surfaces; gate them on installed extras, available docs, or explicit host configuration.
- Pin to a released line such as `0.3.1` when building automation, and review release notes before depending on newly added evolving or optional surfaces.
