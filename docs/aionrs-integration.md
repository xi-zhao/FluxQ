# aionrs Integration

Use aionrs through files plus shell commands. Do not build a custom aionrs tool for Quantum Runtime CLI.

## Canonical host workflow

1. Initialize the workspace once:

   ```bash
   qrun init --workspace .quantum --json
   ```

2. Let aionrs write the current request into `.quantum/intents/latest.md`.

3. Ask FluxQ for a dry-run runtime plan:

   ```bash
   qrun plan --workspace .quantum --intent-file .quantum/intents/latest.md --json
   ```

4. Execute the runtime:

   ```bash
   qrun exec --workspace .quantum --intent-file .quantum/intents/latest.md --jsonl
   ```

5. Read the current selection:

   ```bash
   qrun status --workspace .quantum --json
   qrun show --workspace .quantum --json
   ```

6. Save an approved baseline, then enforce policy gates before continuing:

   ```bash
   qrun baseline set --workspace .quantum --revision rev_000001 --json
   qrun compare --workspace .quantum --baseline --fail-on subject_drift --json
   qrun doctor --workspace .quantum --json --ci
   ```

7. Produce a delivery bundle after compare and doctor pass:

   ```bash
   qrun pack --workspace .quantum --revision rev_000001 --json
   qrun pack-inspect --pack-root .quantum/packs/rev_000001 --json
   qrun pack-import --pack-root .quantum/packs/rev_000001 --workspace downstream/.quantum --json
   ```

8. If you want a structural backend comparison, run:

   ```bash
   qrun bench --workspace .quantum --json
   ```

This host workflow reuses the same runtime contract documented in [Runtime Adoption Workflow](./agent-ci-adoption.md). The point is to let aionrs drive FluxQ through files plus shell commands, not to invent a host-specific protocol.

## Machine-readable signals to consume

Agents should read `health`, `reason_codes`, `next_actions`, `decision`, and `gate` from `qrun status`, `qrun show`, `qrun compare`, `qrun doctor`, and `qrun pack-inspect` instead of guessing from prose or manually opening generated code.

- `reason_codes` tells the host why a gate passed, degraded, or failed.
- `next_actions` gives compact remediation hints such as rerunning execution, reviewing compare output, or fixing the environment.
- `gate` is the stop-or-continue contract for compare, doctor, and bundle inspection.

If compare or doctor returns a blocking gate, revise the intent and rerun FluxQ before creating or importing a delivery bundle.

## Files

- `integrations/aionrs/CLAUDE.md.example`
- `integrations/aionrs/hooks.example.toml`

These examples avoid any aionrs core changes and rely only on `Read`, `Write`, `Bash`, `CLAUDE.md`, and optional hooks.
