# Codebase Concerns

**Analysis Date:** 2026-04-18

## Tech Debt

**Monolithic command and import orchestration:**
- Issue: `src/quantum_runtime/cli.py` (1864 lines), `src/quantum_runtime/runtime/imports.py` (1197 lines), `src/quantum_runtime/runtime/pack.py` (1158 lines), `src/quantum_runtime/runtime/control_plane.py` (739 lines), and `src/quantum_runtime/runtime/executor.py` (757 lines) each combine multiple responsibilities that should evolve independently.
- Files: `src/quantum_runtime/cli.py`, `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/pack.py`, `src/quantum_runtime/runtime/control_plane.py`, `src/quantum_runtime/runtime/executor.py`
- Impact: small changes cut across CLI parsing, JSON/JSONL presentation, detached report resolution, replay-integrity validation, pack verification, workspace mutation, and rollback behavior. Regressions are harder to localize because the public contract and the filesystem side effects live in the same modules.
- Fix approach: split command-family adapters from runtime services, separate detached-import resolution from replay-integrity evaluation, and separate pack inspection from pack import/promotion while keeping the existing result models stable.

**Retention settings are persisted but not enforced:**
- Issue: `history_limit` is seeded in `src/quantum_runtime/workspace/manager.py` and persisted in `src/quantum_runtime/workspace/manifest.py`, but no runtime path prunes revision history or pack history.
- Files: `src/quantum_runtime/workspace/manager.py`, `src/quantum_runtime/workspace/manifest.py`, `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/runtime/pack.py`, `src/quantum_runtime/diagnostics/benchmark.py`
- Impact: `reports/history/`, `specs/history/`, `artifacts/history/`, `events/history/`, `trace/history/`, `benchmarks/history/`, `doctor/history/`, and `packs/` grow without bound even when operators believe retention is configured.
- Fix approach: implement manifest-aware pruning after successful revision commits, pin the active revision and baseline, and add a dry-run retention audit before deleting anything.

**`qrun.toml` round-tripping is custom and lossy:**
- Issue: `write_ibm_profile()` rewrites the full `qrun.toml` using `_dump_toml()` and `_append_toml_table()` instead of a round-trip TOML editor.
- Files: `src/quantum_runtime/runtime/ibm_access.py`
- Impact: comments, formatting, and key ordering are dropped on every IBM profile write, and future config growth is limited by the custom serializer's supported types.
- Fix approach: move managed config into a smaller machine-owned file or adopt a TOML round-trip library before expanding workspace configuration further.

## Known Bugs

**Stale workspace locks survive crashed writers with no reclaim path:**
- Symptoms: mutating commands keep returning `workspace_conflict` after a crash or `kill -9`, even when no live writer remains.
- Files: `src/quantum_runtime/workspace/locking.py`, `src/quantum_runtime/workspace/manager.py`, `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/runtime/pack.py`, `src/quantum_runtime/runtime/ibm_access.py`, `src/quantum_runtime/runtime/doctor.py`
- Trigger: a process exits before `WorkspaceLock.release()` runs and leaves `<workspace>/.workspace.lock` behind.
- Workaround: manually inspect and delete the lock file after confirming no active writer still owns the workspace.

**Detached copied reports can resolve against the source workspace instead of the explicit target workspace:**
- Symptoms: commands that accept `--report-file` can bind to the workspace embedded in report provenance while that source workspace still exists; the explicit `--workspace` path is only tried later as a fallback.
- Files: `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/cli.py`, `tests/test_runtime_imports.py`, `tests/test_cli_compare.py`, `tests/test_cli_export.py`, `tests/test_cli_baseline.py`
- Trigger: reuse a copied `reports/history/*.json` or `reports/latest.json` that still contains accessible source-workspace provenance.
- Workaround: remove or rename the source workspace, or strip embedded provenance before using the copied report as a detached input.

## Security Considerations

**Pack bundle inspection and import follow symlinks inside untrusted bundles:**
- Risk: `inspect_pack_bundle()` and `import_pack_bundle()` treat symlinked files as ordinary files via `Path.is_file()`, `read_bytes()`, `_sha256_file()`, and `atomic_copy_file()`. A crafted bundle can point `report.json`, `qspec.json`, or members under `exports/` outside `pack_root`, causing local file reads during verification or import.
- Files: `src/quantum_runtime/runtime/pack.py`, `src/quantum_runtime/workspace/manifest.py`
- Current mitigation: digest verification proves byte consistency for the chosen paths, and required-entry checks ensure expected names exist.
- Recommendations: reject symlinks with `lstat()`, require every imported member to stay under `pack_root.resolve()`, and add malicious-bundle tests before treating pack bundles as a safe external handoff format.

**Detached report provenance is trusted before operator-supplied workspace context:**
- Risk: `_infer_workspace_root_from_report_payload()` can steer resolution to absolute local paths embedded in a detached report before `workspace_option_relocated_report` is attempted. Untrusted report JSON can therefore influence which local `workspace.json`, QSpec, and artifact paths are opened.
- Files: `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/export.py`, `src/quantum_runtime/runtime/compare.py`, `src/quantum_runtime/runtime/executor.py`
- Current mitigation: `canonicalize_artifact_provenance()` rejects cross-revision path drift once a workspace is selected, and replay-integrity checks reject mismatched QSpec and artifact digests.
- Recommendations: make explicit `workspace_root` authoritative, require an opt-in flag to trust embedded provenance, and prefer pack bundles over detached raw reports for external exchange.

## Performance Bottlenecks

**`qrun exec` is always full-diagnostics, even for artifact-only use cases:**
- Problem: `_execute_qspec()` always runs `run_local_simulation()`, `write_diagrams()`, `estimate_resources()`, and `validate_target_constraints()` before the report is written.
- Files: `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/diagnostics/simulate.py`, `src/quantum_runtime/diagnostics/diagrams.py`, `src/quantum_runtime/diagnostics/transpile_validate.py`, `src/quantum_runtime/cli.py`
- Cause: execution, diagnostics, and reporting are tightly coupled, and `qrun exec` exposes no fast/skip mode.
- Improvement path: add diagnostic profiles such as `full`, `fast`, and `artifact-only`, or add granular flags like `--no-simulate` and `--no-diagram`.

**Replay-integrity resolution re-hashes artifacts on every import-style command:**
- Problem: import-style flows re-hash resolved artifacts from disk through `_evaluate_replay_integrity()` and `_sha256_file()` every time a report is imported, inspected, exported, or compared.
- Files: `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/inspect.py`, `src/quantum_runtime/runtime/export.py`, `src/quantum_runtime/runtime/compare.py`
- Cause: integrity checks are recomputed from filesystem bytes rather than reusing validated run-manifest metadata when the manifest is already trusted.
- Improvement path: reuse run-manifest digests when the manifest validates, and reserve full artifact re-hash mode for strict verification or detached-report scenarios.

## Fragile Areas

**Workspace commit and alias promotion pipeline:**
- Files: `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/runtime/run_manifest.py`, `src/quantum_runtime/workspace/manifest.py`, `src/quantum_runtime/workspace/locking.py`, `src/quantum_runtime/runtime/pack.py`
- Why fragile: one successful exec spans revision reservation, history writes, report generation, event snapshotting, run-manifest writing, event-log append, and alias promotion. Rollback only restores `workspace.json.current_revision`, so partial history artifacts can still remain on disk after mid-flight failure.
- Safe modification: preserve the ordering of history writes before alias promotion, keep `reports/latest.json`, `specs/current.json`, `manifests/latest.json`, and active artifact aliases as one coherent set, and update recovery logic whenever a new active alias is introduced.
- Test coverage: strong coverage exists in `tests/test_runtime_revision_artifacts.py`, `tests/test_workspace_locking.py`, `tests/test_cli_workspace_safety.py`, and `tests/test_cli_pack_import.py`; there is no stale-lock recovery test and no interrupted-write test for non-atomic artifact writers.

**Detached report import and provenance canonicalization:**
- Files: `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/artifact_provenance.py`, `src/quantum_runtime/runtime/inspect.py`, `src/quantum_runtime/runtime/export.py`, `src/quantum_runtime/runtime/compare.py`
- Why fragile: one flow handles workspace inference, detached-report relocation, artifact path canonicalization, QSpec lookup, replay-integrity checks, and summary generation.
- Safe modification: change workspace-candidate precedence intentionally, keep detached-report behavior explicit, and update runtime-level plus CLI-level detached-import tests together.
- Test coverage: `tests/test_runtime_imports.py`, `tests/test_cli_compare.py`, `tests/test_cli_export.py`, and `tests/test_cli_baseline.py` cover happy-path copied reports; there is no regression test asserting explicit workspace precedence or warning behavior when embedded provenance wins.

**Several revision-bearing writers bypass atomic persistence helpers:**
- Files: `src/quantum_runtime/reporters/writer.py`, `src/quantum_runtime/diagnostics/diagrams.py`, `src/quantum_runtime/lowering/qiskit_emitter.py`, `src/quantum_runtime/lowering/qasm3_emitter.py`, `src/quantum_runtime/lowering/classiq_emitter.py`, `src/quantum_runtime/runtime/pack.py`
- Why fragile: these paths use direct `write_text()` instead of `atomic_write_text()` or `atomic_copy_file()`, but workspace recovery only scans for interrupted atomic temp files.
- Safe modification: move all revision-bearing artifact/report writes onto the atomic helpers before extending recovery logic or adding more artifact families.
- Test coverage: `tests/test_workspace_locking.py` covers interrupted atomic writes for bootstrap files only; there is no equivalent failure-path coverage for reports, diagrams, emitted source files, or staged bundle manifests.

**IBM config persistence surface:**
- Files: `src/quantum_runtime/runtime/ibm_access.py`, `src/quantum_runtime/cli.py`, `tests/test_cli_ibm_config.py`
- Why fragile: one module owns config validation, persistence, service construction, and TOML serialization for a growing integration surface.
- Safe modification: keep secrets external to `.quantum`, keep `IbmAccessProfile` non-secret, and add serializer and import-compat tests before expanding `[remote.ibm]`.
- Test coverage: local unit and CLI tests exist, but there is no CI workflow that installs `qiskit-ibm-runtime` and exercises the real dependency surface.

## Scaling Limits

**Local simulation has no width guard beyond basic schema validation:**
- Current capacity: examples and tests concentrate on small workloads, typically 2-5 qubits and at most 16 parameter-sweep points.
- Limit: `run_local_simulation()` evaluates each parameter point with `Statevector.from_instruction()`, so memory and runtime will grow exponentially with qubit width while `validate_target_constraints()` adds extra transpilation cost on the same path.
- Files: `src/quantum_runtime/diagnostics/simulate.py`, `src/quantum_runtime/diagnostics/transpile_validate.py`, `src/quantum_runtime/qspec/validation.py`, `src/quantum_runtime/intent/planner.py`
- Scaling path: add explicit local width/depth guardrails, downgrade-to-fast-mode behavior, or approximate simulation/backpressure before accepting larger planned workloads.

**Workspace history retention is effectively unlimited:**
- Current capacity: `history_limit = 50` is metadata only; every successful exec, benchmark persistence, doctor persistence, compare history write, and pack can accumulate indefinitely.
- Limit: disk usage and workspace scan time will continue to grow for long-lived agent workspaces and reused CI caches.
- Files: `src/quantum_runtime/workspace/manager.py`, `src/quantum_runtime/workspace/manifest.py`, `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/diagnostics/benchmark.py`, `src/quantum_runtime/runtime/pack.py`
- Scaling path: implement revision pruning with current-revision, baseline, and pack retention rules instead of treating history as append-only forever.

## Dependencies at Risk

**Optional integration paths are outside the default CI lane:**
- Risk: the default workflow in `.github/workflows/ci.yml` does not install `qiskit-ibm-runtime`, and it skips `tests/test_qspec_validation.py`. `classiq` coverage only runs through the separate manual `.github/workflows/classiq.yml`.
- Impact: core schema validation plus optional remote/backend integrations can drift without blocking pull requests.
- Files: `.github/workflows/ci.yml`, `.github/workflows/classiq.yml`, `src/quantum_runtime/runtime/ibm_access.py`, `src/quantum_runtime/runtime/backend_list.py`, `src/quantum_runtime/runtime/doctor.py`, `tests/test_qspec_validation.py`, `tests/test_classiq_backend.py`, `tests/test_classiq_emitter.py`
- Migration plan: move core validation back into default CI, add an IBM import-smoke lane, and make optional integration coverage at least scheduled or PR-triggered for dependency-compat regression detection.

## Missing Critical Features

**No built-in stale-lock remediation command:**
- Problem: `workspace_conflict` surfaces holder metadata, but there is no supported unlock/reclaim flow for orphaned `.workspace.lock` files.
- Blocks: unattended CI retries, agent loops, and crash recovery after abnormal termination.

**No retention/pruning workflow despite persisted retention metadata:**
- Problem: the workspace advertises `history_limit`, but there is no runtime or maintenance command that enforces it.
- Blocks: predictable disk usage for long-lived workspaces and shared CI caches.

**No fast execution mode for control-plane-only use cases:**
- Problem: users cannot request canonical normalization, revisioning, and artifact emission without also paying for local simulation, diagrams, and transpilation.
- Blocks: larger workloads where FluxQ should still act as a control plane even when full local validation is impractical.

## Test Coverage Gaps

**Core QSpec validation is excluded from default CI:**
- What's not tested: `tests/test_qspec_validation.py` is ignored in the default pytest workflow.
- Files: `.github/workflows/ci.yml`, `tests/test_qspec_validation.py`, `src/quantum_runtime/qspec/validation.py`
- Risk: schema and semantic guardrails can regress without blocking pull requests.
- Priority: High

**No malicious-bundle or symlink coverage for pack import:**
- What's not tested: bundle roots containing symlinked `report.json`, `qspec.json`, or symlinked files under `exports/`.
- Files: `tests/test_cli_pack_import.py`, `src/quantum_runtime/runtime/pack.py`, `src/quantum_runtime/workspace/manifest.py`
- Risk: unsafe local file reads or copies from untrusted bundles can change unnoticed.
- Priority: High

**No regression test for explicit workspace precedence over detached report provenance:**
- What's not tested: behavior when both embedded provenance and `--workspace` or `workspace_root` are present and disagree.
- Files: `tests/test_runtime_imports.py`, `tests/test_cli_compare.py`, `tests/test_cli_export.py`, `tests/test_cli_baseline.py`, `src/quantum_runtime/runtime/imports.py`
- Risk: detached report reuse remains ambiguous and can surprise automation or CI pipelines.
- Priority: High

**No stale-lock recovery or dead-PID reclaim test:**
- What's not tested: reclaim behavior after an orphaned `.workspace.lock` whose `pid` is no longer alive.
- Files: `tests/test_workspace_locking.py`, `src/quantum_runtime/workspace/locking.py`
- Risk: workspace mutation can deadlock indefinitely after abnormal termination.
- Priority: Medium

**No interrupted-write tests for non-atomic artifact and report writers:**
- What's not tested: failures during `write_report()`, `write_diagrams()`, `write_qiskit_program()`, `write_qasm3_program()`, `write_classiq_program()`, or staged bundle-manifest writes.
- Files: `tests/test_workspace_locking.py`, `tests/test_report_writer.py`, `src/quantum_runtime/reporters/writer.py`, `src/quantum_runtime/diagnostics/diagrams.py`, `src/quantum_runtime/lowering/qiskit_emitter.py`, `src/quantum_runtime/lowering/qasm3_emitter.py`, `src/quantum_runtime/lowering/classiq_emitter.py`, `src/quantum_runtime/runtime/pack.py`
- Risk: the current recovery model can miss partial files because only interrupted atomic temp files are scanned.
- Priority: High

---

*Concerns audit: 2026-04-18*
