"""Thin HTTP gateway for the split-host `cc-connect` personal WeChat route."""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Mapping, cast


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIRMATION_MODULE_PATH = SCRIPT_DIR / "confirmation.py"


def _load_confirmation_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "cc_connect_gateway_confirmation",
        CONFIRMATION_MODULE_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_confirmation_module = _load_confirmation_module()
ConfirmationRequest = _confirmation_module.ConfirmationRequest
PendingConfirmationStore = _confirmation_module.PendingConfirmationStore


WORKSPACE_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
CONFIRM_PATTERN = re.compile(r"^(?i:confirm|确认)\s+(confirm_[A-Za-z0-9]+)$")
CANCEL_PATTERN = re.compile(r"^(?i:cancel|取消)\s+(confirm_[A-Za-z0-9]+)$")
DEFAULT_LAUNCHER_PATH = SCRIPT_DIR.parent / "bin" / "run-claw-agent"


Launcher = Callable[[dict[str, object]], dict[str, object]]


@dataclass(frozen=True)
class GatewayConfig:
    """Runtime configuration for the HTTP-only execution gateway."""

    shared_secret: str
    allowlist_file: Path
    workspaces_root: Path
    state_root: Path
    max_skew_seconds: int = 300
    confirmation_ttl_seconds: int = 600
    timestamp_header: str = "X-FluxQ-Timestamp"
    nonce_header: str = "X-FluxQ-Nonce"
    signature_header: str = "X-FluxQ-Signature"

    @classmethod
    def from_env(cls) -> "GatewayConfig":
        """Build configuration from the documented gateway environment variables."""

        shared_secret = os.environ["FLUXQ_GATEWAY_SHARED_SECRET"]
        allowlist_file = Path(os.environ["FLUXQ_WECHAT_ALLOWLIST_FILE"])
        workspaces_root = Path(os.environ["FLUXQ_GATEWAY_WORKSPACES_ROOT"])
        state_root = Path(os.environ["FLUXQ_GATEWAY_STATE_ROOT"])
        return cls(
            shared_secret=shared_secret,
            allowlist_file=allowlist_file,
            workspaces_root=workspaces_root,
            state_root=state_root,
            max_skew_seconds=int(os.environ.get("FLUXQ_GATEWAY_MAX_SKEW_SECONDS", "300")),
            confirmation_ttl_seconds=int(
                os.environ.get("FLUXQ_GATEWAY_CONFIRMATION_TTL_SECONDS", "600")
            ),
            timestamp_header=os.environ.get("FLUXQ_GATEWAY_TIMESTAMP_HEADER", "X-FluxQ-Timestamp"),
            nonce_header=os.environ.get("FLUXQ_GATEWAY_NONCE_HEADER", "X-FluxQ-Nonce"),
            signature_header=os.environ.get("FLUXQ_GATEWAY_SIGNATURE_HEADER", "X-FluxQ-Signature"),
        )


class NonceStore:
    """Persist a short-lived nonce cache so replayed requests fail closed."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def remember(self, *, nonce: str, now: int, ttl_seconds: int) -> bool:
        """Record a nonce if it has not been seen within the active TTL window."""

        with self._lock:
            payload = self._load()
            valid_after = now - ttl_seconds
            entries = {
                key: value
                for key, value in payload.items()
                if isinstance(value, int) and value >= valid_after
            }
            if nonce in entries:
                self._save(entries)
                return False

            entries[nonce] = now
            self._save(entries)
            return True

    def _load(self) -> dict[str, int]:
        if not self.path.exists():
            return {}
        try:
            raw_payload = json.loads(self.path.read_text())
        except json.JSONDecodeError:
            return {}
        if not isinstance(raw_payload, dict):
            return {}
        loaded: dict[str, int] = {}
        for key, value in raw_payload.items():
            if isinstance(key, str) and isinstance(value, int):
                loaded[key] = value
        return loaded

    def _save(self, payload: dict[str, int]) -> None:
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True))


class GatewayHTTPServer(ThreadingHTTPServer):
    """HTTP server carrying gateway config and the launcher handoff seam."""

    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        config: GatewayConfig,
        launcher: Launcher | None = None,
    ) -> None:
        self.gateway_config = config
        self.gateway_nonce_store = NonceStore(config.state_root / "recent_nonces.json")
        self.gateway_confirmation_store = PendingConfirmationStore(
            config.state_root / "confirmations",
            ttl_seconds=config.confirmation_ttl_seconds,
        )
        self.gateway_launcher = launcher or default_launcher
        super().__init__(server_address, GatewayRequestHandler)


class GatewayRequestHandler(BaseHTTPRequestHandler):
    """Serve health and signed WeChat turn ingress for the local launcher."""

    server: GatewayHTTPServer

    def do_GET(self) -> None:
        """Return a fixed health signal for operator checks."""

        if self.path != "/healthz":
            self._write_json(
                status_code=HTTPStatus.NOT_FOUND,
                payload={"status": "error", "reason_codes": ["not_found"]},
            )
            return
        self._write_json(
            status_code=HTTPStatus.OK,
            payload={"status": "ok", "service": "fluxq_cc_gateway"},
        )

    def do_POST(self) -> None:
        """Verify, allowlist, and normalize an ingress message for the launcher."""

        if self.path != "/v1/integrations/wechat/turn":
            self._write_json(
                status_code=HTTPStatus.NOT_FOUND,
                payload={"status": "error", "reason_codes": ["not_found"]},
            )
            return

        raw_body = self._read_body()
        auth_failure = self._validate_auth(raw_body)
        if auth_failure is not None:
            status_code, payload = auth_failure
            self._write_json(status_code=status_code, payload=payload)
            return

        parse_result = self._parse_payload(raw_body)
        if parse_result is None:
            self._write_json(
                status_code=HTTPStatus.BAD_REQUEST,
                payload=self._blocked_payload(
                    conversation=None,
                    workspace=None,
                    reason_codes=["invalid_json_payload"],
                    next_actions=["fix_gateway_request_body"],
                ),
            )
            return

        validation_error = self._validate_turn_payload(parse_result)
        if validation_error is not None:
            self._write_json(
                status_code=HTTPStatus.BAD_REQUEST,
                payload=self._blocked_payload(
                    conversation=_conversation_payload(parse_result),
                    workspace=None,
                    reason_codes=[validation_error],
                    next_actions=["fix_gateway_request_body"],
                ),
            )
            return

        allowlist_entry = self._resolve_allowlist_entry(parse_result)
        if allowlist_entry is None:
            self._write_json(
                status_code=HTTPStatus.FORBIDDEN,
                payload=self._blocked_payload(
                    conversation=_conversation_payload(parse_result),
                    workspace=None,
                    reason_codes=["wechat_user_not_allowlisted"],
                    next_actions=["review_wechat_allowlist"],
                ),
            )
            return

        try:
            workspace = self._workspace_payload(allowlist_entry)
        except ValueError:
            self._write_json(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                payload=self._blocked_payload(
                    conversation=_conversation_payload(parse_result),
                    workspace=None,
                    reason_codes=["invalid_workspace_key"],
                    next_actions=["fix_allowlist_workspace_key"],
                ),
            )
            return

        message_text = cast(str, _lookup(parse_result, "message", "text"))
        confirmation_command = self._confirmation_command(message_text)
        if confirmation_command is not None:
            status_code, payload = self._handle_confirmation_command(
                command=confirmation_command[0],
                confirmation_id=confirmation_command[1],
                conversation=_conversation_payload(parse_result),
                wechat_user=_wechat_user_payload(parse_result),
                workspace=workspace,
            )
            self._write_json(status_code=status_code, payload=payload)
            return

        launcher_request = {
            "mode": "chat_turn",
            "project": cast(str, parse_result["project"]),
            "platform": cast(str, parse_result["platform"]),
            "wechat_user": _wechat_user_payload(parse_result),
            "conversation": _conversation_payload(parse_result),
            "message": _message_payload(parse_result),
            "workspace": workspace,
        }

        try:
            launcher_response = self.server.gateway_launcher(launcher_request)
        except Exception:
            self._write_json(
                status_code=HTTPStatus.BAD_GATEWAY,
                payload=self._blocked_payload(
                    conversation=_conversation_payload(parse_result),
                    workspace=workspace,
                    reason_codes=["launcher_failed"],
                    next_actions=["inspect_gateway_launcher"],
                ),
            )
            return

        if launcher_response.get("status") == "confirmation_required":
            payload = self._persist_confirmation(
                conversation=_conversation_payload(parse_result),
                wechat_user=_wechat_user_payload(parse_result),
                workspace=workspace,
                launcher_request=launcher_request,
                launcher_response=launcher_response,
            )
            self._write_json(status_code=HTTPStatus.OK, payload=payload)
            return

        payload = self._success_payload(
            conversation=_conversation_payload(parse_result),
            workspace=workspace,
            launcher_request=launcher_request,
            launcher_response=launcher_response,
        )
        self._write_json(status_code=HTTPStatus.OK, payload=payload)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        """Silence default request logging for CLI and test output."""

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0"))
        return self.rfile.read(length)

    def _validate_auth(self, raw_body: bytes) -> tuple[HTTPStatus, dict[str, object]] | None:
        config = self.server.gateway_config
        timestamp = self.headers.get(config.timestamp_header)
        nonce = self.headers.get(config.nonce_header)
        signature = self.headers.get(config.signature_header)

        if not timestamp:
            return HTTPStatus.UNAUTHORIZED, self._blocked_payload(
                conversation=None,
                workspace=None,
                reason_codes=["missing_timestamp_header"],
                next_actions=["set_gateway_timestamp_header"],
            )
        if not nonce:
            return HTTPStatus.UNAUTHORIZED, self._blocked_payload(
                conversation=None,
                workspace=None,
                reason_codes=["missing_nonce_header"],
                next_actions=["set_gateway_nonce_header"],
            )
        if not signature:
            return HTTPStatus.UNAUTHORIZED, self._blocked_payload(
                conversation=None,
                workspace=None,
                reason_codes=["missing_signature_header"],
                next_actions=["set_gateway_signature_header"],
            )

        expected_signature = _sign_request(
            config.shared_secret,
            timestamp=timestamp,
            nonce=nonce,
            raw_body=raw_body,
        )
        if not hmac.compare_digest(signature, expected_signature):
            return HTTPStatus.UNAUTHORIZED, self._blocked_payload(
                conversation=None,
                workspace=None,
                reason_codes=["invalid_signature"],
                next_actions=["check_gateway_shared_secret"],
            )

        try:
            timestamp_value = int(timestamp)
        except ValueError:
            return HTTPStatus.UNAUTHORIZED, self._blocked_payload(
                conversation=None,
                workspace=None,
                reason_codes=["invalid_timestamp_header"],
                next_actions=["set_gateway_timestamp_header"],
            )

        now = int(time.time())
        if abs(now - timestamp_value) > config.max_skew_seconds:
            return HTTPStatus.UNAUTHORIZED, self._blocked_payload(
                conversation=None,
                workspace=None,
                reason_codes=["timestamp_skew_exceeded"],
                next_actions=["synchronize_gateway_clock"],
            )

        if not self.server.gateway_nonce_store.remember(
            nonce=nonce,
            now=now,
            ttl_seconds=config.max_skew_seconds,
        ):
            return HTTPStatus.UNAUTHORIZED, self._blocked_payload(
                conversation=None,
                workspace=None,
                reason_codes=["nonce_replayed"],
                next_actions=["rotate_gateway_nonce"],
            )

        return None

    def _parse_payload(self, raw_body: bytes) -> dict[str, object] | None:
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def _validate_turn_payload(self, payload: dict[str, object]) -> str | None:
        required_fields = (
            ("project",),
            ("platform",),
            ("wechat_user", "id"),
            ("wechat_user", "display_name"),
            ("conversation", "id"),
            ("conversation", "message_id"),
            ("message", "text"),
            ("message", "received_at"),
        )
        for path in required_fields:
            if _lookup(payload, *path) in (None, ""):
                return "invalid_turn_payload"
        return None

    def _resolve_allowlist_entry(self, payload: dict[str, object]) -> dict[str, object] | None:
        wechat_user_id = cast(str, _lookup(payload, "wechat_user", "id"))
        try:
            raw_allowlist = json.loads(self.server.gateway_config.allowlist_file.read_text())
        except FileNotFoundError:
            return None
        except json.JSONDecodeError:
            return None

        entries = raw_allowlist.get("wechat_users", {}) if isinstance(raw_allowlist, dict) else {}
        if not isinstance(entries, dict):
            return None
        entry = entries.get(wechat_user_id)
        if isinstance(entry, str):
            return {"workspace_key": entry}
        if isinstance(entry, dict):
            return cast(dict[str, object], entry)
        return None

    def _workspace_payload(self, allowlist_entry: dict[str, object]) -> dict[str, str]:
        workspace_key = cast(str | None, allowlist_entry.get("workspace_key"))
        if not workspace_key or not WORKSPACE_KEY_PATTERN.match(workspace_key):
            raise ValueError("Invalid workspace key")
        root = self.server.gateway_config.workspaces_root / workspace_key / ".quantum"
        return {
            "workspace_key": workspace_key,
            "root": str(root),
        }

    def _confirmation_command(self, message_text: str) -> tuple[str, str] | None:
        normalized = message_text.strip()
        confirm_match = CONFIRM_PATTERN.match(normalized)
        if confirm_match is not None:
            return "confirm", confirm_match.group(1)
        cancel_match = CANCEL_PATTERN.match(normalized)
        if cancel_match is not None:
            return "cancel", cancel_match.group(1)
        return None

    def _persist_confirmation(
        self,
        *,
        conversation: dict[str, object],
        wechat_user: dict[str, object],
        workspace: dict[str, str],
        launcher_request: dict[str, object],
        launcher_response: dict[str, object],
    ) -> dict[str, object]:
        approved_tool_request = launcher_response.get("approved_tool_request")
        if not isinstance(approved_tool_request, Mapping):
            return self._blocked_payload(
                conversation=conversation,
                workspace=workspace,
                reason_codes=["invalid_confirmation_request"],
                next_actions=["fix_confirmation_payload"],
            )

        confirmation_id = approved_tool_request.get("confirmation_id")
        if not isinstance(confirmation_id, str) or not confirmation_id:
            return self._blocked_payload(
                conversation=conversation,
                workspace=workspace,
                reason_codes=["invalid_confirmation_request"],
                next_actions=["fix_confirmation_payload"],
            )

        stored_request = self.server.gateway_confirmation_store.create(
            confirmation_id=confirmation_id,
            wechat_user_id=cast(str, wechat_user["id"]),
            conversation_id=cast(str, conversation["id"]),
            workspace_key=workspace["workspace_key"],
            workspace_root=str(approved_tool_request.get("workspace_root", workspace["root"])),
            approved_tool_request=approved_tool_request,
        )
        reply_text = _render_confirmation_reply(stored_request)
        return {
            "status": "confirmation_required",
            "conversation": conversation,
            "workspace": workspace,
            "reply": {
                "kind": "text",
                "text": reply_text,
            },
            "confirmation": {
                "pending": True,
                "confirmation_id": stored_request.confirmation_id,
                "created_at": stored_request.created_at,
                "expires_at": stored_request.expires_at,
                "summary": stored_request.summary.to_dict(),
            },
            "reason_codes": ["confirmation_required"],
            "next_actions": ["reply_with_confirmation_token"],
            "gate": _gate_payload(
                ready=False,
                status="confirmation_required",
                severity="warning",
                reason_codes=["confirmation_required"],
                next_actions=["reply_with_confirmation_token"],
            ),
            "launcher_request": launcher_request,
        }

    def _handle_confirmation_command(
        self,
        *,
        command: str,
        confirmation_id: str,
        conversation: dict[str, object],
        wechat_user: dict[str, object],
        workspace: dict[str, str],
    ) -> tuple[HTTPStatus, dict[str, object]]:
        pending_request = self.server.gateway_confirmation_store.load(confirmation_id)
        if pending_request is None:
            return HTTPStatus.CONFLICT, self._confirmation_blocked_payload(
                conversation=conversation,
                workspace=workspace,
                confirmation_id=confirmation_id,
                pending_request=None,
                reason_codes=["missing_confirmation_request"],
                next_actions=["request_new_high_risk_action"],
            )

        if pending_request.is_expired():
            self.server.gateway_confirmation_store.delete(confirmation_id)
            return HTTPStatus.CONFLICT, self._confirmation_blocked_payload(
                conversation=conversation,
                workspace=workspace,
                confirmation_id=confirmation_id,
                pending_request=None,
                reason_codes=["expired_confirmation"],
                next_actions=["request_new_high_risk_action"],
            )

        if pending_request.wechat_user_id != wechat_user["id"]:
            reason_code = f"{command}_same_user_required"
            return HTTPStatus.CONFLICT, self._confirmation_blocked_payload(
                conversation=conversation,
                workspace=workspace,
                confirmation_id=confirmation_id,
                pending_request=pending_request,
                reason_codes=[reason_code],
                next_actions=["reply_from_original_allowlisted_user"],
            )

        if pending_request.conversation_id != conversation["id"]:
            reason_code = f"{command}_same_conversation_required"
            return HTTPStatus.CONFLICT, self._confirmation_blocked_payload(
                conversation=conversation,
                workspace=workspace,
                confirmation_id=confirmation_id,
                pending_request=pending_request,
                reason_codes=[reason_code],
                next_actions=["reply_in_original_conversation"],
            )

        if command == "cancel":
            self.server.gateway_confirmation_store.delete(confirmation_id)
            return HTTPStatus.OK, self._cancelled_payload(
                conversation=conversation,
                workspace=workspace,
                pending_request=pending_request,
            )

        launcher_request = {
            "mode": "confirmed_tool_request",
            "workspace": {
                "workspace_key": pending_request.workspace_key,
                "root": pending_request.workspace_root,
            },
            "conversation": {
                "id": pending_request.conversation_id,
            },
            "confirmation_id": pending_request.confirmation_id,
        }
        try:
            launcher_response = self.server.gateway_launcher(launcher_request)
        except Exception:
            return HTTPStatus.BAD_GATEWAY, self._confirmation_blocked_payload(
                conversation=conversation,
                workspace=workspace,
                confirmation_id=confirmation_id,
                pending_request=pending_request,
                reason_codes=["launcher_failed"],
                next_actions=["inspect_gateway_launcher"],
            )

        self.server.gateway_confirmation_store.delete(confirmation_id)
        payload = self._success_payload(
            conversation=conversation,
            workspace={
                "workspace_key": pending_request.workspace_key,
                "root": pending_request.workspace_root,
            },
            launcher_request=launcher_request,
            launcher_response=launcher_response,
        )
        return HTTPStatus.OK, payload

    def _confirmation_blocked_payload(
        self,
        *,
        conversation: dict[str, object],
        workspace: dict[str, object],
        confirmation_id: str,
        pending_request: ConfirmationRequest | None,
        reason_codes: list[str],
        next_actions: list[str],
    ) -> dict[str, object]:
        reply_text = _confirmation_blocked_text(
            confirmation_id=confirmation_id,
            reason_codes=reason_codes,
        )
        confirmation_payload: dict[str, object] = {
            "pending": pending_request is not None,
            "confirmation_id": confirmation_id,
        }
        if pending_request is not None:
            confirmation_payload["expires_at"] = pending_request.expires_at
            confirmation_payload["summary"] = pending_request.summary.to_dict()
        return {
            "status": "blocked",
            "conversation": conversation,
            "workspace": workspace,
            "reply": {
                "kind": "text",
                "text": reply_text,
            },
            "confirmation": confirmation_payload,
            "reason_codes": reason_codes,
            "next_actions": next_actions,
            "gate": _gate_payload(
                ready=False,
                status="blocked",
                severity="error",
                reason_codes=reason_codes,
                next_actions=next_actions,
            ),
        }

    def _cancelled_payload(
        self,
        *,
        conversation: dict[str, object],
        workspace: dict[str, object],
        pending_request: ConfirmationRequest,
    ) -> dict[str, object]:
        reply_text = (
            f"Cancelled pending FluxQ action `{pending_request.confirmation_id}`. "
            "Send a new request if you still want to run it."
        )
        return {
            "status": "cancelled",
            "conversation": conversation,
            "workspace": workspace,
            "reply": {
                "kind": "text",
                "text": reply_text,
            },
            "confirmation": {
                "pending": False,
                "confirmation_id": pending_request.confirmation_id,
                "summary": pending_request.summary.to_dict(),
            },
            "reason_codes": ["confirmation_cancelled"],
            "next_actions": ["request_new_high_risk_action"],
            "gate": _gate_payload(
                ready=False,
                status="cancelled",
                severity="info",
                reason_codes=["confirmation_cancelled"],
                next_actions=["request_new_high_risk_action"],
            ),
        }

    def _success_payload(
        self,
        *,
        conversation: dict[str, object],
        workspace: dict[str, str],
        launcher_request: dict[str, object],
        launcher_response: dict[str, object],
    ) -> dict[str, object]:
        status = launcher_response.get("status")
        if not isinstance(status, str):
            status = "ok"

        has_tool_result = isinstance(launcher_response.get("tool_result"), Mapping)
        if has_tool_result:
            default_reason_codes = ["confirmed_tool_request_executed"]
            default_next_actions = ["inspect_confirmed_tool_result"]
            default_gate = _gate_payload(
                ready=True,
                status="open",
                severity="info",
                reason_codes=default_reason_codes,
                next_actions=default_next_actions,
            )
        elif status == "blocked":
            default_reason_codes = ["launcher_request_blocked"]
            default_next_actions = ["inspect_launcher_response"]
            default_gate = _gate_payload(
                ready=False,
                status="blocked",
                severity="error",
                reason_codes=default_reason_codes,
                next_actions=default_next_actions,
            )
        elif status == "error":
            default_reason_codes = ["launcher_request_failed"]
            default_next_actions = ["inspect_launcher_response"]
            default_gate = _gate_payload(
                ready=False,
                status="error",
                severity="error",
                reason_codes=default_reason_codes,
                next_actions=default_next_actions,
            )
        else:
            default_reason_codes = ["launcher_request_ready"]
            default_next_actions = ["run_claw_launcher"]
            default_gate = _gate_payload(
                ready=True,
                status="open",
                severity="info",
                reason_codes=default_reason_codes,
                next_actions=default_next_actions,
            )

        reason_codes = _normalize_string_list(
            launcher_response.get("reason_codes"),
            fallback=default_reason_codes,
        )
        next_actions = _normalize_string_list(
            launcher_response.get("next_actions"),
            fallback=default_next_actions,
        )
        gate = launcher_response.get("gate")
        if not isinstance(gate, dict):
            gate = {
                **default_gate,
                "reason_codes": reason_codes,
                "next_actions": next_actions,
                "recommended_action": next_actions[0] if next_actions else None,
            }

        reply = launcher_response.get("reply")
        if not isinstance(reply, dict):
            if has_tool_result:
                reply = _tool_result_reply(cast(Mapping[str, Any], launcher_response["tool_result"]))
            elif status == "blocked":
                reply = {
                    "kind": "text",
                    "text": "Request blocked by the FluxQ gateway.",
                }
            elif status == "error":
                reply = {
                    "kind": "text",
                    "text": "FluxQ could not complete the requested action.",
                }
            else:
                reply = {
                    "kind": "text",
                    "text": "Queued request for the local claw launcher.",
                }

        confirmation = launcher_response.get("confirmation")
        if not isinstance(confirmation, dict):
            confirmation = {"pending": False}

        payload: dict[str, object] = {
            "status": status,
            "conversation": conversation,
            "workspace": workspace,
            "reply": reply,
            "confirmation": confirmation,
            "reason_codes": reason_codes,
            "next_actions": next_actions,
            "gate": gate,
            "launcher_request": launcher_request,
        }
        tool_result = launcher_response.get("tool_result")
        if isinstance(tool_result, Mapping):
            payload["tool_result"] = dict(tool_result)
        for field in ("stdout", "stderr", "exit_code", "assistant_output", "tool_summaries"):
            value = launcher_response.get(field)
            if value is not None:
                payload[field] = value
        return payload

    def _blocked_payload(
        self,
        *,
        conversation: dict[str, object] | None,
        workspace: dict[str, object] | None,
        reason_codes: list[str],
        next_actions: list[str],
    ) -> dict[str, object]:
        return {
            "status": "blocked",
            "conversation": conversation or {"id": None, "message_id": None},
            "workspace": workspace or {"workspace_key": None, "root": None},
            "reply": {
                "kind": "text",
                "text": "Request blocked by the FluxQ gateway.",
            },
            "confirmation": {"pending": False},
            "reason_codes": reason_codes,
            "next_actions": next_actions,
            "gate": _gate_payload(
                ready=False,
                status="blocked",
                severity="error",
                reason_codes=reason_codes,
                next_actions=next_actions,
            ),
        }

    def _write_json(self, *, status_code: HTTPStatus, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status_code.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _lookup(payload: dict[str, object], *path: str) -> object | None:
    current: object = payload
    for segment in path:
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
    return current


def _conversation_payload(payload: dict[str, object]) -> dict[str, object]:
    return {
        "id": _lookup(payload, "conversation", "id"),
        "message_id": _lookup(payload, "conversation", "message_id"),
    }


def _wechat_user_payload(payload: dict[str, object]) -> dict[str, object]:
    return {
        "id": _lookup(payload, "wechat_user", "id"),
        "display_name": _lookup(payload, "wechat_user", "display_name"),
    }


def _message_payload(payload: dict[str, object]) -> dict[str, object]:
    return {
        "text": _lookup(payload, "message", "text"),
        "received_at": _lookup(payload, "message", "received_at"),
    }


def _normalize_string_list(value: object, *, fallback: list[str]) -> list[str]:
    if isinstance(value, list):
        normalized = [item for item in value if isinstance(item, str) and item]
        if normalized:
            return normalized
    return list(fallback)


def _gate_payload(
    *,
    ready: bool,
    status: str,
    severity: str,
    reason_codes: list[str],
    next_actions: list[str],
) -> dict[str, object]:
    return {
        "ready": ready,
        "status": status,
        "severity": severity,
        "recommended_action": next_actions[0] if next_actions else None,
        "reason_codes": list(reason_codes),
        "next_actions": list(next_actions),
    }


def _render_confirmation_reply(pending_request: ConfirmationRequest) -> str:
    summary = pending_request.summary
    backend_instance = " / ".join(
        [value for value in (summary.backend, summary.instance) if value]
    ) or "n/a"
    return (
        "High-risk FluxQ action requires explicit confirmation.\n\n"
        f"action: {summary.action}\n"
        f"input source: {summary.input_source['kind']}={summary.input_source['value']}\n"
        f"workspace: {summary.workspace}\n"
        f"backend / instance: {backend_instance}\n"
        f"may_create_remote_job: {str(summary.may_create_remote_job).lower()}\n"
        f"may_spend: {str(summary.may_spend).lower()}\n"
        f"consequence: {summary.consequence}\n\n"
        f"Reply `CONFIRM {pending_request.confirmation_id}` or `确认 {pending_request.confirmation_id}` "
        "to execute the stored request.\n"
        f"Reply `CANCEL {pending_request.confirmation_id}` or `取消 {pending_request.confirmation_id}` "
        "to clear it."
    )


def _confirmation_blocked_text(*, confirmation_id: str, reason_codes: list[str]) -> str:
    reason_text = ", ".join(reason_codes)
    return (
        f"Confirmation `{confirmation_id}` is blocked.\n\n"
        f"reason_codes: {reason_text}\n"
        "Send a fresh high-risk request if you still want FluxQ to continue."
    )


def _tool_result_reply(tool_result: Mapping[str, Any]) -> dict[str, object]:
    if isinstance(tool_result.get("reply"), Mapping):
        return dict(cast(Mapping[str, Any], tool_result["reply"]))
    rendered = json.dumps(dict(tool_result), ensure_ascii=True, sort_keys=True)
    return {
        "kind": "json",
        "text": rendered,
        "payload": dict(tool_result),
    }


def _prepare_launcher_request(request: Mapping[str, object]) -> dict[str, object]:
    normalized = dict(request)
    workspace = normalized.get("workspace")
    if isinstance(workspace, Mapping):
        workspace_payload = dict(workspace)
        workspace_key = workspace_payload.get("workspace_key")
        if "key" not in workspace_payload and isinstance(workspace_key, str):
            workspace_payload["key"] = workspace_key
        normalized["workspace"] = workspace_payload
    return normalized


def _parse_launcher_output(stdout: str) -> dict[str, object]:
    if not stdout.strip():
        return {}
    payload = json.loads(stdout)
    if not isinstance(payload, dict):
        raise ValueError("invalid_launcher_output")
    return payload


def default_launcher(request: dict[str, object]) -> dict[str, object]:
    """Run the local launcher seam and normalize pending confirmations."""

    launcher_path = Path(
        os.environ.get("FLUXQ_GATEWAY_LAUNCHER_PATH", str(DEFAULT_LAUNCHER_PATH))
    )
    launcher_request = _prepare_launcher_request(request)
    completed = subprocess.run(
        [sys.executable, str(launcher_path)],
        input=json.dumps(launcher_request, ensure_ascii=True),
        capture_output=True,
        text=True,
        check=False,
        shell=False,
        env=dict(os.environ),
    )
    payload = _parse_launcher_output(completed.stdout)
    pending_tool_request = payload.get("pending_tool_request")
    if payload.get("status") == "ok" and isinstance(pending_tool_request, Mapping):
        normalized_payload = dict(payload)
        normalized_payload["status"] = "confirmation_required"
        normalized_payload["approved_tool_request"] = dict(pending_tool_request)
        return normalized_payload
    return payload


def _sign_request(secret: str, *, timestamp: str, nonce: str, raw_body: bytes) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        msg=f"{timestamp}\n{nonce}\n".encode("utf-8") + raw_body,
        digestmod=hashlib.sha256,
    )
    return digest.hexdigest()


def build_server(
    *,
    host: str,
    port: int,
    config: GatewayConfig,
    launcher: Launcher | None = None,
) -> GatewayHTTPServer:
    """Construct a server instance for tests or local operator runs."""

    return GatewayHTTPServer((host, port), config=config, launcher=launcher)


def main() -> int:
    """Run the gateway from the documented environment variables."""

    config = GatewayConfig.from_env()
    host = os.environ.get("FLUXQ_GATEWAY_HOST", "127.0.0.1")
    port = int(os.environ.get("FLUXQ_GATEWAY_PORT", "8787"))
    server = build_server(host=host, port=port, config=config)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
