from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = PROJECT_ROOT / "integrations" / "cc-connect" / "gateway" / "server.py"


def _load_gateway_module() -> Any:
    assert SERVER_PATH.exists(), f"Gateway server module missing: {SERVER_PATH}"
    spec = importlib.util.spec_from_file_location("cc_connect_gateway_confirmation_server", SERVER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _seed_allowlist(path: Path, users: dict[str, str]) -> None:
    path.write_text(
        json.dumps(
            {
                "wechat_users": {
                    user_id: {
                        "workspace_key": workspace_key,
                        "display_name": user_id,
                    }
                    for user_id, workspace_key in users.items()
                }
            },
            indent=2,
        )
    )


def _sign(secret: str, *, timestamp: str, nonce: str, body: bytes) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        msg=f"{timestamp}\n{nonce}\n".encode("utf-8") + body,
        digestmod=hashlib.sha256,
    )
    return digest.hexdigest()


def _make_config(module: Any, tmp_path: Path) -> Any:
    allowlist_file = tmp_path / "allowlist.json"
    state_root = tmp_path / "state"
    workspaces_root = tmp_path / "workspaces"
    _seed_allowlist(
        allowlist_file,
        {
            "wxid_alice": "alice-main",
            "wxid_bob": "bob-main",
        },
    )
    state_root.mkdir()
    workspaces_root.mkdir()
    return module.GatewayConfig(
        shared_secret="test-shared-secret",
        allowlist_file=allowlist_file,
        workspaces_root=workspaces_root,
        state_root=state_root,
    )


def _start_server(module: Any, *, config: Any, launcher: Any) -> tuple[Any, threading.Thread]:
    server = module.build_server(
        host="127.0.0.1",
        port=0,
        config=config,
        launcher=launcher,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _post_json(
    url: str,
    *,
    payload: dict[str, object],
    secret: str,
    nonce: str,
) -> tuple[int, dict[str, Any]]:
    body = json.dumps(payload).encode("utf-8")
    timestamp = str(int(time.time()))
    headers = {
        "Content-Type": "application/json",
        "X-FluxQ-Timestamp": timestamp,
        "X-FluxQ-Nonce": nonce,
        "X-FluxQ-Signature": _sign(secret, timestamp=timestamp, nonce=nonce, body=body),
    }
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _turn_payload(
    *,
    wechat_user_id: str = "wxid_alice",
    conversation_id: str = "conv-123",
    message_id: str = "msg-001",
    text: str,
) -> dict[str, object]:
    return {
        "project": "fluxq-personal",
        "platform": "weixin",
        "wechat_user": {
            "id": wechat_user_id,
            "display_name": wechat_user_id,
        },
        "conversation": {
            "id": conversation_id,
            "message_id": message_id,
        },
        "message": {
            "text": text,
            "received_at": "2026-04-21T10:00:00Z",
        },
    }


def _confirmation_path(config: Any, confirmation_id: str) -> Path:
    return config.state_root / "confirmations" / f"{confirmation_id}.json"


def test_confirmation_required_uses_standard_summary_and_no_execute_before_confirm(
    tmp_path: Path,
) -> None:
    module = _load_gateway_module()
    config = _make_config(module, tmp_path)
    workspace_root = str(config.workspaces_root / "alice-main" / ".quantum")
    confirmation_id = "confirm_pending123"
    launcher_calls: list[dict[str, object]] = []

    def _launcher(request_payload: dict[str, object]) -> dict[str, object]:
        launcher_calls.append(request_payload)
        assert request_payload["mode"] == "chat_turn"
        return {
            "status": "confirmation_required",
            "approved_tool_request": {
                "command": "remote submit",
                "workspace_root": workspace_root,
                "options": {
                    "backend": "ibm_kyiv",
                    "instance": "ibm-q/open/main",
                    "intent_file": "intent.md",
                },
                "output_mode": "json",
                "confirmation_id": confirmation_id,
            },
        }

    server, thread = _start_server(module, config=config, launcher=_launcher)
    try:
        url = f"http://127.0.0.1:{server.server_port}/v1/integrations/wechat/turn"
        status_code, payload = _post_json(
            url,
            payload=_turn_payload(text="remote submit the current run to ibm_kyiv on ibm-q/open/main"),
            secret=config.shared_secret,
            nonce="nonce-001",
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    stored_confirmation = json.loads(_confirmation_path(config, confirmation_id).read_text())

    assert status_code == 200
    assert payload["status"] == "confirmation_required"
    assert payload["confirmation"]["pending"] is True
    assert payload["confirmation"]["confirmation_id"] == confirmation_id
    # standard summary contract
    assert payload["confirmation"]["summary"]["action"] == "remote submit"
    assert payload["confirmation"]["summary"]["may_create_remote_job"] is True
    assert payload["confirmation"]["summary"]["may_spend"] is True
    assert "consequence" in payload["confirmation"]["summary"]
    assert f"CONFIRM {confirmation_id}" in payload["reply"]["text"]
    assert f"确认 {confirmation_id}" in payload["reply"]["text"]
    assert launcher_calls == [
        {
            "mode": "chat_turn",
            "project": "fluxq-personal",
            "platform": "weixin",
            "wechat_user": {
                "id": "wxid_alice",
                "display_name": "wxid_alice",
            },
            "conversation": {
                "id": "conv-123",
                "message_id": "msg-001",
            },
            "message": {
                "text": "remote submit the current run to ibm_kyiv on ibm-q/open/main",
                "received_at": "2026-04-21T10:00:00Z",
            },
            "workspace": {
                "workspace_key": "alice-main",
                "root": workspace_root,
            },
        }
    ]
    assert stored_confirmation["wechat_user_id"] == "wxid_alice"
    assert stored_confirmation["conversation_id"] == "conv-123"
    assert stored_confirmation["workspace_root"] == workspace_root
    assert stored_confirmation["approved_tool_request"]["confirmation_id"] == confirmation_id


def test_confirm_same_user_and_conversation_replays_stored_request(
    tmp_path: Path,
) -> None:
    module = _load_gateway_module()
    config = _make_config(module, tmp_path)
    workspace_root = str(config.workspaces_root / "alice-main" / ".quantum")
    confirmation_id = "confirm_pending123"
    launcher_calls: list[dict[str, object]] = []

    def _launcher(request_payload: dict[str, object]) -> dict[str, object]:
        launcher_calls.append(request_payload)
        if request_payload["mode"] == "chat_turn":
            return {
                "status": "confirmation_required",
                "approved_tool_request": {
                    "command": "remote submit",
                    "workspace_root": workspace_root,
                    "options": {
                        "backend": "ibm_kyiv",
                        "intent_file": "intent.md",
                    },
                    "output_mode": "json",
                    "confirmation_id": confirmation_id,
                },
            }
        return {
            "status": "ok",
            "tool_result": {
                "status": "submitted",
                "job_id": "job-123",
            },
        }

    server, thread = _start_server(module, config=config, launcher=_launcher)
    try:
        url = f"http://127.0.0.1:{server.server_port}/v1/integrations/wechat/turn"
        _post_json(
            url,
            payload=_turn_payload(text="remote submit the current run"),
            secret=config.shared_secret,
            nonce="nonce-002",
        )
        status_code, payload = _post_json(
            url,
            payload=_turn_payload(
                text=f"CONFIRM {confirmation_id}",
                message_id="msg-002",
            ),
            secret=config.shared_secret,
            nonce="nonce-003",
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status_code == 200
    assert payload["status"] == "ok"
    assert payload["tool_result"]["status"] == "submitted"
    assert "job-123" in payload["reply"]["text"]
    assert launcher_calls[1]["mode"] == "confirmed_tool_request"
    assert launcher_calls[1]["confirmation_id"] == confirmation_id
    assert launcher_calls[1]["workspace"]["root"] == workspace_root
    assert not _confirmation_path(config, confirmation_id).exists()


def test_confirm_same_user_is_enforced_before_execution(tmp_path: Path) -> None:
    module = _load_gateway_module()
    config = _make_config(module, tmp_path)
    workspace_root = str(config.workspaces_root / "alice-main" / ".quantum")
    confirmation_id = "confirm_pending123"
    launcher_calls: list[dict[str, object]] = []

    def _launcher(request_payload: dict[str, object]) -> dict[str, object]:
        launcher_calls.append(request_payload)
        return {
            "status": "confirmation_required",
            "approved_tool_request": {
                "command": "remote submit",
                "workspace_root": workspace_root,
                "options": {
                    "backend": "ibm_kyiv",
                    "intent_file": "intent.md",
                },
                "output_mode": "json",
                "confirmation_id": confirmation_id,
            },
        }

    server, thread = _start_server(module, config=config, launcher=_launcher)
    try:
        url = f"http://127.0.0.1:{server.server_port}/v1/integrations/wechat/turn"
        _post_json(
            url,
            payload=_turn_payload(text="remote submit the current run"),
            secret=config.shared_secret,
            nonce="nonce-004",
        )
        status_code, payload = _post_json(
            url,
            payload=_turn_payload(
                wechat_user_id="wxid_bob",
                text=f"CONFIRM {confirmation_id}",
                message_id="msg-005",
            ),
            secret=config.shared_secret,
            nonce="nonce-005",
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status_code == 409
    assert payload["status"] == "blocked"
    assert payload["reason_codes"] == ["confirm_same_user_required"]
    assert len(launcher_calls) == 1
    assert _confirmation_path(config, confirmation_id).exists()


def test_expired_confirmation_is_blocked_without_execution(tmp_path: Path) -> None:
    module = _load_gateway_module()
    config = _make_config(module, tmp_path)
    workspace_root = str(config.workspaces_root / "alice-main" / ".quantum")
    confirmation_id = "confirm_pending123"
    launcher_calls: list[dict[str, object]] = []

    def _launcher(request_payload: dict[str, object]) -> dict[str, object]:
        launcher_calls.append(request_payload)
        return {
            "status": "confirmation_required",
            "approved_tool_request": {
                "command": "remote submit",
                "workspace_root": workspace_root,
                "options": {
                    "backend": "ibm_kyiv",
                    "intent_file": "intent.md",
                },
                "output_mode": "json",
                "confirmation_id": confirmation_id,
            },
        }

    server, thread = _start_server(module, config=config, launcher=_launcher)
    try:
        url = f"http://127.0.0.1:{server.server_port}/v1/integrations/wechat/turn"
        _post_json(
            url,
            payload=_turn_payload(text="remote submit the current run"),
            secret=config.shared_secret,
            nonce="nonce-006",
        )
        confirmation_path = _confirmation_path(config, confirmation_id)
        stored_confirmation = json.loads(confirmation_path.read_text())
        stored_confirmation["expires_at"] = "2000-01-01T00:00:00Z"
        confirmation_path.write_text(json.dumps(stored_confirmation, indent=2))
        status_code, payload = _post_json(
            url,
            payload=_turn_payload(
                text=f"确认 {confirmation_id}",
                message_id="msg-007",
            ),
            secret=config.shared_secret,
            nonce="nonce-007",
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status_code == 409
    assert payload["status"] == "blocked"
    assert payload["reason_codes"] == ["expired_confirmation"]
    assert len(launcher_calls) == 1
    assert not _confirmation_path(config, confirmation_id).exists()


def test_cancel_confirmation_clears_pending_request_and_blocks_reuse(tmp_path: Path) -> None:
    module = _load_gateway_module()
    config = _make_config(module, tmp_path)
    workspace_root = str(config.workspaces_root / "alice-main" / ".quantum")
    confirmation_id = "confirm_pending123"
    launcher_calls: list[dict[str, object]] = []

    def _launcher(request_payload: dict[str, object]) -> dict[str, object]:
        launcher_calls.append(request_payload)
        return {
            "status": "confirmation_required",
            "approved_tool_request": {
                "command": "remote submit",
                "workspace_root": workspace_root,
                "options": {
                    "backend": "ibm_kyiv",
                    "intent_file": "intent.md",
                },
                "output_mode": "json",
                "confirmation_id": confirmation_id,
            },
        }

    server, thread = _start_server(module, config=config, launcher=_launcher)
    try:
        url = f"http://127.0.0.1:{server.server_port}/v1/integrations/wechat/turn"
        _post_json(
            url,
            payload=_turn_payload(text="remote submit the current run"),
            secret=config.shared_secret,
            nonce="nonce-008",
        )
        cancel_status, cancel_payload = _post_json(
            url,
            payload=_turn_payload(
                text=f"CANCEL {confirmation_id}",
                message_id="msg-009",
            ),
            secret=config.shared_secret,
            nonce="nonce-009",
        )
        confirm_status, confirm_payload = _post_json(
            url,
            payload=_turn_payload(
                text=f"CONFIRM {confirmation_id}",
                message_id="msg-010",
            ),
            secret=config.shared_secret,
            nonce="nonce-010",
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert cancel_status == 200
    assert cancel_payload["status"] == "cancelled"
    assert cancel_payload["reason_codes"] == ["confirmation_cancelled"]
    assert confirm_status == 409
    assert confirm_payload["reason_codes"] == ["missing_confirmation_request"]
    assert len(launcher_calls) == 1
    assert not _confirmation_path(config, confirmation_id).exists()
