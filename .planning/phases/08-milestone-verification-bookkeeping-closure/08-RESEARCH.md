# Phase 08: Milestone Verification And Bookkeeping Closure - Research

**Researched:** 2026-04-16 [VERIFIED: system date]
**Domain:** milestone closeout, phase-level verification evidence, planning-ledger consistency. [VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md]
**Confidence:** MEDIUM. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][VERIFIED: local test run][ASSUMED]

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| `RUNT-02` | Workspace writes are safe under concurrent agent or CI activity instead of assuming a single writer. [VERIFIED: .planning/REQUIREMENTS.md] | Phase 08 must re-run the current workspace-safety truth set, resolve the one live interrupted-commit regression if it is confirmed, and only then mint `03-VERIFICATION.md`; bookkeeping alone is not enough to close `RUNT-02`. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][VERIFIED: local test run][ASSUMED] |

</phase_requirements>

## Summary

Phase 08 is not a new feature phase; it is a closeout phase that has to make milestone evidence and milestone bookkeeping agree again. The active milestone audit already narrows the remaining work to three items: `RUNT-02` is still partial because Phase 03 has summaries but no `03-VERIFICATION.md`, `INT-02` is stale tracking because Phase 04 work exists on disk but `ROADMAP.md` still leaves that phase unchecked, and `FLOW-02` is broken because the milestone does not yet have one self-consistent proof-of-completion trail. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/STATE.md]

The most important new finding is that Phase 03 is no longer just “missing paperwork”. A current rerun of the Phase 03 workspace-safety probe fails at `tests/test_runtime_workspace_safety.py::test_interrupted_commit_keeps_previous_current_revision_authoritative`, which shows that an interrupted commit can still drift `reports/latest.json`; at the same time, the rest of the focused workspace-safety probe is green (`7 passed, 1 deselected`) when that single regression is excluded. Phase 08 therefore needs explicit room for fresh verification and possibly a minimal runtime repair before `03-VERIFICATION.md` can honestly say `passed`. [VERIFIED: tests/test_runtime_workspace_safety.py][VERIFIED: tests/test_cli_workspace_safety.py][VERIFIED: local test run]

Phase 04 points the other way. The exact repo-local Phase 4 gate from `CONTRIBUTING.md` currently passes with Ruff, module-form MyPy, and the targeted pytest suite (`67 passed in 11.15s`), so the `POLC-*` behaviors are not the remaining blocker. The unresolved problem is that `CONTRIBUTING.md` still says `./scripts/dev-bootstrap.sh verify` runs the same gate, while the script actually runs full `pytest -q`; the script still fails today on unrelated `test_cli_control_plane.py`, `test_cli_inspect.py`, and `test_report_writer.py` failures plus the same Phase 03 interrupted-commit regression. That makes Phase 04 a gate-definition/bookkeeping issue, not a missing-policy-implementation issue. [VERIFIED: CONTRIBUTING.md][VERIFIED: scripts/dev-bootstrap.sh][VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md][VERIFIED: local test run]

**Primary recommendation:** split Phase 08 into three plans: `08-01` re-establishes truthful `RUNT-02` verification and mints `03-VERIFICATION.md`, `08-02` reconciles the canonical Phase 04 gate plus its verification/bookkeeping artifacts, and `08-03` closes the milestone proof by updating `ROADMAP.md`, `STATE.md`, and `REQUIREMENTS.md` together, with `PROJECT.md` and `v1.0-MILESTONE-AUDIT.md` refreshed if the archive workflow expects them. [ASSUMED]

## Standard Stack

Phase 08 should stay entirely on the existing repo-local Python verification and planning-doc stack; no new dependency is justified for this work. [VERIFIED: AGENTS.md][VERIFIED: .planning/ROADMAP.md][VERIFIED: local test run]

### Core

| Library / Tool | Version | Purpose | Why Standard |
|---------------|---------|---------|--------------|
| `.venv/bin/python` | `3.11.15`. [VERIFIED: local test run] | Canonical interpreter for all Phase 08 probes, doc scripts, and verification reruns. [VERIFIED: local test run] | The project is standardized on Python 3.11, while the system `python3` is `3.13.2` and should not be treated as repo truth. [VERIFIED: AGENTS.md][VERIFIED: local test run] |
| `pytest` | `9.0.2`. [VERIFIED: local test run] | Re-run the exact Phase 03 and Phase 04 regression sets that already encode workspace safety and policy-gate behavior. [VERIFIED: tests/test_runtime_workspace_safety.py][VERIFIED: tests/test_cli_workspace_safety.py][VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_cli_bench.py][VERIFIED: tests/test_cli_doctor.py][VERIFIED: tests/test_cli_runtime_gap.py] | Existing tests already describe the intended closeout behaviors; Phase 08 should reuse them instead of inventing new acceptance logic. [VERIFIED: local test run][ASSUMED] |
| `ruff` | `0.15.8`. [VERIFIED: local test run] | Lint portion of the exact Phase 04 gate and Phase 08 combined closeout gate. [VERIFIED: CONTRIBUTING.md][VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VALIDATION.md] | Phase verification already treats Ruff as part of the repo-local validation contract. [VERIFIED: CONTRIBUTING.md][VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VALIDATION.md] |
| `mypy` via `python -m mypy` | `1.20.0`. [VERIFIED: local test run] | Type portion of the exact Phase 04 gate and Phase 08 combined closeout gate. [VERIFIED: CONTRIBUTING.md][VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VALIDATION.md] | Module-form MyPy works in this workspace while the direct launcher is broken; Phase 08 should standardize on the working invocation. [VERIFIED: local test run] |
| Planning ledgers: `ROADMAP.md`, `STATE.md`, `REQUIREMENTS.md` | repo docs. [VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/STATE.md][VERIFIED: .planning/REQUIREMENTS.md] | Canonical status, traceability, and current-position sources for milestone closeout. [VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/STATE.md][VERIFIED: .planning/REQUIREMENTS.md] | `INT-02` and `FLOW-02` are specifically about these files being out of sync with executed work. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md] |

### Supporting

| Library / Tool | Version | Purpose | When to Use |
|---------------|---------|---------|-------------|
| `scripts/dev-bootstrap.sh` | repo script. [VERIFIED: scripts/dev-bootstrap.sh] | Full-repo convenience runner for `qrun version`, Ruff, module-form MyPy, and full `pytest -q`. [VERIFIED: scripts/dev-bootstrap.sh] | Use only as a repo-wide smoke command or after its semantics are intentionally aligned with docs; do not treat it as the exact Phase 04 gate today. [VERIFIED: CONTRIBUTING.md][VERIFIED: scripts/dev-bootstrap.sh][VERIFIED: local test run] |
| `03-VERIFICATION.md` and `04-VERIFICATION.md` | phase artifacts. [VERIFIED: directory listing][VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md] | Phase-level proof documents that close `RUNT-02` and Phase 04 bookkeeping. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md] | Use them as the direct sources of truth for milestone closure; `03-VERIFICATION.md` does not exist yet and `04-VERIFICATION.md` is still `gaps_found`. [VERIFIED: directory listing][VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md] |
| `v1.0-MILESTONE-AUDIT.md` | milestone audit doc. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md] | Gap inventory and before/after proof for `RUNT-02`, `INT-02`, and `FLOW-02`. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md] | Use when writing the final proof-of-completion closeout or deciding whether to refresh the audit to `passed`. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][ASSUMED] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Exact targeted Phase 03 / Phase 04 commands. [VERIFIED: CONTRIBUTING.md][VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VALIDATION.md] | `./scripts/dev-bootstrap.sh verify`. [VERIFIED: scripts/dev-bootstrap.sh] | The script currently runs unrelated full-suite tests and fails outside the owned closeout scope, so it obscures whether Phase 04 itself is green. [VERIFIED: local test run] |
| Re-verifying Phase 03 before writing `03-VERIFICATION.md`. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][VERIFIED: local test run] | Treat the four Phase 03 summaries as sufficient proof. [VERIFIED: directory listing] | Summaries only prove what passed at execution time; they do not detect the current interrupted-commit regression. [VERIFIED: local test run] |
| Updating `ROADMAP.md`, `STATE.md`, and `REQUIREMENTS.md` together. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md] | Updating just the roadmap checkbox. [ASSUMED] | Single-file bookkeeping keeps `INT-02` and `FLOW-02` alive because the ledgers continue to disagree. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/STATE.md][VERIFIED: .planning/REQUIREMENTS.md] |

**Installation:** no new dependency is needed; reuse the repo’s current development environment. [VERIFIED: AGENTS.md][VERIFIED: local test run]

```bash
uv sync --extra dev --extra qiskit
```

**Version verification:** `./.venv/bin/python --version`, `uv --version`, `./.venv/bin/python -m pytest --version`, `./.venv/bin/ruff --version`, and `./.venv/bin/python -m mypy --version` all work locally, while `./.venv/bin/mypy --version` fails because its shebang points at a stale path with `Nutstore Files`. [VERIFIED: local test run]

## Architecture Patterns

### Recommended Project Structure

```text
.planning/
├── phases/
│   ├── 03-concurrent-workspace-safety/
│   │   └── 03-VERIFICATION.md        # Phase 08 must create this after truthful rerun
│   ├── 04-policy-acceptance-gates/
│   │   └── 04-VERIFICATION.md        # Phase 08 should refresh this from gaps_found -> passed if justified
│   └── 08-milestone-verification-bookkeeping-closure/
│       ├── 08-RESEARCH.md
│       ├── 08-VALIDATION.md
│       └── 08-VERIFICATION.md
├── ROADMAP.md
├── REQUIREMENTS.md
├── STATE.md
└── v1.0-MILESTONE-AUDIT.md
CONTRIBUTING.md
scripts/dev-bootstrap.sh
```

This structure keeps Phase 08 as the coordinator phase while still writing the missing proof back to the owning phase directories. [VERIFIED: .planning/ROADMAP.md][VERIFIED: directory listing][ASSUMED]

### Recommended Plan Split

1. **`08-01` — Re-verify `RUNT-02` and decide whether a minimal repair is required.** This plan should own the current Phase 03 truth set, rerun the workspace-safety regressions, investigate the interrupted-commit failure, and only mint `03-VERIFICATION.md` once the result is truthful. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][VERIFIED: local test run][ASSUMED]
2. **`08-02` — Reconcile the canonical Phase 04 gate and its verification/bookkeeping artifacts.** This plan should treat the exact targeted gate as canonical, decide whether to update `CONTRIBUTING.md`, `scripts/dev-bootstrap.sh`, or both, and then refresh `04-VERIFICATION.md` so it no longer stays at `gaps_found` for bookkeeping reasons alone. [VERIFIED: CONTRIBUTING.md][VERIFIED: scripts/dev-bootstrap.sh][VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md][VERIFIED: local test run][ASSUMED]
3. **`08-03` — Close milestone proof-of-completion and synchronize ledgers.** This plan should update `ROADMAP.md`, `STATE.md`, and `REQUIREMENTS.md` atomically, and refresh `v1.0-MILESTONE-AUDIT.md` plus `PROJECT.md` if the archive workflow expects one final passed/complete snapshot. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/STATE.md][VERIFIED: .planning/REQUIREMENTS.md][VERIFIED: .planning/PROJECT.md][ASSUMED]

### Pattern 1: Evidence First, Bookkeeping Second

**What:** Never flip roadmap or state ledgers until the current targeted verification runs are green and the relevant `*-VERIFICATION.md` file has been regenerated or refreshed. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][VERIFIED: local test run]

**When to use:** Phase closeout, milestone archive preparation, and any gap-closure phase that claims to repair planning drift. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][ASSUMED]

**Example:**

```bash
./.venv/bin/python -m pytest tests/test_cli_workspace_safety.py tests/test_runtime_workspace_safety.py -q --maxfail=1
./.venv/bin/ruff check src tests
./.venv/bin/python -m mypy src
./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_cli_observability.py tests/test_runtime_policy.py -q --maxfail=1
```

These commands are the right ordering because they establish whether Phase 03 and Phase 04 are currently true before any ledger is edited. [VERIFIED: CONTRIBUTING.md][VERIFIED: local test run][ASSUMED]

### Pattern 2: Separate Phase-Owned Gates from Repo-Wide Smoke

**What:** Keep the exact targeted phase gate separate from convenience scripts that execute the whole repository test suite. [VERIFIED: CONTRIBUTING.md][VERIFIED: scripts/dev-bootstrap.sh]

**When to use:** Any time a phase verification file or roadmap checkbox is meant to answer “is this phase done?” rather than “is the entire repo healthy today?”. [VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md][ASSUMED]

**Example:**

```bash
# Canonical Phase 04 gate
./.venv/bin/ruff check src tests
./.venv/bin/python -m mypy src
./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_cli_observability.py tests/test_runtime_policy.py -q --maxfail=1

# Repo-wide smoke, not the same thing
./scripts/dev-bootstrap.sh verify
```

The first command set currently passes while the second still fails on unrelated suites plus one overlapping Phase 03 regression. [VERIFIED: local test run]

### Pattern 3: Ledger Sync Must Be Atomic

**What:** Treat `ROADMAP.md`, `STATE.md`, and `REQUIREMENTS.md` as one bookkeeping unit for milestone closeout. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md]

**When to use:** The final plan in Phase 08 and any later milestone archival step. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][ASSUMED]

**Example:**

```bash
rg -n "Phase 4|Phase 8|RUNT-02|POLC-01" .planning/ROADMAP.md .planning/STATE.md .planning/REQUIREMENTS.md
```

The closeout is only credible when those three ledgers describe the same owner, status, and current project position. [VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/STATE.md][VERIFIED: .planning/REQUIREMENTS.md][ASSUMED]

### Documentation / Bookkeeping vs New Verification Work

| Item | Documentation / bookkeeping only? | Why |
|------|-----------------------------------|-----|
| Marking Phase 04 complete in `ROADMAP.md` | Yes, after the exact Phase 04 gate is rerun and `04-VERIFICATION.md` is refreshed. [VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md][VERIFIED: local test run] | The current blocker is stale bookkeeping, not a failing `POLC-*` gate. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][VERIFIED: local test run] |
| Updating `STATE.md` current focus, blockers, and progress | Yes. [VERIFIED: .planning/STATE.md] | `STATE.md` explicitly still lists the Phase 3 verification gap and Phase 4 bookkeeping drift as open blockers. [VERIFIED: .planning/STATE.md] |
| Updating `CONTRIBUTING.md` wording about `./scripts/dev-bootstrap.sh verify` | Yes, if docs are chosen as the source of truth. [VERIFIED: CONTRIBUTING.md][VERIFIED: scripts/dev-bootstrap.sh] | The mismatch is textual/contractual: the script does not run the same gate that the docs claim. [VERIFIED: CONTRIBUTING.md][VERIFIED: scripts/dev-bootstrap.sh] |
| Changing `scripts/dev-bootstrap.sh` so it becomes the canonical Phase 04 one-shot gate | Optional code/tooling work, not required if docs are instead corrected to describe it as a full-suite smoke command. [VERIFIED: CONTRIBUTING.md][VERIFIED: scripts/dev-bootstrap.sh][ASSUMED] | This is a product/tooling choice, not a missing policy implementation. [VERIFIED: local test run][ASSUMED] |
| Creating `03-VERIFICATION.md` | No. [VERIFIED: directory listing] | A live workspace-safety regression still exists, so Phase 03 needs fresh verification evidence and possibly a minimal repair before a truthful `passed` file can be written. [VERIFIED: local test run] |
| Closing `FLOW-02` milestone-proof-of-completion | No. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md] | The milestone proof depends on regenerated verification truth plus synchronized ledgers, not on narrative bookkeeping alone. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][ASSUMED] |

### Anti-Patterns to Avoid

- **Summary-as-proof:** Do not treat the four Phase 03 summaries as enough to close `RUNT-02`; the current interrupted-commit regression would stay invisible. [VERIFIED: directory listing][VERIFIED: local test run]
- **One-shot-script absolutism:** Do not let `./scripts/dev-bootstrap.sh verify` define Phase 04 completion while it still runs unrelated full-suite tests. [VERIFIED: CONTRIBUTING.md][VERIFIED: scripts/dev-bootstrap.sh][VERIFIED: local test run]
- **Ledger-first closeout:** Do not update `ROADMAP.md` before refreshing `03-VERIFICATION.md` and `04-VERIFICATION.md`; that recreates `FLOW-02` in a new form. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][ASSUMED]
- **Single-file bookkeeping fixes:** Do not update only one of `ROADMAP.md`, `STATE.md`, or `REQUIREMENTS.md`; the current audit already proves that inconsistent ledgers are themselves a blocker. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Phase-closeout verification commands. [VERIFIED: tests/test_runtime_workspace_safety.py][VERIFIED: tests/test_cli_workspace_safety.py][VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_cli_bench.py][VERIFIED: tests/test_cli_doctor.py][VERIFIED: tests/test_cli_runtime_gap.py] | New ad hoc smoke scripts for Phase 08. [ASSUMED] | Reuse the existing targeted pytest files and the exact Phase 04 gate already documented in `CONTRIBUTING.md`. [VERIFIED: CONTRIBUTING.md][VERIFIED: local test run] | The existing suites already encode the behavior that matters; new one-off commands would drift immediately. [VERIFIED: local test run][ASSUMED] |
| Milestone status narrative. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md] | A hand-written “everything is done now” summary detached from artifacts. [ASSUMED] | Use `03-VERIFICATION.md`, `04-VERIFICATION.md`, `08-VERIFICATION.md`, and the ledgers as the proof chain. [VERIFIED: directory listing][VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][ASSUMED] | `FLOW-02` is specifically about missing proof, not missing prose. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md] |
| Requirement ownership conventions. [VERIFIED: .planning/REQUIREMENTS.md] | Inconsistent per-file status edits. [ASSUMED] | Pick one traceability rule and apply it across roadmap, requirements, and state in one pass. [VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/REQUIREMENTS.md][VERIFIED: .planning/STATE.md][ASSUMED] | Phase 07 already shows that a gap-closure phase can become the terminal requirement owner (`POLC-01 -> Phase 07`). [VERIFIED: .planning/REQUIREMENTS.md] |
| Phase 04 one-shot gate semantics. [VERIFIED: CONTRIBUTING.md][VERIFIED: scripts/dev-bootstrap.sh] | A new third command path on top of the exact gate and `dev-bootstrap verify`. [ASSUMED] | Either make docs describe the script truthfully, or change the script to match the documented exact gate. [VERIFIED: CONTRIBUTING.md][VERIFIED: scripts/dev-bootstrap.sh][ASSUMED] | Adding a third path would worsen drift instead of removing it. [ASSUMED] |

**Key insight:** Phase 08 is a truth-recovery phase, not a feature-addition phase; its hardest problem is restoring one trusted proof chain from current test reality to phase verification to milestone bookkeeping. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][VERIFIED: local test run][ASSUMED]

## Common Pitfalls

### Pitfall 1: Mistaking “missing verification file” for “docs-only work”

**What goes wrong:** Planning assumes Phase 03 only needs a missing markdown file, then the phase closes without rerunning the actual workspace-safety regressions. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][VERIFIED: directory listing]

**Why it happens:** The audit recorded Phase 03 as verification-missing, but current test reality now also shows a live interrupted-commit failure. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][VERIFIED: local test run]

**How to avoid:** Make `08-01` rerun the Phase 03 truth set first and treat `03-VERIFICATION.md` as an output, not as the task itself. [VERIFIED: local test run][ASSUMED]

**Warning signs:** `tests/test_runtime_workspace_safety.py::test_interrupted_commit_keeps_previous_current_revision_authoritative` is red, or `03-VERIFICATION.md` is drafted before any current rerun exists. [VERIFIED: local test run][ASSUMED]

### Pitfall 2: Letting full-repo failures redefine a phase-owned gate

**What goes wrong:** Phase 04 remains blocked because `./scripts/dev-bootstrap.sh verify` is red, even though the exact Phase 04 gate is green. [VERIFIED: CONTRIBUTING.md][VERIFIED: scripts/dev-bootstrap.sh][VERIFIED: local test run]

**Why it happens:** The docs currently claim that the one-shot script runs the same gate, but the script actually runs the entire test suite. [VERIFIED: CONTRIBUTING.md][VERIFIED: scripts/dev-bootstrap.sh]

**How to avoid:** Decide explicitly whether the canonical fix is “docs now describe the script truthfully” or “script now matches the exact phase gate”, and then update `04-VERIFICATION.md` against that decision. [VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md][ASSUMED]

**Warning signs:** `CONTRIBUTING.md` and `scripts/dev-bootstrap.sh` describe different scopes, or the Phase 04 verification doc still says `gaps_found` after the exact gate is green. [VERIFIED: CONTRIBUTING.md][VERIFIED: scripts/dev-bootstrap.sh][VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md]

### Pitfall 3: Updating planning ledgers in isolation

**What goes wrong:** One file says Phase 04 is complete, another still says Phase 08 is pending, and the milestone audit remains frozen at `gaps_found`. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/STATE.md][VERIFIED: .planning/REQUIREMENTS.md]

**Why it happens:** Planning artifacts have different responsibilities, but the current process gap does not enforce atomic sync across them. [VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/STATE.md][VERIFIED: .planning/REQUIREMENTS.md][ASSUMED]

**How to avoid:** Reserve one explicit closeout plan that edits all ledgers together after verification truth is settled. [ASSUMED]

**Warning signs:** `ROADMAP.md`, `STATE.md`, and `REQUIREMENTS.md` disagree on the owner or completion state of `RUNT-02` or Phase 04. [VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/STATE.md][VERIFIED: .planning/REQUIREMENTS.md]

### Pitfall 4: Widening Phase 08 into a generic repo-health cleanup

**What goes wrong:** Phase 08 absorbs every red test from the full suite and loses its closeout focus. [VERIFIED: local test run][ASSUMED]

**Why it happens:** `./scripts/dev-bootstrap.sh verify` currently fails on unrelated control-plane, inspect, and report-writer tests in addition to one overlapping Phase 03 regression. [VERIFIED: local test run]

**How to avoid:** Separate “blocking because it closes `RUNT-02`/`INT-02`/`FLOW-02`” from “residual repo-health debt outside this milestone closeout scope”, and record the latter explicitly if you do not fix it here. [VERIFIED: local test run][ASSUMED]

**Warning signs:** New tasks start targeting unrelated `inspect` or report-writer behavior without a direct line back to the closeout gaps. [VERIFIED: local test run][ASSUMED]

## Code Examples

Verified closeout commands from current FluxQ sources and local probes:

### Phase 03 Truth Probe

```bash
./.venv/bin/python -m pytest tests/test_cli_workspace_safety.py tests/test_runtime_workspace_safety.py -q --maxfail=1
```

This is the smallest trustworthy Phase 03 closeout probe because it exercises both CLI-facing workspace-safety contracts and runtime interrupted-commit behavior. [VERIFIED: tests/test_cli_workspace_safety.py][VERIFIED: tests/test_runtime_workspace_safety.py][VERIFIED: local test run]

### Exact Phase 04 Gate

```bash
./.venv/bin/ruff check src tests
./.venv/bin/python -m mypy src
./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_cli_observability.py tests/test_runtime_policy.py -q --maxfail=1
```

This is the gate that currently passes and should be treated as the canonical Phase 04 closeout truth unless the script is changed to match it. [VERIFIED: CONTRIBUTING.md][VERIFIED: local test run]

### Ledger Consistency Audit

```bash
test -f .planning/phases/03-concurrent-workspace-safety/03-VERIFICATION.md
test -f .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md
rg -n "Phase 4|Phase 8|RUNT-02|POLC-01" .planning/ROADMAP.md .planning/STATE.md .planning/REQUIREMENTS.md .planning/v1.0-MILESTONE-AUDIT.md
```

This is the minimum scripted proof that Phase 08 closed both the missing verification artifact and the bookkeeping drift. [VERIFIED: directory listing][VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][ASSUMED]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| “All plan summaries exist, so the phase is effectively complete.” [VERIFIED: directory listing][ASSUMED] | Phase completion for closeout now requires a current `*-VERIFICATION.md` plus matching ledgers. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md] | Explicitly visible in the 2026-04-15 milestone audit. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md] | Phase 08 must regenerate proof, not just restate history. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][ASSUMED] |
| “`./scripts/dev-bootstrap.sh verify` is the same as the repo-local Phase 04 gate.” [VERIFIED: CONTRIBUTING.md][ASSUMED] | The exact targeted gate passes, while the script runs the full suite and still fails outside that scope. [VERIFIED: CONTRIBUTING.md][VERIFIED: scripts/dev-bootstrap.sh][VERIFIED: local test run] | Verified on 2026-04-16. [VERIFIED: system date][VERIFIED: local test run] | Phase 08 must either align docs to script truth or align script behavior to docs. [VERIFIED: CONTRIBUTING.md][VERIFIED: scripts/dev-bootstrap.sh][ASSUMED] |
| “Phase 03 is blocked only by missing verification paperwork.” [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][ASSUMED] | Phase 03 currently also has one live interrupted-commit regression. [VERIFIED: local test run] | Verified on 2026-04-16. [VERIFIED: system date][VERIFIED: local test run] | `08-01` needs repair capacity, not just markdown capacity. [ASSUMED] |

**Deprecated/outdated:**

- Treating `ROADMAP.md` alone as the authoritative milestone status is outdated for this repo because the audit now treats cross-file inconsistency itself as a blocker. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Phase 08 is best split into three plans rather than two. [ASSUMED] | Summary / Architecture Patterns | The planner might over-split or under-split the closeout work and lose momentum or traceability. |
| A2 | `PROJECT.md` and `v1.0-MILESTONE-AUDIT.md` should be refreshed during the final closeout if the archive workflow expects a final passed snapshot. [ASSUMED] | Summary / Recommended Plan Split | The plan could either miss a required archival artifact or spend time on a document the workflow does not actually consume. |
| A3 | `./scripts/dev-bootstrap.sh` does not need to be changed if `CONTRIBUTING.md` is updated to describe it as full-repo smoke rather than the exact Phase 04 gate. [ASSUMED] | Documentation / Bookkeeping vs New Verification Work | The team may prefer the opposite source-of-truth choice and want the script changed instead. |

## Resolved Questions (RESOLVED)

1. **`RUNT-02` remains mapped to Phase 08 in `REQUIREMENTS.md`.**
   - Resolved direction: Phase 08 is the terminal closure owner for `RUNT-02`, even though the missing proof artifact is written into the Phase 03 directory. This matches the current repo precedent where a gap-closure phase can become the final traceability owner (`POLC-01 -> Phase 07`). [VERIFIED: .planning/REQUIREMENTS.md]
   - Planning consequence: `ROADMAP.md`, `STATE.md`, and `REQUIREMENTS.md` should all preserve `RUNT-02 -> Phase 08 -> Complete` during closeout. [VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/STATE.md][VERIFIED: .planning/REQUIREMENTS.md][ASSUMED]

2. **Retroactive `03-VALIDATION.md` backfill is out of scope.**
   - Resolved direction: `03-VERIFICATION.md` is the required missing artifact for milestone closeout; retroactive `03-VALIDATION.md` is not required for Phase 08 unless a later archive workflow explicitly introduces that requirement. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][VERIFIED: .planning/phases/08-milestone-verification-bookkeeping-closure/08-VALIDATION.md]
   - Planning consequence: `08-01` should spend scope on truthful rerun evidence plus `03-VERIFICATION.md`, not on reconstructing historical validation paperwork. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][ASSUMED]

3. **Unrelated full-suite failures do not block Phase 08 closeout.**
   - Resolved direction: Only the Phase 08-owned truth sets block closure: the Phase 03 workspace-safety rerun, the canonical Phase 04 gate, and the final ledger/audit sync. Unrelated failures from `./scripts/dev-bootstrap.sh verify` remain residual repo-smoke debt once those owned proofs are green and documented honestly. [VERIFIED: local test run][VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md]
   - Planning consequence: the overlapping Phase 03 regression is in scope, but unrelated control-plane, inspect, and report-writer failures stay recorded as residual debt instead of reopening `RUNT-02`, `INT-02`, or `FLOW-02`. [VERIFIED: local test run][ASSUMED]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `.venv/bin/python` | All Phase 08 verification and doc-generation commands. [VERIFIED: AGENTS.md][VERIFIED: local test run] | ✓ [VERIFIED: local test run] | `3.11.15`. [VERIFIED: local test run] | None needed; this is the canonical interpreter. [VERIFIED: local test run] |
| `uv` | Environment sync and optional one-shot setup. [VERIFIED: AGENTS.md][VERIFIED: local test run] | ✓ [VERIFIED: local test run] | `0.11.1`. [VERIFIED: local test run] | `./scripts/dev-bootstrap.sh install` can bootstrap the venv if needed. [VERIFIED: scripts/dev-bootstrap.sh] |
| `pytest` | Phase 03 / 04 reruns and Phase 08 closeout gate. [VERIFIED: tests/test_runtime_workspace_safety.py][VERIFIED: tests/test_cli_compare.py] | ✓ [VERIFIED: local test run] | `9.0.2`. [VERIFIED: local test run] | Use `./.venv/bin/python -m pytest ...` as the stable invocation. [VERIFIED: local test run] |
| `ruff` | Phase 04 exact gate and Phase 08 combined gate. [VERIFIED: CONTRIBUTING.md][VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VALIDATION.md] | ✓ [VERIFIED: local test run] | `0.15.8`. [VERIFIED: local test run] | None needed. [VERIFIED: local test run] |
| `mypy` via module form | Phase 04 exact gate and Phase 08 combined gate. [VERIFIED: CONTRIBUTING.md][VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VALIDATION.md] | ✓ [VERIFIED: local test run] | `1.20.0`. [VERIFIED: local test run] | Use `./.venv/bin/python -m mypy src`; do not rely on the broken launcher. [VERIFIED: local test run] |
| `./scripts/dev-bootstrap.sh` | Optional repo-wide smoke or one-shot install/verify helper. [VERIFIED: scripts/dev-bootstrap.sh] | ✓ [VERIFIED: local test run] | repo script. [VERIFIED: scripts/dev-bootstrap.sh] | Not a fallback for the exact Phase 04 gate; it is a different command path. [VERIFIED: CONTRIBUTING.md][VERIFIED: scripts/dev-bootstrap.sh] |
| `python3` | Ad hoc shell usage only. [VERIFIED: local test run] | ✓ [VERIFIED: local test run] | `3.13.2`. [VERIFIED: local test run] | Do not use it for repo work; use `.venv/bin/python`. [VERIFIED: AGENTS.md][VERIFIED: local test run] |

**Missing dependencies with no fallback:**

- None. The required local verification stack is present. [VERIFIED: local test run]

**Missing dependencies with fallback:**

- The direct `./.venv/bin/mypy` launcher is unusable because its shebang points at a stale path, but `./.venv/bin/python -m mypy src` works and is already what the repo script falls back to. [VERIFIED: local test run][VERIFIED: scripts/dev-bootstrap.sh]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest 9.0.2`, `ruff 0.15.8`, `mypy 1.20.0`. [VERIFIED: local test run] |
| Config file | `pyproject.toml` and `mypy.ini`. [VERIFIED: AGENTS.md] |
| Quick run command | `./.venv/bin/python -m pytest tests/test_cli_workspace_safety.py tests/test_runtime_workspace_safety.py -q --maxfail=1`. [VERIFIED: local test run] |
| Full suite command | `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_workspace_safety.py tests/test_runtime_workspace_safety.py tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_cli_observability.py tests/test_runtime_policy.py -q --maxfail=1`. [VERIFIED: CONTRIBUTING.md][VERIFIED: local test run][ASSUMED] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| `RUNT-02` | Shared-workspace writes remain coherent under conflicts and interrupted commits. [VERIFIED: .planning/REQUIREMENTS.md] | Runtime + CLI integration. [VERIFIED: tests/test_runtime_workspace_safety.py][VERIFIED: tests/test_cli_workspace_safety.py] | `./.venv/bin/python -m pytest tests/test_cli_workspace_safety.py tests/test_runtime_workspace_safety.py tests/test_cli_compare.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_cli_runtime_gap.py -q --maxfail=1`. [VERIFIED: local test run][ASSUMED] | ✅ [VERIFIED: directory listing] |
| `INT-02` | Phase 04 bookkeeping reflects executed work and the canonical local gate. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md] | Tooling + doc audit. [VERIFIED: CONTRIBUTING.md][VERIFIED: scripts/dev-bootstrap.sh][VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md] | `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_cli_observability.py tests/test_runtime_policy.py -q --maxfail=1`. [VERIFIED: local test run] | ✅ [VERIFIED: directory listing] |
| `FLOW-02` | Milestone closeout has one self-consistent proof chain across verification artifacts and ledgers. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md] | Scripted ledger audit + manual review. [VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/STATE.md][VERIFIED: .planning/REQUIREMENTS.md] | `test -f .planning/phases/03-concurrent-workspace-safety/03-VERIFICATION.md && test -f .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md && rg -n "Phase 4|Phase 8|RUNT-02|POLC-01" .planning/ROADMAP.md .planning/STATE.md .planning/REQUIREMENTS.md .planning/v1.0-MILESTONE-AUDIT.md`. [VERIFIED: directory listing][ASSUMED] | ⚠️ `03-VERIFICATION.md` missing in Wave 0. [VERIFIED: directory listing] |

### Sampling Rate

- **Per task commit:** rerun the owning targeted probe only. `08-01` uses the Phase 03 workspace-safety tests; `08-02` uses the exact Phase 04 gate; `08-03` uses the ledger audit command. [VERIFIED: local test run][ASSUMED]
- **Per wave merge:** run the Phase 08 full suite command, not `./scripts/dev-bootstrap.sh verify`. [VERIFIED: local test run][ASSUMED]
- **Phase gate:** targeted closeout gate green plus ledger audit clean before writing `08-VERIFICATION.md`. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][ASSUMED]
- **Out-of-band smoke:** `./scripts/dev-bootstrap.sh verify` may still be run as a repo-health signal, but it should not redefine Phase 08 completion while unrelated failures remain. [VERIFIED: local test run][ASSUMED]

### Wave 0 Gaps

- [ ] `03-VERIFICATION.md` does not exist yet. [VERIFIED: directory listing]
- [ ] The current Phase 03 truth set is not green: `tests/test_runtime_workspace_safety.py::test_interrupted_commit_keeps_previous_current_revision_authoritative` fails. [VERIFIED: local test run]
- [ ] `04-VERIFICATION.md` still says `status: gaps_found` even though the exact targeted Phase 04 gate now passes. [VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md][VERIFIED: local test run]
- [ ] `CONTRIBUTING.md` and `scripts/dev-bootstrap.sh` still disagree about what `./scripts/dev-bootstrap.sh verify` actually verifies. [VERIFIED: CONTRIBUTING.md][VERIFIED: scripts/dev-bootstrap.sh]
- [ ] Final milestone-ledger consistency (`ROADMAP.md` / `STATE.md` / `REQUIREMENTS.md`) still needs one explicit closeout pass. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no. [VERIFIED: .planning/PROJECT.md] | This phase is local CLI closeout work; no auth surface is added. [VERIFIED: .planning/PROJECT.md] |
| V3 Session Management | no. [VERIFIED: .planning/PROJECT.md] | No session layer is in scope. [VERIFIED: .planning/PROJECT.md] |
| V4 Access Control | no new surface. [VERIFIED: .planning/PROJECT.md][ASSUMED] | The work is on local files and verification contracts, not on ACL design. [VERIFIED: .planning/PROJECT.md][ASSUMED] |
| V5 Input Validation | yes. [VERIFIED: tests/test_runtime_workspace_safety.py][VERIFIED: tests/test_cli_compare.py] | Reuse existing CLI/runtime validation and schema-versioned outputs; do not accept milestone closure claims without current test evidence. [VERIFIED: AGENTS.md][VERIFIED: local test run][ASSUMED] |
| V6 Cryptography | no new cryptography. [VERIFIED: AGENTS.md][VERIFIED: .planning/PROJECT.md] | Reuse the existing replay-integrity and artifact-digest model; Phase 08 should not introduce a second trust scheme. [VERIFIED: AGENTS.md][ASSUMED] |

### Known Threat Patterns for Milestone Closeout

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Marking a phase complete before current verification truth is green. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][VERIFIED: local test run] | Tampering / Repudiation | Require current targeted reruns and `*-VERIFICATION.md` refresh before ledger updates. [VERIFIED: local test run][ASSUMED] |
| Letting a convenience script redefine a phase gate. [VERIFIED: CONTRIBUTING.md][VERIFIED: scripts/dev-bootstrap.sh] | Repudiation | Keep exact phase-owned commands separate from repo-wide smoke commands and document the distinction. [VERIFIED: local test run][ASSUMED] |
| Cross-file ledger drift after closeout. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md] | Tampering / Repudiation | Update `ROADMAP.md`, `STATE.md`, and `REQUIREMENTS.md` atomically and audit them together. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][ASSUMED] |

## Sources

### Primary (HIGH confidence)

- `AGENTS.md` - project constraints, Python 3.11 / `uv` stack, and workflow rules. [VERIFIED: AGENTS.md]
- `.planning/ROADMAP.md` - Phase 08 goal, dependencies, and Phase 04/08 status. [VERIFIED: .planning/ROADMAP.md]
- `.planning/REQUIREMENTS.md` - `RUNT-02` definition and current traceability mapping. [VERIFIED: .planning/REQUIREMENTS.md]
- `.planning/STATE.md` - active blockers and current project position. [VERIFIED: .planning/STATE.md]
- `.planning/PROJECT.md` - milestone/product constraints and current stale update marker. [VERIFIED: .planning/PROJECT.md]
- `.planning/v1.0-MILESTONE-AUDIT.md` - canonical gap inventory for `RUNT-02`, `INT-02`, and `FLOW-02`. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md]
- Phase 03 summaries and directory listing - existing plan completion evidence plus missing `03-VERIFICATION.md`. [VERIFIED: .planning/phases/03-concurrent-workspace-safety/03-concurrent-workspace-safety-01-SUMMARY.md][VERIFIED: .planning/phases/03-concurrent-workspace-safety/03-concurrent-workspace-safety-02-SUMMARY.md][VERIFIED: .planning/phases/03-concurrent-workspace-safety/03-concurrent-workspace-safety-03-SUMMARY.md][VERIFIED: .planning/phases/03-concurrent-workspace-safety/03-concurrent-workspace-safety-04-SUMMARY.md][VERIFIED: directory listing]
- Phase 04/05/06/07 verification and validation artifacts - precedent for closeout shape and current status. [VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VERIFICATION.md][VERIFIED: .planning/phases/04-policy-acceptance-gates/04-VALIDATION.md][VERIFIED: .planning/phases/05-verified-delivery-bundles/05-VERIFICATION.md][VERIFIED: .planning/phases/06-runtime-adoption-surface/06-VERIFICATION.md][VERIFIED: .planning/phases/07-compare-trust-closure/07-VERIFICATION.md][VERIFIED: .planning/phases/07-compare-trust-closure/07-VALIDATION.md]
- `CONTRIBUTING.md` and `scripts/dev-bootstrap.sh` - exact gate vs one-shot script behavior. [VERIFIED: CONTRIBUTING.md][VERIFIED: scripts/dev-bootstrap.sh]
- Phase-owned tests - current verification truth set and gap localization. [VERIFIED: tests/test_runtime_workspace_safety.py][VERIFIED: tests/test_cli_workspace_safety.py][VERIFIED: tests/test_cli_compare.py][VERIFIED: tests/test_cli_bench.py][VERIFIED: tests/test_cli_doctor.py][VERIFIED: tests/test_cli_runtime_gap.py]
- Local test runs on 2026-04-16 - exact Phase 04 gate pass, `dev-bootstrap verify` fail summary, Phase 03 interrupted-commit failure, and focused workspace-safety rerun. [VERIFIED: local test run]

### Secondary (MEDIUM confidence)

- None. This research was grounded in repo artifacts and local command probes instead of secondary commentary. [VERIFIED: directory listing][VERIFIED: local test run]

### Tertiary (LOW confidence)

- None. The prior requirement-ownership, retroactive-validation, and full-suite-blocker questions are now resolved for planning; only archive-wording preferences remain as low-risk assumptions. [VERIFIED: local test run][ASSUMED]

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - all required local tools and command forms were verified in the current workspace. [VERIFIED: local test run]
- Architecture: HIGH - the closeout structure, requirement ownership, retroactive validation scope, and blocker policy are now explicit for execution; only archive-wording preferences remain assumed. [VERIFIED: .planning/REQUIREMENTS.md][ASSUMED]
- Pitfalls: HIGH - the main risks were verified directly by current audit artifacts and fresh local probes. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md][VERIFIED: local test run]

**Research date:** 2026-04-16. [VERIFIED: system date]
**Valid until:** 2026-04-23, because the repo state and verification results are changing quickly and should be rechecked if implementation is delayed. [VERIFIED: system date][ASSUMED]
