"""NDJSON trace logging for workspace events."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .manifest import atomic_write_text


SCHEMA_VERSION = "0.3.0"


class TraceEvent(BaseModel):
    """A single workspace trace event."""

    schema_version: str = SCHEMA_VERSION
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    event_type: str
    phase: str
    status: str = "ok"
    revision: str | None = None
    error_code: str | None = None
    remediation: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class TraceWriter:
    """Append trace events to the workspace NDJSON log."""

    def __init__(self, *paths: Path) -> None:
        self.paths = tuple(dict.fromkeys(Path(path) for path in paths))

    def append(
        self,
        event_type: str,
        payload: dict[str, Any],
        revision: str | None = None,
        status: str = "ok",
        error_code: str | None = None,
    ) -> TraceEvent:
        """Append one event and return the normalized record."""
        event = TraceEvent(
            event_type=event_type,
            phase=_phase_for_event_type(event_type),
            status=status,
            revision=revision,
            error_code=error_code,
            remediation=_remediation_for_error(error_code) if error_code is not None else None,
            payload=payload,
        )
        encoded = json.dumps(event.model_dump(mode="json"), ensure_ascii=True) + "\n"
        for path in self.paths:
            _append_text(path, encoded)
        return event


def append_trace_log(*, source_path: Path, destination_path: Path) -> None:
    """Atomically append staged NDJSON records onto an authoritative event log."""
    staged = source_path.read_text(encoding="utf-8") if source_path.exists() else ""
    if not staged:
        return

    existing = destination_path.read_text(encoding="utf-8") if destination_path.exists() else ""
    atomic_write_text(destination_path, f"{existing}{staged}")


def write_trace_snapshot(*, source_path: Path, snapshot_path: Path) -> None:
    """Persist one revision-scoped NDJSON snapshot from staged event records."""
    staged = source_path.read_text(encoding="utf-8") if source_path.exists() else ""
    atomic_write_text(snapshot_path, staged)


def _phase_for_event_type(event_type: str) -> str:
    if event_type.startswith("exec_"):
        return "execute"
    if event_type.startswith("compare_"):
        return "compare"
    if event_type.startswith("doctor_"):
        return "doctor"
    if event_type.startswith("backend_"):
        return "benchmark"
    return "runtime"


def _remediation_for_error(error_code: str | None) -> str | None:
    if error_code is None:
        return None
    return "Inspect the workspace event payload, then rerun the originating command with --json or --jsonl."


def _append_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
