# Milo — testing slice status (Del's crew-wide testing directive, sliced by Pax 2026-11-02)

Spend cap: $10 total for the directive, guardrail-tracked. Spent so far on this
slice: $0. No live-key call has been made from Milo's VM.

Blocker on every live-key item (2026-11-02 21:38 EST): Meta API billing
returned HTTP 402 (out of credits) during Pax's live hunt #3, AND no key route
has been picked yet (Route A: Del places the key on Milo's VM; Route B: Milo
specs the check, Pax executes the live run and posts the receipt, Milo verdicts
it). Until BOTH are resolved, every live-key item below is PREP ONLY: written
and fixtured, ready to fire, not run live. Nothing here is a pass. A check that
cannot run is BLOCKED, in those words.

One line per check, per os-build/MILO_TEST_SLICE.md:

- MT-01 | BLOCKED | prep only, full detail landed 2026-11-02 21:43 EST in MILO_TEST_MT01.md (per-division run record shape, five-step timeline, judge_mode recorded, sim- receipt rule; vigiles has no eval/ scenario set on main, staged frames are test-footage/frames/vigiles-*.jpg); no run yet, firing still waits on Del's route pick AND 402 top-up | est cost: TBD at fire time from published Spark rates, inside the $10 cap | receipt: none yet; run record per division (vigiles, ignis, medicus) to land on main via Pax (Route B) or Milo (Route A) when fired
- MT-02 | BLOCKED | prep only: live-frame loop spec written, no run yet; hunt machinery is server/queue/livehunt.py | est cost: TBD at fire time from published Spark rates, inside the $10 cap | receipt: none yet; hunt-format record to land on main via Pax when fired
- MT-03 | BLOCKED | prep only: Science Lab gateway cycle spec written, no run yet; backend is mcp-gateway/ (Pax bench 1) | est cost: TBD at fire time from published Spark rates, inside the $10 cap | receipt: none yet; cycle record + gateway record naming backend "MCP-GATEWAY" when fired
- MT-04 | BLOCKED | prep only: Officina cycle spec written, no run yet; harness fixtures start at tests/officina/ | est cost: TBD at fire time from published Spark rates, inside the $10 cap | receipt: none yet; harness output + cycle record when fired; known `green cycle` failure reported as-is if it still fails
- MT-05 | BLOCKED | prep only: Musica keeper miniature spec written, no run yet; keeper fixtures start at tests/musica-keepers.test.mjs and tests/musica-overnight.test.mjs | est cost: TBD at fire time from published Spark rates, inside the $10 cap | receipt: none yet; keeper ledger lines + Milo PASS/FAIL verdict when fired
- MT-06 | BLOCKED | prep only: Nuntius round-trip spec written, no relay message sent for this check | est cost: TBD at fire time from published Spark rates, inside the $10 cap | receipt: none yet; both sides of the round trip in one record when fired
- MT-07 | BLOCKED | prep only: Hands-Free intake spec written, no run yet; fixture start is the Buffy R13 cases, path handsfree/ | est cost: TBD at fire time from published Spark rates, inside the $10 cap | receipt: none yet; case results file, failures named, none hidden, when fired
- MT-08 | BLOCKED | prep only for this branch: gate duty for agentic-loop branches stays with Milo's rust-work loop (this 5-minute job does not run gate-1); this branch monitors loop branches and records gate verdicts from that loop here as they land | est cost: $0 (compile gate, no live key) | receipt: rust-work loop room 1 posts + branch tips, relayed here as they land

Fences: dispatch is simulated loopback only, labelled SIMULATED everywhere.
Nothing dials a real service, ever. No mock or placeholder result is presented
as a pass. syscalls.rs stays frozen; kernel/src stays Rowan's pen.
