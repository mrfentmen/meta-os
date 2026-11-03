# Contract note — R13-018, input socket use

Status: **AUDITED — 2 gaps filed**.
Facet: whether `input` opens, reads or writes a socket, and what its actual transport is.

## Evidence

Commands:

```sh
grep -nEi 'socket|sock_|sys_sock|fd|open|connect|recv|send|peer' services/input/*.goose
grep -nE '^fn input_|^struct |^let ' services/input/input.goose
```

Relevant output:

```text
NO MATCHES
```

```text
99  fn input_init(repeat_delay_ms_in: i64, repeat_rate_ms_in: i64)
121 fn input_char(sc: i64, shift: bool) -> u8
188 fn input_decode(sc_raw: i64, now_ms: i64) -> KeyEvent, bool
247 fn input_repeat(now_ms: i64) -> KeyEvent, bool
275 fn input_passthrough(byte: u8) -> KeyEvent
```

## Corrected contract

`input` uses no socket and makes no syscall. It is a pure decoder library: callers pass a scancode
and a timestamp, and receive a `KeyEvent` plus a `got_event` flag. There is no fd, peer, connect,
recv, send or service handle in the source. The transport is the caller's: the K3 PS/2 ring, the
serial passthrough path, or a scripted test driver.

`input` is listed as service 10 in `services/MANIFEST.md` but has no `svc_entry`, so the socket
layer has no service endpoint to reach.

## Mismatches

- **R13-018-G1** — the service has no socket use at all; the socket contract is unimplemented.
- **R13-018-G2** — `Decoder.dropped` is declared but never read or incremented, so even the
  internal loss counter is dead state. See `services/input/GAPS_R13.md`.
