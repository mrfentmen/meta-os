# devices — the device table

Status: **RUNS** — reached by `tests/t77_gaps` (73 checks, exit 0) and typechecked with the
corpus; `tests/t112_devices_r11.goose` drives the table's capacity and the hot-plug queue.
Layer 4, service 8.

## Why a table at all

BootInfo is a boot-time fact. Services need a live one: a device that faults
after boot must stop reading as healthy, and every caller must see the same
answer. The table adds exactly one thing BootInfo cannot carry — **current
state** — plus a single place to ask instead of nine services each reading
fields for themselves.

## What it probes

| Device | Source | Usable when |
|---|---|---|
| serial | `BootInfo.serial.port` (K1: COM1 0x3F8) | port != 0, `DS_READY` (K1 proved it by printing) |
| framebuffer | `BootInfo.framebuffer.address/cols/rows` | `[PROPOSED]` — address and cols both non-zero, else `DS_ABSENT` |
| timer | `BootInfo.time.tick_hz` | non-zero, else `DS_FAULT` (no tick makes every timeout infinite) |
| keyboard | **nothing** | never, and that is the honest answer |

**The keyboard is absent from BootInfo.** `SerialInfo`, `FramebufferInfo`,
`TimeInfo` and `MemoryInfo` are the whole block (`boot.goose:123-129`). K3's PS/2
driver exists in Rowan's branch but nothing publishes it to a service. This
service registers the keyboard as `DS_ABSENT` and says so, rather than inventing a
field to probe or leaving the device out of the table. Recorded as requirement
A11 in `os-build/layer1/BOUNDARIES.md`.

## States

```
ABSENT ──▶ DETECTED ──▶ READY ──▶ FAULT
   ▲            ▲          │         │
   └────────────┴──────────┴─────────┘   (anything may vanish; FAULT may recover)
```

`READY → DETECTED` is illegal on purpose: "became less ready without failing" is
not a thing a driver reports, and allowing it would let a missed `FAULT` be
papered over.

## Queries

- `dev_ready(kind)` — the question callers actually ask before using a device.
- `dev_detail(kind)` — (a, b, code). `(cols, rows)` for the framebuffer, `(hz, 0)`
  for the timer. On a faulted device it returns zeros and `E_STATE`, so a caller
  that ignores the code gets zeros rather than the stale numbers of a broken
  device.
- `dev_summary()` — (ready, faulted, absent) for the boot line and health line.
  Three numbers, not a formatted string: `common/fmt` owns formatting, and a
  service that formats its own diagnostics disagrees with its neighbours.

## Hot-plug

`hotplug.goose` is the change-notification half. `hp_raise` is called after the
table has already been updated, so a subscriber that re-reads the table on
notification always sees the new truth. Subscribers register a mask (add, remove,
fault, ready) and **drain** events with `hp_next`; there are no callbacks and no
IPC needed.

The queue holds 8 events. When it is full the **oldest** is dropped and counted,
because a storm is almost always a flapping device and the newest events describe
its current state. Per-subscriber `delivered` and `dropped` are kept so a health
line can name the service that is behind, and `delivered + dropped` never exceeds
`raised`.

## Limits, and the test that reaches each

| Limit | Value | Reached by |
|---|---|---|
| `DEV_MAX` | 16 devices | `t112`: one device per kind fills the table; the 17th returns `E_NOROOM` |
| `HP_QUEUE` | 8 events | `t112`: the ninth raise drops the oldest, `dropped=1` |
| `HP_SUBS` | 8 subscribers | `t112`: the ninth subscription returns `-1` |

`HP_QUEUE` and `HP_SUBS` are not yet in the generated `os-build/layer1/LIMITS.md`; the tests
exist and the inventory should catch up.

## Deliberately absent

No driver code (Layer 3), and no PCI/ACPI walk — that is Layer 3 enumeration, and duplicated
enumeration disagrees with itself.

## Not verified

- **Restart continuity.** The table is rebuilt from `BootInfo`; post-boot state changes
  (faults, removals, recoveries) are lost on restart. Named in
  `os-build/layer1/r11/devices.md`.
- **A real keyboard.** Nothing publishes one, so the absent row is the whole test.
