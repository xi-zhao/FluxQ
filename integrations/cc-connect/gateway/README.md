# FluxQ `cc-connect` Gateway

This directory defines the split-host transport seam for personal WeChat ingress:

`ilink -> cc-connect (fork) -> claw adapter -> HTTP gateway -> local launcher`

This is a thin execution gateway in front of a launcher. It is not a standalone bridge
service, and it does not use SSH as a fallback transport.

## Endpoints

- `GET /healthz`
- `POST /v1/integrations/wechat/turn`

## Request Contract

The `cc-connect` fork should send one signed JSON payload per allowlisted turn:

```json
{
  "project": "fluxq-personal",
  "platform": "weixin",
  "wechat_user": {
    "id": "wxid_alice",
    "display_name": "Alice"
  },
  "conversation": {
    "id": "conv-123",
    "message_id": "msg-456"
  },
  "message": {
    "text": "Inspect the latest workspace status.",
    "received_at": "2026-04-21T08:55:00Z"
  }
}
```

Required request fields:

- `project`
- `platform`
- `wechat_user.id`
- `wechat_user.display_name`
- `conversation.id`
- `conversation.message_id`
- `message.text`
- `message.received_at`

## Auth Envelope

The gateway requires these headers on every `POST /v1/integrations/wechat/turn` request:

- `X-FluxQ-Timestamp`
- `X-FluxQ-Nonce`
- `X-FluxQ-Signature`

`X-FluxQ-Signature` must be the lowercase hex HMAC-SHA256 digest of:

`timestamp + "\n" + nonce + "\n" + raw_body`

The shared secret comes from `FLUXQ_GATEWAY_SHARED_SECRET`.

Replay protection rules:

- reject clock skew over five minutes
- reject duplicate nonces persisted under `FLUXQ_GATEWAY_STATE_ROOT`
- reject the request before any launcher work if headers or signature are invalid

## Response Contract

The gateway responds with a thin machine-readable envelope:

```json
{
  "status": "ok",
  "conversation": {
    "id": "conv-123",
    "message_id": "msg-456"
  },
  "workspace": {
    "workspace_key": "alice-main",
    "root": "/srv/fluxq/workspaces/alice-main/.quantum"
  },
  "reply": {
    "kind": "text",
    "text": "Queued request for the local claw launcher."
  },
  "confirmation": {
    "pending": false
  },
  "reason_codes": [
    "launcher_request_ready"
  ],
  "next_actions": [
    "run_claw_launcher"
  ],
  "gate": {
    "ready": true,
    "status": "open",
    "severity": "info",
    "recommended_action": "run_claw_launcher",
    "reason_codes": [
      "launcher_request_ready"
    ],
    "next_actions": [
      "run_claw_launcher"
    ]
  },
  "launcher_request": {
    "project": "fluxq-personal",
    "platform": "weixin",
    "workspace": {
      "workspace_key": "alice-main",
      "root": "/srv/fluxq/workspaces/alice-main/.quantum"
    },
    "conversation": {
      "id": "conv-123",
      "message_id": "msg-456"
    },
    "wechat_user": {
      "id": "wxid_alice",
      "display_name": "Alice"
    },
    "message": {
      "text": "Inspect the latest workspace status.",
      "received_at": "2026-04-21T08:55:00Z"
    }
  }
}
```

Required response fields:

- `status`
- `conversation`
- `workspace`
- `reply`
- `confirmation.pending`
- `reason_codes`
- `next_actions`
- `gate`

`launcher_request` is included for the execution host handoff. The gateway stays thin:
it authenticates, normalizes, allowlists, and routes to a local launcher without
reimplementing FluxQ runtime semantics.

## Allowlist Format

Set `FLUXQ_WECHAT_ALLOWLIST_FILE` to a JSON file shaped like:

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

The gateway resolves `wechat_user.id` to the server-side `workspace_key` and computes
the only valid execution root as:

`<FLUXQ_GATEWAY_WORKSPACES_ROOT>/<workspace_key>/.quantum`

Callers never provide raw workspace paths.
