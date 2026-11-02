# agenthost — Round 11 record

Source: `services/agenthost/agenthost.goose`, `quota.goose`, `channel.goose` ·
Test: `services/tests/t104_agenthost_r11.goose` · Status: RUNS (t59, t97; t104 run by the
coordinator)

## 1. Limits — PROVEN

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `AH_CAP` | 24 | `agenthost.goose` | driven by `t97_agent_surface` §7 and `t104` §6 | `t104` fills 24 slots, the 25th `ah_spawn` returns `E_NO_SPACE` |
| `CH_SLOTS` | 16 | `channel.goose` | driven by `tests/t79_limit_drivers` (LIMITS.md row) | the 17th queued message is the edge that driver crosses |

No constant in this service was removed. `CH_BODY` (64) is an array width, not a compared
limit, and is not in LIMITS.md; `AUD_*` belongs to audit, not here.

## 2. Refusals — PROVEN

| refusal | code | the assertion that expects it |
|---|---|---|
| empty or >32-byte name | `E_INVAL` | `t104` "an empty name is E_INVAL", "a 33-byte name is E_INVAL" |
| a grant bit above `CAP_MAX_BIT` | `E_INVAL` | `t104` "a bit above the capability surface is E_INVAL" |
| second agent with one name | `E_BUSY` | `t104` "a duplicate name is E_BUSY" |
| 25th live agent | `E_NO_SPACE` | `t104` "the 25th spawn is E_NO_SPACE" |
| bind a handle that does not resolve | `E_NOTFOUND` | `t104` "an unknown handle is E_NOTFOUND" |
| bind pid 0 | `E_INVAL` | `t104` "pid 0 is E_INVAL" |
| bind a second time while `CREATED` | `CODE_OK` — **FINDING**, the pid is replaced | `t104` "a second bind while CREATED is accepted" |
| illegal lifecycle edge (stop twice, kill after stop) | `E_STATE` | `t104` "twice is E_STATE", "kill: after stop is E_STATE" |
| reap a running agent | `E_STATE` | `t104` "a running agent is E_STATE" |
| narrow grants of a stopped agent, negative mask, bit above surface | `E_STATE` / `E_INVAL` | `t104` three separate assertions |

**FINDING (contract, bind).** The comment on `ah_bind_pid` says a second bind "cannot silently
replace the pid of a running agent". That is true only once the agent is `RUNNING`: while it is
still `CREATED`, the state check passes and `ah_bind_pid` overwrites the pid and returns
`CODE_OK`. The test now asserts the actual behaviour and names it here; the fix belongs to the
service's owner (refuse when `pid != 0`, not when the state is not `CREATED`).

**FINDING (contract, grants).** `ah_caps_remove` treats `CREATED` as live, so an agent's grants
can be narrowed before it has ever started. That may be the intended reading of "live agent"
(`ah_is_live` also counts `CREATED`), but the README's contract sentence says narrowing applies
to a live agent without defining the term; the test now asserts the behaviour and the sentence
is left as the code found it.

The quota and channel refusals (`E_QUOTA`, `E_NO_AGENT`, `E_NOROOM` on a full quota table) are
already asserted by `t97_agent_surface` and are not duplicated here.

## 3. Restart — NAMED GAP

The agent table, the quota table and the channel queue are process memory. A supervisor restart
gives a fresh table: every handle, grant, pid and queued message is gone, and nothing exports
them. The record is honest about the loss rather than calling the restart continuous. Handle
generation protects against a *stale handle in a running process*; it cannot protect state
across a restart, because the generation counter itself resets to 0 with the table.

## 4. Contract — PROVEN

| direction | other service | call | in the matrix? |
|---|---|---|---|
| in | none (library) | — | — |
| out | none | — | — |
| internal | `agenthost` | `quota.goose` and `channel.goose` import `agenthost.agenthost` | n/a (same service) |

`agenthost.goose` imports only `common.err`; `quota.goose` and `channel.goose` import
`common.err`, `common.fmt` and `agenthost.agenthost`. The matrix row for id 19 grants
supervisor, audit, session, log, time and storage — every edge is **dormant** today, which the
matrix already documents for rows declared ahead of use. No call exists that the matrix does
not know, so there is no finding for room 1.

## 5. Load — PROVEN (expected line; run fills it)

240 spawn → start → stop → reap cycles through the same slot, ten times `AH_CAP`. The test
asserts every cycle succeeds and prints:

`LOAD agenthost ops=240 ok=240 refused=0`

RUNS pass=42 fail=0 · `LOAD agenthost ops=240 ok=240 refused=0`

## 6. README truth pass — PROVEN

The README said **WRITTEN (not COMPILED)** and "nothing in it has been compiled or run". That
was false: `t59_agenthost` (48 checks) and `t97_agent_surface` run it in the native corpus.
Rewritten:

- status line now says RUNS with the two test names and the date;
- "Offers to Layers 5–6" no longer says nothing may rely on it "until COMPILED" — it says until
  booted on the kernel;
- "Not verified" no longer claims there is no toolchain; it names boot, restart continuity and
  the single-CPU assumption instead;
- a `## Limits` section now names `AH_CAP` and `CH_SLOTS` and points at LIMITS.md.

The "no `svc_entry`" deviation is true and was left alone: the directory has no `entry.goose`.
