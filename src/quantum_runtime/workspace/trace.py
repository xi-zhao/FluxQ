"""NDJSON trace logging for workspace events."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class TraceEvent(BaseModel):
    """A single workspace trace event."""

    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    event_type: str
    revision: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class TraceWriter:
    """Append trace events to the workspace NDJSON log."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, event_type: str, payload: dict[str, Any], revision: str | None = None) -> TraceEvent:
        """Append one event and return the normalized record."""
        event = TraceEvent(event_type=event_type, revision=revision, payload=payload)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.model_dump(), ensure_ascii=True) + "\n")
        return event
