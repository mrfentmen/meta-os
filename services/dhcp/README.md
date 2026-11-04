# dhcp — the client state machine

Status: **COMPILED** (Lane B R5, 2026-11-04 — build+run log: services/dhcp/BUILD_LOG.txt; was RUNS on the 2026-11-02 host corpus) — `tests/t57_dhcp_dns` (45 checks, exit 0), plus
`tests/t114_dhcp_r11` for every parser refusal and the lease clock. Layer 4,
service 15. Speaks the packet interface (B-L1-29); takes time as a parameter.

## Why time is a parameter

`dhcp_step(client, now_ms, reply_type, offer)` never reads a clock. That is what lets
B-L1-57 drive a whole lease lifetime — DISCOVER through expiry — in a test program
without sleeping, and it means the same sequence of inputs always produces the same
decisions.

## States

```
IDLE ─▶ SELECTING ──OFFER──▶ REQUESTING ──ACK──▶ BOUND
          │  ▲  ▲                 │               │
          │  │  └─────NAK─────────┘               │ T1
          │  └────────expiry────────────────────┐ │
          │                                     ▼ ▼
          └──retries exhausted──▶ FAILED     RENEWING ──T2──▶ REBINDING
```

`BOUND` is not terminal: T1 and T2 are option 58/59 when the server offers them,
otherwise half and ⅞ of the lease. Expiry returns to `SELECTING` — a client that waited
too long is exactly what DISCOVER is for, not a failure.

## What the parser refuses

| Condition | Result |
|---|---|
| < 240 bytes, `op != 2`, `htype != 1` or `hlen != 6` | `E_CORRUPT` — never trust `chaddr` without checking `hlen` |
| magic cookie missing | `E_CORRUPT` — not DHCP whatever it claims |
| option length runs past the packet | `E_CORRUPT` |
| `yiaddr` is 0.0.0.0 | `E_NO_ADDRESS` — an offer of nothing is not an offer |
| lease time 0 | `E_INVAL` — a zero lease renews in a tight loop |
| **no subnet mask (option 1)** | `E_NO_MASK` — classful guessing is what DHCP exists to end, so the interface stays unconfigured rather than getting a mask nobody chose |

Unknown options are **skipped**, not refused: the option space is shared with vendors
and a strict client fails on most real networks.

## Honest gaps

- **No jitter.** RFC 2131 §4.1 asks for randomised retransmit backoff; this doubles and
  caps at 64 s. Randomness needs an entropy source the kernel does not have yet. Recorded,
  not faked with a constant.
- **No DECLINE / RELEASE / INFORM.** A client that cannot yet tell a server it is leaving
  says nothing; a malformed RELEASE is worse than silence.
- **Broadcast flag never set.** Servers that insist on it will not answer a client that
  cannot receive unicast before it has an address. A compatibility question, noted.

Compiled to C and run as a host process, against real memory and a real clock. Not
booted on the kernel: there is no supervisor and no network device in this path.
