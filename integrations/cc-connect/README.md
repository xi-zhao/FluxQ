# FluxQ Personal WeChat `cc-connect` Integration

This guide covers the split-host personal WeChat route:

`personal WeChat -> ilink -> cc-connect (fork) -> claw adapter -> HTTP gateway -> run-claw-agent -> fluxq-qrun -> qrun`

FluxQ stays external in this integration. The WeChat agent and launcher call `qrun ... --json/--jsonl`; they do not embed FluxQ runtime logic into `cc-connect` or `claw`.

## Split-Host Topology

- The ingress host runs the `cc-connect` fork plus `ilink`.
- The execution host runs the thin HTTP gateway plus the local launcher assets under `integrations/cc-connect/bin/`.
- The gateway is transport and policy glue only. FluxQ execution still happens through the shipped CLI surface.

## Ingress Host Setup

Use [`config.toml.example`](./config.toml.example) as the starting point for the `cc-connect` fork.

1. Copy the example into the forked `cc-connect` project config.
2. Run `cc-connect weixin setup --project fluxq-personal`.
3. Fill the returned `ilink` token, base URL, and account ID into the `config.toml`.
4. Point `[claw].gateway_url` at the execution-host `POST /v1/integrations/wechat/turn` endpoint.
5. Set `[claw].shared_secret_env` to the same secret used by the execution host.

The `cc-connect` fork should send one signed payload per message turn and never pass raw workspace paths from the ingress host.

## Execution Host Setup

Gateway env vars:

```bash
export FLUXQ_GATEWAY_HOST=127.0.0.1
export FLUXQ_GATEWAY_PORT=8787
export FLUXQ_GATEWAY_SHARED_SECRET=replace-with-random-secret
export FLUXQ_WECHAT_ALLOWLIST_FILE=/srv/fluxq/gateway/allowlist.json
export FLUXQ_GATEWAY_STATE_ROOT=/srv/fluxq/gateway/state
export FLUXQ_GATEWAY_WORKSPACES_ROOT=/srv/fluxq/workspaces
export FLUXQ_GATEWAY_CONFIRMATION_TTL_SECONDS=600
export FLUXQ_GATEWAY_LAUNCHER_PATH=/abs/path/to/integrations/cc-connect/bin/run-claw-agent
```

Launcher and FluxQ env vars:

```bash
export PATH=\"/abs/path/to/integrations/cc-connect/bin:$PATH\"
export QISKIT_IBM_TOKEN=...            # required only when the workspace uses IBM access
export QISKIT_IBM_INSTANCE=ibm-q/open/main
```

Start the gateway with:

```bash
uv run python integrations/cc-connect/gateway/server.py
```

Then verify:

```bash
curl -fsS http://127.0.0.1:8787/healthz
```

Expected response:

```json
{"status":"ok","service":"fluxq_cc_gateway"}
```

## Allowlist And Workspace Isolation

The allowlist is server-side JSON keyed by personal WeChat user id:

```json
{
  "wechat_users": {
    "wxid_alice": {
      "workspace_key": "alice-main",
      "display_name": "Alice"
    }
  }
}
```

workspace isolation is per allowlisted WeChat user:

- `workspace_key` resolves to `<FLUXQ_GATEWAY_WORKSPACES_ROOT>/<workspace_key>/.quantum`
- the ingress host never supplies `workspace_root`
- confirmation state lives under `<FLUXQ_GATEWAY_STATE_ROOT>/confirmations/`
- transcript state lives under `<FLUXQ_GATEWAY_STATE_ROOT>/conversations/<workspace_key>/<conversation_id>.json`

## High-Risk Confirmation Policy

`remote submit` is currently the high-risk action. It may create a remote IBM job and may spend quota.

The gateway stores a pending confirmation bound to:

- `wechat_user.id`
- `conversation.id`
- `workspace_key`
- `workspace.root`
- the exact approved tool request

The default confirmation TTL is `600` seconds and is controlled by `FLUXQ_GATEWAY_CONFIRMATION_TTL_SECONDS`.

The standard confirmation summary must show:

- `action`
- `input source`
- `workspace`
- `backend / instance`
- `may_create_remote_job`
- `may_spend`
- `consequence`

Only these second-step replies execute the stored request:

- `CONFIRM <id>`
- `确认 <id>`

These replies clear the pending request without execution:

- `CANCEL <id>`
- `取消 <id>`

Any foreign-user, wrong-conversation, stale, or replayed confirmation token must stay blocked.

## FluxQ Boundary

The launcher uses only the shipped FluxQ control-plane wrapper:

- `integrations/cc-connect/bin/run-claw-agent`
- `integrations/cc-connect/bin/fluxq-qrun`

That wrapper turns structured requests into `qrun ... --json/--jsonl` calls. It does not shell through `bash -lc`, and it does not add private runtime shortcuts.

unsupported remote lifecycle verbs remain unavailable:

- `remote cancel`
- `remote poll`
- `remote reopen`
- `remote finalize`

The only shipped high-risk remote operation in this route is `remote submit`.

## Live Smoke

Run this smoke on the real split deployment, not with mocked WeChat or a fake launcher.

1. On the execution host, export the gateway and launcher env vars, start the gateway, and confirm `/healthz` returns `status = ok`.
2. On the ingress host, apply the `cc-connect` fork config, run `cc-connect weixin setup --project fluxq-personal`, and verify the personal WeChat account is online through `ilink`.
3. From an allowlisted account, send a low-risk message such as `show the current FluxQ workspace status and explain what it means`.
4. Expect an explanatory reply with reasoning and risk context, with no confirmation gate.
5. From the same account, send a high-risk message such as `remote submit the current run to ibm_kyiv on ibm-q/open/main`.
6. Expect the standard confirmation summary, including `action`, `input source`, `workspace`, `backend / instance`, `may_create_remote_job`, `may_spend`, and `consequence`.
7. Reply `CONFIRM <id>` or `确认 <id>`.
8. Expect the stored approved request to execute and the reply to include the confirmed result rather than a second natural-language reinterpretation.
9. Send the same confirmation token from a different account or after the TTL expires.
10. Expect the request to stay blocked.
