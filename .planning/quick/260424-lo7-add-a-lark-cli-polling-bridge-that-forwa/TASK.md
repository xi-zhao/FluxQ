# Quick Task: `lark-cli` Feishu Bridge

- Quick ID: `260424-lo7`
- Date: `2026-04-24`
- Description: Add a local `lark-cli` polling bridge that forwards Feishu bot chat messages to the existing FluxQ gateway and replies through the official Feishu CLI app.

## Scope

Create a single-machine Feishu route that:

- uses the official `lark-cli` app for Feishu auth, message polling, and bot replies
- keeps FluxQ external by forwarding each user turn to the existing signed gateway
- reuses the existing gateway allowlist and launcher contract without embedding Feishu logic into FluxQ runtime internals
- can checkpoint old chat history by default and optionally process existing messages for smoke tests
- ships with focused tests and operator documentation

## Locked Decisions

- Transport: `lark-cli` polling first, not WebSocket event subscription.
- Gateway contract: reuse `/v1/integrations/wechat/turn` and the existing `wechat_user` envelope field for compatibility.
- Runtime boundary: the bridge only transports messages; `run-claw-agent`, `fluxq-qrun`, and `qrun` remain the execution path.
- Safety: first continuous poll checkpoints existing history unless `--process-existing` is set.

## Guardrails

- Do not deep-embed Qcli/FluxQ inside Feishu or claw-code internals.
- Do not add a second gateway implementation for Feishu until the compatibility path is proven.
- Keep secrets in environment variables; do not persist them in repo files.
