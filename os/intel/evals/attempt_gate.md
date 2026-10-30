# OS-096: attempt budgets + the escalation gate (Milo, 2026-10-27)

OS-096's acceptance, proven on fixtures: a deliberately
impossible job burns exactly its budget, parks, and
escalates exactly once -- no loop, no duplicate pushes; a
crew-fixable blocker in the same drill is resolved with
zero escalation.

The gate (intel/gate.py) is the OS-095 ladder's other
half. The ladder acts while attempts remain; the gate
ends a job's repair life when the budget is spent or when
the blocker is genuinely Dale's call (money, permission,
direction, as an explicit blocker_kind field -- never
inferred from free text, so a crew-fixable job is never
parked by a guessed kind). Each park yields two journal
records: a parked record and an escalation record carrying
the blocked-push payload built by intel/push.py
build_blocked_push on the parked job shape (status
"blocked", question as note), so the payload quotes the
question verbatim and validates. The gate builds the
payload and never sends it: the ring belongs to the Web
Push worker, and the call site wiring a real gate park to
that worker is Hana's OS-097 work, owed after this one.
Dedupe (park:<job>) makes a second tick over a parked job
journal nothing new.

The drill (intel/drills/attempt_gate.py, transcript
intel/evals/attempt_gate.log) runs seven phases, all
PASS:

- impossible: job 7 at 0/2 and 1/2 stays quiet; at 2/2
  it parks with exactly one escalation whose payload
  validates, and a third tick journals nothing new.
- crew-fixable: job 8 blocked on a dependency at 0/3
  across three ticks yields zero parks, zero escalations.
- dale-call: job 9 blocked on money at 1/5 parks at once
  despite attempts remaining, its payload quoting the
  note "needs $40/mo API key approval" verbatim, and a
  second tick journals nothing new.
- malformed: non-numeric, missing, zero, and negative
  budgets plus id-less records yield nothing, no crash.
- no-extra-contact: exactly two escalations across the
  drill, both payloads valid, the drill's sent ledger
  empty (the gate builds, never sends).
- immutable: a gate tick leaves snapshot and journal
  unchanged.
- brief: parked and escalation lines name job 7.

Pinning tests: tests/test_intel_attempt_gate.py (14
tests: spent budget, second-tick silence, Dale-call with
and without a note, crew-fixable kinds, unbudgeted and
malformed budgets, done jobs, id-less entries, attempts
arithmetic, brief lines, immutability, no send path,
drill pass, eval note, no em dash).

NOT proven here: a phone actually ringing (the Web Push
worker wiring is OS-097, owed to Hana); a live worker
burning real attempts on a booted test image (no test
image in repo); the plan/META_OS.md spec line (shared
files are integrator-only under the 2026-10-27 folders
rule, so that line is Pax's to add). The decision,
journal, brief, and exactly-once halves are proven here.
