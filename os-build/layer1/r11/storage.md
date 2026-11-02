# storage — Round 11 record

Source: `services/storage/storage.goose` · Test: `services/tests/t134_storage_r11.goose` · Status: RUNS

## 1. Limits — PROVEN

`os-build/layer1/LIMITS.md` has **no row for any storage constant**. The generated table does
not pick up this file's module constants, so the audit under-reports the surface rather than
finding an unproven limit. That is a `gen_limits.py` gap and is filed as one, not fixed here.

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `BLOCK_SIZE` | `512` | `storage.goose` | enforced by the buffer type, not a numeric edge | `t54` passes `u8[..512]`; `t134` asserts the constant and the three-comparison identity `RAM_BYTES == BLOCK_SIZE * RAM_BLOCKS` |
| `RAM_BLOCKS` | `64` | `storage.goose` | driven by a test | `t134` calls `storage_init(0)`, `init(-1)` and `init(65)` and expects `E_INVAL`; `init(64)` is accepted |
| `RAM_BYTES` | `32768` | `storage.goose` | derived, not an independent limit | `t134` asserts it equals `BLOCK_SIZE * RAM_BLOCKS` |

## 2. Refusals — PROVEN

| refusal | code | the test assertion that expects it |
|---|---|---|
| read/write/seal/wipe/stats before `storage_init` | `E_NO_DEVICE` | `t134` calls each one on a fresh process and checks the code; `t54` starts at init |
| `storage_init` with a count of zero, negative, or past `RAM_BLOCKS` | `E_INVAL` | `t134` `init(0)`, `init(-1)`, `init(65)` |
| read or write with an LBA below 0 or at/after `block_count` | `E_BAD_BLOCK` | `t134` `read(-1)`, `read(64)`, `write(-1)`, `write(64)`; last valid block 63 still reads |
| write to a sealed device | `E_READ_ONLY` | `t134` seals, writes, expects the code, and checks the write counter did not move |
| a refused write being counted as a write | none — the counter is asserted | `t134` compares `storage_stats` before and after both the LBA refusal and the sealed refusal |

`storage_read`/`storage_write` cannot return `E_INVAL` in the code as written, although the
file header's contract line lists it. The README always listed the true set; the header comment
is the stale one and is noted in §6 rather than edited here.

## 3. Restart — NAMED GAP

The backend is RAM. A process restart loses every block, the write counter and the seal state;
`storage_volatile()` returns `true` and exists so a caller has to ask. This is structural, not
measured: no host driver can restart the service as a process because there is no spawn call.
The loss is named, not softened. A restart that must preserve data needs the Layer 3 block
driver (`B-L1-74`), not a change here.

## 4. Contract — PROVEN

| direction | other service | call | in the matrix? |
|---|---|---|---|
| in | `fs` (`SVC_FS`) | `storage_read` / `storage_write` | yes — `SVC_FS` allows `STORAGE` |
| in | `logd` (`SVC_LOG`) | block records | yes — `SVC_LOG` allows `STORAGE` |
| in | `netcfg` (`SVC_NETCFG`) | persisted configuration | yes — `SVC_NETCFG` allows `STORAGE` |
| in | `updater` (`SVC_UPDATER`) | update content | yes |
| in | `agenthost` (`SVC_AGENTHOST`) | agent storage | yes |
| in | `audit` (`SVC_AUDIT`) | record storage | yes |
| in | `settings`, `wallpaper`, `dock` | face state | yes — each row allows `STORAGE` |
| out | `logd`, `devices` | — | declared on `SVC_STORAGE`, **dormant**: `storage.goose` imports only `common.err` |

No call this service makes is missing from the matrix. The inbound edges are the callers'
rows, not storage's; storage itself calls nothing.

## 5. Load — PROVEN

Five rounds of 64 writes and 64 reads (ten times a normal block batch), all inside the
64-block device, so every call is accepted and any refusal would be a boundary bug.

RUNS pass=38 fail=0 · `LOAD storage ops=640 ok=640 refused=0`

## 6. README truth pass — PROVEN

- `Status: **WRITTEN** (not COMPILED — no Goose toolchain on this Mac)` → `Status: **RUNS**`,
  naming `tests/t54_storage` (26 checks) and the new driver.
- Closing `Not compiled, not run.` → removed; it contradicted the measured run row.
- The contract block now names `storage_init`'s `E_INVAL` range beside read and write, which is
  the refusal a caller hits first.
- `storage_stats()` was described only in the Parameters table; it is now part of the contract
  row's sentence, since the write counter is what two refusals are asserted against.
