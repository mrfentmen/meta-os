# net — contract (Round 7 B, 2026-11-02)

What this stack promises, checked against the code as it stands. Status: **RUNS** as
a host process for every parser and builder. **NO-HARNESS for framing:** the host
shim refuses `sys_net_send` and `sys_net_recv` (both return -1), so no frame leaves
or arrives on this machine.

Scope, stated once: IPv4 only, no options, no fragmentation (a fragment is refused,
never reassembled), no IPv6, no routing beyond "on my subnet or via the gateway".

## Inputs

| Input | Accepted | Refused |
|---|---|---|
| `ip_parse_header(pkt, len)` | version 4 / IHL 5, `20 ≤ total ≤ len`, `frag == 0`, correct header checksum | `len < 20` → `E_CORRUPT`; not `0x45` → `E_UNSUPPORTED`; total out of range → `E_CORRUPT`; fragment → `E_UNSUPPORTED`; checksum mismatch → `E_CORRUPT` |
| `arp_parse(pkt, len)` | `len ≥ 28`, hw type 1, proto 0x0800, hlen 6, plen 4, op 1 or 2 | short → `E_CORRUPT`; any other field → `E_UNSUPPORTED` |
| `arp_build(out, op, …)` | op 1 or 2 | any other op → `E_INVAL` |
| `udp_parse(dgram, len, src, dst)` | `len ≥ 8`, declared length `== len`, checksum valid or zero | declared length disagreement → `E_CORRUPT`; bad checksum → `E_CORRUPT`; zero checksum parses with `checksum_ok = false` |
| `icmp_parse(msg, len)` | `len ≥ 8`, checksum correct | short or checksum mismatch → `E_CORRUPT` |
| `icmp_build_echo(out, …)` | header + payload ≤ 1472 | over the MTU → `E_NOROOM` |
| `tcp_parse(seg, len)` | `len ≥ 20`, data offset ≥ 5 words, offset ≤ len | any violation → `E_CORRUPT` |
| `pkt_send(id, frame)` | link up, `14 ≤ frame.len ≤ mtu + 14` | down/faulted → `E_NO_LINK`; short → `E_INVAL`; past the MTU → `E_INVAL`; syscall failure → `E_IO` |
| `pkt_recv(id, out)` | link up | down/faulted → `E_NO_LINK`; short or > `FRAME_MAX` from the kernel → `E_CORRUPT` |

## Outputs

- **Views, not buffers:** every parser returns a struct describing the packet
  (`IpView`, `ArnMsg`, `UdpView`, `IcmpView`, `TcpHeader`); nothing hands back a
  pointer into the caller's buffer.
- **Counters:** per link `sent`, `received`, `dropped`. A refusal before the syscall
  increments `dropped`; a failed syscall does too; a partial send is `E_IO` and is
  never counted as sent.

## Limits (see `LIMITS.md`)

| Constant | Value | Enforced | Proven by |
|---|---|---|---|
| `FRAME_MAX` | 1514 | `pkt_recv` refuses a larger frame from the kernel | `t85_net_deep` (asserted at the send side; the receive side needs a kernel) |
| `ETH_HDR_MIN` | 14 | 13-byte frame refused | `t85_net_deep` |
| link table | 4 | the 5th `pkt_add_link` is `E_NOROOM` | `t85_net_deep` |
| `mtu` | 576 … 1500 | 575 refused; `mtu + 14 > FRAME_MAX` refused | `t85_net_deep` |
| `ARP_SLOTS` | 8 | oldest entry evicted at 9, never refused | `t85_net_deep` (fill 8, add 1, oldest gone) |
| `ARP_TTL_MS` | 60 000 | valid at TTL, expired at TTL+1 | `t85_net_deep` |
| `IP_MTU` | 1500 | ICMP payload over 1472 refused | `t85_net_deep` |
| `RTO_MIN/MS` | 200 / 30 000 | doubling capped at the max; gives up at `RTO_TRIES` | `t85_net_deep` |

## Failure modes

| Failure | Behaviour |
|---|---|
| truncated packet | `E_CORRUPT` before any field is read past the buffer |
| checksum present and wrong | refused — the parse side recomputes rather than trusting the field |
| UDP zero checksum | parses, `checksum_ok = false`: the sender did not compute one, and the caller is told |
| UDP length disagreement | `E_CORRUPT` — a shorter declared length is the overlap attack, a longer one reads past the buffer |
| fragment | `E_UNSUPPORTED`; this stack does not reassemble |
| ARP cache full | the **oldest** entry is evicted; refusing would make the newest host unreachable while a dead entry holds a slot |
| ARP entry expired | reported as a miss and its slot freed on lookup |
| link down / faulted | `E_NO_LINK` before any length check, counted as a drop |
| partial send | `E_IO`. A frame either goes or it does not; half a frame leaves the peer with a broken packet |

## Restart semantics

`arp_cache_clear()` empties the cache; a restart of the process does the same by
starting from zero. **The link table has no removal**: `pkt_add_link` only appends and
nothing shrinks `link_count`, so four links is a lifetime limit for the process, not a
concurrent one. A link that is no longer wanted can only be taken `DOWN`.

## Findings (asserted, not fixed)

1. **`pkt_recv` had never been called.** Until `t85_net_deep`, every receive path was
   unexercised — the calls compiled, nothing drove them. On the host both branches
   (`E_NO_LINK`, `E_IO`) are now asserted; the success branch needs a kernel with a
   real link.
2. **`arp_drops` is maintained and unreadable.** The eviction counter increments on
   every eviction and no accessor exposes it, so nothing — not the health line, not a
   test — can report it.
3. **No `pkt_remove_link`.** Combined with the append-only table, a link slot cannot
   be reused after a NIC is replaced.
4. **`pkt_for_us` compares only the first six bytes.** It is correct for Ethernet and
   has no length guard beyond `frame.len < 6`, which it does have.

## Drivers

| Driver | Checks | Covers |
|---|---|---|
| `t67_net` | 89 | build/parse round trips for IP, ARP, ICMP, UDP, TCP |
| `t85_net_deep` | 154 | hostile input to every parser, ARP cache TTL and eviction, link table boundaries, MTU and frame-size refusals, TCP serial arithmetic, state machine, timer cap, loopback delivery |
