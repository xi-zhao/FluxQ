"""Pending confirmation models and a file-backed store for WeChat risk gates."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Mapping


INPUT_SOURCE_FIELDS = (
    "intent_file",
    "intent_json_file",
    "qspec_file",
    "report_file",
    "revision",
    "intent_text",
)
REMOTE_SUBMIT_CONSEQUENCE = (
    "May create a remote IBM job and consume provider quota on the selected backend."
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _input_source(approved_tool_request: Mapping[str, Any]) -> dict[str, str]:
    options = approved_tool_request.get("options", {})
    if isinstance(options, Mapping):
        for field in INPUT_SOURCE_FIELDS:
            raw_value = options.get(field)
            if raw_value is not None:
                return {
                    "kind": field,
                    "value": str(raw_value),
                }
    workspace_root = approved_tool_request.get("workspace_root")
    if isinstance(workspace_root, str) and workspace_root:
        return {
            "kind": "workspace",
            "value": workspace_root,
        }
    return {
        "kind": "none",
        "value": "",
    }


@dataclass(frozen=True)
class ConfirmationSummary:
    """Stable summary fields shown before a high-risk action may execute."""

    action: str
    input_source: dict[str, str]
    workspace: str
    backend: str | None
    instance: str | None
    may_create_remote_job: bool
    may_spend: bool
    consequence: str

    @classmethod
    def from_approved_tool_request(
        cls,
        approved_tool_request: Mapping[str, Any],
    ) -> "ConfirmationSummary":
        command = approved_tool_request.get("command")
        action = str(command) if isinstance(command, str) else "unknown"
        options = approved_tool_request.get("options", {})
        normalized_options = options if isinstance(options, Mapping) else {}
        backend = normalized_options.get("backend")
        if backend is None and normalized_options.get("backends") is not None:
            backend = normalized_options.get("backends")
        instance = normalized_options.get("instance")
        workspace_root = approved_tool_request.get("workspace_root")
        workspace = str(workspace_root) if isinstance(workspace_root, str) else ""
        may_create_remote_job = action == "remote submit"
        may_spend = action == "remote submit"
        consequence = REMOTE_SUBMIT_CONSEQUENCE if action == "remote submit" else (
            "Requires explicit confirmation before FluxQ executes the approved request."
        )
        return cls(
            action=action,
            input_source=_input_source(approved_tool_request),
            workspace=workspace,
            backend=None if backend is None else str(backend),
            instance=None if instance is None else str(instance),
            may_create_remote_job=may_create_remote_job,
            may_spend=may_spend,
            consequence=consequence,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ConfirmationSummary":
        input_source = payload.get("input_source", {})
        if not isinstance(input_source, Mapping):
            input_source = {}
        return cls(
            action=str(payload.get("action", "")),
            input_source={
                "kind": str(input_source.get("kind", "")),
                "value": str(input_source.get("value", "")),
            },
            workspace=str(payload.get("workspace", "")),
            backend=None if payload.get("backend") is None else str(payload.get("backend")),
            instance=None if payload.get("instance") is None else str(payload.get("instance")),
            may_create_remote_job=bool(payload.get("may_create_remote_job", False)),
            may_spend=bool(payload.get("may_spend", False)),
            consequence=str(payload.get("consequence", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConfirmationRequest:
    """One pending confirmation bound to a specific WeChat user and conversation."""

    confirmation_id: str
    wechat_user_id: str
    conversation_id: str
    workspace_key: str
    workspace_root: str
    approved_tool_request: dict[str, Any]
    summary: ConfirmationSummary
    created_at: str
    expires_at: str

    @classmethod
    def create(
        cls,
        *,
        confirmation_id: str,
        wechat_user_id: str,
        conversation_id: str,
        workspace_key: str,
        workspace_root: str,
        approved_tool_request: Mapping[str, Any],
        ttl_seconds: int,
        created_at: datetime | None = None,
    ) -> "ConfirmationRequest":
        created = created_at or _utc_now()
        expires = created + timedelta(seconds=ttl_seconds)
        return cls(
            confirmation_id=confirmation_id,
            wechat_user_id=wechat_user_id,
            conversation_id=conversation_id,
            workspace_key=workspace_key,
            workspace_root=workspace_root,
            approved_tool_request=dict(approved_tool_request),
            summary=ConfirmationSummary.from_approved_tool_request(approved_tool_request),
            created_at=_format_timestamp(created),
            expires_at=_format_timestamp(expires),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ConfirmationRequest":
        summary = payload.get("summary", {})
        if not isinstance(summary, Mapping):
            summary = {}
        approved_tool_request = payload.get("approved_tool_request", {})
        if not isinstance(approved_tool_request, Mapping):
            approved_tool_request = {}
        return cls(
            confirmation_id=str(payload.get("confirmation_id", "")),
            wechat_user_id=str(payload.get("wechat_user_id", "")),
            conversation_id=str(payload.get("conversation_id", "")),
            workspace_key=str(payload.get("workspace_key", "")),
            workspace_root=str(payload.get("workspace_root", "")),
            approved_tool_request=dict(approved_tool_request),
            summary=ConfirmationSummary.from_dict(summary),
            created_at=str(payload.get("created_at", "")),
            expires_at=str(payload.get("expires_at", "")),
        )

    def is_expired(self, *, now: datetime | None = None) -> bool:
        reference = now or _utc_now()
        return reference >= _parse_timestamp(self.expires_at)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["summary"] = self.summary.to_dict()
        return payload


class PendingConfirmationStore:
    """Persist pending confirmations under one gateway state root."""

    def __init__(self, root: Path, *, ttl_seconds: int) -> None:
        self.root = root
        self.ttl_seconds = ttl_seconds
        self._lock = Lock()
        self.root.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        *,
        confirmation_id: str,
        wechat_user_id: str,
        conversation_id: str,
        workspace_key: str,
        workspace_root: str,
        approved_tool_request: Mapping[str, Any],
    ) -> ConfirmationRequest:
        request = ConfirmationRequest.create(
            confirmation_id=confirmation_id,
            wechat_user_id=wechat_user_id,
            conversation_id=conversation_id,
            workspace_key=workspace_key,
            workspace_root=workspace_root,
            approved_tool_request=approved_tool_request,
            ttl_seconds=self.ttl_seconds,
        )
        with self._lock:
            self._write(request)
        return request

    def load(self, confirmation_id: str) -> ConfirmationRequest | None:
        with self._lock:
            path = self._path(confirmation_id)
            if not path.exists():
                return None
            try:
                payload = json.loads(path.read_text())
            except json.JSONDecodeError:
                return None
            if not isinstance(payload, dict):
                return None
            return ConfirmationRequest.from_dict(payload)

    def delete(self, confirmation_id: str) -> None:
        with self._lock:
            path = self._path(confirmation_id)
            if path.exists():
                path.unlink()

    def _path(self, confirmation_id: str) -> Path:
        return self.root / f"{confirmation_id}.json"

    def _write(self, request: ConfirmationRequest) -> None:
        path = self._path(request.confirmation_id)
        path.write_text(json.dumps(request.to_dict(), indent=2, ensure_ascii=True, sort_keys=True))
