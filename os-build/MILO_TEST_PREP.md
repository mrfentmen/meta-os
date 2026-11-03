# Milo — testing slice prep (MT-01..MT-08, ready-to-fire specs)

Status: PREP ONLY as of 2026-11-02 21:38 EST. No live-key call has been made
from Milo's VM for this slice. Firing waits on BOTH: (1) Del tops up Meta API
billing (HTTP 402 during Pax's live hunt #3), and (2) Del picks a key route
(Route A: key placed on Milo's VM; Route B: Milo specs, Pax runs live, posts
the receipt, Milo verdicts). Spend cap $10 total, guardrail-tracked; stop at
the cap, partial runs reported partial. Dispatch is simulated loopback only,
labelled SIMULATED everywhere; nothing dials a real service, ever.

How to fire each check (Route B wording: Pax executes, posts the receipt,
Milo verdicts from the receipt; Route A wording: Milo runs the same steps
himself inside the cap):

- MT-01 — Agentic loop, staged frames. Run patrol -> review -> judge ->
  investigation -> simulated dispatch over the committed eval frames, one run
  record per division (vigiles, ignis, medicus), timeline showing every step,
  `judge_mode` recorded. PASS needs every step on the timeline and a `sim-`
  receipt from the loopback endpoint; a flag ending anywhere else is a FAIL,
  reported as failed, never faked.
- MT-02 — Agentic loop, live frames. Same loop over live DOT cameras via the
  hunt machinery (server/queue/livehunt.py). An honest zero (no flag) is a
  PASS if the loop ran clean; a flag must end in a `sim-` receipt or be
  reported as failed. Proof is a hunt-format record landed on main by Pax.
- MT-03 — Science Lab gateway, live backend. One discovery cycle through the
  MCP-GATEWAY backend (mcp-gateway/, Pax bench 1) with a real query. PASS
  needs the cycle record plus the gateway record naming backend "MCP-GATEWAY".
- MT-04 — Officina loop, one full cycle. The faber loop runs one cycle
  against its harness (fixtures start at tests/officina/). The known `green
  cycle` failure, if it still fails, is reported as-is, not worked around.
  Proof is harness output + cycle record.
- MT-05 — Musica keeper, overnight pattern in miniature. Keeper starts,
  ticks, and writes its ledger on a short clock (fixtures start at
  tests/musica-keepers.test.mjs and tests/musica-overnight.test.mjs). Proof
  is ledger lines + a PASS/FAIL verdict from Milo.
- MT-06 — Nuntius relay + board round trip. One message posted through the
  relay is read back from the board with matching content. Proof is both
  sides of the round trip in one record; a mismatch is a FAIL.
- MT-07 — Hands-Free intake path. The text-first intake case set runs
  against the real intake path (fixture start: Buffy R13 cases, handsfree/).
  Proof is a case results file with failures named, none hidden.
- MT-08 — Gate duty for the loop itself. Every agentic-loop branch that lands
  during this directive gets Milo's gate-1 in his own words before Pax merges,
  same discipline as B10 and the kernel lanes. This 5-minute job does not run
  gate-1; that duty sits with Milo's rust-work loop, and its verdicts are
  relayed into MILO_TEST_STATUS.md as they land. No duplicate gate, no
  gate run from this branch.

Cost notes: no cost estimate is claimed in this prep file — estimates are
made at fire time from the published Spark rates and tracked against the $10
cap, because an invented estimate would be worse than an honest TBD.
