# netcfg — addresses and interface configuration as data

Status: **COMPILED** (Lane B R5, 2026-11-04 — build+run log: services/netcfg/BUILD_LOG.txt; was RUNS on the 2026-11-02 host corpus) — `tests/t67_net`, `tests/t79_limit_drivers`,
`tests/t80_limit_drivers2` and `tests/t126_netcfg_r11` run in the native host corpus, and
the corpus typechecks under `os-build/layer1/check_services.sh`. Layer 4, service 14.

## Bytes, not text

Every protocol layer asks questions about an address — in my subnet? broadcast? is this
mask real? On text, every layer re-implements parsing and they disagree in exactly the
cases that matter (leading zeros, `/31`, the difference between `0.0.0.0` and "unset").
Configuration is text; there is one parser; everything above it is bytes.

## "Unset" is not 0.0.0.0

`0.0.0.0` is a real address — DHCP must send from it before it has one. So every parse
returns `(value, ok)` and the caller cannot confuse "the user wrote 0.0.0.0" with "the
user wrote nothing". `IfaceCfg.configured` records the second question separately.

## `ip4_parse` is strict on purpose

Exactly four parts, 1–3 digits each, each 0–255, **no leading zeroes** (an
octal-looking address is a config error, and every system that accepted it shipped a
bug), no spaces, no signs, no hex. A rejected string returns `0.0.0.0` with
`ok = false`, so a caller that ignores the flag gets an obvious value rather than a
plausible wrong one.

## Masks

`ip4_mask(prefix)` builds one; `ip4_mask_contiguous` rejects `255.0.255.0` — if that
passed, every subnet comparison below it would be meaningless.

## Configuration rules, in the order they apply

1. **`dhcp=yes` beats static fields.** A file with both is contradictory; the dynamic
   reading cannot black-hole the machine with a stale address that no longer routes.
2. **Static address without a netmask is refused.** There is no sensible default, and
   guessing `/24` has put hosts on the wrong network for decades.
3. **One invalid address fails the whole interface.** Half an interface configured is a
   machine that looks fine and reaches nothing.
4. **MTU is clamped to 576..1500.** Below 576 DHCP/DNS responses do not fit.

Each read uses a **fresh** buffer: reusing one would parse `1.2.3.4` followed by
`5.6.7.8` as a single string and produce an address nobody typed.

## What persistence proves, and what it does not

`netcfg_save` truncates the inode and writes the rendered section; `netcfg_load` reads it
back through the same parser (`tests/t80_limit_drivers2`). The configuration survives a
process death. A supervisor-driven restart of the service has **not** been run, so
"restarted and re-applied the address" is unproven; the file is the part that is tested.
