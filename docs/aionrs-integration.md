# aionrs Integration

Use aionrs through files plus shell commands. Do not build a custom aionrs tool for Quantum Runtime CLI.

## Recommended workflow

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

5. Read `.quantum/reports/latest.json` and `.quantum/manifests/latest.json`, or call:

   ```bash
   qrun status --workspace .quantum --json
   qrun show --workspace .quantum --json
   ```

   Agents can also consume `health`, `reason_codes`, `next_actions`, and `decision` directly from these payloads instead of opening workspace files themselves.

6. Optionally run a lightweight post-tool health hook:

   ```bash
   qrun doctor --workspace .quantum
   ```

7. If you want a structural backend comparison, run:

   ```bash
   qrun bench --workspace .quantum --jsonl
   ```

## Files

- `integrations/aionrs/CLAUDE.md.example`
- `integrations/aionrs/hooks.example.toml`

These examples avoid any aionrs core changes and rely only on `Read`, `Write`, `Bash`, `CLAUDE.md`, and optional hooks.
