# Codebase Concerns

**Analysis Date:** 2026-04-12

## Tech Debt

**Runtime orchestration is concentrated in a few large, overlapping modules:**
- Issue: command parsing, control-plane policy, and execution side effects are spread across `src/quantum_runtime/cli.py`, `src/quantum_runtime/runtime/control_plane.py`, and `src/quantum_runtime/runtime/executor.py`. Backend selection logic is duplicated in `src/quantum_runtime/cli.py` and `src/quantum_runtime/runtime/control_plane.py`.
- Files: `src/quantum_runtime/cli.py`, `src/quantum_runtime/runtime/control_plane.py`, `src/quantum_runtime/runtime/executor.py`
- Impact: changes to `plan`, `bench`, `exec`, `show`, and exit-code behavior can drift apart; safe refactoring cost is high because one feature change crosses multiple layers.
- Fix approach: move backend selection and runtime service logic into one shared module, keep `cli.py` focused on argument parsing and output formatting, and split execution/report-writing into smaller service units.

**Static typing is part of the documented verification gate but is currently failing:**
- Issue: `PYTHONPATH=src ./.venv/bin/python -m mypy src` fails with 7 errors in active runtime code, including `src/quantum_runtime/runtime/control_plane.py:223`, `src/quantum_runtime/runtime/control_plane.py:442`, `src/quantum_runtime/runtime/run_manifest.py:188`, and `src/quantum_runtime/runtime/pack.py:217`.
- Files: `src/quantum_runtime/runtime/control_plane.py`, `src/quantum_runtime/runtime/run_manifest.py`, `src/quantum_runtime/runtime/pack.py`, `.github/workflows/ci.yml`, `scripts/dev-bootstrap.sh`
- Impact: the stated CI and local verification contract is red on current code, so typed interfaces around manifests, schema generation, and status reporting cannot be trusted during refactors.
- Fix approach: clear the current `mypy` errors first, then keep `mypy src` green in both `.github/workflows/ci.yml` and `scripts/dev-bootstrap.sh`.

## Known Bugs

**`WorkspaceManager.init_workspace()` misreports whether a workspace was newly created:**
- Symptoms: direct callers get `created=True` even when reopening an existing workspace, because `src/quantum_runtime/workspace/manager.py:54-61` checks filesystem existence after `load_or_init()` has already created or loaded the workspace. The CLI compensates by mutating the result in `src/quantum_runtime/cli.py:183-185`.
- Files: `src/quantum_runtime/workspace/manager.py`, `src/quantum_runtime/cli.py`, `tests/test_workspace_manager.py`, `tests/test_cli_init.py`
- Trigger: call `WorkspaceManager.init_workspace()` against an already initialized workspace.
- Workaround: determine existence before calling `WorkspaceManager.init_workspace()`, or use `qrun init --json`, which patches the field in the CLI layer.

**The documented local verify flow currently fails before completion:**
- Symptoms: `scripts/dev-bootstrap.sh verify` runs `mypy src` at `scripts/dev-bootstrap.sh:100-104`, and that command currently fails on runtime code. The same check is part of the GitHub Actions lint job at `.github/workflows/ci.yml:25-29`.
- Files: `scripts/dev-bootstrap.sh`, `.github/workflows/ci.yml`, `src/quantum_runtime/runtime/control_plane.py`, `src/quantum_runtime/runtime/run_manifest.py`, `src/quantum_runtime/runtime/pack.py`
- Trigger: run `./scripts/dev-bootstrap.sh verify`, `./scripts/dev-bootstrap.sh all`, or the lint job defined in `.github/workflows/ci.yml`.
- Workaround: use `PYTHONPATH=src ./.venv/bin/python -m ruff check src tests` and `PYTHONPATH=src ./.venv/bin/python -m pytest -q` until the `mypy` errors are fixed.

## Security Considerations

**`qrun pack --revision` accepts unchecked path input and can escape the workspace root:**
- Risk: `src/quantum_runtime/cli.py:852-882` passes raw `--revision` input into `src/quantum_runtime/runtime/pack.py:73-156`, where the value is used in `paths.pack_revision_dir(revision)`, history filenames, and `shutil.rmtree(pack_root)` without validating a `rev_000001`-style format. A revision like `../../outside` can redirect deletion and writes outside `packs/`.
- Files: `src/quantum_runtime/cli.py`, `src/quantum_runtime/runtime/pack.py`
- Current mitigation: not detected in the pack flow. Revision validation exists in `src/quantum_runtime/runtime/imports.py` for `resolve_report_revision()`, but `pack_revision()` does not use it.
- Recommendations: validate `revision` in both `pack_command()` and `pack_revision()`, reject path separators, resolve the destination, and assert it stays under `WorkspacePaths.packs_dir` before any delete or write.

**The Classiq backend executes generated Python from a workspace file:**
- Risk: `src/quantum_runtime/backends/classiq_backend.py:146-150` calls `exec(compile(path.read_text(), ...))` on `artifacts/classiq/main.py`. The emitter in `src/quantum_runtime/lowering/classiq_emitter.py` generates the file, but the runtime trusts the on-disk contents at execution time. A tampered file or symlinked workspace path can execute arbitrary Python in-process.
- Files: `src/quantum_runtime/backends/classiq_backend.py`, `src/quantum_runtime/lowering/classiq_emitter.py`
- Current mitigation: the emitter only supports a narrow validated QSpec subset, and Classiq execution is optional.
- Recommendations: execute the in-memory emitted source instead of rereading from disk, reject symlinks, verify the file hash and resolved path before execution, or isolate the Classiq run in a subprocess/sandbox.

## Performance Bottlenecks

**Local simulation does repeated exponential work per parameter point:**
- Problem: `src/quantum_runtime/diagnostics/simulate.py:35-68` computes a `Statevector` for every parameter point, then still transpiles and runs an `AerSimulator` for the representative circuit. `src/quantum_runtime/runtime/executor.py:284-347` always runs simulation, resource estimation, diagrams, and transpile validation serially in the main execution path.
- Files: `src/quantum_runtime/diagnostics/simulate.py`, `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/qspec/parameter_workflow.py`
- Cause: diagnostics are synchronous and uncached, and exact statevector evaluation is the default. Sweep grids are capped at 16 points in `src/quantum_runtime/qspec/parameter_workflow.py:11-12`, but there is no qubit-count guard.
- Improvement path: add width/depth guardrails before exact evaluation, make expensive diagnostics opt-in, cache built circuits for reused parameter sets, and offer a sampled or summary-only mode for larger workloads.

**Pack generation rescans the whole event log on every bundle build:**
- Problem: `src/quantum_runtime/runtime/pack.py:159-174` reads the full `events.jsonl` or `trace/events.ndjson` file, filters it in memory, then rewrites a bundle-local `events.jsonl`.
- Files: `src/quantum_runtime/runtime/pack.py`
- Cause: event history is append-only NDJSON with no per-revision index or streaming filter.
- Improvement path: stream the source file line-by-line, or persist per-revision event shards while events are appended so `pack` stays proportional to the selected revision instead of total workspace history.

## Fragile Areas

**Workspace mutation assumes one writer but does not enforce one:**
- Files: `src/quantum_runtime/workspace/manager.py`, `src/quantum_runtime/workspace/manifest.py`, `src/quantum_runtime/workspace/trace.py`, `src/quantum_runtime/runtime/executor.py`, `src/quantum_runtime/reporters/writer.py`
- Why fragile: revision reservation in `src/quantum_runtime/workspace/manager.py:41-45`, trace appends in `src/quantum_runtime/workspace/trace.py:38-60`, and current/history artifact writes in `src/quantum_runtime/runtime/executor.py:270-438` are plain filesystem writes with no lock, transaction, or atomic rename strategy.
- Safe modification: add a workspace lock before mutating revision/current files, use temp-file-plus-rename writes for `workspace.json`, `reports/latest.json`, `specs/current.json`, and `manifests/latest.json`, and add explicit conflict handling for concurrent runs.
- Test coverage: `tests/test_workspace_manager.py` covers creation and a single append path, but there is no concurrent writer coverage.

**Replay integrity and comparison logic is central, stateful, and easy to destabilize:**
- Files: `src/quantum_runtime/runtime/imports.py`, `src/quantum_runtime/runtime/compare.py`, `src/quantum_runtime/runtime/run_manifest.py`, `tests/test_runtime_imports.py`, `tests/test_cli_compare.py`
- Why fragile: this path handles current workspace inputs, historical revisions, copied reports, relocated workspaces, manifest integrity, replay hashes, and compare policy gating. The fallback matrix is large and a small path change can silently alter trust semantics.
- Safe modification: only change this area with end-to-end tests for copied reports, tampered manifests, history/current fallbacks, hash mismatches, and compare policy outcomes.
- Test coverage: `tests/test_runtime_imports.py` and `tests/test_cli_compare.py` are strong, but `src/quantum_runtime/runtime/run_manifest.py` has no dedicated unit test file.

## Scaling Limits

**A workspace currently scales to one active writer, not to many agents:**
- Current capacity: effectively one `qrun exec`, `qrun bench`, `qrun compare`, or `qrun doctor` writer per workspace.
- Limit: parallel agent or CI runs can race on `workspace.json`, `specs/current.json`, `reports/latest.json`, `manifests/latest.json`, `artifacts/*/main.*`, and `events.jsonl`.
- Scaling path: enforce workspace-level locking or move to per-run working directories with a controlled promotion step for current aliases and manifests.

**Parameterized local evaluation is intentionally small and will hit local-memory limits first:**
- Current capacity: sweep grids stop at 16 points in `src/quantum_runtime/qspec/parameter_workflow.py:11-12`, and all evaluation still uses local `Statevector` and `AerSimulator` code in `src/quantum_runtime/diagnostics/simulate.py`.
- Limit: wider circuits are bounded by local CPU and memory instead of by an explicit runtime guardrail, so failures will show up as latency spikes or simulation errors rather than a clear up-front refusal.
- Scaling path: add explicit qubit/depth thresholds before simulation starts, and offer remote or approximate evaluation modes for larger circuits.

## Dependencies at Risk

**`classiq` support is outside the default CI contract:**
- Risk: the default CI pipeline skips Classiq coverage, and the dedicated Classiq workflow only runs when manually triggered.
- Impact: regressions in optional backend behavior can ship without blocking merges, even though the backend is wired into `exec` and `bench`.
- Migration plan: add scheduled or pre-release Classiq runs, or add mocked contract tests that exercise the Classiq code path without the real SDK.

**Default CI excludes a core QSpec validation test file:**
- Risk: `.github/workflows/ci.yml:45-46` skips `tests/test_qspec_validation.py` in the main pytest job, even though `validate_qspec()` sits on the main resolve/plan/exec path.
- Impact: semantic validation regressions can land while the default CI stays green.
- Migration plan: bring `tests/test_qspec_validation.py` back into the default CI run, or split only the genuinely optional/flaky cases into a separate job.

## Missing Critical Features

**There is no concurrency-safe workspace transaction layer:**
- Problem: the product is positioned as agent-first and CI-friendly, but the write path does not include locking, atomic commits of related files, or recovery for partially written revisions.
- Blocks: safe shared-workspace usage by multiple agents, robust background execution, and reliable promotion of “latest” aliases under failure.

## Test Coverage Gaps

**Pack input validation is not exercised beyond happy-path bundle shape checks:**
- What's not tested: malicious or malformed `--revision` values for `qrun pack`. `tests/test_pack_bundle.py` only validates `inspect_pack_bundle()` against a prebuilt directory and missing manifest case.
- Files: `src/quantum_runtime/runtime/pack.py`, `src/quantum_runtime/cli.py`, `tests/test_pack_bundle.py`
- Risk: the path traversal bug in `pack_revision()` can ship unnoticed because there is no regression test around user-controlled revision input.
- Priority: High

**Several core helpers only have indirect coverage:**
- What's not tested: dedicated unit tests for `src/quantum_runtime/runtime/resolve.py`, `src/quantum_runtime/runtime/run_manifest.py`, `src/quantum_runtime/workspace/paths.py`, and failure/concurrency behavior in `src/quantum_runtime/workspace/trace.py`.
- Files: `src/quantum_runtime/runtime/resolve.py`, `src/quantum_runtime/runtime/run_manifest.py`, `src/quantum_runtime/workspace/paths.py`, `src/quantum_runtime/workspace/trace.py`
- Risk: serialization/path invariant regressions can hide behind broad CLI tests and appear only after release or in cross-workspace replay scenarios.
- Priority: Medium

**Default CI does not cover all validation-critical paths:**
- What's not tested: `tests/test_classiq_backend.py`, `tests/test_classiq_emitter.py`, and `tests/test_qspec_validation.py` are outside the default GitHub Actions pytest job.
- Files: `.github/workflows/ci.yml`, `.github/workflows/classiq.yml`, `tests/test_classiq_backend.py`, `tests/test_classiq_emitter.py`, `tests/test_qspec_validation.py`
- Risk: backend-specific or semantic validation regressions can bypass the main green build signal.
- Priority: High

---

*Concerns audit: 2026-04-12*
