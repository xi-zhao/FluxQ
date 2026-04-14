# Phase 5: Verified Delivery Bundles - Research

**Researched:** 2026-04-14 [VERIFIED: system date]  
**Domain:** Portable runtime bundle production, bundle-local trust verification, and downstream bundle re-import for FluxQ revisions. [VERIFIED: ROADMAP.md][VERIFIED: REQUIREMENTS.md]  
**Confidence:** MEDIUM [VERIFIED: code review][ASSUMED]

## User Constraints

No phase-specific `CONTEXT.md` exists for Phase 5, so the constraints below are inherited from `AGENTS.md`, `.planning/PROJECT.md`, `.planning/ROADMAP.md`, and `.planning/REQUIREMENTS.md`. [VERIFIED: init plan-phase 5][VERIFIED: AGENTS.md][VERIFIED: PROJECT.md]

### Locked Decisions

- Keep Python 3.11, `uv`, Typer, Pydantic, and the existing local CLI packaging flow as the implementation stack. [VERIFIED: AGENTS.md][VERIFIED: pyproject.toml]
- Evolve the current `QSpec`, run-manifest, and CLI contracts compatibly instead of introducing a new bundle-specific IR. [VERIFIED: AGENTS.md][VERIFIED: PROJECT.md]
- Treat machine-readable output as a product contract: bundle production, verification, and import must stay schema-versioned and agent-friendly. [VERIFIED: AGENTS.md][VERIFIED: PROJECT.md]
- Prioritize replay trust, policy gating, and delivery bundles before remote breadth. [VERIFIED: PROJECT.md][VERIFIED: ROADMAP.md]
- Reuse immutable revision history and existing provenance checks rather than trusting mutable aliases or raw copied files. [VERIFIED: 02-VERIFICATION.md][VERIFIED: src/quantum_runtime/runtime/imports.py]

### Claude's Discretion

- Add a bundle-local manifest, verification result contract, and import command if they preserve existing report, manifest, and provenance semantics instead of replacing them. [VERIFIED: PROJECT.md][ASSUMED]
- Tighten `qrun pack` semantics so delivery is read-only over immutable revision artifacts, even if that means turning current compatibility backfill into explicit errors. [VERIFIED: .planning/codebase/CONCERNS.md][ASSUMED]

### Deferred Ideas (Out of Scope)

- Remote signing, registry publishing, or provider-to-provider bundle exchange. [VERIFIED: PROJECT.md][VERIFIED: REQUIREMENTS.md]
- New bundle encryption, key-management, or trust-root infrastructure beyond repo-local digest verification. [ASSUMED]
- Broad documentation/adoption work; that remains Phase 6. [VERIFIED: ROADMAP.md]

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DELV-01 | Agent can package one revision into a portable delivery bundle that includes the core runtime objects and export outputs. [VERIFIED: REQUIREMENTS.md] | Harden `qrun pack` so it packages only immutable revision artifacts, revision-scoped event snapshots, selected exports, and bundle-local trust metadata. [VERIFIED: src/quantum_runtime/runtime/pack.py][VERIFIED: tests/test_cli_runtime_gap.py] |
| DELV-02 | Agent can inspect and verify a delivery bundle outside the original workspace. [VERIFIED: REQUIREMENTS.md] | Extend `qrun pack-inspect` from shape-only checks to bundle-local digest/provenance verification that does not depend on the source workspace. [VERIFIED: src/quantum_runtime/runtime/pack.py][VERIFIED: tests/test_pack_bundle.py] |
| DELV-03 | Agent can unpack or re-import a verified delivery bundle into downstream workflows. [VERIFIED: REQUIREMENTS.md] | Add a bundle import path that verifies first, writes revision history into a target workspace, promotes aliases, and lets existing `show`/`inspect`/`compare` flows continue from imported evidence. [ASSUMED][VERIFIED: src/quantum_runtime/runtime/imports.py] |

## Current State

### What Already Exists

- `qrun pack --workspace ... --revision ... --json` produces `.quantum/packs/<revision>/` and currently copies `intent.json`, `qspec.json`, `plan.json`, `report.json`, `manifest.json`, `events.jsonl`, `exports/`, and optional `bench.json` / `doctor.json` / `compare.json`. [VERIFIED: src/quantum_runtime/cli.py][VERIFIED: src/quantum_runtime/runtime/pack.py][VERIFIED: tests/test_cli_runtime_gap.py]
- `qrun pack-inspect --pack-root ... --json` exists, but it only checks whether a small required file set is present. [VERIFIED: src/quantum_runtime/cli.py][VERIFIED: src/quantum_runtime/runtime/pack.py][VERIFIED: tests/test_pack_bundle.py]
- The broader runtime already has strong provenance and replay-integrity logic in `runtime/imports.py`, `runtime/run_manifest.py`, and `artifact_provenance.py`. [VERIFIED: src/quantum_runtime/runtime/imports.py][VERIFIED: src/quantum_runtime/runtime/run_manifest.py][VERIFIED: src/quantum_runtime/artifact_provenance.py]

### What Is Missing

- `pack` still behaves like a workspace mutation command instead of a read-only delivery command. It backfills missing `intents/history/<revision>.json` and `plans/history/<revision>.json` on demand and rescans live event logs instead of using revision snapshots. [VERIFIED: src/quantum_runtime/runtime/pack.py][VERIFIED: .planning/codebase/CONCERNS.md]
- `pack` accepts raw `--revision` text and derives `packs/<revision>` paths without the `invalid_revision` validation already used by report-history imports. [VERIFIED: src/quantum_runtime/runtime/pack.py][VERIFIED: src/quantum_runtime/runtime/imports.py][VERIFIED: .planning/codebase/CONCERNS.md]
- Repacking an existing bundle can delete the last good bundle before the staged replacement is verified. [VERIFIED: src/quantum_runtime/runtime/pack.py][VERIFIED: .planning/codebase/CONCERNS.md]
- `pack-inspect` cannot detect tampered bundle bytes, mismatched revision metadata, or degraded trust states because there is no bundle-local digest manifest. [VERIFIED: src/quantum_runtime/runtime/pack.py][VERIFIED: tests/test_pack_bundle.py]
- There is no CLI or runtime helper to import a verified bundle into a target workspace and continue from that revision. [VERIFIED: src/quantum_runtime/cli.py][VERIFIED: ROADMAP.md]

## Summary

Phase 5 should deepen the existing `pack` surface rather than invent a second delivery subsystem. The codebase already knows how to produce immutable revision artifacts, canonical provenance, and replay-integrity judgments. The missing pieces are bundle-local trust metadata, workspace-independent verification, and a downstream import path. [VERIFIED: src/quantum_runtime/runtime/pack.py][VERIFIED: src/quantum_runtime/runtime/imports.py][VERIFIED: src/quantum_runtime/runtime/run_manifest.py]

**Primary recommendation:** split the phase into three sequential plans:

1. Harden `qrun pack` into a path-safe, non-destructive bundle producer that packages only immutable history artifacts plus bundle-local trust metadata.
2. Upgrade `qrun pack-inspect` into a bundle verifier that checks bundle-local digests and provenance outside the source workspace.
3. Add `qrun pack-import` so a verified bundle can seed a downstream workspace and resume existing runtime workflows from the imported revision.

This sequencing keeps delivery bundle production, verification, and import separately testable while reusing the trust surfaces already established in Phases 2 through 4. [VERIFIED: ROADMAP.md][VERIFIED: 02-VERIFICATION.md][VERIFIED: 04-VERIFICATION.md]

## Standard Stack

No new dependency is required for Phase 5. The work fits the current brownfield Python/Typer/Pydantic/runtime-module stack. [VERIFIED: pyproject.toml][ASSUMED]

| Library / Module | Current Role | Phase 5 Use |
|------------------|-------------|-------------|
| `src/quantum_runtime/runtime/pack.py` | Bundle creation and shape-only inspection. [VERIFIED] | Primary home for bundle manifest creation, verification, and import helpers. [ASSUMED] |
| `src/quantum_runtime/runtime/imports.py` | Trusted report/revision reopening with `invalid_revision`, provenance, and replay-integrity checks. [VERIFIED] | Reuse revision validation and fail-closed trust semantics instead of duplicating them in delivery code. [VERIFIED][ASSUMED] |
| `src/quantum_runtime/runtime/run_manifest.py` | Immutable per-run manifest with digests for report/qspec/optional artifacts. [VERIFIED] | Reuse its digest and optional-artifact concepts when defining a bundle-local manifest. [ASSUMED] |
| `src/quantum_runtime/artifact_provenance.py` | Canonicalize artifact paths and detect drift. [VERIFIED] | Reuse bundle import trust rules when mapping imported artifacts into a new workspace. [ASSUMED] |
| `src/quantum_runtime/workspace/paths.py` | Canonical workspace path layout including `packs/`, history snapshots, and aliases. [VERIFIED] | Keep bundle import/export paths aligned with the established workspace contract. [VERIFIED] |
| `tests/test_cli_runtime_gap.py` | Existing end-to-end CLI regression home for `pack` and workspace safety behaviors. [VERIFIED] | Extend with invalid revision, non-destructive repack, verify, and import regressions. [ASSUMED] |
| `tests/test_pack_bundle.py` | Current pack module/unit-style coverage. [VERIFIED] | Extend to bundle manifest and bundle verification internals. [ASSUMED] |

## Architecture Patterns

### Pattern 1: Bundle-Local Trust Manifest

**What:** Add one bundle-local manifest file such as `bundle_manifest.json` that records the bundle revision, schema version, relative file paths, required/optional classification, and SHA-256 digests for every bundled artifact. [ASSUMED]

**Why:** The copied runtime `manifest.json` contains absolute workspace expectations, which are useful provenance but not sufficient for verifying a copied bundle in another directory. A bundle-local manifest lets `pack-inspect` validate bytes without depending on the source workspace still existing. [VERIFIED: src/quantum_runtime/runtime/run_manifest.py][VERIFIED: tests/test_pack_bundle.py][ASSUMED]

### Pattern 2: Read-Only Packaging From Immutable History

**What:** `qrun pack` should package only immutable history artifacts that already exist: `intents/history/<revision>.json`, `plans/history/<revision>.json`, `specs/history/<revision>.json`, `reports/history/<revision>.json`, `manifests/history/<revision>.json`, `events/history/<revision>.jsonl`, and `trace/history/<revision>.ndjson`. [ASSUMED]

**Why:** Delivery should not backfill history, re-run planners, or scan live mutable logs. That behavior makes bundle semantics harder to trust and harder to reason about under failure. [VERIFIED: src/quantum_runtime/runtime/pack.py][VERIFIED: .planning/codebase/CONCERNS.md]

### Pattern 3: Verify Before Import

**What:** Downstream import must call the same bundle verification logic as `pack-inspect` and refuse any bundle whose digest, revision, or required-entry contract fails. [ASSUMED]

**Why:** Bundle import is effectively a replay/import surface for a foreign filesystem object, so it should be at least as strict as the Phase 2 report/revision import path. [VERIFIED: 02-VERIFICATION.md][VERIFIED: src/quantum_runtime/runtime/imports.py]

### Pattern 4: History First, Alias Promotion Second

**What:** Bundle import should copy immutable revision history first, then promote `current` aliases and `workspace.json` / `manifests/latest.json` only after the imported revision is fully materialized. [ASSUMED]

**Why:** This mirrors the existing workspace safety and immutable-history contract from Phases 2 and 3 and avoids partial current/history mismatches. [VERIFIED: 02-VERIFICATION.md][VERIFIED: 03-04-PLAN.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Revision validation | A second regex/parser for `rev_000001` strings. | The existing `invalid_revision` contract from `resolve_report_revision()` or a shared helper extracted from it. | Keeps CLI error codes and safety rules consistent across import and pack surfaces. |
| Absolute-path verification | Bundle checks that trust source workspace paths still being valid. | Bundle-local relative paths plus SHA-256 digests in `bundle_manifest.json`. | Copied bundles must remain verifiable outside the original workspace. |
| Import trust semantics | A new “bundle trust” language disconnected from report replay integrity. | Existing replay/provenance concepts from `runtime/imports.py`, `run_manifest.py`, and `artifact_provenance.py`. | Downstream agents should keep seeing one trust vocabulary. |
| Destructive promotion | Delete-then-build replacement bundle roots. | Stage under `.packs/.<revision>.tmp`, verify, then promote. | Preserves the last good bundle when staging fails. |

## Common Pitfalls

### Pitfall 1: Treating `pack-inspect` As A File-Existence Check

**What goes wrong:** A tampered bundle with all required filenames still passes inspection because the inspector never compares bytes against expected digests. [VERIFIED: tests/test_pack_bundle.py][ASSUMED]

**Avoid by:** Making `bundle_manifest.json` required and validating every required entry's digest before returning `status == "ok"`. [ASSUMED]

### Pitfall 2: Letting `pack` Mutate History While Packaging

**What goes wrong:** Packaging a revision silently writes missing `intent` / `plan` history or rescans live event logs, so delivery is no longer a pure snapshot of previously trusted artifacts. [VERIFIED: src/quantum_runtime/runtime/pack.py][VERIFIED: .planning/codebase/CONCERNS.md]

**Avoid by:** Requiring the immutable history artifacts to already exist and failing with a structured error when they do not. [ASSUMED]

### Pitfall 3: Importing Bundle Bytes Before Verifying Them

**What goes wrong:** A downstream workspace ingests tampered `report.json`, `qspec.json`, or exports and only discovers the mismatch after aliases or history paths are already written. [ASSUMED]

**Avoid by:** Running one shared verification routine first, then importing history under the workspace lock, and promoting aliases last. [ASSUMED]

### Pitfall 4: Reusing Source-Workspace Paths During External Verification

**What goes wrong:** A copied bundle passes only because the original workspace still exists at the absolute paths stored in `manifest.json` or report provenance. [ASSUMED]

**Avoid by:** Verifying bundle-local digests and revision metadata first, and treating copied runtime manifest/report paths as descriptive provenance rather than as trusted verification inputs. [ASSUMED]

## Validation Architecture

Phase 5 should keep validation entirely automated. The bundle workflows are filesystem-heavy but deterministic, so `tmp_path`-based CLI/runtime tests are sufficient. [VERIFIED: tests/test_cli_runtime_gap.py][VERIFIED: tests/test_pack_bundle.py]

### Existing Infrastructure To Reuse

- `tests/test_cli_runtime_gap.py` already covers `qrun pack`, `qrun pack-inspect`, and pack workspace-safety errors. [VERIFIED]
- `tests/test_pack_bundle.py` already loads `runtime/pack.py` directly and asserts inspection behavior against synthetic bundle shapes. [VERIFIED]
- `tests/test_runtime_imports.py` already proves fail-closed replay/import behavior and is the right place to confirm imported bundles behave like trusted revision artifacts once materialized. [VERIFIED]

### Recommended Test Expansion

- Extend `tests/test_cli_runtime_gap.py` with invalid revision, non-destructive repack, copied-bundle verification, and bundle-import end-to-end flows. [ASSUMED]
- Extend `tests/test_pack_bundle.py` to cover `bundle_manifest.json`, digest mismatches, and bundle-local verification status. [ASSUMED]
- Create `tests/test_cli_pack_import.py` for a focused CLI contract around `qrun pack-import --json`. [ASSUMED]

### Recommended Commands

**Wave 1 quick command**
```bash
./.venv/bin/python -m pytest tests/test_cli_runtime_gap.py tests/test_pack_bundle.py -q --maxfail=1
```

**Wave 2 quick command**
```bash
./.venv/bin/python -m pytest tests/test_cli_runtime_gap.py tests/test_pack_bundle.py -q --maxfail=1
```

**Wave 3 quick command**
```bash
./.venv/bin/python -m pytest tests/test_cli_runtime_gap.py tests/test_pack_bundle.py tests/test_cli_pack_import.py tests/test_runtime_imports.py -q --maxfail=1
```

**Full phase gate**
```bash
./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_runtime_gap.py tests/test_pack_bundle.py tests/test_cli_pack_import.py tests/test_runtime_imports.py -q --maxfail=1
```

## Key Insight

The hard part of Phase 5 is not “zipping files.” The real product work is turning a local pack directory into a trustworthy, portable runtime boundary that can be verified and continued elsewhere without reintroducing the same provenance and alias drift risks that earlier phases already closed inside one workspace. [VERIFIED: PROJECT.md][VERIFIED: ROADMAP.md][ASSUMED]
