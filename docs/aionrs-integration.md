# aionrs Integration

Use aionrs through files plus shell commands. Do not build a custom aionrs tool for Quantum Runtime CLI.

## Recommended workflow

1. Initialize the workspace once:

   ```bash
   qrun init --workspace .quantum --json
   ```

2. Let aionrs write the current request into `.quantum/intents/latest.md`.

3. Execute the runtime:

   ```bash
   qrun exec --workspace .quantum --intent-file .quantum/intents/latest.md --json
   ```

4. Read `.quantum/reports/latest.json` and inspect generated artifacts before editing emitted code.

5. Optionally run a lightweight post-tool benchmark hook:

   ```bash
   qrun bench --workspace .quantum --json
   ```

## Files

- `integrations/aionrs/CLAUDE.md.example`
- `integrations/aionrs/hooks.example.toml`

These examples avoid any aionrs core changes and rely only on `Read`, `Write`, `Bash`, `CLAUDE.md`, and optional hooks.
