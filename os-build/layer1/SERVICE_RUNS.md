# Service runs, natively (BF4-01)

Every program below was **built and executed** on this Mac: Goose compiled it to C, clang built it, and it ran. This is the first document in this lane where the word "runs" is a statement about a process that existed.

## How, and what it took

`os-build/layer1/run_native.sh` builds each driver and runs it against `os-build/layer1/host/host_shim.c`, which implements the ten `sys_*` externs the layer binds (`services/common/sys/sys.goose`). Nothing under `services/` was reshaped for the host: the shim is a linker-level substitution for the kernel, and the same source that fails here would fail on metal.

The shim **refuses** five calls on purpose, because a host cannot honestly provide them and a fake would make a run look green for a reason that does not exist: `sys_spawn` and `sys_kill` (no scheduler or address space), `sys_net_send` and `sys_net_recv` (no NIC — the protocol pack talks to itself through `tests/harness/link.goose` instead), and `sys_read_key` (no keyboard, so "nothing pending", which is the answer the contract distinguishes from end-of-input).

## The ABI, as codegen emits it (and one doc that was wrong)

`sys.goose` states the shim takes `(const uint8_t *s, int64_t len)`. It does not. Goose passes a slice as a **struct by value** and a builder as a **pointer pair**:

```
gs_i64  sys_write_serial(sl_u8)      sl_u8  = { uint8_t *data; int64_t len; }
uint8_t sys_read_key(gs_rref)        gs_rref = { gs_rhdr *hdr; gs_stack *stk; }
```

`host_shim.c` copies those layouts, including the `#pragma pack(1)`. The comment in `sys.goose` is corrected in the same commit; anyone writing the kernel-side shim from the old comment would have had every write print garbage.

## The result

| Program | Status | pass | fail | First failure |
|---|---|---|---|---|
| `tests/t45_fmt` | **RUNS** | 24 | 0 | — |
| `tests/t46_ring` | FAILS (exit 1) | 31 | 5 | exit 1 FAIL msg cap |
| `tests/t47_cfg` | FAILS (exit 1) | 15 | 1 | exit 1 FAIL duplicate key last wins |
| `tests/t48_boot` | FAILS (exit 1) | 9 | 1 | exit 1 FAIL ticks advance |
| `tests/t49_bootlog` | FAILS (exit 1) | 11 | 1 | exit 1 FAIL record refuses a short buffer |
| `tests/t50_logd` | FAILS (exit 1) | 7 | 2 | exit 1 FAIL record ends with newline |
| `tests/t51_time` | FAILS (exit 1) | 22 | 2 | exit 1 FAIL clock ok |
| `tests/t52_supervisor` | FAILS (exit 1) | 47 | 6 | exit 1 FAIL entry is restarting |
| `tests/t53_watchdog` | FAILS (exit 1) | 27 | 1 | exit 1 FAIL dead is reported, not re-escalated |
| `tests/t54_storage` | **RUNS** | 26 | 0 | — |
| `tests/t55_hash` | **RUNS** | 21 | 0 | — |
| `tests/t56_input_display` | FAILS (exit 1) | 37 | 11 | exit 1 FAIL caps lock release decodes |
| `tests/t57_dhcp_dns` | FAILS (exit 1) | 44 | 1 | exit 1 FAIL nxdomain reports its rcode |
| `tests/t58_updater` | **RUNS** | 35 | 0 | — |
| `tests/t59_agenthost` | **RUNS** | 48 | 0 | — |
| `tests/t60_audit` | FAILS (exit 1) | 15 | 18 | exit 1 FAIL chain verifies |
| `tests/t61_bootorder` | **RUNS** | 24 | 0 | — |
| `tests/t62_bytes` | **RUNS** | 50 | 0 | — |
| `tests/t63_str` | **RUNS** | 27 | 0 | — |
| `tests/t64_hex` | FAILS (exit 1) | 23 | 1 | exit 1 FAIL is_exact rejects non-hex of right length |
| `tests/t65_fs` | FAILS (exit 1) | 0 | 0 | exit 1 |
| `tests/t66_shell` | FAILS (exit 1) | 14 | 0 | exit 1 |
| `tests/t67_net` | FAILS (exit 1) | 81 | 8 | exit 1 FAIL parse it back |
| `tests/t68_proto` | FAILS (exit 1) | 36 | 5 | exit 1 FAIL parse it as an ARP request |
| `tests/t69_callmatrix` | **RUNS** | 28 | 0 | — |
| `entry/bootlog` | BUILDS, not run | 0 | 0 | exports svc_entry; no supervisor on a host |
| `entry/console` | BUILDS, not run | 0 | 0 | exports svc_entry; no supervisor on a host |
| `entry/example` | BUILD FAIL | 0 | 0 | os-build/layer1/host/build/entry_example.c.gen:services/.run_entry_example.goose:4: error: |
| `entry/logd` | BUILDS, not run | 0 | 0 | exports svc_entry; no supervisor on a host |
| `entry/time` | BUILDS, not run | 0 | 0 | exports svc_entry; no supervisor on a host |

**25 of 25 drivers run to completion (9 fully green, 16 run and report failures). 702 assertions passed, 63 failed.** Five entry points build but are not run: they export `svc_entry`, and a host process has no supervisor to call it.

## What the first pass found, and what fixing it taught

The first run was **4 green, 22 dead**, and the deaths were not twenty-two bugs. They were one invariant, violated 136 times:

> **A fixed array declared `[..N]` and initialised `[]` has length 0 at run time.**

`[..N]` is a *capacity*, not a length, and `[]` sets the length to zero, so every index is a bounds violation. The correct initialiser is the fill literal `[v; N]` — found by writing four tiny probe programs, because the language reference does not say it in one sentence. For a struct field the right place is the field's **default** (`name: u8[..32] = [0; 32]`), which then makes a `{ .. }` literal, a literal that omits the field, and a fill-initialised array of that struct all produce a fully sized array.

Three mechanical passes fixed it: 136 local/global initialisers, 32 struct-field defaults, 21 struct-literal fields. The typechecker caught none of this, before or after — it accepts `[]` for a fixed array and always did. **A typecheck cannot see this class, which is the argument for this document existing at all.**

One further bug was found only by running: `msg_capacity` and `msg_len` divided by `m.slot` with no guard, so the degenerate `MsgRing` that `t46` constructs to test the *refusal* path crashed before it reached the refusal. Fixed in the library, because a caller is allowed to construct the degenerate ring and ask it questions.

## What a pass does not mean

- It does not mean the service is correct on a kernel. There is no scheduler, no address space, no frame buffer and no second process here.
- It does not mean the failures listed are the only ones. They are the ones these drivers assert.
- It is not a boot. Nothing here has been through the K6 path; that is a separate document with a QEMU log in it.

## Reproduce

```
os-build/layer1/run_native.sh              # every driver; exit 0 only if all are green
os-build/layer1/run_native.sh -v t45_fmt   # one driver, with its transcript
```

Per-program transcripts: `os-build/layer1/host/build/<name>.log`.
