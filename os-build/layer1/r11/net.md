# net — Round 11 record

Source: `services/net/{packet,ip,arp,icmp,udp,tcp,loopback}.goose` ·
Test: `services/tests/t125_net_r11.goose` ·
Status: RUNS via `t67_net` and `t85_net_deep`; this round's driver is **WRITTEN, not yet run**.

## 1. Limits — PROVEN for `t67`/`t85`; this round's rows are NAMED GAP until `t125` runs

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `ARP_SLOTS` | 8 | `arp.goose` | already driven | `t85_net_deep`: fills 8, ninth evicts the oldest, count stays 8 |
| `FRAME_MAX` | 1514 | `packet.goose` | already driven | `t85_net_deep`: a frame past `mtu + ETH_HDR_MIN` is `E_INVAL` |
| `RTO_MAX_MS` | 30000 | `tcp.goose` | already driven | `t67_net`: repeated expiry never exceeds the cap, then gives up |
| link table size | 4 | `packet.goose` | written in `t125`, pending run | `t125`: four links fit, the fifth is `E_NOROOM`, a duplicate id is `E_STATE` |
| `IP_MTU` | 1500 | `ip.goose` | written in `t125`, pending run | `t125`: a 1480-byte payload makes exactly 1500; 1481 is `E_NOROOM` |
| UDP datagram cap | 1480 | `udp.goose` | written in `t125`, pending run | `t125`: a 1472-byte payload makes 1480; 1473 is `E_NOROOM` |
| ICMP message cap | 1472 | `icmp.goose` | written in `t125`, pending run | `t125`: a 1464-byte payload makes 1472; 1465 is `E_NOROOM` |
| `ARP_TTL_MS` | 60000 | `arp.goose` | already driven | `t85`: valid at the TTL, expired one ms past it |

The link table and the three payload ceilings are not in `LIMITS.md` because they are array
sizes and arithmetic, not named `let` constants. They are limits a caller can cross, so they
are listed here with the assertion that crosses them.

## 2. Refusals — PROVEN for `t67`/`t85`; `t125` assertions pending run

| refusal | code | assertion |
|---|---|---|
| unknown link | `E_NOTFOUND` | `t125`: send on link 9 |
| link down / faulted | `E_NO_LINK` | `t85`: send and recv in both states |
| frame < 14 bytes, or past mtu+14 | `E_INVAL` | `t85`: 13-byte frame; `t125`: 14-byte minimum reaches the syscall |
| backend refuses a frame | `E_IO` | `t125`: the shim returns -1, drop counter moves once, `sent` does not |
| table full, payload past MTU | `E_NOROOM` | `t125`: fifth link, 1481-byte IP, 1473-byte UDP payload, 1465-byte ICMP payload |
| ttl 0 or 256; port 0 or 65536 | `E_INVAL` | `t125`: build-side bounds |
| malformed IP/UDP/ICMP/ARP | `E_CORRUPT` / `E_UNSUPPORTED` | `t85`: bad lengths, bad checksums, fragments, wrong hardware type |
| unconfigured route | `E_NO_ADDRESS` / `E_UNREACHABLE` | `t125`: `lo_route` with 0.0.0.0 local, and with no gateway |

## 3. Restart — NAMED GAP

The link table (`link_count`, four `Link` records) and the ARP cache are process memory.
A supervisor restart rebuilds both empty: every link must be re-added and re-brought-up by
whatever owns the driver, and the cache re-learns. Nothing writes either to disk and nothing
replays them. Not tested — no supervisor restart of a network service has been run.

## 4. Contract — PROVEN

Matrix id `SVC_NET` (12), row allows `NETCFG | LOG | DEVICES`.

| direction | other | call | in the matrix? |
|---|---|---|---|
| out | netcfg | `Ipv4` type and `ip4_*` helpers (import) | yes |
| out | common.err | `E_*` codes | library, not a service |
| in | socket (16) | link send/recv | yes — socket's row carries `NET` |
| in | dhcp (14), dns (15) | address model and packets | yes — both rows carry `NET` |
| out | log, devices | none today | declared, dormant |

No call found that the matrix does not carry.

## 5. Load — NAMED GAP

The load loop builds and parses 100 IP+UDP pairs in one process, counting a pair only when
all four calls return `CODE_OK`. It approaches no limit — it is a stability check, not a
capacity check; the capacity ceilings are in section 1.

RUNS pass=55 fail=0 · `LOAD net ops=100 ok=100 refused=0`

## 6. README truth pass — PROVEN

- `services/net/README.md` said **WRITTEN (not COMPILED)** and closed with "Not compiled,
  not run." Both were false: `t67_net` and `t85_net_deep` run in the native corpus. The status
  now says RUNS with both drivers named, and the closing line is gone.
- The README's central claim — that `sys_net_send`/`sys_net_recv` do not exist and B-L1-73 is
  blocked on Layer 3 — is still true and was left as written.
- The decisions table matches the code (frame ownership, 576 floor, 1514 ceiling, drop
  counters, partial-send refusal). No change needed.
