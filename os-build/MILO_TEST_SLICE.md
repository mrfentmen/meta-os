# Milo — testing slice (Del's crew-wide testing directive, sliced by Pax 2026-11-02)

Del's direction, as Milo acked it on room 1: more testing on the programs and the
OS with the Meta API (about $10), an agentic end-to-end loop, programs autonomous
too. This file is Milo's piece of it: the lane, the cap, the key route, and the
checks. Everything else in the 500 order is unchanged.

## Lane

- Milo owns **gate-1 for agentic-loop work** as branches land (his own bus words
  are the verdict, as always) and **the API-backed end-to-end checks** below.
- Milo does NOT run live-key calls from his VM (see key route). He writes the
  checks, the fixtures, and the verdicts; the live runs execute where a key
  already works.
- Status file: `os-build/MILO_TEST_STATUS.md` on his branch, one line per check:
  `MT-xx | VERIFIED or BLOCKED | what ran | est cost | where the receipt lives`.

## Spend cap

- **$10 total** for this directive, all live-key work combined, tracked through
  the spark guardrail state. At the cap: stop, post the tally to room 1, no
  overage. Estimates use the published Spark rates and say so.
- Current state (2026-11-02 21:36): the Meta API billing account returned
  **HTTP 402 (out of credits)** during Pax's live hunt #3. Until Del tops the
  account up, every live-key item below is PREP ONLY — write it, fixture it,
  leave it ready to fire.

## Key route

- Pax's key lives in the Secure Vault connector; Pax has never seen the value
  and cannot hand it over. Milo's VM holds no key (Milo's own report).
- Route A (Del's action): Del places the key on Milo's VM the same way it sits
  on the Mac. Then Milo runs live checks himself, inside the cap.
- Route B (works today, once credits exist): Milo posts the check spec; Pax
  executes the live run through the helper and posts the receipt; Milo issues
  the verdict from the receipt. Slower, no key movement.
- Until Del picks a route AND credits exist: prep only. No workaround, no new
  account, no borrowed key.

## The checks

- **MT-01 — Agentic loop, end to end, staged frames.** Patrol -> review ->
  judge -> investigation -> simulated dispatch on the committed eval frames.
  Proof: one run record per division (vigiles, ignis, medicus) with the
  timeline showing every step and `judge_mode` recorded; dispatch receipt is a
  `sim-` receipt from the loopback endpoint or the check is BLOCKED, never
  faked.
- **MT-02 — Agentic loop, live frames.** Same loop over live DOT cameras via
  the hunt machinery. An honest zero (no flag) is a passing result if the loop
  ran clean; a flag must end in a `sim-` receipt or be reported as failed.
  Proof: hunt-format record on main, landed by Pax.
- **MT-03 — Science Lab gateway, live backend.** One discovery cycle through
  the MCP-GATEWAY backend (Pax bench 1) with a real query. Proof: the cycle
  record plus the gateway record naming backend "MCP-GATEWAY".
- **MT-04 — Officina loop, one full cycle.** The faber loop runs one cycle
  against its harness; the known `green cycle` failure is reported as-is if it
  still fails. Proof: harness output + cycle record.
- **MT-05 — Musica keeper, overnight pattern in miniature.** Keeper starts,
  ticks, and writes its ledger on a short clock. Proof: ledger lines + a
  PASS/FAIL verdict from Milo.
- **MT-06 — Nuntius relay + board round trip.** A message posted through the
  relay is read back from the board with matching content. Proof: both sides
  of the round trip in one record.
- **MT-07 — Hands-Free intake path.** Text-first intake case set runs against
  the real intake path (Buffy R13 cases are the fixture start). Proof: case
  results file, failures named, none hidden.
- **MT-08 — Gate duty for the loop itself.** Every agentic-loop branch that
  lands during this directive gets Milo's gate-1 in his own words before Pax
  merges, same discipline as B10 and the kernel lanes.

## Fences (unchanged, repeated because they bind here too)

- Dispatch is simulated loopback only, labelled SIMULATED everywhere. Nothing
  dials a real service, ever.
- No mock or placeholder result presented as a pass. A check that cannot run
  is BLOCKED with the reason, in those words.
- Kernel fences untouched: syscalls.rs frozen, kernel/src is Rowan's pen.
- Spend stops at the cap even mid-check; a partial run is reported partial.
