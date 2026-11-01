# net — the packet interface (and, from B-L1-95, the protocols on it)

Status: **WRITTEN** (not COMPILED — no Goose toolchain on this Mac). Layer 4,
service 13.

## Why an interface rather than a driver

There is no network driver in the kernel yet. Writing DHCP, DNS and sockets against a
driver means all three wait for it, and all three get rewritten when the driver's real
shape appears. Written against this interface, the driver plugs in underneath and
none of them change.

Two calls carry it:

```
extern fn sys_net_send(link, frame) -> i64
extern fn sys_net_recv(link, out)   -> i64
```

**These do not exist.** They are the shape the kernel must provide, declared so the
requirement has a name (`services/common/sys/sys.goose` declares six calls, none of
them a packet). B-L1-73 is the binding task and it is blocked on Layer 3. Everything
else in `packet.goose` — framing checks, MTU handling, drop counters, address
matching — is real code that runs against any backend implementing those two symbols.

## Decisions

| Decision | Reason |
|---|---|
| frames, not payloads | the 14-byte link header belongs to the caller; this layer does not own it and must not invent one |
| MTU floor 576 | the IPv4 minimum; below it DHCP and DNS responses do not fit and the failure shows up much later as a truncated message |
| MTU ceiling `FRAME_MAX - 14` | 1514 is what every link accepts; larger is a frame no hardware sends |
| `recv` returning 0 with `CODE_OK` = "nothing arrived" | not an error: an idle link must not fill the log with failures |
| partial send is `E_IO` | a frame either goes or it does not; half of it leaves the peer with a broken packet |
| every refusal increments `dropped` | a dropped frame is the first thing anyone debugging a network wants, and the counter is the only record that survives the moment |
| short/large frames refused at the interface | corruption, rejected once instead of by every parser above |

`pkt_for_us` accepts unicast-to-us and broadcast, and rejects another host's traffic
delivered by a shared medium — normal on a hub, never something this layer answers.

Not compiled, not run.
