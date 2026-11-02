# dhcp — Round 11 record

Source: `services/dhcp/dhcp.goose` · Test: `services/tests/t114_dhcp_r11.goose` · Status: RUNS
(`t57_dhcp_dns` 45 checks, exit 0; this round adds the refusal table and the state machine)

## 1. Limits — NAMED GAP

`LIMITS.md` carries no `dhcp` row: the file declares no limit-shaped constant. What looks like
one is structural, not named:

| bound | value | in | outcome | evidence |
|---|---|---|---|---|
| packet buffer | 576 bytes | `dhcp_build_discover` / `dhcp_build_request` / `dhcp_parse` signatures | not a limit (a caller-owned buffer size) | `t114`: a discover and a request both fit under it (`dn < 576`, `rn < 576`) |
| fixed header | 240 bytes | `dhcp_parse` | driven by `t114` | a 239-byte slice returns `E_CORRUPT` |
| retry ceiling | 6 in SELECTING, 4 in REQUESTING | `dhcp_step` | driven by `t114` | seven unanswered DISCOVERs end `-1` / `E_TIMEOUT` / `D_FAILED` (the seventh increments `retries` to 7) |

The ceiling is inside `dhcp_step`, not a named constant, so `gen_limits.py` cannot see it. That
is the gap this section names: a limit enforced by a literal is still a limit, and it now has a
test but no entry in the generated table.

## 2. Refusals — PROVEN

| refusal | code | the `t114` assertion that expects it |
|---|---|---|
| packet under 240 bytes | `E_CORRUPT` | `a packet under 240 bytes is E_CORRUPT` |
| `op` not BOOTREPLY | `E_CORRUPT` | `a BOOTREQUEST where a reply is expected is E_CORRUPT` |
| `hlen` not 6 | `E_CORRUPT` | `hlen other than 6 is E_CORRUPT` |
| missing magic cookie | `E_CORRUPT` | `a missing magic cookie is E_CORRUPT` |
| option length past the packet | `E_CORRUPT` | `an option that runs past the packet is E_CORRUPT` |
| `yiaddr` 0.0.0.0 | `E_NO_ADDRESS` | `yiaddr 0.0.0.0 is E_NO_ADDRESS` |
| zero-second lease | `E_INVAL` | `a zero lease is E_INVAL` |
| no subnet mask | `E_NO_MASK` | `no subnet mask is E_NO_MASK` |
| non-contiguous mask | `E_NO_MASK` | `a non-contiguous mask is not accepted as a mask` |
| NAK from the server | `E_REFUSED` | `a NAK is E_REFUSED and returns to SELECTING` |
| clock moved backwards | `E_STATE` | `a clock that moved backwards is E_STATE` |
| retries exhausted | `E_TIMEOUT` | `seven unanswered DISCOVERs end in FAILED with E_TIMEOUT` |
| unknown option | skipped, not refused | covered by the valid ACK in `t114` (options 53/1/51 only) |

Not reachable from a host driver: none of the refusals above. The state machine takes time as
an argument, which is what makes the timeout and expiry cases drivable without sleeping.

### FINDING — the state machine never installs the lease (2026-11-02)

`dhcp_step` calls `dhcp_lease_ok(offer)` in both the OFFER and ACK branches but never assigns
`offer` to `c.lease`. The validation passes and the client advances to `D_BOUND`, yet
`lease_ms`, `t1_ms` and `t2_ms` remain 0 from `dhcp_init`. On the next step `age >= c.lease.lease_ms`
is true for every age, so the client treats the lease as already expired, drops to `D_SELECTING`
and sends DISCOVER. Consequences, all reproduced by `t114` and asserted there as FINDING lines:

- **T1 renewal is unreachable** — the client never reaches `D_RENEWING`.
- **T2 rebinding is unreachable** — likewise `D_REBINDING`.
- **A bound client re-DISCOVERs on its next poll**, one step after the ACK, instead of waiting
  out any part of the lease.

The fix belongs to the dhcp owner: in the ACK branch, copy the lease in (`c.lease = offer`) and
set `bound_at_ms` from the same clock; in the OFFER branch, keep the offer so the REQUEST and the
later ACK can be checked against it. `t114`'s three FINDING assertions flip to the contract tests
(`silent before T1`, `renews at T1`, `rebinds at T2`) when that lands. They were not deleted: the
contract is still written, asserted against the behaviour that actually runs.

## 3. Restart — NAMED GAP

`Client` holds the whole lease in memory (`state`, `lease`, `retries`, `backoff_ms`). A restart
under the supervisor therefore loses the lease and the client begins at `D_IDLE`; the first
`dhcp_step` sends DISCOVER. That is safe — a fresh DISCOVER is the correct response to
"address unknown" — but **continuity was not run**: no supervisor drill killed this client
mid-lease and observed the re-DISCOVER. The loss is named: the lease, the retry counter and the
backoff state, all recoverable by protocol, none persisted.

## 4. Contract — PROVEN

Read from the file and the matrix (`SVC_DHCP = 14`):

| direction | other service | call | in the matrix? |
|---|---|---|---|
| out | `netcfg` (13) | `ip4`, `ip4_mask_contiguous`, `Ipv4` | **yes** — `SVC_DHCP` row allows `NET`, `NETCFG`, `TIME`, `LOG` |
| out | `net` (12) | none today | allowed but dormant |
| out | `time` (5) | none — time is a parameter | allowed but dormant |
| out | `logd` (3) | none | allowed but dormant |
| in | — | none | **FINDING: no service imports `dhcp`; no `entry.goose` exists** |

The finding is the one worth carrying: `dhcp` is compiled into `services/root.goose` as a
library and driven by tests and a peer, not started by the supervisor. The matrix declares four
outbound edges and only one is live.

## 5. Load — NAMED GAP

Ten exchanges' worth of parse + OFFER handling, counted by the test; it approaches the retry
ceiling's neighbourhood (20 operations, no refusals). The numbers exist only after a run:

```
RUNS pass=41 fail=0 · `LOAD dhcp ops=20 ok=20 refused=0`
```

## 6. README truth pass — PROVEN

- **“Status: WRITTEN (not COMPILED — no Goose toolchain on this Mac)”** → `RUNS`, naming
  `t57_dhcp_dns` (45 checks) and this round's `t114`.
- **“Not compiled, not run.”** at the end → removed; both were false.
- The “Honest gaps” list (no jitter, no DECLINE/RELEASE/INFORM, broadcast flag) is true and was
  left as written.
- The parser refusal table matches the code exactly and needed no change.
