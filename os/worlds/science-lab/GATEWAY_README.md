# Gateway README — controlled MCP gateway (Section 8)

The lab's agents reach outside tools through exactly one door:
`os/worlds/science-lab/gateway.py`. No agent calls a tool server
directly. Every call is recorded; every refusal is recorded.

## Tools (allowlist, Task 71)

Nine boss-named MCP servers, nothing else:

`openalex` · `archive-org` · `open-library` · `gbif` · `wikidata` ·
`wikisource` · `ietf` · `federal-register` · `osv`

`gateway.ALLOWLIST` is the source of truth. A call naming any other
tool raises `GatewayRefused` and files a `refused-allowlist` record.

## Scopes (Task 74)

Each agent may perform only its scoped operations (`search` / `read`):

| agent | scope |
|---|---|
| research-director, literature-researcher | search, read |
| hypothesis-generator, scientific-analyst, mathematics-researcher, statistician, scientific-critic, research-archivist, independent-verifier | read |
| computational-scientist, biology/chemistry/physics-researcher (runners) | none — may not browse |
| unknown agents | none (default-deny) |

Short aliases (`literature`, `runner`, `director`, …) map to the
canonical lab agent ids. A call outside scope raises `GatewayRefused`
and files a `refused-scope` record.

## Call records (Task 72) and refusal (Task 73)

`call_tool(agent, tool, args)` records to
`records/gateway/calls.jsonl` on EVERY path — success and refusal:

`agent, tool, op, args_hash, result_hash, cost, cycle_id, backend,
status, timestamp`. Refusals carry `result_hash: null` plus a `reason`
and a `status` of `refused-allowlist`, `refused-scope`,
`refused-op`, `budget-stopped`, or `gateway-closed`.

## Quarantine (Task 75)

`call_tool` returns `quarantine(result)`: a `gateway-source` envelope
with `status: "unconfirmed"`. A gateway result is a lead, never
evidence. Confirmation happens ONLY when the literature job pins it
(`literature.assemble_brief`); `is_quarantined()` tells the two apart.
Quarantined records never carry `pinned_sources`.

## Budget (Task 76)

Calls per cycle are capped by `lab_config.json`'s `gateway` section
(`maxCallsPerCycle`, default 50). The next call over the cap raises
`GatewayBudgetExceeded`, files a `budget-stopped` record, and writes
`records/gateway/<cycle>.budget-receipt.json`. The caller must stop
the run. A stopped run earns no level and files no claim.

## Offline mode (Task 77)

`Gateway(cycle_id, offline_mode=True)` (or `set_offline(True)`)
closes the gateway: `call_tool` raises `GatewayClosed`, records the
refusal, and the cycle runs its deterministic parts only.
`Gateway.status()` / `offline_record()` file the closed-gateway
state (`records/gateway/<cycle>.offline.json`) so the record says
the cycle ran offline.

## Honesty

Backend is always named. Today only `LOCAL-SHELF` exists: calls are
answered from the lab's own department shelves (`shelves/*.json`),
with `cost 0.0` and `network: no external network touched`. There is
no live-network path in this module. See the worked example
`records/examples/gateway_example.json` (hashes re-verifiable) and
the tests `tests/science-lab/test_section8.py`.
