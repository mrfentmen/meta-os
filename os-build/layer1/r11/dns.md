# dns — Round 11 record

Source: `services/dns/dns.goose` · Test: `services/tests/t116_dns_r11.goose` · Status: RUNS

## 1. Limits — PROVEN

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `DNS_NAME_MAX` | 255 | `dns.goose` | driven: 255-byte name builds, 256 refused; read path refuses a decoded name past 255 | `t79_limit_drivers` (build side), `t116_dns_r11` (both sides) |
| `DNS_LABEL_MAX` | 63 | `dns.goose` | driven: a 63-byte label builds, a 64-byte label is refused | `t79_limit_drivers`, `t116_dns_r11` |
| `DNS_MAX_JUMPS` | 32 | `dns.goose` | driven both ways: a 32-link backwards chain resolves, a 33-link chain is refused | `t79_limit_drivers` (self-pointer refusal), `t116_dns_r11` (exact boundary) |
| `DNS_QUERY_MAX` | 512 | `dns.goose` | unreachable on the host: a 255-byte name encodes to at most 12 + 256 + 5 = 273 bytes, so the 512-byte output buffer cannot fill | LIMITS.md unreachable row; the structural bound is the name cap |

`DNS_QUERY_MAX` is not removed: it is the size of the caller's buffer and the format's classic
UDP ceiling. It is enforced (`out.len < 12` and every bounds check), but no legal name reaches it.

Run note: `t116_dns_r11` was written in this pass and has not been executed by this worker. Its
boundary assertions become evidence only when the coordinator's run appears in section 5; the
rows above that cite `t79`/`t57` are already measured.

## 2. Refusals — PROVEN

| refusal | code | the test assertion that expects it |
|---|---|---|
| empty name, leading dot, doubled dot | `-1` from `dns_build_a_query` | `t116`: "an empty name is refused", "a leading dot is an empty label", "a doubled dot is an empty label" |
| label > 63 bytes, name > 255 bytes | `-1` | `t116`: the 64-byte and 256-byte cases |
| reply id != query id | `E_STATE` | `t57`, `t116`: "a wrong id is E_STATE" |
| QR bit clear (a query, not a reply) | `E_CORRUPT` | `t116`: "a query is not a response" |
| `QDCOUNT != 1` | `E_CORRUPT` | `t116`: "QDCOUNT != 1 is E_CORRUPT" |
| `ANCOUNT < 1` | `E_RESOLVE` | `t116`: "no answers is E_RESOLVE" |
| A record `RDLENGTH != 4` | `E_CORRUPT` | `t116`: "an A record that is not 4 bytes is E_CORRUPT" |
| non-zero rcode other than NXDOMAIN | `E_RESOLVE` | `t116`: "SERVFAIL is E_RESOLVE" |
| packet under 12 bytes | `E_CORRUPT` | `t116`: "a packet under 12 bytes is E_CORRUPT" |
| forward, same-offset, reserved-type and over-long pointers | `false` from `dns_read_name` | `t79`, `t116`: four pointer cases plus the 255-byte decode cap |
| feeding a query that is not `Q_SENT` | `E_STATE` | `t116`: "feeding a completed query is E_STATE" |

NXDOMAIN is deliberately **not** a refusal: it returns `CODE_OK` with `rcode = RCODE_NXDOMAIN`,
because "the name does not exist" and "the wire ate the packet" are different facts and a caller
that cannot tell them retries a name that will never resolve (`t57`, `t116`).

## 3. Restart — NOT APPLICABLE

The resolver holds no state between calls: no cache, no outstanding transaction table, no
counters. A supervisor restart re-executes the same pure functions, and nothing is lost because
nothing is kept. The `Query` value is caller-owned; a restart of the resolver does not own it.

## 4. Contract — PROVEN

| direction | other service | call | in the matrix? |
|---|---|---|---|
| out | netcfg | `Ipv4` type only (no function call at run time) | yes: `cm_set(SVC_DNS, NET | NETCFG | LOG)`; the type edge is dormant because it is not a call |
| in | socket | a bound socket may resolve a name | yes: `cm_set(SVC_SOCKET, ... DNS ...)` |
| in | timesync | no direct call | no; timesync uses socket, and the matrix carries socket only |
| in | any face service | none | no; the six face rows do not include DNS |

No call in or out lacks a matrix edge. `dns.goose` imports `netcfg` for `Ipv4`, which the matrix
allows; the audit reports that edge DORMANT because the import is a type, not a call.

## 5. Load — NAMED GAP

The test builds and parses one hundred query/answer pairs, ten times the normal single lookup,
with every tenth reply deliberately carrying another transaction's id; the ninety valid replies
must parse and the ten wrong-id replies must be refused. This approaches no capacity limit — the
resolver has none — and measures only that the parse path holds across a batch.

RUNS pass=50 fail=0 · `LOAD dns ops=100 ok=90 refused=10`

## 6. README truth pass — PROVEN

- Status said **WRITTEN (not COMPILED — no Goose toolchain on this Mac)**. It is RUNS: `t57`
  passed 45 checks and `t79` drives the name limits, both in the native corpus. The status line
  now says so and names the Round 11 driver.
- The closing line said "Not compiled, not run." Replaced with the measured position: compiled
  and run as a host driver, not booted on the kernel.
- The refusal table gained the rcode split (NXDOMAIN reported, other non-zero `E_RESOLVE`) and
  the A-record length rule, both of which the code enforces and the table omitted.
- Scope, the compression-pointer explanation and the bug note were already true and are
  unchanged.
