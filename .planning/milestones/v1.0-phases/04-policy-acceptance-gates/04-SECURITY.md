---
phase: 04
slug: policy-acceptance-gates
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-14T12:39:19Z
---

# Phase 04 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| local shell -> repo validation commands | Contributors and agents rely on local verification commands to prove policy-gate changes are safe before they become durable workflow guidance. | local executable paths, lint/type/test verdicts |
| saved workspace baseline -> current revision compare result | Baseline state is treated as approved evidence for compare gating decisions. | revision metadata, workload/report integrity summaries |
| saved baseline benchmark history -> current benchmark policy decision | Benchmark policy decisions depend on persisted benchmark history rather than ad hoc shell math. | benchmark metrics, backend status, source revision metadata |
| doctor findings -> CI verdict | Existing workspace and dependency findings are projected into machine-readable CI pass/fail behavior. | blocking/advisory issue lists, verdict, gate metadata |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-04-01-01 | T | `scripts/dev-bootstrap.sh` verification path | mitigate | Use `./.venv/bin/python -m mypy src` so local verification does not depend on the broken direct MyPy launcher. | closed |
| T-04-01-02 | R | contributor validation workflow | accept | Accepted risk: contributor-facing docs and the one-shot verifier are temporarily misaligned; tracked as a documented workflow integrity risk until the script and docs are reconciled. | closed |
| T-04-02-01 | T | baseline/current compare policy activation | mitigate | Keep compare policy activation explicit in `compare_command()` via CLI flags and baseline-mode delegation. | closed |
| T-04-02-02 | T/R | persisted compare JSON | mitigate | Persist compare artifacts through `ensure_schema_payload()` so durable compare evidence matches the CLI JSON contract. | closed |
| T-04-03-01 | S/T | baseline benchmark evidence loading | mitigate | Load saved baseline benchmark history explicitly and fail closed with `baseline_benchmark_missing` when it is absent. | closed |
| T-04-03-02 | T | benchmark policy evaluation | mitigate | Enforce subject/backend/comparability/status checks before threshold math and emit stable benchmark-specific reason codes. | closed |
| T-04-03-03 | R | imported-revision benchmark persistence | mitigate | Persist `source_kind` and `source_revision` and key benchmark history by the evaluated revision. | closed |
| T-04-04-01 | T | doctor blocking/advisory classification | mitigate | Reuse the existing `issues` versus `advisories` split and project it into CI-facing fields. | closed |
| T-04-04-02 | R | `doctor --ci` JSON and JSONL output | mitigate | Build the CI payload through the shared policy envelope so JSON and JSONL describe the same blocking state. | closed |
| T-04-04-03 | D | doctor shell-level CI behavior | mitigate | Use verdict-driven exit mapping only when `--ci` is requested, preserving legacy doctor behavior otherwise. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-04-01 | T-04-01-02 | `CONTRIBUTING.md` advertises `./scripts/dev-bootstrap.sh verify` as the same Phase 4 repo-local gate, but the script currently runs full `pytest -q` and the one-shot path can fail early on local interpreter issues. The phase's core compare/benchmark/doctor policy mitigations were verified and UAT passed, so this workflow-integrity gap is accepted temporarily rather than blocking the entire phase. | user (via `/gsd-secure-phase 4`) | 2026-04-14 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-14 | 10 | 10 | 0 | Codex + `gsd-security-auditor` |
| 2026-04-14 | 10 | 10 | 0 | Codex re-audit |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-14
