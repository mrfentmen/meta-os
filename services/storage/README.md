# storage — block contract + RAM backend

Status: **COMPILED** (Lane B R5, 2026-11-04 — build+run log: services/storage/BUILD_LOG.txt; was RUNS on the 2026-11-02 host corpus) — driven by `tests/t54_storage` (26 checks) and
`tests/t134_storage_r11`. Layer 4, service 9.

## Real, not a mock

The RAM backend is real storage: write a block, read it back, the bytes are the
bytes. What it is *not* is persistent — it survives until the process exits.
`storage_volatile()` returns `true` by construction and exists so every caller has
to ask the question by name.

That distinction is the whole point. A mock pretends to be the thing it replaces;
this backend claims exactly what it does. Layer 3 block drivers bind to the same
two calls and nothing above them changes.

## The contract

```
storage_init(blocks)    -> CODE_OK | E_INVAL        (0 < blocks <= RAM_BLOCKS)
storage_read(lba, buf)  -> CODE_OK | E_NO_DEVICE | E_BAD_BLOCK
storage_write(lba, buf) -> CODE_OK | E_NO_DEVICE | E_BAD_BLOCK | E_READ_ONLY
```

- **One block per call.** `buf` is `u8[..512]`, exactly one block. "Up to a block"
  would make every caller responsible for a short-read case the backend already
  knows the answer to.
- **Synchronous, no deadline.** Honest for RAM, not honest for a real controller —
  which is why B-L1-74 has to revisit this signature instead of assuming it. Said
  here so that task cannot skip the question.
- **`storage_lba_ok` is one function** used by both read and write, so the two cannot
  disagree about the boundary. An off-by-one in only one of them is how a
  filesystem's last block becomes untrustworthy.

## Parameters

| Name | Value | Why |
|---|---|---|
| `BLOCK_SIZE` | 512 | the size a PC block driver reports |
| `RAM_BLOCKS` | 64 | 32 KiB: config, records, a test filesystem |
| `storage_seal()` | — | models a device that went write-protected; writes then fail `E_READ_ONLY` |
| `storage_stats()` | (blocks, writes, code) | the number a test asserts on |

## Deliberately absent

No caching (a cache over 32 KiB of RAM is a cache over nothing), no partition
table, no bad-block map, no flush, no async queue. The first three are Layer 3
facts this backend does not have; the flush is meaningless for a volatile store.
Async is real work B-L1-74 inherits.

Driven by `t54_storage` and `t134_storage_r11`; the RAM backend's volatility is
asserted, not assumed.
