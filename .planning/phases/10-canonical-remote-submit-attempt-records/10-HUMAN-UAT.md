---
status: partial
phase: 10-canonical-remote-submit-attempt-records
source: [10-VERIFICATION.md]
started: 2026-04-18T15:40:00Z
updated: 2026-04-18T15:40:00Z
---

## Current Test

Awaiting live IBM remote submit verification.

## Tests

### 1. Live Env-Token IBM Submit Smoke
expected: `qrun remote submit --workspace <path> --backend <backend> --intent-file examples/intent-ghz.md --json` returns `status=ok`, persists a durable remote attempt record under `.quantum/remote/...`, includes provider `job.id` plus explicit `backend.instance`, and leaves `reports/latest.json` / `manifests/latest.json` unchanged.
result: [pending]

### 2. Live IBM Submit JSONL Smoke
expected: `qrun remote submit --workspace <path> --backend <backend> --intent-file examples/intent-ghz.md --jsonl` emits `submit_started`, `submit_persisted`, and `submit_completed` with the same reason-code / decision vocabulary as JSON mode and no token / Authorization leakage.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps

None yet - awaiting human execution.
