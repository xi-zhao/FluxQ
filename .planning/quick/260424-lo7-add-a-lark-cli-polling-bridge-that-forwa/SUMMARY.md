# Quick Task Summary: `lark-cli` Feishu Bridge

## Outcome

Added a local Feishu bridge that lets a configured `lark-cli` app poll bot chat
messages, forward user turns to the existing FluxQ gateway, and send gateway
replies back to the chat.

Implemented assets:

- `integrations/cc-connect/lark_cli_bridge.py`
- `integrations/cc-connect/bin/run-lark-cli-bridge`
- `tests/test_lark_cli_bridge.py`

## Design Notes

- The bridge intentionally stays outside FluxQ runtime internals and speaks to
  the already signed gateway endpoint.
- The payload marks `platform = "feishu"` while preserving the existing
  `wechat_user` field name so the current gateway allowlist and workspace
  isolation code can be reused unchanged.
- The first continuous poll checkpoints existing chat history by default; smoke
  tests can opt into `--process-existing --once`.
- The bin wrapper loads the bridge module by file path because
  `integrations/cc-connect/` is not an importable Python package name.

## Verification

Verified with:

- `uv run pytest tests/test_lark_cli_bridge.py -q`
- `uv run pytest tests/test_lark_cli_bridge.py tests/test_cc_connect_gateway.py tests/test_claw_launcher.py tests/test_wechat_confirmation_flow.py -q`
- `uv run ruff check integrations/cc-connect tests/test_lark_cli_bridge.py`
- `uv run python -m mypy src`
- live Feishu smoke: a real user message was forwarded and the bot replied `Queued request for the local claw launcher.`

## Follow-Up

- Run a live Feishu smoke with the real gateway and the user's authorized
  `lark-cli` app.
- If polling proves stable, optionally add a later Feishu-specific gateway
  envelope name to remove the historical `wechat_user` compatibility wording.
