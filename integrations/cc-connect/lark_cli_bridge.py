"""Polling bridge from `lark-cli` messages into the FluxQ gateway."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import subprocess
import time
import uuid
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence


Runner = Callable[..., subprocess.CompletedProcess[str]]
GatewayPost = Callable[[dict[str, object]], dict[str, object]]


@dataclass(frozen=True)
class BridgeConfig:
    """Runtime configuration for the local `lark-cli` polling bridge."""

    chat_id: str
    gateway_url: str
    shared_secret: str
    state_file: Path
    project: str = "fluxq-feishu"
    lark_cli_bin: str = "lark-cli"
    page_size: int = 20
    process_existing: bool = False
    gateway_timeout_seconds: int = 60


@dataclass(frozen=True)
class LarkMessage:
    """Normalized subset of a Feishu/Lark message needed by the gateway."""

    message_id: str
    text: str
    created_at: str
    sender_id: str
    sender_name: str


def poll_once(
    config: BridgeConfig,
    *,
    runner: Runner = subprocess.run,
    gateway_post: GatewayPost | None = None,
) -> dict[str, object]:
    """Read one page of Lark messages, forward new user turns, and send replies."""

    state = _load_state(config.state_file)
    messages = _list_messages(config, runner=runner)
    user_messages = _user_messages(messages)
    last_message_id = _state_last_message_id(state)

    if last_message_id is None and not config.process_existing:
        checkpoint = user_messages[0].message_id if user_messages else None
        if checkpoint is not None:
            _save_state(config.state_file, {"last_message_id": checkpoint})
        return {
            "processed": 0,
            "checkpointed": checkpoint,
        }

    new_messages = _new_messages(user_messages, last_message_id)
    post = gateway_post or (lambda payload: post_to_gateway(config, payload))
    processed = 0
    sent_replies: list[str] = []

    for message in new_messages:
        gateway_payload = _gateway_payload(config, message)
        gateway_response = post(gateway_payload)
        reply_text = _reply_text(gateway_response)
        _send_reply(config, reply_text, runner=runner)
        _save_state(config.state_file, {"last_message_id": message.message_id})
        processed += 1
        sent_replies.append(message.message_id)

    return {
        "processed": processed,
        "forwarded_message_ids": sent_replies,
    }


def post_to_gateway(config: BridgeConfig, payload: dict[str, object]) -> dict[str, object]:
    """POST one signed gateway turn and return the JSON response."""

    raw_body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    timestamp = str(int(time.time()))
    nonce = f"lark-{uuid.uuid4().hex}"
    signature = _sign_request(
        config.shared_secret,
        timestamp=timestamp,
        nonce=nonce,
        raw_body=raw_body,
    )
    request = urllib.request.Request(
        config.gateway_url,
        data=raw_body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-FluxQ-Timestamp": timestamp,
            "X-FluxQ-Nonce": nonce,
            "X-FluxQ-Signature": signature,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=config.gateway_timeout_seconds) as response:
            return _decode_json_response(response.read())
    except urllib.error.HTTPError as exc:
        return _decode_json_response(exc.read())


def run_loop(
    config: BridgeConfig,
    *,
    poll_interval_seconds: float,
    once: bool,
    runner: Runner = subprocess.run,
) -> None:
    """Run the polling bridge until interrupted, printing summaries as JSON lines."""

    while True:
        summary = poll_once(config, runner=runner)
        print(json.dumps(summary, ensure_ascii=True), flush=True)
        if once:
            return
        time.sleep(poll_interval_seconds)


def _load_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text())
    return payload if isinstance(payload, dict) else {}


def _save_state(path: Path, state: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(state), indent=2, sort_keys=True, ensure_ascii=True))


def _state_last_message_id(state: Mapping[str, object]) -> str | None:
    value = state.get("last_message_id")
    return value if isinstance(value, str) and value else None


def _list_messages(config: BridgeConfig, *, runner: Runner) -> list[dict[str, object]]:
    completed = runner(
        [
            config.lark_cli_bin,
            "im",
            "+chat-messages-list",
            "--as",
            "user",
            "--chat-id",
            config.chat_id,
            "--page-size",
            str(config.page_size),
        ],
        capture_output=True,
        text=True,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"lark-cli message list failed: {completed.stderr.strip()}")
    payload = json.loads(completed.stdout)
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        raise RuntimeError("lark-cli message list returned non-ok payload")
    data = payload.get("data")
    if not isinstance(data, dict):
        return []
    messages = data.get("messages")
    if not isinstance(messages, list):
        return []
    return [message for message in messages if isinstance(message, dict)]


def _user_messages(messages: Sequence[Mapping[str, object]]) -> list[LarkMessage]:
    user_messages: list[LarkMessage] = []
    for raw_message in messages:
        sender = raw_message.get("sender")
        if not isinstance(sender, Mapping) or sender.get("sender_type") != "user":
            continue
        message_id = raw_message.get("message_id")
        content = raw_message.get("content")
        sender_id = sender.get("id")
        if not isinstance(message_id, str) or not message_id:
            continue
        if not isinstance(content, str) or not content:
            continue
        if not isinstance(sender_id, str) or not sender_id:
            continue
        created_at = raw_message.get("create_time")
        sender_name = sender.get("name")
        user_messages.append(
            LarkMessage(
                message_id=message_id,
                text=content,
                created_at=created_at if isinstance(created_at, str) else "",
                sender_id=sender_id,
                sender_name=sender_name if isinstance(sender_name, str) and sender_name else sender_id,
            )
        )
    return user_messages


def _new_messages(messages_desc: Sequence[LarkMessage], last_message_id: str | None) -> list[LarkMessage]:
    if last_message_id is None:
        return list(reversed(messages_desc))

    pending: list[LarkMessage] = []
    for message in messages_desc:
        if message.message_id == last_message_id:
            break
        pending.append(message)
    return list(reversed(pending))


def _gateway_payload(config: BridgeConfig, message: LarkMessage) -> dict[str, object]:
    return {
        "project": config.project,
        "platform": "feishu",
        "wechat_user": {
            "id": message.sender_id,
            "display_name": message.sender_name,
        },
        "conversation": {
            "id": config.chat_id,
            "message_id": message.message_id,
        },
        "message": {
            "text": message.text,
            "received_at": message.created_at,
        },
    }


def _reply_text(gateway_response: Mapping[str, object]) -> str:
    reply = gateway_response.get("reply")
    if isinstance(reply, Mapping):
        text = reply.get("text")
        if isinstance(text, str) and text:
            return text

    reason_codes = gateway_response.get("reason_codes")
    if isinstance(reason_codes, list):
        reason_text = ", ".join(str(reason) for reason in reason_codes)
    else:
        reason_text = "unknown_gateway_result"
    return f"FluxQ gateway returned no text reply. reason_codes={reason_text}"


def _send_reply(config: BridgeConfig, text: str, *, runner: Runner) -> None:
    completed = runner(
        [
            config.lark_cli_bin,
            "im",
            "+messages-send",
            "--as",
            "bot",
            "--chat-id",
            config.chat_id,
            "--text",
            text,
        ],
        capture_output=True,
        text=True,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"lark-cli reply send failed: {completed.stderr.strip()}")


def _decode_json_response(raw_body: bytes) -> dict[str, object]:
    payload = json.loads(raw_body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("gateway returned non-object JSON")
    return payload


def _sign_request(secret: str, *, timestamp: str, nonce: str, raw_body: bytes) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        msg=f"{timestamp}\n{nonce}\n".encode("utf-8") + raw_body,
        digestmod=hashlib.sha256,
    )
    return digest.hexdigest()


def _build_config(args: argparse.Namespace) -> BridgeConfig:
    shared_secret = os.environ.get(args.shared_secret_env)
    if shared_secret is None or not shared_secret.strip():
        raise SystemExit(f"missing shared secret env: {args.shared_secret_env}")
    chat_id = args.chat_id or os.environ.get("FLUXQ_LARK_CHAT_ID")
    if chat_id is None or not chat_id.strip():
        raise SystemExit("missing --chat-id or FLUXQ_LARK_CHAT_ID")
    return BridgeConfig(
        chat_id=chat_id,
        gateway_url=args.gateway_url,
        shared_secret=shared_secret,
        state_file=Path(args.state_file),
        project=args.project,
        lark_cli_bin=args.lark_cli_bin,
        page_size=args.page_size,
        process_existing=args.process_existing,
        gateway_timeout_seconds=args.gateway_timeout_seconds,
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Poll lark-cli messages into the FluxQ gateway.")
    parser.add_argument("--chat-id", default=None)
    parser.add_argument(
        "--gateway-url",
        default="http://127.0.0.1:8787/v1/integrations/wechat/turn",
    )
    parser.add_argument("--shared-secret-env", default="FLUXQ_GATEWAY_SHARED_SECRET")
    parser.add_argument("--state-file", default="/tmp/fluxq-lark-cli-bridge-state.json")
    parser.add_argument("--project", default="fluxq-feishu")
    parser.add_argument("--lark-cli-bin", default="lark-cli")
    parser.add_argument("--page-size", type=int, default=20)
    parser.add_argument("--gateway-timeout-seconds", type=int, default=60)
    parser.add_argument("--poll-interval-seconds", type=float, default=2.0)
    parser.add_argument("--process-existing", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    config = _build_config(args)
    run_loop(
        config,
        poll_interval_seconds=args.poll_interval_seconds,
        once=args.once,
    )


if __name__ == "__main__":
    main()
