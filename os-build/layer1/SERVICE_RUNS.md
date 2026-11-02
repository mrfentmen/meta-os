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
| `tests/t46_ring` | **RUNS** | 36 | 0 | — |
| `tests/t47_cfg` | **RUNS** | 16 | 0 | — |
| `tests/t48_boot` | **RUNS** | 10 | 0 | — |
| `tests/t49_bootlog` | **RUNS** | 23 | 0 | — |
| `tests/t50_logd` | **RUNS** | 19 | 0 | — |
| `tests/t51_time` | **RUNS** | 24 | 0 | — |
| `tests/t52_supervisor` | **RUNS** | 53 | 0 | — |
| `tests/t53_watchdog` | **RUNS** | 28 | 0 | — |
| `tests/t54_storage` | **RUNS** | 26 | 0 | — |
| `tests/t55_hash` | **RUNS** | 21 | 0 | — |
| `tests/t56_input_display` | **RUNS** | 49 | 0 | — |
| `tests/t57_dhcp_dns` | **RUNS** | 45 | 0 | — |
| `tests/t58_updater` | **RUNS** | 35 | 0 | — |
| `tests/t59_agenthost` | **RUNS** | 48 | 0 | — |
| `tests/t60_audit` | **RUNS** | 33 | 0 | — |
| `tests/t61_bootorder` | **RUNS** | 24 | 0 | — |
| `tests/t62_bytes` | **RUNS** | 50 | 0 | — |
| `tests/t63_str` | **RUNS** | 27 | 0 | — |
| `tests/t64_hex` | **RUNS** | 25 | 0 | — |
| `tests/t65_fs` | **RUNS** | 75 | 0 | — |
| `tests/t66_shell` | **RUNS** | 57 | 0 | — |
| `tests/t67_net` | **RUNS** | 89 | 0 | — |
| `tests/t68_proto` | **RUNS** | 41 | 0 | — |
| `tests/t69_callmatrix` | **RUNS** | 31 | 0 | — |
| `tests/t70_status` | **RUNS** | 20 | 0 | — |
| `tests/t71_rotate` | **RUNS** | 48 | 0 | — |
| `tests/t72_hostile` | **RUNS** | 77 | 0 | — |
| `tests/t73_shell_hard` | **RUNS** | 46 | 0 | — |
| `tests/t74_failure` | **RUNS** | 26 | 0 | — |
| `tests/t75_supervisor_load` | **RUNS** | 32 | 0 | — |
| `tests/t76_demo_session` | **RUNS** | 25 | 0 | — |
| `tests/t77_gaps` | **RUNS** | 73 | 0 | — |
| `tests/t78_lib_limits` | **RUNS** | 27 | 0 | — |
| `tests/t79_limit_drivers` | **RUNS** | 42 | 0 | — |
| `tests/t80_limit_drivers2` | **RUNS** | 30 | 0 | — |
| `tests/t81_logd_deep` | **RUNS** | 24 | 0 | — |
| `tests/t82_fs_deep` | **RUNS** | 35 | 0 | — |
| `tests/t83_sup_deep` | **RUNS** | 117 | 0 | — |
| `tests/t84_session_deep` | **RUNS** | 106 | 0 | — |
| `tests/t85_net_deep` | **RUNS** | 154 | 0 | — |
| `tests/t86_settings` | **RUNS** | 67 | 0 | — |
| `tests/t87_wallpaper` | **RUNS** | 56 | 0 | — |
| `tests/t88_dock` | **RUNS** | 61 | 0 | — |
| `tests/t89_dashboard` | **RUNS** | 50 | 0 | — |
| `tests/t90_updater_client` | **RUNS** | 62 | 0 | — |
| `tests/t91_board` | **RUNS** | 58 | 0 | — |
| `tests/t92_sup_load` | **RUNS** | 27 | 0 | — |
| `entry/bootlog` | BUILDS (not run) | 0 | 0 | svc_entry; no supervisor on a host |
| `entry/console` | BUILDS (not run) | 0 | 0 | svc_entry; no supervisor on a host |
| `entry/example` | TYPECHECKS (not run) | 0 | 0 | svc_entry takes a kernel BootInfo; no host boot block |
| `entry/logd` | BUILDS (not run) | 0 | 0 | svc_entry; no supervisor on a host |
| `entry/time` | BUILDS (not run) | 0 | 0 | svc_entry; no supervisor on a host |

**48 of 48 drivers run to completion, all green: 2172 assertions passed, 0 failed** (measured 2026-11-02, `run_native.sh` exit 0). 4 entry points **build** and are not run — they export `svc_entry`, and a host process has no supervisor to call it. 1 entry point **typechecks** and is not run: its `svc_entry` takes a kernel `BootInfo`, and a host has no boot block to hand it.

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
