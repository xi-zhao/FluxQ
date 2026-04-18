"""Shared policy helpers for benchmark acceptance gating."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from quantum_runtime.diagnostics.benchmark import BenchmarkReport
from quantum_runtime.runtime.observability import gate_block, next_actions_for_reason_codes, normalize_reason_codes

if TYPE_CHECKING:
    from quantum_runtime.runtime.doctor import DoctorReport


PolicySeverity = Literal["info", "warning", "error"]

_STATUS_RANK = {
    "ok": 0,
    "dependency_missing": 1,
    "backend_unavailable": 1,
    "error": 2,
}


class PolicyVerdict(BaseModel):
    """Policy verdict for a machine-readable runtime gate."""

    status: Literal["not_requested", "pass", "fail"]
    summary: str
    failed_checks: list[str] = Field(default_factory=list)
    passed_checks: list[str] = Field(default_factory=list)


class BenchmarkPolicy(BaseModel):
    """Configurable benchmark acceptance policy."""

    baseline: bool = True
    require_comparable: bool = False
    forbid_status_regressions: bool = False
    max_width_regression: int | None = Field(default=None, ge=0)
    max_depth_regression: int | None = Field(default=None, ge=0)
    max_two_qubit_regression: int | None = Field(default=None, ge=0)
    max_measure_regression: int | None = Field(default=None, ge=0)


class DoctorPolicy(BaseModel):
    """Configurable doctor acceptance policy."""

    mode: Literal["ci"] = "ci"
    block_on_issues: bool = True


def policy_gate_payload(
    *,
    policy: BaseModel | None,
    verdict: PolicyVerdict,
    ready: bool,
    severity: PolicySeverity,
    reason_codes: list[str],
    next_actions: list[str],
) -> dict[str, object]:
    """Build the policy envelope for benchmark-like runtime payloads."""
    normalized_reason_codes = normalize_reason_codes(reason_codes)
    normalized_next_actions = normalize_reason_codes(next_actions)
    return {
        "policy": policy.model_dump(mode="json") if policy is not None else {},
        "verdict": verdict.model_dump(mode="json"),
        "reason_codes": normalized_reason_codes,
        "next_actions": normalized_next_actions,
        "gate": gate_block(
            ready=ready,
            severity=severity,
            reason_codes=normalized_reason_codes,
            next_actions=normalized_next_actions,
        ),
    }


def apply_doctor_policy(
    *,
    report: DoctorReport,
    policy: DoctorPolicy | None = None,
) -> DoctorReport:
    """Project doctor findings into a CI-friendly blocking/advisory envelope."""
    effective_policy = policy or DoctorPolicy(mode="ci", block_on_issues=True)
    raw_issues = [str(item) for item in report.issues]
    raw_advisories = [str(item) for item in report.advisories]
    blocking_issues = list(raw_issues) if effective_policy.block_on_issues else []
    advisory_issues = list(raw_advisories)
    if not effective_policy.block_on_issues:
        advisory_issues = raw_issues + advisory_issues

    report_reason_codes = normalize_reason_codes([str(code) for code in report.reason_codes or []])
    blocking_reason_codes = [_doctor_reason_code("doctor_blocking_issue", item) for item in blocking_issues]
    advisory_reason_codes = [_doctor_reason_code("doctor_advisory_issue", item) for item in advisory_issues]
    reason_codes = normalize_reason_codes(
        blocking_reason_codes + advisory_reason_codes + report_reason_codes
    )
    next_actions = _doctor_next_actions(
        blocking_issues,
        advisory_issues,
        reason_codes=reason_codes,
    )

    verdict_failed = bool(blocking_issues)
    if verdict_failed:
        verdict = PolicyVerdict(
            status="fail",
            summary="Doctor CI failed: blocking findings remain.",
            failed_checks=["doctor_blocking_issues"],
            passed_checks=["doctor_advisory_projection"],
        )
        severity: PolicySeverity = "error"
    else:
        summary = "Doctor CI passed."
        if advisory_issues:
            summary = "Doctor CI passed with advisory findings."
        verdict = PolicyVerdict(
            status="pass",
            summary=summary,
            failed_checks=[],
            passed_checks=["doctor_blocking_issues", "doctor_advisory_projection"],
        )
        severity = "info"

    envelope = policy_gate_payload(
        policy=effective_policy,
        verdict=verdict,
        ready=not verdict_failed,
        severity=severity,
        reason_codes=reason_codes,
        next_actions=next_actions,
    )
    return report.model_copy(
        update={
            "blocking_issues": blocking_issues,
            "advisory_issues": advisory_issues,
            **envelope,
        }
    )


def apply_benchmark_policy(
    *,
    report: BenchmarkReport,
    baseline_report: BenchmarkReport,
    baseline_revision: str,
    policy: BenchmarkPolicy | None,
) -> BenchmarkReport:
    """Evaluate one benchmark report against saved baseline evidence."""
    if policy is None:
        verdict = PolicyVerdict(
            status="not_requested",
            summary="No benchmark policy requested.",
        )
        envelope = policy_gate_payload(
            policy=None,
            verdict=verdict,
            ready=True,
            severity="info",
            reason_codes=[],
            next_actions=[],
        )
        return report.model_copy(
            update={
                "baseline": {
                    "revision": baseline_revision,
                    "status": baseline_report.status,
                },
                "comparison": {
                    "baseline_revision": baseline_revision,
                    "subject_match": True,
                    "checked_backends": sorted(report.backends),
                    "failed_stage": None,
                },
                **envelope,
            }
        )

    subject_match = _subject_identity(report) == _subject_identity(baseline_report)
    if not subject_match:
        return _annotate_report(
            report=report,
            baseline_report=baseline_report,
            baseline_revision=baseline_revision,
            policy=policy,
            verdict=PolicyVerdict(
                status="fail",
                summary="Benchmark policy failed: subject mismatch.",
                failed_checks=["subject_identity"],
                passed_checks=[],
            ),
            reason_codes=["benchmark_subject_changed"],
            failed_stage="subject_identity",
        )

    current_backends = sorted(report.backends)
    baseline_backends = baseline_report.backends

    missing_backends = [
        f"benchmark_backend_missing:{backend}"
        for backend in current_backends
        if backend not in baseline_backends
    ]
    if missing_backends:
        return _annotate_report(
            report=report,
            baseline_report=baseline_report,
            baseline_revision=baseline_revision,
            policy=policy,
            verdict=PolicyVerdict(
                status="fail",
                summary="Benchmark policy failed: missing baseline backend evidence.",
                failed_checks=["baseline_backend_presence"],
                passed_checks=["subject_identity"],
            ),
            reason_codes=missing_backends,
            failed_stage="baseline_backend_presence",
        )

    if policy.require_comparable:
        incomparable = [
            f"benchmark_backend_incomparable:{backend}"
            for backend in current_backends
            if not _backend_comparable(report, backend) or not _backend_comparable(baseline_report, backend)
        ]
        if incomparable:
            return _annotate_report(
                report=report,
                baseline_report=baseline_report,
                baseline_revision=baseline_revision,
                policy=policy,
                verdict=PolicyVerdict(
                    status="fail",
                    summary="Benchmark policy failed: backend comparability requirements were not met.",
                    failed_checks=["backend_comparability"],
                    passed_checks=["subject_identity", "baseline_backend_presence"],
                ),
                reason_codes=incomparable,
                failed_stage="backend_comparability",
            )

    if policy.forbid_status_regressions:
        status_regressions = [
            f"benchmark_status_regressed:{backend}"
            for backend in current_backends
            if _status_rank(report.backends[backend].status) > _status_rank(baseline_backends[backend].status)
        ]
        if status_regressions:
            return _annotate_report(
                report=report,
                baseline_report=baseline_report,
                baseline_revision=baseline_revision,
                policy=policy,
                verdict=PolicyVerdict(
                    status="fail",
                    summary="Benchmark policy failed: backend status regressed from the saved baseline.",
                    failed_checks=["status_regressions"],
                    passed_checks=[
                        "subject_identity",
                        "baseline_backend_presence",
                        "backend_comparability" if policy.require_comparable else "backend_comparability:not_required",
                    ],
                ),
                reason_codes=status_regressions,
                failed_stage="status_regressions",
            )

    metric_regressions: list[str] = []
    thresholds = {
        "width": policy.max_width_regression,
        "depth": policy.max_depth_regression,
        "two_qubit_gates": policy.max_two_qubit_regression,
        "measure_count": policy.max_measure_regression,
    }
    for backend in current_backends:
        baseline_backend = baseline_backends[backend]
        current_backend = report.backends[backend]
        for metric, allowed_regression in thresholds.items():
            if allowed_regression is None:
                continue
            current_value = getattr(current_backend, metric, None)
            baseline_value = getattr(baseline_backend, metric, None)
            if not isinstance(current_value, int) or not isinstance(baseline_value, int):
                continue
            if current_value - baseline_value > allowed_regression:
                metric_regressions.append(f"benchmark_metric_regressed:{backend}:{metric}")

    if metric_regressions:
        return _annotate_report(
            report=report,
            baseline_report=baseline_report,
            baseline_revision=baseline_revision,
            policy=policy,
            verdict=PolicyVerdict(
                status="fail",
                summary="Benchmark policy failed: one or more benchmark metrics regressed past the allowed threshold.",
                failed_checks=["metric_regressions"],
                passed_checks=[
                    "subject_identity",
                    "baseline_backend_presence",
                    "backend_comparability" if policy.require_comparable else "backend_comparability:not_required",
                    "status_regressions" if policy.forbid_status_regressions else "status_regressions:allowed",
                ],
            ),
            reason_codes=metric_regressions,
            failed_stage="metric_regressions",
        )

    return _annotate_report(
        report=report,
        baseline_report=baseline_report,
        baseline_revision=baseline_revision,
        policy=policy,
        verdict=PolicyVerdict(
            status="pass",
            summary="Benchmark policy passed.",
            failed_checks=[],
            passed_checks=[
                "subject_identity",
                "baseline_backend_presence",
                "backend_comparability" if policy.require_comparable else "backend_comparability:not_required",
                "status_regressions" if policy.forbid_status_regressions else "status_regressions:allowed",
                "metric_regressions:none",
            ],
        ),
        reason_codes=[],
        failed_stage=None,
    )


def _annotate_report(
    *,
    report: BenchmarkReport,
    baseline_report: BenchmarkReport,
    baseline_revision: str,
    policy: BenchmarkPolicy,
    verdict: PolicyVerdict,
    reason_codes: list[str],
    failed_stage: str | None,
) -> BenchmarkReport:
    next_actions = next_actions_for_reason_codes(reason_codes)
    if reason_codes and not next_actions:
        next_actions = ["review_benchmark_policy"]
    severity: PolicySeverity = "error" if verdict.status == "fail" else "info"
    ready = verdict.status != "fail"
    envelope = policy_gate_payload(
        policy=policy,
        verdict=verdict,
        ready=ready,
        severity=severity,
        reason_codes=reason_codes,
        next_actions=next_actions,
    )
    return report.model_copy(
        update={
            "baseline": {
                "revision": baseline_revision,
                "status": baseline_report.status,
                "source_kind": baseline_report.source_kind,
                "source_revision": baseline_report.source_revision,
            },
            "comparison": {
                "baseline_revision": baseline_revision,
                "subject_match": _subject_identity(report) == _subject_identity(baseline_report),
                "checked_backends": sorted(report.backends),
                "failed_stage": failed_stage,
            },
            **envelope,
        }
    )


def _backend_comparable(report: BenchmarkReport, backend: str) -> bool:
    details = report.backends[backend].details
    if not isinstance(details, dict):
        return False
    return bool(details.get("comparable"))


def _subject_identity(report: BenchmarkReport) -> str | None:
    subject = report.subject if isinstance(report.subject, dict) else {}
    workload_hash = subject.get("workload_hash")
    if isinstance(workload_hash, str) and workload_hash:
        return workload_hash
    semantic_hash = subject.get("semantic_hash")
    if isinstance(semantic_hash, str) and semantic_hash:
        return semantic_hash
    return None


def _status_rank(status: str) -> int:
    return _STATUS_RANK.get(status, 99)


def _doctor_reason_code(prefix: str, issue: str) -> str:
    return f"{prefix}:{_doctor_issue_slug(issue)}"


def _doctor_issue_slug(issue: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", str(issue).lower()).strip("_")
    return slug or "unknown_issue"


def _doctor_next_actions(
    blocking_issues: list[str],
    advisory_issues: list[str],
    *,
    reason_codes: list[str] | None = None,
) -> list[str]:
    if reason_codes:
        reason_actions = next_actions_for_reason_codes(reason_codes)
        if reason_actions:
            return reason_actions

    actions: list[str] = []
    for issue in blocking_issues + advisory_issues:
        normalized_issue = str(issue)
        if normalized_issue in {
            "workspace_root_missing",
            "workspace_manifest_missing",
            "workspace_manifest_invalid",
            "active_spec_missing",
            "active_spec_invalid",
            "active_report_missing",
            "active_report_invalid",
        } or normalized_issue.startswith("missing_directories:"):
            actions.append("run_exec")
        elif "unavailable" in normalized_issue:
            actions.append("run_doctor")

    if actions:
        return normalize_reason_codes(actions)
    return ["run_doctor"]
