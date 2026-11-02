# Integration packs, first three services (BF5-06)

One pack per service, for the first three in the 2026-11-02 load order (`LOAD_ORDER_1102.md`):
`bootlog`, `storage`, `time`. Each pack answers four questions with the repo as evidence:

1. **What is the entry point**, exactly — the symbol the loader jumps to and its signature.
2. **What does it need from the kernel**, cell by cell against the F1 freeze, not in prose.
3. **What does it run on today**, which is the host shim, and what that means for the claim.
4. **What is the smallest kernel-side change** that would load it, and the exact line that proves
   the change worked.

| Pack | Service | Load order | ABI class | Native today |
|---|---|---|---|---|
| [`bootlog.md`](bootlog.md) | `bootlog` | 1 | needs P1 (`sys_ticks`) | RUNS (t49, 23 checks) + starts in the rehearsal |
| [`storage.md`](storage.md) | `storage` | 4 | library, no kernel calls | RUNS (t54, 26 checks); no entry point yet |
| [`time.md`](time.md) | `time` | 3 | needs P1 (`sys_ticks`) | RUNS (t51, 24 checks) + starts in the rehearsal |

`storage` is ahead of `time` in the load order table only if you read the order column, not the
`order` field: the table has `time` at order 3 and `storage` at order 4. The packs are listed here in
the order the boss said "first three", which is bootlog, time, storage.

## The honest summary of all three

- **One of the three (`storage`) needs no new syscall at all.** Its kernel-side cost is the loader.
- **Two of the three need `sys_ticks`** (proposal P1). Without it, `bootlog` prints `0` for every
  timestamp and `time` cannot verify that the clock advanced, so it returns 2 and the supervisor
  records a failure.
- **All three need the same loader work**: one static image mapped at a fixed address, `svc_entry`
  called with the agreed convention, and a started/ready line each. That is `BOOT_PLAN.md` S1–S3 —
  one mechanism, three services, and the fourth (`console`) is where a hang becomes possible.
