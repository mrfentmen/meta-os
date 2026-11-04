# Meta Surveyor — model adapter (Mac-side verifier, under-a-dollar cap)

Branch-only, no merge, no OS touched. Rowan's lane for del's 2026-11-04
final-hours orders: every application needs to be agentic, and the
model is to be implemented with spend under a dollar.

## What this is

The guard and budget ledger in front of a model-backed verifier for
Surveyor: `eval/surveyor/model_adapter.py` (stdlib only) plus its
tests in `eval/surveyor/test_model_adapter.py`.

It answers del's "implement them model" order as far as this VM can
honestly go. The live call itself is NOT here, for two standing
reasons that del set himself:

- The key lives on del's Mac. Del supplies it at run time; it is never
  committed, never posted on the bus, and never held on this VM.
- This VM fires no live model calls. The real transport is Mac-side:
  the runner there injects a transport into `ModelAdapter`, and only
  then can a verdict be produced. Until then every request returns
  `unconfigured` or `no-transport` — and, crucially, no verdict is
  fabricated to fill the gap.

Spend on this branch: $0. The tests use fixture rates only.

## What the model may and may not decide

Surveyor's spec roles are S sensor, V verifier, H human-confirm
(`docs/META_SURVEYOR_SPEC.md`, branch `rowan/surveyor-spec`). The
model backs the V side as triage help for flagged readings only:

- MAY: read a flagged reading's summary (field, value, place, device
  class) and suggest triage — e.g. "flag for human", with a reason.
- NEVER: publish a reading. Publication still requires the spec's
  two-agent confirmation: an S reading plus an independent V check
  from a different device, same place/window, within tolerance. The
  model never replaces the second sensor and never counts as
  confirmation. Every verdict the adapter returns carries
  `advisory_only: True, publishes: False`.
- NEVER: see audio or person data. Summaries carrying either are
  rejected before they reach the guard, same as the eval harness
  (`rowan/surveyor-eval` @ 431a8b7, 11/11 scenarios + 6/6 unit tests).
- NEVER: trigger dispatch. Dispatch happens only on a confirmed
  cluster (>= 3 confirmed readings, same field + place), per spec.

## The under-a-dollar cap, enforced in code

- Hard cap: $1.00 per run by default (`Budget`, Decimal ledger, exact
  to the cent — no float drift).
- Guard order before any transport call: key present, then transport
  present, then budget. A request that would take spending past the
  cap is refused with status `refused-over-budget`, the transport is
  never called, and nothing is charged. Refused, unconfigured, and
  no-transport requests all charge $0.
- Rates are NOT shipped in this module. The operator sets
  prompt/completion rates at run time from the provider's current
  price page; the constructor refuses to run without them, so a stale
  price can never silently become a false quote. Test rates in
  `test_model_adapter.py` are fixtures, not vendor prices.

## Mac-side run book (for del, when he runs it)

1. Set the key in the environment on the Mac (never in a file that
   gets committed, never on the bus).
2. Set the current prompt/completion rates from the provider's price
   page, and the cap (default $1.00).
3. Inject the real transport, run the flagged-reading queue through
   `request_verdict`, and keep the ledger output with the run: spent,
   remaining, and every refusal. If the ledger shows a refusal, that
   is the cap working, not a failure to hide.
4. Verdicts go to role H triage only. Nothing the model says
   publishes, confirms, or dispatches on its own.

## Honest caps

- This branch proves the guard, the ledger, and the refusal paths —
  14 unit tests, all green — not any model result. No model has been called from this branch, and no
  verdict in it is real model output (the tests use a fake transport
  that says so).
- This covers Surveyor only. Science Lab's agentic question stays
  Hana's lane; no claim is made about any other application, any
  cure, or any compound.
- Companion branches: spec `rowan/surveyor-spec` @ 0dadabd, demo
  `rowan/surveyor-demo` @ 4f6056c, eval `rowan/surveyor-eval` @
  431a8b7 — all branch-only, all off main af457eb.
