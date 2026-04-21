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

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = PROJECT_ROOT / "integrations" / "cc-connect" / "gateway" / "server.py"


def _load_gateway_module():
    assert SERVER_PATH.exists(), f"Gateway server module missing: {SERVER_PATH}"
    spec = importlib.util.spec_from_file_location("cc_connect_gateway_server", SERVER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _seed_allowlist(path: Path, *, wechat_user_id: str, workspace_key: str) -> None:
    path.write_text(
        json.dumps(
            {
                "wechat_users": {
                    wechat_user_id: {
                        "workspace_key": workspace_key,
                        "display_name": "Alice",
                    }
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


def _base_payload() -> dict[str, object]:
    return {
        "project": "fluxq-personal",
        "platform": "weixin",
        "wechat_user": {
            "id": "wxid_alice",
            "display_name": "Alice",
        },
        "conversation": {
            "id": "conv-123",
            "message_id": "msg-456",
        },
        "message": {
            "text": "Inspect the latest workspace status.",
            "received_at": "2026-04-21T08:55:00Z",
        },
    }


def _make_config(module, tmp_path: Path):
    allowlist_file = tmp_path / "allowlist.json"
    state_root = tmp_path / "state"
    workspaces_root = tmp_path / "workspaces"
    _seed_allowlist(allowlist_file, wechat_user_id="wxid_alice", workspace_key="alice-main")
    state_root.mkdir()
    workspaces_root.mkdir()
    return module.GatewayConfig(
        shared_secret="test-shared-secret",
        allowlist_file=allowlist_file,
        workspaces_root=workspaces_root,
        state_root=state_root,
    )


def _start_server(module, *, config, launcher=None):
    server = module.build_server(
        host="127.0.0.1",
        port=0,
        config=config,
        launcher=launcher,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _post_json(url: str, *, payload: dict[str, object], secret: str, headers: dict[str, str] | None = None):
    body = json.dumps(payload).encode("utf-8")
    timestamp = str(int(time.time()))
    nonce = "nonce-123"
    signed_headers = {
        "Content-Type": "application/json",
        "X-FluxQ-Timestamp": timestamp,
        "X-FluxQ-Nonce": nonce,
        "X-FluxQ-Signature": _sign(secret, timestamp=timestamp, nonce=nonce, body=body),
    }
    if headers:
        signed_headers.update(headers)
    request = urllib.request.Request(url, data=body, headers=signed_headers, method="POST")
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


@pytest.mark.parametrize(
    ("headers", "expected_reason_code"),
    [
        (
            {
                "X-FluxQ-Timestamp": "",
            },
            "missing_timestamp_header",
        ),
        (
            {
                "X-FluxQ-Nonce": "",
            },
            "missing_nonce_header",
        ),
        (
            {
                "X-FluxQ-Signature": "",
            },
            "missing_signature_header",
        ),
        (
            {
                "X-FluxQ-Signature": "invalid-signature",
            },
            "invalid_signature",
        ),
    ],
)
def test_invalid_signature_headers_return_blocked_payload_without_launcher_call(
    tmp_path: Path,
    headers: dict[str, str],
    expected_reason_code: str,
) -> None:
    module = _load_gateway_module()
    config = _make_config(module, tmp_path)
    launcher_calls: list[dict[str, object]] = []

    def _launcher(request_payload: dict[str, object]) -> dict[str, object]:
        launcher_calls.append(request_payload)
        return {}

    server, thread = _start_server(module, config=config, launcher=_launcher)
    try:
        url = f"http://127.0.0.1:{server.server_port}/v1/integrations/wechat/turn"
        status_code, payload = _post_json(
            url,
            payload=_base_payload(),
            secret=config.shared_secret,
            headers=headers,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status_code == 401
    assert payload["status"] == "blocked"
    assert payload["reason_codes"] == [expected_reason_code]
    assert payload["gate"]["ready"] is False
    assert launcher_calls == []


def test_allowlist_miss_returns_403_without_workspace_side_effects(tmp_path: Path) -> None:
    module = _load_gateway_module()
    config = _make_config(module, tmp_path)
    config.allowlist_file.write_text(json.dumps({"wechat_users": {}}, indent=2))
    launcher_calls: list[dict[str, object]] = []

    def _launcher(request_payload: dict[str, object]) -> dict[str, object]:
        launcher_calls.append(request_payload)
        return {}

    server, thread = _start_server(module, config=config, launcher=_launcher)
    try:
        url = f"http://127.0.0.1:{server.server_port}/v1/integrations/wechat/turn"
        status_code, payload = _post_json(
            url,
            payload=_base_payload(),
            secret=config.shared_secret,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status_code == 403
    assert payload["status"] == "blocked"
    assert payload["reason_codes"] == ["wechat_user_not_allowlisted"]
    assert payload["gate"]["ready"] is False
    assert launcher_calls == []
    assert not (config.workspaces_root / "alice-main").exists()


def test_allowlisted_user_uses_server_side_workspace_root(tmp_path: Path) -> None:
    module = _load_gateway_module()
    config = _make_config(module, tmp_path)
    launcher_calls: list[dict[str, object]] = []

    def _launcher(request_payload: dict[str, object]) -> dict[str, object]:
        launcher_calls.append(request_payload)
        return {
            "reply": {
                "kind": "text",
                "text": "Queued request for the local claw launcher.",
            },
            "reason_codes": ["launcher_request_ready"],
            "next_actions": ["run_claw_launcher"],
            "gate": {
                "ready": True,
                "status": "open",
                "severity": "info",
                "recommended_action": "run_claw_launcher",
                "reason_codes": ["launcher_request_ready"],
                "next_actions": ["run_claw_launcher"],
            },
            "confirmation": {
                "pending": False,
            },
        }

    server, thread = _start_server(module, config=config, launcher=_launcher)
    try:
        url = f"http://127.0.0.1:{server.server_port}/v1/integrations/wechat/turn"
        payload = _base_payload()
        payload["workspace_root"] = "/tmp/attacker"
        payload["qrun_args"] = ["--workspace", "/tmp/attacker"]
        payload["shell_command"] = "rm -rf /tmp/attacker"
        status_code, response = _post_json(
            url,
            payload=payload,
            secret=config.shared_secret,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    expected_root = str(config.workspaces_root / "alice-main" / ".quantum")

    assert status_code == 200
    assert response["status"] == "ok"
    assert response["workspace"]["workspace_key"] == "alice-main"
    assert response["workspace"]["root"] == expected_root
    assert response["launcher_request"]["workspace"]["workspace_key"] == "alice-main"
    assert response["launcher_request"]["workspace"]["root"] == expected_root
    assert "workspace_root" not in response["launcher_request"]
    assert "qrun_args" not in response["launcher_request"]
    assert "shell_command" not in response["launcher_request"]
    assert launcher_calls[0]["workspace"]["root"] == expected_root


def test_stale_or_replayed_nonce_requests_are_blocked(tmp_path: Path) -> None:
    module = _load_gateway_module()
    config = _make_config(module, tmp_path)
    launcher_calls: list[dict[str, object]] = []

    def _launcher(request_payload: dict[str, object]) -> dict[str, object]:
        launcher_calls.append(request_payload)
        return {}

    server, thread = _start_server(module, config=config, launcher=_launcher)
    try:
        url = f"http://127.0.0.1:{server.server_port}/v1/integrations/wechat/turn"
        body = json.dumps(_base_payload()).encode("utf-8")
        stale_timestamp = str(int(time.time()) - 301)
        stale_nonce = "stale-nonce"
        stale_headers = {
            "Content-Type": "application/json",
            "X-FluxQ-Timestamp": stale_timestamp,
            "X-FluxQ-Nonce": stale_nonce,
            "X-FluxQ-Signature": _sign(
                config.shared_secret,
                timestamp=stale_timestamp,
                nonce=stale_nonce,
                body=body,
            ),
        }
        stale_request = urllib.request.Request(url, data=body, headers=stale_headers, method="POST")
        with pytest.raises(urllib.error.HTTPError) as stale_error:
            urllib.request.urlopen(stale_request)

        timestamp = str(int(time.time()))
        nonce = "replayed-nonce"
        replay_headers = {
            "Content-Type": "application/json",
            "X-FluxQ-Timestamp": timestamp,
            "X-FluxQ-Nonce": nonce,
            "X-FluxQ-Signature": _sign(
                config.shared_secret,
                timestamp=timestamp,
                nonce=nonce,
                body=body,
            ),
        }
        request = urllib.request.Request(url, data=body, headers=replay_headers, method="POST")
        with urllib.request.urlopen(request) as first_response:
            assert first_response.status == 200

        with pytest.raises(urllib.error.HTTPError) as replay_error:
            urllib.request.urlopen(request)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    stale_payload = json.loads(stale_error.value.read().decode("utf-8"))
    replay_payload = json.loads(replay_error.value.read().decode("utf-8"))
    assert stale_payload["reason_codes"] == ["timestamp_skew_exceeded"]
    assert replay_payload["reason_codes"] == ["nonce_replayed"]
    assert launcher_calls == [launcher_calls[0]]


def test_response_envelope_exposes_reason_codes_gate_and_confirmation(tmp_path: Path) -> None:
    module = _load_gateway_module()
    config = _make_config(module, tmp_path)

    def _launcher(_: dict[str, object]) -> dict[str, object]:
        return {
            "reply": {
                "kind": "text",
                "text": "Queued request for the local claw launcher.",
            },
            "reason_codes": ["launcher_request_ready"],
            "next_actions": ["run_claw_launcher"],
            "gate": {
                "ready": True,
                "status": "open",
                "severity": "info",
                "recommended_action": "run_claw_launcher",
                "reason_codes": ["launcher_request_ready"],
                "next_actions": ["run_claw_launcher"],
            },
            "confirmation": {
                "pending": False,
            },
        }

    server, thread = _start_server(module, config=config, launcher=_launcher)
    try:
        url = f"http://127.0.0.1:{server.server_port}/v1/integrations/wechat/turn"
        status_code, payload = _post_json(
            url,
            payload=_base_payload(),
            secret=config.shared_secret,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status_code == 200
    assert payload["conversation"]["id"] == "conv-123"
    assert payload["conversation"]["message_id"] == "msg-456"
    assert payload["launcher_request"]["message"]["text"] == "Inspect the latest workspace status."
    assert payload["reply"]["kind"] == "text"
    assert payload["reply"]["text"] == "Queued request for the local claw launcher."
    assert payload["reason_codes"] == ["launcher_request_ready"]
    assert payload["next_actions"] == ["run_claw_launcher"]
    assert payload["gate"]["ready"] is True
    assert payload["confirmation"]["pending"] is False
