---
status: partial
phase: 05-verified-delivery-bundles
source:
  - 05-VERIFICATION.md
started: 2026-04-14T13:56:38Z
updated: 2026-04-14T13:56:38Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. 跨目录终端流复核
expected: 在真实 shell 中执行 `qrun pack -> 复制 bundle -> qrun pack-inspect -> qrun pack-import -> qrun compare/export/bench/doctor` 后，源 workspace 删除也不影响 bundle 校验，导入后的目标 workspace 能继续复用该 revision evidence，且 provenance / replay_integrity 保持 ok。
result: [pending]

### 2. 错误 JSON 可用性复核
expected: `invalid_revision`、`bundle_digest_mismatch`、`pack_revision_conflict` 的 JSON 输出中，`reason`、`error_code`、`remediation` 足够清晰，可直接支持操作者和 CI 排障。
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
