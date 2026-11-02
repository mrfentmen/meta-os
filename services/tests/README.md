# Layer 4 test programs

One Goose program per B-L1-45..B-L1-60 task. Each is a `main` that runs a sequence of
assertions, prints `ok <name>` or `FAIL <name>` per case, prints `passed <n>`, and exits 0
(pass) or 1 (any failure).

**Status: WRITTEN, not COMPILED, not RUN.** Nothing in this directory has executed. The
programs need the six syscalls in `services/common/sys/sys.goose` bound to a kernel (K6),
and `goose build` on a machine with the toolchain. Until then they are source that will run,
not evidence that anything works.

| File | Task | Target |
|---|---|---|
| `t45_fmt.goose` | B-L1-45 | format library, incl. cap refusals and i64 min |
| `t46_ring.goose` | B-L1-46 | byte ring across the wrap, overflow push, message ring framing |
| `t47_cfg.goose` | B-L1-47 | config parser: comments, duplicates, broken section, defaults |
| `t48_boot.goose` | B-L1-48 | BootInfo version gate, six syscalls, framebuffer consistency |
| `t49_bootlog.goose` | B-L1-49 | boot record shape, console editor guards, history |
| `t50_logd.goose` | B-L1-50 | record format, buffering, and the loss counter |
| `t51_time.goose` | B-L1-51 | tick conversions, deadlines, budget, monotonic uptime |
| `t52_supervisor.goose` | B-L1-52 | registry handles, state machine, restart policy decisions |
| `t53_watchdog.goose` | B-L1-53 | grace, allowance, escalate-once, backwards clock |
| `t54_storage.goose` | B-L1-54 | block round trip, bounds on both paths, seal |
| `t55_hash.goose` | B-L1-55 | published SHA-256 and CRC-32 vectors, streamed vs one-shot |
| `t56_input_display.goose` | B-L1-56 | decode/release/modifiers/repeat; consoles, switching, scroll |
| `t57_dhcp_dns.goose` | B-L1-57 | both protocol ends in the file, plus the refusals |
| `t58_updater.goose` | B-L1-58 | manifest refusals, content verification, plan, rollback record |
| `t59_agenthost.goose` | B-L1-59 | grant ceiling, narrowing, stale handles, terminal states |
| `t60_audit.goose` | B-L1-60 | chain verify, tamper located by sequence, full-buffer refusal |

## What these tests do not do

- They do not assert drawn pixels. `put_ch`/`disp_paint` report failure on K1 (no
  framebuffer); the tests state that rather than pretending a mock is a screen.
- They do not invent a network. t57 builds both packets.
- They do not claim the audit chain is unforgeable: it is tamper-evident from the middle
  onward. Rewriting the whole log verifies.
