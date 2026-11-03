# Contract note — R13-001, agenthost startup contract

Status: **AUDITED — 2 gaps filed**.
Facet: what happens when this unit starts, what it requires before serving, and what it does
when that requirement is missing.

## Evidence

Command:

```sh
grep -nE 'svc_entry|service_main|fn ah_init|ah_inited|supervisor|refus' services/agenthost/*.goose
```

Output (comments kept because they are the only supervisor references):

```text
agenthost.goose:15:// discipline as the supervisor (B-L1-19..21). An operator who types the wrong number, or a
agenthost.goose:24:// something to make room -- is a policy this layer has no mandate to invent. Refusing the
agenthost.goose:77:var ah_inited: bool = false;
agenthost.goose:79:fn ah_init() {
agenthost.goose:88:    ah_inited = true;
```

No `svc_entry` and no `service_main` match. The word `supervisor` occurs in comments only;
no supervisor call or handle check is made in this unit.

## Corrected contract

`ah_init()` clears the 24 fixed agent slots and sets `ah_inited`. `ah_ensure()` calls it lazily.
The unit is a library: it has no process entry, no dependency probe, and no startup refusal path.
Its caller owns startup. Handles encode slot and generation; a handle is valid only while
`ah_inited` is true.

## Mismatches

- **R13-001-G1** — the README documents the missing `svc_entry` as a deviation, but the startup
  contract has no implementation to audit. Filed as a gap, not invented.
- **R13-001-G2** — the README says the unit "refuses to start without the supervisor (no table
  owner)"; `ah_init()` performs no such check and returns no code. See `GAPS_R13.md`.
