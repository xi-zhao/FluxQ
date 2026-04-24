# Runtime Adoption Workflow

FluxQ adoption works best when every host and CI job reuses one runtime contract: ingress becomes a canonical `QSpec`, execution produces a revisioned workspace, policy gates decide whether the run may continue, and delivery handoff moves only verified bundles downstream.

## Canonical Loop

Use one exact runtime loop for docs, agent hosts, and CI jobs:

```bash
qrun prompt "Build a 4-qubit GHZ circuit and measure all qubits." --json
qrun resolve --workspace .quantum --intent-file examples/intent-ghz.md --json
qrun init --workspace .quantum --json
qrun plan --workspace .quantum --intent-file examples/intent-ghz.md --json
qrun exec --workspace .quantum --intent-file examples/intent-ghz.md --jsonl
qrun baseline set --workspace .quantum --revision rev_000001 --json
qrun compare --workspace .quantum --baseline --fail-on subject_drift --json
qrun doctor --workspace .quantum --json --ci
qrun pack --workspace .quantum --revision rev_000001 --json
qrun pack-inspect --pack-root .quantum/packs/rev_000001 --json
qrun pack-import --pack-root .quantum/packs/rev_000001 --workspace downstream/.quantum --json
```

This loop is the reusable adoption path for SURF-02: ingress, execution, policy evaluation, and verified delivery handoff all stay on one command contract.

## Agent Host Loop

Host agents should write intents to files, call FluxQ through shell commands, and read machine-readable JSON back from the workspace.

Recommended host behavior:

- keep `.quantum/intents/latest.md` as the current ingress file
- run `plan` before `exec` so the host can inspect feasibility without mutating the workspace
- read `status`, `show`, `compare`, and `doctor` payloads instead of guessing from generated code
- revise the intent and rerun FluxQ when policy gates fail

For a concrete host-facing variant of the same workflow, see [aionrs Integration](./aionrs-integration.md).

## CI Gate

CI should treat `compare` and `doctor` as the canonical policy checkpoints for one selected revision.

- `qrun compare --workspace .quantum --baseline --fail-on subject_drift --json` enforces subject identity before promotion.
- `qrun doctor --workspace .quantum --json --ci` turns runtime health into a machine-readable verdict.
- machine consumers should read `reason_codes`, `next_actions`, and `gate` rather than inferring status from free-form logs

If either command reports a blocking `gate`, stop the pipeline, update the intent or environment, and rerun FluxQ. Do not patch generated artifacts to make CI pass.

## Delivery Handoff

Delivery starts only after compare and doctor pass.

- `qrun pack --workspace .quantum --revision rev_000001 --json` creates the portable bundle for the approved revision
- `qrun pack-inspect --pack-root .quantum/packs/rev_000001 --json` verifies the copied bundle with bundle-local evidence
- `qrun pack-import --pack-root .quantum/packs/rev_000001 --workspace downstream/.quantum --json` seeds the downstream workspace only after inspection succeeds

The ordering matters: inspect the bundle before importing it, and keep downstream consumers on the same `reason_codes` / `next_actions` / `gate` contract used by compare and doctor.
