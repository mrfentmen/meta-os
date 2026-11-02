# Size audit (B-L1-136)

Tool: `python3 os-build/layer1/size_audit.py --top 12`. Method: every fixed array and struct
instance in `services/`, sized from the type table, with array counts applied.

Measured today: **27 services, 384.7 KiB of resident fixed storage, 0 unresolvable element types.**

## Why this is not "count the big arrays"

The first version of the tool did exactly that and produced two wrong numbers, both of which
would have led to wrong cuts:

1. **A declaration is not a footprint.** `vcons: VCon[..4]` counted as its 32 KiB `history` field
   once instead of four times, and `var cs: ContentSet;` (a single instance, no `[..N]`) counted
   as nothing at all. Struct sizes are now computed and multiplied.
2. **Struct names collide across services.** `net.packet` has a `Link` of 54 bytes;
   `tests/harness/link.goose` has a `Link` with a 12 KiB frame buffer. Keyed by name alone, the
   audit handed `net` the test's size — 48 KiB of lossy-link table that does not exist. Types are
   now resolved per service, and ambiguity is reported rather than resolved by luck.

Both bugs are recorded here because the audit is only worth what its measurement is worth, and a
size table that is quietly wrong is worse than no table: it invites cuts in the wrong place.

## The table

| service | arrays | resident | share |
|---|---|---|---|
| `display` | 2 | 136.6 KiB | 35.5% |
| `tests` | 73 | 67.0 KiB | 17.4% |
| `socket` | 4 | 37.6 KiB | 9.8% |
| `storage` | 4 | 33.0 KiB | 8.6% |
| `common` | 20 | 31.3 KiB | 8.1% |
| `net` | 20 | 25.3 KiB | 6.6% |
| `updater` | 22 | 13.8 KiB | 3.6% |
| `logd` | 3 | 10.3 KiB | 2.7% |
| `fs` | 21 | 9.6 KiB | 2.5% |
| everything else (18 services) | — | 20.2 KiB | 5.2% |

The largest single allocations:

```
139588 B  VCon x 4        vcons    display/display.goose:55
 34944 B  Sock x 16       socks    socket/socket.goose:72
 32768 B  u8 x 32768      ram      storage/storage.goose:45
 24160 B  Pool            p        common/pool/pool.goose:50
 10240 B  u8 x 10240      storage  logd/logd.goose:72
  3616 B  ServiceEntry[32] table   supervisor/supervisor.goose:85
```

## Review, one by one

**No cuts made, and here is why for each of the top five.**

- `display` 136.6 KiB — four virtual consoles (`VCON_MAX`), each a 2 KiB screen plus a 32 KiB
  history ring. The ring is *exactly* sized to its contract, not oversized: `SCROLL_MAX` 256 lines
  × `LINE_MAX` 128 bytes. Cutting it silently breaks a documented scrollback, and shrinking
  `SCROLL_MAX` is a product decision, not an audit fix. **Flagged for Pax/Hana:** the real lever is
  `VCON_MAX`. Four consoles cost 128 KiB of the layer's 385 KiB; two would cost 64 KiB, and the
  fourth console is documented as "one spare".
- `socket` 34.9 KiB — 16 sockets × 2184 B, dominated by the per-socket receive buffer. Sixteen is a
  policy number the socket contract promises; not an oversize.
- `storage` 32 KiB — the RAM block backend, which is the *only* backend until a real driver lands
  (B-L1-74). Cutting it cuts the block count.
- `net` 25.3 KiB — five packet buffers of 1514 B (one Ethernet MTU each, per direction and per
  link) plus the small `Link` table. Sizing is `FRAME_MAX`, no slack.
- `logd` 10.24 KiB — `SLOT` 160 × `SLOTS` 64, exact. The comment says "a boot's worth of history",
  and 64 records is that; the risk here is *undersize* (records refused with `E_NOROOM` on a noisy
  boot), which is what the `dropped_full` counter exists to report.

**Undersized / at-risk, flagged rather than changed:** `logd` (a detailed boot can exceed 64
records), `agenthost` (24 agent slots), `watchdog` (32 watches, mirroring the supervisor's 32
slots — if `MAX_SERVICES` rises, this silently truncates).

**One structural finding, not a size one:** `common/pool`'s `Pool` is 24 KiB as a *constant*, so
any service that owns one pays 24 KiB. A pool library should take its block count as a parameter.
It has no consumers yet (see below), so nothing pays it today.

## What is not measured

Stack depth, struct padding, string literals in `.rodata`, and code size. All four need the
compiler. This audit is the part that can be read off the source, and the honest status of every
number above is **measured, not proven** — proven requires a link map from a real Goose toolchain,
which does not exist on this machine.

## A note the audit exposed

`common/text`, `common/table`, `common/sort` and `common/pool` (gap libraries 4–7, B-L1-142..145)
have **no consumers and no tests** in the tree. They are WRITTEN, and nothing exercises them — so
their sizes above are the size of a library nobody linked. That is an honest gap, listed in
`BUFFY_REPORT.md`, not a defect in the libraries.
