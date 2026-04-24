---
phase: 04-policy-acceptance-gates
verified: 2026-04-16T01:16:06Z
status: passed
score: 12/12 must-haves verified
overrides_applied: 0
---

# Phase 4: Policy Acceptance Gates Verification Report

**Phase Goal:** Agents and CI can accept or reject runtime revisions directly from FluxQ policy surfaces.
**Verified:** 2026-04-16T01:16:06Z
**Status:** passed
**Re-verification:** Yes - refreshed after the Phase 08 gate-contract reconciliation

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Agent or CI can compare a revision against baseline state and fail on selected drift classes using FluxQ output and exit behavior alone. | ✓ VERIFIED | `compare_command()` builds `ComparePolicy` only from CLI flags and baseline mode delegates to `compare_workspace_baseline()` (`src/quantum_runtime/cli.py:1461-1510`); `compare_workspace_baseline()` resolves baseline/current and returns a populated `baseline` block (`src/quantum_runtime/runtime/compare.py:110-133`); manual CLI smoke returned `exit_code=2`, `verdict=fail`, `failed_checks=["subject_drift"]`, `gate_ready=false`; regression coverage at `tests/test_cli_compare.py:811-876` and `tests/test_cli_runtime_gap.py:119-170`. |
| 2 | Agent or CI can use benchmark results as policy evidence, including compare-to-baseline flows, without custom wrapper logic. | ✓ VERIFIED | `bench_command()` builds `BenchmarkPolicy` from explicit flags, loads saved baseline benchmark evidence, applies `apply_benchmark_policy()`, persists the augmented report, and exits through `exit_code_for_benchmark()` (`src/quantum_runtime/cli.py:879-987`); the refreshed exact Phase 4 suite passed with `70 passed in 10.70s`, including `tests/test_cli_bench.py:266-367` and `tests/test_runtime_policy.py:41-84`. |
| 3 | Agent or CI can run doctor in CI-oriented mode and receive explicit blocking versus advisory outcomes in machine-readable form. | ✓ VERIFIED | `doctor_command()` exposes `--ci`, threads it into `run_doctor()`, emits CI-enriched JSON/JSONL, and uses verdict-driven exits (`src/quantum_runtime/cli.py:1591-1642`); `run_doctor(ci=True)` applies `DoctorPolicy` before persistence/output (`src/quantum_runtime/runtime/doctor.py:98-122`); manual CLI smoke returned `exit_code=2`, `blocking_issues=["active_report_missing"]`, `gate_ready=false`; regression coverage at `tests/test_cli_doctor.py:126-228`. |
| 4 | The exact Phase 4 repo-local gate is the canonical proof path for the targeted policy-gate pytest files, and it is clearly distinguished from the broader repo smoke command. | ✓ VERIFIED | The canonical gate is `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_cli_observability.py tests/test_runtime_policy.py -q --maxfail=1`, which passed on refresh with `70 passed in 10.70s`. `CONTRIBUTING.md:22-38` now names that exact Phase 4 gate explicitly and includes `tests/test_runtime_policy.py`, while `scripts/dev-bootstrap.sh:19-20,104-108` describes `./scripts/dev-bootstrap.sh verify` as the broader repo smoke command running `qrun version`, Ruff, module-form MyPy, and full `pytest -q`, not as equivalent proof for `POLC-01`, `POLC-02`, or `POLC-03`. |
| 5 | Local verification still works when `./.venv/bin/mypy` is unusable under the current workspace path, because the repo runs MyPy through `./.venv/bin/python -m mypy`. | ✓ VERIFIED | `scripts/dev-bootstrap.sh:100-105` explicitly probes the broken direct launcher and falls back to `"$ROOT_DIR/.venv/bin/python" -m mypy src`; live run logged “Direct MyPy launcher failed...” and completed `mypy` successfully. |
| 6 | Phase 4 plans no longer rely on pytest-only verification; lint and type checks are part of the owned validation path. | ✓ VERIFIED | `scripts/dev-bootstrap.sh:97-105` runs Ruff then module-form MyPy before pytest, and `CONTRIBUTING.md:22-33` documents repo-local Ruff/MyPy/pytest usage; live runs returned `All checks passed!` for Ruff and `Success: no issues found in 54 source files` for MyPy. |
| 7 | Persisted compare artifacts under `.quantum/compare/` remain schema-versioned machine output, not CLI-only payloads. | ✓ VERIFIED | `persist_compare_result()` serializes `ensure_schema_payload(result)` before writing `compare/latest.json` and `compare/history/*.json` (`src/quantum_runtime/runtime/compare.py:251-269`); `tests/test_cli_compare.py:878-934` pins `schema_version == "0.3.0"` on both persisted files. |
| 8 | Baseline/current compare policy activation stays explicit through CLI flags instead of silently consuming `QSpec.runtime.policy_hints`. | ✓ VERIFIED | `compare_command()` only constructs policy from `--expect`, `--fail-on`, `--allow-report-drift`, `--forbid-backend-regressions`, and `--forbid-replay-integrity-regressions` (`src/quantum_runtime/cli.py:1461-1475`); repository grep found no `policy_hints` consumption in compare/benchmark/doctor CLI/runtime paths, only in golden fixtures. |
| 9 | Benchmark gating fails closed on subject mismatch, missing baseline benchmark evidence, incomparable backends, and forbidden status regressions before threshold math runs. | ✓ VERIFIED | `apply_benchmark_policy()` checks subject identity, missing baseline backends, comparability, and status regressions before metric thresholds (`src/quantum_runtime/runtime/policy.py:175-303`), while `bench_command()` fails with `_json_error("baseline_benchmark_missing")` if saved baseline evidence is absent (`src/quantum_runtime/cli.py:921-944`); direct regression coverage exists for subject mismatch, missing baseline evidence, and threshold failure at `tests/test_runtime_policy.py:41-84` and `tests/test_cli_bench.py:266-367`. |
| 10 | Benchmark history and persisted report metadata identify the revision that was actually benchmarked, even when the benchmark source is an imported report or historical revision. | ✓ VERIFIED | `run_structural_benchmark()` threads `source_kind`/`source_revision` through the report (`src/quantum_runtime/diagnostics/benchmark.py:63-76,225-226`), and `persist_benchmark_report()` keys history writes to the evaluated revision (`src/quantum_runtime/diagnostics/benchmark.py:358-387`); `bench_command()` persists using `benchmark.source_revision` (`src/quantum_runtime/cli.py:976-981`); regression coverage at `tests/test_cli_bench.py:230-263`. |
| 11 | Advisory-only doctor CI results exit `0`, while blocking doctor CI findings exit `2`, without changing the existing non-`--ci` command behavior. | ✓ VERIFIED | `exit_code_for_doctor()` is verdict-first only when a CI verdict exists and falls back to legacy workspace/dependency mapping otherwise (`src/quantum_runtime/runtime/exit_codes.py:64-76`); `tests/test_cli_doctor.py:126-137` pins advisory-only `--ci` pass, `tests/test_cli_doctor.py:189-228` pins blocking `--ci` failure, and `tests/test_cli_doctor.py:173-186` keeps non-`--ci` dependency behavior at exit 7. |
| 12 | The final `doctor_completed` JSONL payload carries the same blocking/advisory decision data as the JSON payload. | ✓ VERIFIED | `doctor_command()` emits `doctor_completed` with `report.model_dump(mode="json", exclude_none=not ci)` after policy application (`src/quantum_runtime/cli.py:1638-1640`); `tests/test_cli_observability.py:390-421` asserts `blocking_issues`, `advisory_issues`, `verdict`, and `gate` are present in the final JSONL payload. |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `scripts/dev-bootstrap.sh` | Truthful broader repo smoke command for `qrun version`, Ruff, MyPy, and full pytest | ✓ VERIFIED | 152 lines. Substantive `verify_project()` implementation uses module-form MyPy fallback and now describes `verify` as the broader smoke path rather than the exact Phase 4 gate (`scripts/dev-bootstrap.sh:19-20,89-109`). |
| `CONTRIBUTING.md` | Documented exact Phase 4 gate plus truthful guidance for the broader local smoke path | ✓ VERIFIED | 68 lines. Documents the exact repo-local Phase 4 command sequence, including `tests/test_runtime_policy.py`, and explicitly distinguishes it from `./scripts/dev-bootstrap.sh verify` (`CONTRIBUTING.md:22-38`). |
| `src/quantum_runtime/runtime/compare.py` | Schema-versioned compare persistence for latest/history outputs | ✓ VERIFIED | 904 lines. `compare_workspace_baseline()`, `compare_import_resolutions()`, and `persist_compare_result()` are substantive and wired (`src/quantum_runtime/runtime/compare.py:110-269`). |
| `src/quantum_runtime/cli.py` | Explicit compare, benchmark, and doctor policy surfaces | ✓ VERIFIED | 1667 lines. Contains `bench`, `compare`, and `doctor` command surfaces with explicit flag-driven policy activation and verdict-driven exits (`src/quantum_runtime/cli.py:784-1004,1440-1642`). |
| `src/quantum_runtime/runtime/policy.py` | Shared benchmark/doctor policy primitives | ✓ VERIFIED | 422 lines. Provides `PolicyVerdict`, `BenchmarkPolicy`, `DoctorPolicy`, `apply_benchmark_policy()`, and `apply_doctor_policy()` with substantive fail-closed logic (`src/quantum_runtime/runtime/policy.py:27-422`). |
| `src/quantum_runtime/diagnostics/benchmark.py` | Policy-bearing benchmark reports with source provenance | ✓ VERIFIED | 422 lines. `BenchmarkReport` includes policy envelope fields and provenance, and persistence keys history to the evaluated revision (`src/quantum_runtime/diagnostics/benchmark.py:45-60,358-387`). |
| `src/quantum_runtime/runtime/doctor.py` | Policy-bearing doctor reports with explicit blocking and advisory fields | ✓ VERIFIED | 332 lines. `DoctorReport` now carries CI fields and `run_doctor()` applies CI policy before persistence/output (`src/quantum_runtime/runtime/doctor.py:28-122`). |
| `tests/test_cli_compare.py` | Baseline/current compare regressions and compare persistence shape | ✓ VERIFIED | 1127 lines. Contains substantive baseline fail-on and persisted compare artifact checks (`tests/test_cli_compare.py:811-934`). |
| `tests/test_cli_runtime_gap.py` | Explicit compare fail-on exit-code regression | ✓ VERIFIED | 469 lines. Pins left/right compare `--fail-on` exit 2 behavior (`tests/test_cli_runtime_gap.py:119-170`). |
| `tests/test_cli_bench.py` | Benchmark baseline gating and imported-revision persistence coverage | ✓ VERIFIED | 616 lines. Covers missing baseline evidence, metric failures, and provenance-safe history writes (`tests/test_cli_bench.py:230-367`). |
| `tests/test_cli_doctor.py` | Advisory-only and blocking `doctor --ci` regressions | ✓ VERIFIED | 349 lines. Covers advisory pass, blocking failure, and legacy non-`--ci` behavior (`tests/test_cli_doctor.py:126-228`). |
| `tests/test_cli_observability.py` | JSONL completion payload coverage for benchmark/doctor gates | ✓ VERIFIED | 421 lines. Pins policy-bearing `benchmark_completed` and `doctor_completed` payloads (`tests/test_cli_observability.py:349-421`). |
| `tests/test_runtime_policy.py` | Unit coverage for benchmark and doctor policy evaluators | ✓ VERIFIED | 107 lines. Substantive unit coverage for benchmark subject/metric failures and doctor issue projection (`tests/test_runtime_policy.py:41-107`). |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `scripts/dev-bootstrap.sh` | `.venv/bin/python` | Module-form MyPy invocation that avoids the broken launcher path | ✓ WIRED | `scripts/dev-bootstrap.sh:100-105` probes the broken launcher and always runs `"$ROOT_DIR/.venv/bin/python" -m mypy src`. |
| `CONTRIBUTING.md` | `scripts/dev-bootstrap.sh` | Matching wording for the exact Phase 4 gate versus the broader repo smoke command | ✓ WIRED | `CONTRIBUTING.md:22-38` names the exact Phase 4 gate and explicitly says `./scripts/dev-bootstrap.sh verify` is broader full local smoke, while `scripts/dev-bootstrap.sh:19-20,104-108` describes that same broader smoke path and its full `pytest -q` scope. |
| `src/quantum_runtime/cli.py` | `src/quantum_runtime/runtime/compare.py` | Baseline mode delegates to compare baseline/current evaluation with explicit CLI policy flags | ✓ WIRED | `src/quantum_runtime/cli.py:1483-1510` delegates baseline mode to `compare_workspace_baseline()`. |
| `src/quantum_runtime/runtime/compare.py` | `src/quantum_runtime/runtime/contracts.py` | Schema-versioned JSON persistence | ✓ WIRED | `src/quantum_runtime/runtime/compare.py:257` serializes `ensure_schema_payload(result)` from `runtime/contracts.py:140-150`; `gsd-tools` false-negatived this because the stored regex is invalid. |
| `src/quantum_runtime/cli.py` | `src/quantum_runtime/runtime/policy.py` | Explicit benchmark flags build `BenchmarkPolicy` and evaluate against saved baseline evidence | ✓ WIRED | `src/quantum_runtime/cli.py:879-980` builds the policy, loads baseline evidence, and calls `apply_benchmark_policy()`. |
| `src/quantum_runtime/diagnostics/benchmark.py` | `.quantum/benchmarks/history/<revision>.json` | Persistence keyed to the evaluated source revision | ✓ WIRED | `persist_benchmark_report()` writes `benchmarks/history/<revision>.json` from the `revision` argument and `bench_command()` passes `benchmark.source_revision` (`src/quantum_runtime/diagnostics/benchmark.py:358-387`, `src/quantum_runtime/cli.py:976-981`). |
| `src/quantum_runtime/cli.py` | `src/quantum_runtime/runtime/doctor.py` | `--ci` flag threads into `run_doctor(ci=True)` | ✓ WIRED | `src/quantum_runtime/cli.py:1627-1632` passes `ci=ci` into `run_doctor()`; `gsd-tools` false-negatived this because the stored regex is invalid. |
| `src/quantum_runtime/runtime/doctor.py` | `src/quantum_runtime/runtime/policy.py` | Doctor CI mode projects existing findings into the shared policy envelope | ✓ WIRED | `src/quantum_runtime/runtime/doctor.py:107-111` calls `apply_doctor_policy()` from `runtime/policy.py:81-135`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `src/quantum_runtime/runtime/compare.py` | `serialized` compare payload | `CompareResult` -> `ensure_schema_payload(result)` -> `compare/latest.json` and `compare/history/*.json` | Yes | ✓ FLOWING |
| `src/quantum_runtime/cli.py` (`bench_command`) | `benchmark` policy-bearing report | `run_structural_benchmark()` -> optional `_load_saved_baseline_benchmark()` -> `apply_benchmark_policy()` -> `persist_benchmark_report()` | Yes | ✓ FLOWING |
| `src/quantum_runtime/diagnostics/benchmark.py` | `source_kind` / `source_revision` | `bench_command` import resolution or current manifest -> `BenchmarkReport` -> `benchmarks/history/<source_revision>.json` | Yes | ✓ FLOWING |
| `src/quantum_runtime/runtime/doctor.py` | `blocking_issues`, `advisory_issues`, `verdict`, `gate` | Raw `issues`/`advisories` -> `apply_doctor_policy()` -> persisted `DoctorReport` -> CLI JSON/JSONL | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Phase 4 targeted validation gate passes | `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_runtime_gap.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_cli_observability.py tests/test_runtime_policy.py -q --maxfail=1` | `All checks passed!`, `Success: no issues found in 54 source files`, `70 passed in 10.70s` | ✓ PASS |
| Baseline compare policy fails with FluxQ-native gate output | Ad hoc `qrun exec -> qrun baseline set -> qrun exec -> qrun compare --baseline --fail-on subject_drift --json` | `exit_code=2`, `verdict=fail`, `failed_checks=["subject_drift"]`, `gate_ready=false`, `baseline_revision="rev_000001"` | ✓ PASS |
| Doctor CI blocking path fails with machine-readable blocking/advisory fields | Ad hoc `qrun exec -> remove reports/latest.json -> qrun doctor --ci --json` | `exit_code=2`, `verdict=fail`, `blocking_issues=["active_report_missing"]`, `advisory_issues_count=1`, `gate_ready=false` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `POLC-01` | `04-02-PLAN.md` | Agent can compare current state against baseline and fail on specific drift classes without external wrapper logic | ✓ SATISFIED | Baseline compare is CLI-flag driven, delegates to `compare_workspace_baseline()`, persists schema-versioned compare artifacts, and returns exit code 2 on policy failure (`src/quantum_runtime/cli.py:1461-1553`, `src/quantum_runtime/runtime/compare.py:110-269`, `tests/test_cli_compare.py:811-934`). |
| `POLC-02` | `04-03-PLAN.md` | Agent can use benchmark results as policy evidence, including compare-to-baseline workflows | ✓ SATISFIED | `bench_command()` builds/uses `BenchmarkPolicy`, loads saved baseline benchmark evidence, persists provenance-safe benchmark reports, and exits verdict-first (`src/quantum_runtime/cli.py:879-987`, `src/quantum_runtime/runtime/policy.py:138-366`, `tests/test_cli_bench.py:230-367`). |
| `POLC-03` | `04-04-PLAN.md` | Agent can use doctor results in CI-oriented mode with clear blocking versus advisory outputs | ✓ SATISFIED | `doctor --ci` emits additive blocking/advisory fields plus verdict/gate, with JSON/JSONL parity and verdict-driven exit handling (`src/quantum_runtime/runtime/doctor.py:28-122`, `src/quantum_runtime/cli.py:1591-1642`, `tests/test_cli_doctor.py:126-228`, `tests/test_cli_observability.py:390-421`). |

No orphaned Phase 4 requirements were found. PLAN frontmatter declares exactly `POLC-01`, `POLC-02`, and `POLC-03`, and `REQUIREMENTS.md` maps those same IDs to Phase 4 (`.planning/REQUIREMENTS.md:24-26,80-82`).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| - | - | No blocker anti-patterns detected in the Phase 4 implementation files scanned | ℹ️ Info | Grep hits were limited to legitimate list/dict initializers and test expectations, not placeholders or empty user-visible implementations. |

### Disconfirmation Notes

- Scope note: `./scripts/dev-bootstrap.sh verify` remains a broader repo smoke command, so it is not Phase 4 proof and can still fail outside the phase-owned compare/benchmark/doctor scope without reopening `POLC-01`, `POLC-02`, or `POLC-03`.
- Misleading test: `tests/test_cli_observability.py:349-368` proves benchmark JSONL policy payload shape only for a passing gate; it does not show fail-case JSONL parity.
- Uncovered error path: no regression directly exercises `benchmark_backend_incomparable:*` or `benchmark_status_regressed:*` branches in `apply_benchmark_policy()` (`src/quantum_runtime/runtime/policy.py:216-262`), so those fail-closed paths rely on code inspection rather than dedicated tests.

### Human Verification Required

None. The Phase 4 surface is machine-readable CLI/runtime behavior and the critical flows were verified with targeted suites plus direct CLI spot-checks.

### Gaps Summary

No blocking gaps found.

Phase 4’s core product goal is met: compare, benchmark, and doctor all expose FluxQ-native policy surfaces, all three mapped requirements (`POLC-01`, `POLC-02`, `POLC-03`) are satisfied, and the refreshed exact Phase 4 gate passes. The canonical local proof path is now the exact Phase 4 repo-local sequence, while `./scripts/dev-bootstrap.sh verify` is documented truthfully as a broader repo smoke command rather than equivalent proof. That preserves the warning that the one-shot script can still fail outside the phase-owned scope without creating new Phase 4 blockers.

---

_Verified: 2026-04-16T01:16:06Z_  
_Verifier: Codex (gsd-verifier)_
