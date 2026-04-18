"""Path helpers for workspace layout."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspacePaths:
    """Resolved filesystem paths for a workspace root."""

    root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", self.root.resolve())

    @property
    def workspace_json(self) -> Path:
        return self.root / "workspace.json"

    @property
    def qrun_toml(self) -> Path:
        return self.root / "qrun.toml"

    @property
    def events_jsonl(self) -> Path:
        return self.root / "events.jsonl"

    @property
    def events_dir(self) -> Path:
        return self.root / "events"

    @property
    def events_history_dir(self) -> Path:
        return self.events_dir / "history"

    def event_history_jsonl(self, revision: str) -> Path:
        return self.events_history_dir / f"{revision}.jsonl"

    @property
    def trace_events(self) -> Path:
        return self.trace_dir / "events.ndjson"

    @property
    def trace_dir(self) -> Path:
        return self.root / "trace"

    @property
    def trace_history_dir(self) -> Path:
        return self.trace_dir / "history"

    def trace_history_ndjson(self, revision: str) -> Path:
        return self.trace_history_dir / f"{revision}.ndjson"

    @property
    def intents_dir(self) -> Path:
        return self.root / "intents"

    @property
    def intents_history_dir(self) -> Path:
        return self.intents_dir / "history"

    @property
    def intents_latest_json(self) -> Path:
        return self.intents_dir / "latest.json"

    def intent_history_json(self, revision: str) -> Path:
        return self.intents_history_dir / f"{revision}.json"

    @property
    def plans_dir(self) -> Path:
        return self.root / "plans"

    @property
    def plans_history_dir(self) -> Path:
        return self.plans_dir / "history"

    @property
    def plans_latest_json(self) -> Path:
        return self.plans_dir / "latest.json"

    def plan_history_json(self, revision: str) -> Path:
        return self.plans_history_dir / f"{revision}.json"

    @property
    def packs_dir(self) -> Path:
        return self.root / "packs"

    def pack_revision_dir(self, revision: str) -> Path:
        return self.packs_dir / revision

    @property
    def compare_dir(self) -> Path:
        return self.root / "compare"

    @property
    def compare_latest_json(self) -> Path:
        return self.compare_dir / "latest.json"

    @property
    def benchmarks_dir(self) -> Path:
        return self.root / "benchmarks"

    @property
    def benchmarks_latest_json(self) -> Path:
        return self.benchmarks_dir / "latest.json"

    def benchmark_history_json(self, revision: str) -> Path:
        return self.benchmarks_dir / "history" / f"{revision}.json"

    @property
    def doctor_dir(self) -> Path:
        return self.root / "doctor"

    @property
    def doctor_latest_json(self) -> Path:
        return self.doctor_dir / "latest.json"

    def doctor_history_json(self, revision: str) -> Path:
        return self.doctor_dir / "history" / f"{revision}.json"

    @property
    def manifests_dir(self) -> Path:
        return self.root / "manifests"

    @property
    def manifests_history_dir(self) -> Path:
        return self.manifests_dir / "history"

    @property
    def manifests_latest_json(self) -> Path:
        return self.manifests_dir / "latest.json"

    def manifest_history_json(self, revision: str) -> Path:
        return self.manifests_history_dir / f"{revision}.json"

    @property
    def baselines_dir(self) -> Path:
        return self.root / "baselines"

    @property
    def baseline_current_json(self) -> Path:
        return self.baselines_dir / "current.json"

    @property
    def remote_dir(self) -> Path:
        return self.root / "remote"

    @property
    def remote_attempts_dir(self) -> Path:
        return self.remote_dir / "attempts"

    @property
    def remote_attempts_history_dir(self) -> Path:
        return self.remote_attempts_dir / "history"

    @property
    def remote_attempt_latest_json(self) -> Path:
        return self.remote_attempts_dir / "latest.json"

    def remote_attempt_history_json(self, attempt_id: str) -> Path:
        return self.remote_attempts_history_dir / f"{attempt_id}.json"

    @property
    def remote_artifacts_dir(self) -> Path:
        return self.remote_dir / "artifacts"

    @property
    def remote_artifacts_history_dir(self) -> Path:
        return self.remote_artifacts_dir / "history"

    def remote_artifact_attempt_dir(self, attempt_id: str) -> Path:
        return self.remote_artifacts_history_dir / attempt_id

    @property
    def remote_events_dir(self) -> Path:
        return self.remote_dir / "events"

    @property
    def remote_events_history_dir(self) -> Path:
        return self.remote_events_dir / "history"

    @property
    def remote_trace_dir(self) -> Path:
        return self.remote_dir / "trace"

    @property
    def remote_trace_history_dir(self) -> Path:
        return self.remote_trace_dir / "history"

    def required_directories(self) -> list[Path]:
        """Return the required directory skeleton for a workspace."""
        return [
            self.root,
            self.baselines_dir,
            self.events_dir,
            self.events_history_dir,
            self.intents_dir,
            self.intents_history_dir,
            self.plans_dir,
            self.plans_history_dir,
            self.root / "specs",
            self.root / "specs" / "history",
            self.manifests_dir,
            self.manifests_history_dir,
            self.root / "artifacts",
            self.root / "artifacts" / "history",
            self.root / "artifacts" / "qiskit",
            self.root / "artifacts" / "classiq",
            self.root / "artifacts" / "qasm",
            self.root / "figures",
            self.root / "reports",
            self.root / "reports" / "history",
            self.trace_dir,
            self.trace_history_dir,
            self.root / "cache",
            self.packs_dir,
            self.remote_dir,
            self.remote_attempts_dir,
            self.remote_attempts_history_dir,
            self.remote_artifacts_dir,
            self.remote_artifacts_history_dir,
            self.remote_events_dir,
            self.remote_events_history_dir,
            self.remote_trace_dir,
            self.remote_trace_history_dir,
        ]
