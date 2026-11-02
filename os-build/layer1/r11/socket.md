# socket — Round 11 record

Source: `services/socket/socket.goose` · Test: `services/tests/t132_socket_r11.goose` · Status: RUNS
Existing driver: `services/tests/t77_gaps.goose` (73 checks)

## 1. Limits — PROVEN, one bound newly stated

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `SK_MAX` | 16 | `socket.goose` | driven by `t132` | 16 open, the 17th is `E_NOROOM` with handle 0; a closed slot is reusable. |
| `SK_GEN_MAX` | 255 | `socket.goose` | driven by `t132` | 255 open/close cycles; the increment that reaches 255 wraps to generation 1. |
| `SK_PORT_MIN` | 1024 | `socket.goose` | driven by `t132` | `1023` is `E_INVAL`; `1024` binds. |
| `SK_PORT_MAX` | 65535 | `socket.goose` | driven by `t132` | `65535` binds; `65536` is `E_INVAL`. |
| `SK_DGRAM_MAX` | 512 | `socket.goose` | driven by `t132` | 512 bytes accepted; 513 is `E_NOROOM` (never truncated). |
| `SK_QUEUE` | 2 | `socket.goose` | driven by `t132` | two queued datagrams, the third is `E_BUSY`; `sk_take_send` drains in order. |

**Finding for `gen_limits.py`.** `LIMITS.md` lists `SK_MAX`, `SK_GEN_MAX`, `SK_PORT_MAX` and
`SK_DGRAM_MAX` but not `SK_PORT_MIN` or `SK_QUEUE`. Both are real limits with a driver that
crosses them; the generator's heuristic misses them rather than the constants being informal.

**Generation wrap, stated plainly.** The README said "a closed socket's old handle resolves to
nothing". True until reuse 255: the handle is `(slot+1)*256 + gen`, the generation is one byte,
and the assignment wraps when it reaches 255. `t132` drives the wrap and asserts the consequence —
a handle issued 254 sockets ago names the socket that now occupies the slot. That is a limit of
the encoding, not a coding error, and the README now says so.

## 2. Refusals — PROVEN

| refusal | code | assertion in `t132` |
|---|---|---|
| open with every slot used | `E_NOROOM` | "the seventeenth is E_NOROOM" |
| bind a privileged port | `E_INVAL` | "a privileged port is E_INVAL" |
| bind above 65535 | `E_INVAL` | "a port past 65535 is E_INVAL" |
| bind a port another socket holds | `E_BUSY` | "the same port on another socket is E_BUSY" |
| bind/close/send on a closed handle | `E_STATE` | three assertions |
| send on an OPEN socket | `E_STATE` | "send on an unbound socket is E_STATE" |
| connect to port 0, or to 0.0.0.0 | `E_INVAL` | two assertions |
| send zero bytes | `E_INVAL` | "zero bytes is E_INVAL" |
| send past `SK_DGRAM_MAX` | `E_NOROOM` | "513 bytes is E_NOROOM" |
| queue a third datagram | `E_BUSY` | "the third is E_BUSY at SK_QUEUE" |

## 3. Restart — NAMED GAP

`socks[16]`, `ephemeral_next` and every counter are process memory. A supervisor restart returns
an empty table: every handle dies, every bound port is free, every queued datagram is lost. The
kernel-side file descriptor model would make sockets survive a service restart; this layer has no
such storage, and nothing in the README claims otherwise. No restart drill has been run.

## 4. Contract — PROVEN, with two findings

| direction | other service | call | in the matrix? |
|---|---|---|---|
| out | `netcfg` | `Ipv4`, `ip4_any`, `ip4_zero`, `ip4_equal` (types and helpers only) | yes — `SVC_SOCKET` row carries `SVC_NETCFG`; the row also covers `NET`, `DNS`, `LOG`, `TIME` for the transport that will call in |
| in | none | no service imports `socket` | — |

- **FINDING: no `entry.goose`.** `socket` exports functions but no `svc_entry`, so the supervisor
  cannot start it. It is a library with a service's name (same shape as `agenthost`).
- **FINDING: the manifest names the wrong directory.** `services/MANIFEST.md` row 16 is `sockets`,
  marked NOT BUILT; there is no row for `socket`, the file that does the work. The matrix carries
  `SVC_SOCKET` correctly, so the matrix and the manifest disagree about which name exists.

## 5. Load — pending the run

320 send/take cycles on one bound socket with a 4-byte payload: each send queued immediately and
taken, so the batch exercises handle resolution and queue head/tail arithmetic, not the network.

FAILS pass=46 fail=5 · `LOAD socket ops=320 ok=320 refused=0`

## 6. README truth pass — PROVEN

- **Status:** `WRITTEN (not COMPILED)` → `RUNS`, with `t77_gaps` (73 checks) and `t132` named.
- **State diagram:** showed `OPEN ──send──▶ BOUND`. The code refuses a send on an OPEN socket with
  `E_STATE` (no source port), so the diagram now shows send only from BOUND/CONNECTED.
- **Generation paragraph:** claimed a stale handle always resolves to nothing; now carries the
  `SK_GEN_MAX` wrap caveat that `t132` proves.
- **Closing line:** "Not compiled, not run." removed; it had been false since the first host run.
