---
phase: 10-canonical-remote-submit-attempt-records
plan: "03"
subsystem: runtime
tags: [python, typer, qiskit, ibm, remote-submit, observability, jsonl]
requires:
  - phase: 10-02
    provides: canonical remote submit orchestration and durable remote attempt persistence
provides:
  - stable remote-submit reason codes, remediations, and next-action mappings
  - fail-closed blocked-submit payloads with machine-readable gates
  - `submit_started` / `submit_persisted` / `submit_completed` JSONL lifecycle events
affects: [remote-submit, remote-lifecycle, observability, ibm, cli]
tech-stack:
  added: []
  patterns:
    - remote submit returns structured blocked results instead of generic CLI-only errors
    - remote submit JSON and JSONL share one reason-code and gate vocabulary from runtime helpers
    - submit lifecycle events are emitted from runtime orchestration so success and blocked paths stay in sync
key-files:
  created: []
  modified:
    - src/quantum_runtime/runtime/contracts.py
    - src/quantum_runtime/runtime/observability.py
    - src/quantum_runtime/runtime/remote_submit.py
    - src/quantum_runtime/cli.py
    - tests/test_cli_observability.py
key-decisions:
  - "Model blocked remote submit outcomes as structured control-plane payloads with gates instead of generic error envelopes."
  - "Emit `submit_*` lifecycle events from `submit_remote_input()` so JSON and JSONL observe the same success and fail-closed transitions."
  - "Redact provider authorization material before it reaches remote-submit machine payloads."
patterns-established:
  - "Remote-submit success uses a persisted-attempt reason code plus a decision block for later lifecycle work."
  - "Blocked remote-submit paths expose actionable `reason_codes`, `next_actions`, and `gate` fields rather than human summary strings."
requirements-completed: [REMT-01, REMT-02]
duration: 3min
completed: 2026-04-18
---

# Phase 10 Plan 03: Canonical Remote Submit Observability Summary

**Shared remote-submit reason codes, blocked-submit gates, and `submit_*` JSONL lifecycle events with IBM secret redaction**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-18T15:10:24Z
- **Completed:** 2026-04-18T15:13:06Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added stable remote-submit remediation codes and next-action mappings for backend selection, backend readiness, IBM access failures, provider submit failures, and attempt-store persistence failures.
- Reworked remote submit to return structured blocked payloads with `reason_codes`, `next_actions`, and `gate`, while successful submits now return a persisted-attempt decision block.
- Added JSONL lifecycle emission for `submit_started`, `submit_persisted`, and `submit_completed`, with parity to JSON mode and explicit regression coverage for secret redaction.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add stable remote-submit reason codes and next-action mappings** - `c7cb43d` (`test`), `3e9f4c2` (`feat`)
2. **Task 2: Emit remote-submit JSONL lifecycle events with parity to JSON mode** - `cef9822` (`test`), `120d6c0` (`feat`)

## Files Created/Modified

- `src/quantum_runtime/runtime/contracts.py` - adds remote-submit remediation vocabulary for backend readiness, provider submit failure, and attempt persistence failure.
- `src/quantum_runtime/runtime/observability.py` - maps remote-submit reason codes to executable next actions and routes `submit_*` events to the `remote` phase.
- `src/quantum_runtime/runtime/remote_submit.py` - returns structured blocked-submit payloads, emits submit lifecycle events, and redacts sensitive provider details.
- `src/quantum_runtime/cli.py` - wires `qrun remote submit --jsonl` through the runtime event stream and preserves exit-code parity across JSON and JSONL.
- `tests/test_cli_observability.py` - locks down remote-submit JSON and JSONL parity, decision/gate semantics, lifecycle events, and IBM secret redaction.

## Decisions Made

- Blocked remote-submit states now use structured control-plane payloads because agents and CI need gates and next actions, not only a top-level error string.
- The runtime orchestrator owns submit lifecycle emission so JSONL can reflect the same success and blocked outcomes that JSON mode returns.
- Remote-submit output keeps credential references like `token_env`, but strips raw token or authorization material before serialization.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required for this plan's mocked verification path.

## Next Phase Readiness

- Later remote lifecycle work can consume persisted-attempt decision metadata and `submit_*` JSONL events without parsing ad hoc prose.
- Blocked-submit states now expose one stable vocabulary for IBM access, backend readiness, provider failure, and local persistence failure.
- No blockers remain from this plan.

## Self-Check: PASSED

- Verified summary file exists at `.planning/phases/10-canonical-remote-submit-attempt-records/10-03-SUMMARY.md`.
- Verified task commits exist: `c7cb43d`, `3e9f4c2`, `cef9822`, `120d6c0`.
