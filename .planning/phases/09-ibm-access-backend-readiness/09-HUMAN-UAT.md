---
status: approved
phase: 09-ibm-access-backend-readiness
source: [09-VERIFICATION.md]
started: 2026-04-18T07:15:00+08:00
updated: 2026-04-18T07:20:00+08:00
---

## Current Test

Approved by user without executing live IBM Quantum Platform verification on 2026-04-18.

## Tests

### 1. Live env-token IBM smoke
expected: `qrun ibm configure --credential-mode env --token-env QISKIT_IBM_TOKEN --instance <crn> --workspace <path> --json` writes only non-secret references to `.quantum/qrun.toml`; `qrun backend list --json --workspace <path>` returns real IBM targets and readiness; `qrun doctor --json --ci --workspace <path>` returns `gate.ready=true` or an IBM-specific fail-closed reason if the instance or access is invalid.
result: skipped (approved by user without live execution)

### 2. Live saved-account IBM smoke
expected: `qrun ibm configure --credential-mode saved_account --saved-account-name <name> --instance <crn> --workspace <path> --json` resolves a real saved IBM account without persisting token material, and both `qrun doctor --json --ci --workspace <path>` and `qrun backend list --json --workspace <path>` preserve the same IBM reason-code / next-action / readiness contract.
result: skipped (approved by user without live execution)

## Summary

total: 2
passed: 0
issues: 0
pending: 2
pending: 0
skipped: 2
blocked: 0

## Gaps

Human IBM verification was explicitly approved by the user without live execution on 2026-04-18.
