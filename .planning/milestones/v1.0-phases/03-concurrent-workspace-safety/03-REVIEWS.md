---
phase: 03
reviewers: [gemini, claude]
reviewed_at: 2026-04-12T16:23:12Z
plans_reviewed:
  - 03-01-PLAN.md
  - 03-02-PLAN.md
  - 03-03-PLAN.md
  - 03-04-PLAN.md
---

# Cross-AI Plan Review — Phase 03

## Gemini Review

Reviewer invocation failed before a substantive review was produced.

- Status: failed
- Failure mode: missing local Gemini authentication configuration
- Raw output:

```text
Please set an Auth method in your /Users/xizhao/.gemini/settings.json or specify one of the following environment variables before running: GEMINI_API_KEY, GOOGLE_GENAI_USE_VERTEXAI, GOOGLE_GENAI_USE_GCA
```

---

## the agent Review

Here is the cross-AI review of the Phase 03 plans.

---

## Phase 03 Review: Concurrent Workspace Safety

### 1. Summary

Phase 03 adds a workspace-scoped file lease, atomic write helpers, structured error payloads, and guards across the full mutation surface (exec, compare, benchmark, doctor, baseline, export, pack). The four plans follow a clean layered sequence: primitive lock first, then the observable error contract, then exec integration, then the remaining writers. The plans are well-scoped, each building strictly on the previous wave's outputs, and the overall design is conservative and appropriate for a local filesystem-backed CLI.

### 2. Strengths

- Dependency ordering is correct and explicit. Each plan's `depends_on` field is set correctly, and the wave structure (1 -> 2 -> 3 -> 4) enforces that the lock primitive exists before the error contract, and both exist before any runtime integration.
- TDD discipline is maintained throughout. Every plan's Task 1 is a failing-test-first step, which means the contract is defined before implementation and the success criteria are machine-checkable.
- Scope is tightly controlled. Every plan explicitly lists what is out of scope (policy gates, bundle semantics, doc cleanup). This is the most common failure mode in phased plans and it is actively guarded against.
- Threat modeling is present at each layer. STRIDE entries are appropriate and not boilerplate-only: they name the specific component and disposition rather than just checking a box.
- Backward compatibility is explicitly preserved. Plans 03 and 04 both call out that alias filenames, history paths, and Phase 2 provenance contracts must not change. This protects downstream consumers.
- Machine-readable signals are first-class. Plan 02 correctly establishes `WorkspaceConflictError` and `WorkspaceRecoveryRequiredError` as concrete typed exceptions before wiring them into runtime paths, which means the CLI surface is defined in one place.

### 3. Concerns

- [HIGH] Lock starvation / no timeout or backoff contract
  The plans say the second writer fails fast, but they do not specify stale-lock recovery, timeout behavior, or whether lock files can become orphaned after process death.
- [HIGH] Lock scope during expensive compute
  Plan 03 says to keep expensive compute outside the guarded mutation section where possible, but does not make that an explicit invariant. If the lock is held across simulation, long jobs serialize all workspace writers.
- [MEDIUM] Stale lock detection is not specified
  Holder metadata exists, but there is no explicit rule for what happens when the recorded PID is dead.
- [MEDIUM] `events.jsonl` append atomicity
  JSONL append with fsync still allows truncated final lines if a process is killed mid-write, and the plans do not spell out reader behavior for that case.
- [MEDIUM] Pack partial-directory cleanup is ambiguous
  Plan 04 says partial pack roots should be cleaned or left clearly non-authoritative, which leaves implementation ambiguity.
- [MEDIUM] Doctor history omission is underspecified
  The interaction between "no history needed" and lock acquisition is implied but not made explicit.
- [LOW] `baseline clear` atomicity
  The plan implies `unlink`, but does not explicitly require it.
- [LOW] Cross-platform behavior for `os.replace`
  Not urgent for the current stack, but worth noting if Windows support ever matters.
- [LOW] No explicit lock release on exception paths
  The plan should explicitly require a context-manager or try/finally pattern for release safety.

### 4. Suggestions

1. Specify stale-lock detection explicitly in Plan 01 and tie it to `workspace_recovery_required`.
2. Bound lock scope precisely in Plan 03 so the lease is held only for commit/promotion, not compute.
3. Define a lock staleness TTL or equivalent operational recovery rule.
4. Harden JSONL readers against truncated final lines.
5. Clarify pack partial-directory policy: reject, clean, or stage-and-rename, but choose one.
6. Make lock acquisition a context-manager requirement in the plan text.
7. Add one integration test for a dead-PID stale lock.

### 5. Risk Assessment

Overall risk posture: Low-Medium.

- The phased dependency structure is sound.
- The main unresolved design risks are stale-lock recovery and exact lock scope during compute.
- Both issues look fixable by tightening the plan specification rather than redesigning the phase.

---

## Consensus Summary

Only one external reviewer returned substantive plan feedback in this run, so this section is a single-reviewer synthesis rather than true cross-reviewer consensus.

### Agreed Strengths

- The phase decomposition is strong: Plan 01 establishes primitives, Plan 02 defines the CLI contract, Plan 03 covers exec, and Plan 04 extends the same safety model to remaining writers.
- The plans are disciplined about scope and backward compatibility.
- TDD and threat-model coverage are both strong.

### Agreed Concerns

- The largest remaining planning ambiguity is stale-lock handling after crashes.
- The other high-value clarification is lock scope: the plan should explicitly state that compute stays outside the lease and only commit/promotion runs under lock.
- Event-log truncation and partial pack directory policy deserve tighter wording before future similar phases.

### Divergent Views

- None captured in this run because only one reviewer produced substantive feedback.
- Gemini did not return a review due to missing local authentication, and Codex was intentionally skipped for independence because this review was orchestrated from Codex.
