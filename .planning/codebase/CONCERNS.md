# Codebase Concerns

**Analysis Date:** 2026-04-14

## Tech Debt

**Runtime orchestration is still concentrated in a few oversized modules:**
- Issue: command parsing, import resolution, compare policy, and execution commit logic are concentrated in very large files: `src/quantum_runtime/cli.py`, `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/compare.py`, `src/quantum_runtime/runtime/control_plane.py`, and `src/quantum_runtime/runtime/executor.py`.
- Files: `src/quantum_runtime/cli.py`, `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/compare.py`, `src/quantum_runtime/runtime/control_plane.py`, `src/quantum_runtime/runtime/executor.py`
- Impact: small behavior changes can cross CLI UX, machine-readable contracts, workspace persistence, and compare/policy semantics in one edit. Review and regression cost stays high because responsibilities are not isolated cleanly.
- Fix approach: split command handlers from services, extract import/replay logic out of `src/quantum_runtime/runtime/imports.py`, and keep the final workspace commit path in one dedicated module with a smaller surface.

**Workspace health evaluation is duplicated across command surfaces:**
- Issue: workspace health is recomputed in separate ways by `src/quantum_runtime/runtime/control_plane.py`, `src/quantum_runtime/runtime/doctor.py`, and `src/quantum_runtime/runtime/inspect.py`. These flows parse similar files, but they do not share one canonical evaluator and they do not fail the same way on corruption.
- Files: `src/quantum_runtime/runtime/control_plane.py`, `src/quantum_runtime/runtime/doctor.py`, `src/quantum_runtime/runtime/inspect.py`
- Impact: agents and CI can get different answers from `status`, `doctor`, and `inspect` for the same broken workspace. That makes remediation logic harder to trust and harder to automate safely.
- Fix approach: move manifest/report/qspec health checks into one shared runtime-health service and have `status`, `doctor`, and `inspect` project that shared result into their own payload formats.

**Packaging is coupled to compatibility backfill instead of being read-only delivery logic:**
- Issue: `src/quantum_runtime/runtime/pack.py` does more than copy an existing revision. It backfills missing `intents/history/<revision>.json` and `plans/history/<revision>.json` on demand through `resolve_runtime_input()` and `build_execution_plan()`.
- Files: `src/quantum_runtime/runtime/pack.py`, `src/quantum_runtime/runtime/resolve.py`, `src/quantum_runtime/runtime/control_plane.py`
- Impact: a delivery command mutates revision history, which makes pack behavior harder to reason about and increases the blast radius of changes in resolve/plan code.
- Fix approach: separate one-time migration/backfill from `qrun pack`, then keep pack logic read-only over already-materialized revision artifacts.

## Known Bugs

**The live worktree contains conflict-copy Python files inside source and test discovery paths:**
- Symptoms: `git status --short` shows 31 outstanding paths, including untracked `src/quantum_runtime/reporters/writer-NSConflict-BlovedSwami-mac26.4.1.py`, `tests/test_cli_bench-NSConflict-BlovedSwami-mac26.4.1.py`, and `tests/test_runtime_imports-NSConflict-BlovedSwami-mac26.4.1.py`.
- Files: `src/quantum_runtime/reporters/writer-NSConflict-BlovedSwami-mac26.4.1.py`, `tests/test_cli_bench-NSConflict-BlovedSwami-mac26.4.1.py`, `tests/test_runtime_imports-NSConflict-BlovedSwami-mac26.4.1.py`
- Trigger: local `pytest`, ad hoc import discovery, or packaging from the dirty worktree.
- Workaround: remove or ignore `-NSConflict-` files before test runs and release packaging. Re-check `git status --short` before changing neighboring modules because the tree is already in an in-flight merge/conflict state.

**Repacking can delete the last good bundle before the replacement bundle is verified:**
- Symptoms: `pack_revision()` deletes `packs/<revision>` first, then builds the replacement bundle, then validates it. Any later copy, backfill, or verification failure leaves no bundle at `packs/<revision>`.
- Files: `src/quantum_runtime/runtime/pack.py`
- Trigger: rerun `qrun pack --revision <revision>` for an existing bundle and hit any failure after `shutil.rmtree(pack_root)`.
- Workaround: keep an external copy of the pack directory before rerunning `qrun pack`, or change the flow to replace only after the staged bundle has passed inspection.

## Security Considerations

**`qrun pack` accepts unchecked revision input and can escape the workspace pack directory:**
- Risk: `src/quantum_runtime/cli.py` forwards raw `--revision` text into `src/quantum_runtime/runtime/pack.py`, and `src/quantum_runtime/workspace/paths.py` builds `packs/<revision>` with no `rev_000001` validation. `pack_revision()` then calls `shutil.rmtree(pack_root)` and `os.replace(staged_root, pack_root)` on that derived path.
- Files: `src/quantum_runtime/cli.py`, `src/quantum_runtime/runtime/pack.py`, `src/quantum_runtime/workspace/paths.py`
- Current mitigation: not detected in the pack flow. Revision validation exists in `src/quantum_runtime/runtime/imports.py` for `resolve_report_revision()`, but pack does not reuse it.
- Recommendations: add one shared revision validator, reject path separators and `..`, resolve the target path, and assert that it remains under `WorkspacePaths.packs_dir` before delete or replace operations.

**The optional Classiq backend executes generated Python from disk:**
- Risk: `src/quantum_runtime/backends/classiq_backend.py` calls `exec(compile(path.read_text(), ...), namespace)` on the generated program file. The emitter in `src/quantum_runtime/lowering/classiq_emitter.py` narrows the supported QSpec surface, but execution still trusts on-disk Python content at runtime.
- Files: `src/quantum_runtime/backends/classiq_backend.py`, `src/quantum_runtime/lowering/classiq_emitter.py`, `src/quantum_runtime/qspec/validation.py`
- Current mitigation: `src/quantum_runtime/qspec/validation.py` restricts supported pattern and rotation-block inputs, and the backend is optional.
- Recommendations: execute an in-memory source string instead of rereading from disk, reject symlinked output paths, verify file hashes before execution, or run the generated program in a subprocess/sandbox boundary.

## Performance Bottlenecks

**Each exec commit rewrites the full authoritative event logs:**
- Problem: `append_trace_log()` reads the entire destination file and rewrites `existing + staged` back through `atomic_write_text()`. `src/quantum_runtime/runtime/executor.py` calls this for both `events.jsonl` and `trace/events.ndjson` after every successful exec.
- Files: `src/quantum_runtime/workspace/trace.py`, `src/quantum_runtime/runtime/executor.py`
- Cause: append is implemented as whole-file rewrite instead of append-only writes or shard promotion.
- Improvement path: treat `events/history/<revision>.jsonl` and `trace/history/<revision>.ndjson` as the durable source, then rebuild or compact the latest aliases separately instead of rewriting the full logs every run.

**Pack generation rescans the full event history and filters it in memory:**
- Problem: `_write_revision_events()` loads all of `events.jsonl` or `trace/events.ndjson`, parses each line, filters by revision, and rewrites the filtered bundle-local log.
- Files: `src/quantum_runtime/runtime/pack.py`
- Cause: pack does not reuse the per-revision event snapshots already written under `events/history/` and `trace/history/`.
- Improvement path: source pack bundles from `events/history/<revision>.jsonl` and `trace/history/<revision>.ndjson`, or stream the authoritative logs line-by-line instead of loading the whole file into memory.

## Fragile Areas

**Replay/import/compare trust logic stays central, stateful, and easy to destabilize:**
- Files: `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/compare.py`, `src/quantum_runtime/runtime/run_manifest.py`, `src/quantum_runtime/artifact_provenance.py`, `tests/test_runtime_imports.py`, `tests/test_cli_compare.py`
- Why fragile: this path handles workspace-current imports, historical revisions, detached reports, relocated workspaces, provenance normalization, manifest validation, replay-integrity scoring, and compare-policy gating. Small fallback changes can silently alter trust semantics.
- Safe modification: change one fallback rule at a time, keep detached-report and relocated-workspace fixtures close to the code, and add tests for every new mismatch or provenance branch before refactoring.
- Test coverage: integration coverage is strong in `tests/test_runtime_imports.py` and `tests/test_cli_compare.py`, but most guarantees are still proven through broad end-to-end cases instead of small, isolated unit tests.

**The packaging flow is destructive and multi-purpose under one critical section:**
- Files: `src/quantum_runtime/runtime/pack.py`, `tests/test_pack_bundle.py`
- Why fragile: `pack_revision()` acquires the workspace lock, deletes old staging and destination directories, backfills missing history objects, copies artifacts, synthesizes bundle events, and only then verifies the staged pack.
- Safe modification: split pack into validation, materialization, and promotion phases. Keep destructive deletion as the last step, not the first one.
- Test coverage: `tests/test_pack_bundle.py` only exercises `inspect_pack_bundle()` against synthetic directory shapes. It does not cover destructive reruns, compatibility backfill, or malformed revision input.

**The repo state around core runtime files is already in-flight and unstable:**
- Files: `src/quantum_runtime/backends/classiq_backend.py`, `src/quantum_runtime/intent/parser.py`, `src/quantum_runtime/intent/planner.py`, `src/quantum_runtime/qspec/model.py`, `src/quantum_runtime/qspec/semantics.py`, `src/quantum_runtime/reporters/writer.py`, `src/quantum_runtime/workspace/trace.py`, `src/quantum_runtime/runtime/resolve.py`
- Why fragile: `git status --short` shows 23 modified and 8 untracked paths, including new or changed files across backend, planner, QSpec, writer, and workspace logic. The map reflects live code, but line-level details are subject to drift while parallel agents continue editing.
- Safe modification: re-check `git status --short` and targeted diffs before editing any file listed above, and avoid assuming the current concern map matches the eventual post-refresh merge state line-for-line.
- Test coverage: not applicable. This is a repository-state caveat rather than a feature test gap.

## Scaling Limits

**A workspace supports one active writer, with the exec lock held across the full runtime pipeline:**
- Current capacity: one active `qrun exec` per workspace.
- Limit: `src/quantum_runtime/runtime/executor.py` acquires the workspace lock before reserving the new revision and keeps it through simulation, artifact emission, report writing, event-log promotion, and alias updates. `tests/test_runtime_workspace_safety.py` confirms the practical outcome: one winner and one `WorkspaceConflictError`.
- Scaling path: move expensive generation and diagnostics into per-run staging directories, then hold the workspace lock only for the final revision reservation and alias/manifest promotion step.

**Observability and packaging cost grows with workspace age, not just with the selected revision:**
- Current capacity: acceptable for short-lived local workspaces with small `events.jsonl` and `trace/events.ndjson` files.
- Limit: long-lived workspaces pay increasingly more for exec-log promotion and pack generation because those flows rescan or rewrite full log files.
- Scaling path: use revision-scoped event shards as the primary source of truth and add log compaction/indexing for the latest aliases.

## Dependencies at Risk

**Default CI does not exercise the Classiq integration path:**
- Risk: `.github/workflows/classiq.yml` runs only via `workflow_dispatch` and only when the `run_classiq` boolean input is set. The default `.github/workflows/ci.yml` job ignores `tests/test_classiq_backend.py` and `tests/test_classiq_emitter.py`.
- Impact: Classiq regressions can merge while the default green build still looks healthy, even though Classiq remains a supported backend in `src/quantum_runtime/backends/classiq_backend.py`.
- Migration plan: add scheduled or pre-release Classiq runs, or add mocked contract tests for the Classiq code path into the default CI lane.

**Runtime dependencies are broad-spec in `pyproject.toml`, but CI installs from live indexes instead of a frozen lock:**
- Risk: `pyproject.toml` leaves `pydantic`, `typer`, `qiskit`, and `qiskit-aer` effectively open-ended, and `.github/workflows/ci.yml` uses `python -m pip install -e '.[dev]'` or `-e '.[dev,qiskit]'` instead of `uv sync --frozen`.
- Impact: upstream dependency releases can change behavior or break builds even when the repository lockfile in `uv.lock` has not changed.
- Migration plan: use `uv sync --frozen` in CI, or add upper bounds and a lockfile-enforced install path for release-critical jobs.

## Missing Critical Features

**There is no automated hygiene gate for conflict-copy artifacts in tracked Python paths:**
- Problem: the repo allows `-NSConflict-` Python files to sit under `src/` and `tests/` with no pre-commit or CI guard to block them.
- Blocks: reliable local test collection, confidence in package contents, and clean release branches when conflict copies are accidentally introduced during merges.

**There is no shared revision-identifier validator across all CLI entry points:**
- Problem: `src/quantum_runtime/runtime/imports.py` enforces `rev_000001`-style revision IDs for report-history imports, but `src/quantum_runtime/cli.py` `pack` and `src/quantum_runtime/runtime/pack.py` accept arbitrary revision strings.
- Blocks: consistent safety guarantees across the control plane, especially for commands that construct filesystem paths directly from revision input.

## Test Coverage Gaps

**Pack input validation and destructive rerun behavior are not covered:**
- What's not tested: malformed `--revision` values, path-escape attempts, repacking an existing revision after partial failure, and compatibility-backfill failure cases.
- Files: `src/quantum_runtime/cli.py`, `src/quantum_runtime/runtime/pack.py`, `tests/test_pack_bundle.py`
- Risk: destructive path handling bugs can regress without tripping the existing pack tests.
- Priority: High

**The default CI signal excludes validation-critical suites and has no coverage gate:**
- What's not tested: `tests/test_qspec_validation.py`, `tests/test_classiq_backend.py`, and `tests/test_classiq_emitter.py` in the main GitHub Actions pipeline. `pyproject.toml` also excludes `tests/test_qspec_validation.py` from Ruff via `extend-exclude`.
- Files: `.github/workflows/ci.yml`, `.github/workflows/classiq.yml`, `pyproject.toml`, `tests/test_qspec_validation.py`, `tests/test_classiq_backend.py`, `tests/test_classiq_emitter.py`
- Risk: core QSpec validation or optional-backend regressions can bypass the main green build and land without strong automated warning.
- Priority: High

**Workspace log growth and dirty-worktree hygiene are not exercised directly:**
- What's not tested: the growth behavior of `append_trace_log()`, pack behavior against large event histories, and automated detection of conflict-copy files under `src/` and `tests/`.
- Files: `src/quantum_runtime/workspace/trace.py`, `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/runtime/pack.py`
- Risk: performance cliffs and packaging/test-discovery surprises appear late, after workspaces or branches have already accumulated enough history or merge debris.
- Priority: Medium

---

*Concerns audit: 2026-04-14*
