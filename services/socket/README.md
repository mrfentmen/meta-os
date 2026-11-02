# socket — what a socket means at Layer 4

Status: **WRITTEN** (not COMPILED — no Goose toolchain on this Mac). Layer 4,
service 17.

## Scope, said once

**Datagram sockets only.** A TCP socket needs buffers, retransmission, windows and a
connection state machine that belongs in B-L1-99/100; defining "socket" to mean both
before either exists produces a contract that fits neither. When TCP lands it adds a
stream kind to this table, it does not replace it.

## The transport is not here

This file owns handles, lifetimes, ports and the state machine. Turning a send into
bytes on a link is B-L1-98 (UDP): `sk_take_send` hands the next queued datagram to
whatever implements the transport. Nothing here pretends to have sent anything, which is
what makes a socket test driveable with no network at all.

## Handles, not indices

`handle = (slot + 1) * 256 + generation`, same reasoning as the supervisor (B-L1-22): a
slot index handed to a client is one that will belong to somebody else later. Every
reuse of a slot bumps the generation, so a closed socket's old handle resolves to
nothing.

## States

```
OPEN ──bind──▶ BOUND ──connect──▶ CONNECTED
  │              │                    │
  └──────send──▶ BOUND ────send──────▶ CONNECTED
                                     close ─▶ CLOSED (handle invalid)
```

- **Send on an unbound socket is `E_STATE`** — it has no source port, so nothing could
  route a reply.
- **`connect` on a datagram socket is not a handshake**: it records a default
  destination. Anything claiming more would be TCP.
- **`0.0.0.0` is refused as a destination** — it is a source address, not a place to
  send.
- **Queued datagrams drop on close and are counted**, because a close that silently
  discarded three queued sends is a bug report nobody can file.
- **`sk_match(0)` never matches**: an unbound socket cannot be a destination, and a
  broadcast-to-all fallback would deliver traffic to sockets that never asked.

## Budget

`SK_DGRAM_MAX` is 512, not 1400: 16 sockets × 2 queued × 1400 is 89 KiB of static
storage against a 64 KiB service allowance (A10). A queue that cannot be allocated is
worse than a smaller datagram; B-L1-98 can raise it when the budget is measured.

Not compiled, not run.
