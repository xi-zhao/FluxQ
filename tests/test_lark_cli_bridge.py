from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_PATH = PROJECT_ROOT / "integrations" / "cc-connect" / "lark_cli_bridge.py"
WRAPPER_PATH = PROJECT_ROOT / "integrations" / "cc-connect" / "bin" / "run-lark-cli-bridge"


def _load_bridge_module() -> Any:
    assert BRIDGE_PATH.exists(), f"Missing bridge module: {BRIDGE_PATH}"
    loader = SourceFileLoader("lark_cli_bridge_test_module", str(BRIDGE_PATH))
    spec = importlib.util.spec_from_loader("lark_cli_bridge_test_module", loader)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_poll_once_forwards_new_user_message_to_gateway_and_replies(tmp_path: Path) -> None:
    module = _load_bridge_module()
    state_file = tmp_path / "state.json"
    runner_calls: list[list[str]] = []
    gateway_payloads: list[dict[str, object]] = []

    def _runner(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        runner_calls.append(argv)
        if argv[:3] == ["lark-cli", "im", "+chat-messages-list"]:
            stdout = json.dumps(
                {
                    "ok": True,
                    "data": {
                        "messages": [
                            {
                                "message_id": "om_new",
                                "content": "你好",
                                "create_time": "2026-04-24 15:31",
                                "msg_type": "text",
                                "sender": {
                                    "id": "ou_alice",
                                    "id_type": "open_id",
                                    "name": "Alice",
                                    "sender_type": "user",
                                },
                            },
                            {
                                "message_id": "om_bot",
                                "content": "previous bot turn",
                                "create_time": "2026-04-24 15:30",
                                "msg_type": "text",
                                "sender": {
                                    "id": "cli_bot",
                                    "id_type": "app_id",
                                    "sender_type": "app",
                                },
                            },
                        ]
                    },
                }
            )
            return subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr="")
        if argv[:3] == ["lark-cli", "im", "+messages-send"]:
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"ok": True}), stderr="")
        raise AssertionError(f"Unexpected command: {argv}")

    def _gateway_post(payload: dict[str, object]) -> dict[str, object]:
        gateway_payloads.append(payload)
        return {
            "status": "ok",
            "reply": {
                "kind": "text",
                "text": "FluxQ gateway reply",
            },
            "reason_codes": ["launcher_request_ready"],
        }

    config = module.BridgeConfig(
        chat_id="oc_chat",
        gateway_url="http://127.0.0.1:8787/v1/integrations/wechat/turn",
        shared_secret="secret",
        state_file=state_file,
        process_existing=True,
    )

    summary = module.poll_once(config, runner=_runner, gateway_post=_gateway_post)

    assert summary["processed"] == 1
    assert len(gateway_payloads) == 1
    assert gateway_payloads[0]["platform"] == "feishu"
    assert gateway_payloads[0]["wechat_user"] == {
        "id": "ou_alice",
        "display_name": "Alice",
    }
    assert gateway_payloads[0]["conversation"] == {
        "id": "oc_chat",
        "message_id": "om_new",
    }
    assert gateway_payloads[0]["message"] == {
        "text": "你好",
        "received_at": "2026-04-24 15:31",
    }
    assert any("FluxQ gateway reply" in argv for argv in runner_calls[-1])
    assert json.loads(state_file.read_text())["last_message_id"] == "om_new"


def test_first_poll_can_checkpoint_without_replaying_existing_history(tmp_path: Path) -> None:
    module = _load_bridge_module()
    state_file = tmp_path / "state.json"
    gateway_payloads: list[dict[str, object]] = []

    def _runner(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert argv[:3] == ["lark-cli", "im", "+chat-messages-list"]
        stdout = json.dumps(
            {
                "ok": True,
                "data": {
                    "messages": [
                        {
                            "message_id": "om_existing",
                            "content": "old message",
                            "create_time": "2026-04-24 15:31",
                            "msg_type": "text",
                            "sender": {
                                "id": "ou_alice",
                                "id_type": "open_id",
                                "name": "Alice",
                                "sender_type": "user",
                            },
                        }
                    ]
                },
            }
        )
        return subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr="")

    config = module.BridgeConfig(
        chat_id="oc_chat",
        gateway_url="http://127.0.0.1:8787/v1/integrations/wechat/turn",
        shared_secret="secret",
        state_file=state_file,
        process_existing=False,
    )

    summary = module.poll_once(config, runner=_runner, gateway_post=gateway_payloads.append)

    assert summary["processed"] == 0
    assert summary["checkpointed"] == "om_existing"
    assert gateway_payloads == []
    assert json.loads(state_file.read_text())["last_message_id"] == "om_existing"


def test_bin_wrapper_loads_bridge_module_help() -> None:
    completed = subprocess.run(
        [sys.executable, str(WRAPPER_PATH), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "Poll lark-cli messages into the FluxQ gateway." in completed.stdout
