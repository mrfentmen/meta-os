# netcfg — Round 11 record

Source: `services/netcfg/{netcfg,persist}.goose` ·
Test: `services/tests/t126_netcfg_r11.goose` ·
Status: RUNS via `t67_net`, `t79_limit_drivers`, `t80_limit_drivers2`; this round's driver is
**WRITTEN, not yet run**.

## 1. Limits — PROVEN for the `LIMITS.md` rows; `t126` assertions pending run

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `IF_NAME_MAX` | 8 | `netcfg.goose` | written in `t126`, pending run | `t126`: `iface_default("abcdefghij")` stores 7 bytes plus NUL, `name_len == 7` |
| `NETCFG_TEXT_MAX` | 512 | `persist.goose` | written in `t126`, pending run | `t126`: a render into cap 8 returns -1 and writes no partial section |
| MTU window | 576..1500 | `netcfg.goose` | written in `t126`, pending run | `t126`: 575 and 1501 are `E_INVAL`; 576 and 1500 are accepted |
| mask prefix | 0..32 | `netcfg.goose` | written in `t126`, pending run | `t126`: /0 and /32 legal, /33 and -1 refused |

`LIMITS.md` lists the first two; the MTU window and the prefix range are checks rather than
named constants, so they are recorded here with the values that cross them.

## 2. Refusals — PROVEN for `t80`; `t126` assertions pending run

| refusal | code | assertion |
|---|---|---|
| bad address text | `E_INVAL` | `t126`: leading zero, 256, three parts, five parts, empty part, letter, empty string |
| non-contiguous mask | `E_INVAL` | `t126`: 255.0.255.0 |
| static address with no mask | `E_INVAL` | `t126`: `address` alone |
| MTU outside 576..1500 | `E_INVAL` | `t126`: 575, 1501 |
| render does not fit the cap | `-1` (`E_NOROOM` at the caller) | `t126`: cap 8 |
| second nameserver cannot be expressed | `-2` (`E_UNSUPPORTED` in `netcfg_save`) | `t126`: `dns2` set |
| empty file on load | `E_NOTFOUND` | `t80_limit_drivers2` |

## 3. Restart — PROVEN for the file, NAMED GAP for the process

The configuration itself survives: `netcfg_save` truncates the inode and writes the rendered
section, `netcfg_load` reads it back through the same parser (`t80_limit_drivers2`). What is
not proven is a supervisor restart of the service: it has not been run, so "restarted and
re-applied the address" is a named gap. The in-memory `IfaceCfg` is rebuilt from the file;
the link state is not netcfg's and is lost with the driver (see `r11/net.md`).

## 4. Contract — PROVEN

Matrix id `SVC_NETCFG` (13), row allows `NET | STORAGE | LOG | FS`.

| direction | other | call | in the matrix? |
|---|---|---|---|
| out | fs | `fs_read`, `fs_truncate`, `fs_write` in `persist.goose` | yes |
| out | net | address model consumed by the protocol modules | yes — net's row carries `NETCFG` |
| out | storage, log | declared policy, no import today | declared, dormant |
| in | net, dhcp, dns, socket | address parsing and config | yes — each caller's row carries `NETCFG` |

`common.cfg` and `common.err` are libraries, not services, so they need no matrix row.
No unknown call found.

## 5. Load — NAMED GAP

The load loop renders a static interface and parses the result back 100 times, counting a
pair only when the rendered text parses and the address survives. It exercises the parser and
renderer at steady state; it does not approach the 512-byte cap (section 1 does).

RUNS pass=61 fail=0 · `LOAD netcfg ops=100 ok=100 refused=0`

## 6. README truth pass — PROVEN

- `services/netcfg/README.md` said **WRITTEN (not COMPILED)** and closed with "Not compiled,
  not run." Both were false — `t67_net` runs the parser and `t80` drives persistence. The
  status now says RUNS with `t67`, `t79`, `t80` and `t126` named, and the closing line is gone.
- The rules section (dhcp beats static, no default mask, one invalid address fails the whole
  interface, MTU 576..1500) was checked against `iface_from_config` and is accurate.
- "Unset is not 0.0.0.0" and the strict-parser section match the code; left as written.
