# Versioning Notes

See also: `docs/plans/2026-04-02-product-roadmap.md` for the current product-level priority order and execution rationale.

## Runtime versions

Released line: `0.2.3`

- `0.1.x`
  Stabilize CLI JSON output, workspace layout, and baseline QSpec fields.

- `0.2.x`
  The released line now covers baseline compare, target-aware benchmark honesty, and bounded local parameter evaluation.
  Next `0.2.x` work should deepen decision policies, tighten release-surface clarity, and keep optional-backend behavior explicit.

- `0.3.x`
  Consider optional remote hardware submission and richer backend benchmarking.

## Compatibility rules

- `QSpec.version` must remain explicit in serialized specs.
- CLI JSON responses can add fields, but should not rename or remove released fields.
- Workspace revision history should remain append-only for generated specs and reports.
