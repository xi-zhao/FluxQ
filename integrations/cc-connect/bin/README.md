# FluxQ cc-connect Launcher Assets

`claw` only sees one FluxQ tool surface in this integration: `integrations/cc-connect/bin/fluxq-qrun`.

The wrapper keeps FluxQ external. It accepts a structured JSON request, builds argv for the current shipped `qrun` surface, injects `--workspace` plus `--json` or `--jsonl` when the underlying command supports machine output, and never shells through `bash -lc`.

## Request Format

Read from stdin by default:

```json
{
  "command": "plan",
  "workspace_root": "/srv/fluxq/workspaces/alice/.quantum",
  "options": {
    "intent_file": ".quantum/intents/latest.md"
  },
  "output_mode": "json"
}
```

Or from a file:

```bash
python integrations/cc-connect/bin/fluxq-qrun --request-file request.json
```

Fields:

- `command`: one approved FluxQ command family. Accepts strings like `plan`, `baseline set`, `backend list`, or `remote submit`.
- `workspace_root`: required whenever the shipped `qrun` command supports `--workspace`.
- `args`: positional arguments for commands that use them today. `prompt` takes one prompt string and `schema` takes one schema name.
- `options`: snake_case option names mapped to the shipped `qrun` flags.
- `output_mode`: `json` or `jsonl` when the command supports machine output.
- `confirmation_id`: required for high-risk commands after the wrapper has already returned `confirmation_required`.

## Approved Commands

The shipped matrix is:

- `init`
- `prompt`
- `resolve`
- `plan`
- `status`
- `show`
- `schema`
- `baseline set`
- `baseline show`
- `baseline clear`
- `exec`
- `inspect`
- `compare`
- `doctor`
- `backend list`
- `ibm configure`
- `bench`
- `export`
- `pack`
- `pack-inspect`
- `pack-import`
- `remote submit`

The wrapper rejects truly unshipped remote lifecycle verbs such as `remote cancel`, `remote poll`, `remote reopen`, or `remote finalize`. It also rejects raw shell fragments in the command field instead of trying to interpret them.

## Feishu Bridge Wrapper

`run-lark-cli-bridge` is a local executable shim for the official `lark-cli`
polling route. It loads `integrations/cc-connect/lark_cli_bridge.py` by file path
so the `cc-connect` directory name does not have to become an importable Python
package.

Example:

```bash
export FLUXQ_GATEWAY_SHARED_SECRET=replace-with-random-secret
export FLUXQ_LARK_CHAT_ID=oc_feishu_chat_id
integrations/cc-connect/bin/run-lark-cli-bridge --poll-interval-seconds 2
```

## High-Risk Confirmation

`remote submit` is currently the high-risk FluxQ action because it may create a remote IBM job and may spend quota. A request without a matching `confirmation_id` returns:

- `status = "confirmation_required"`
- the standard summary fields `action`, `input_source`, `workspace`, `backend`, `instance`, `may_create_remote_job`, `may_spend`, and `consequence`
- `confirmation_id` plus `approved_request`, so the next plan layer can present the exact approved command for a second-step user confirmation

Confirmed calls must replay the exact approved request with the matching `confirmation_id`.

## Rejection Behavior

The wrapper emits stable machine-readable blocked payloads for:

- unsupported command families
- unshipped remote lifecycle verbs
- shell fragments in the command field
- unsupported options
- malformed JSON requests
- invalid or mismatched confirmation IDs

These payloads always include `status`, `reason_codes`, `next_actions`, and a `gate` block so the gateway or a future confirmation UX does not have to parse prose.
