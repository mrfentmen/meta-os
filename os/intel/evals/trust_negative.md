# Eval: OS-114 trust negative test (Milo)

`intel/drills/trust_negative.py`: 8 phases, ALL PASS
(transcript: `intel/evals/trust_negative.log`). An
untrusted machine joins the fixture room and posts a
job; the same job is re-posted under a spoofed crew
nick. The trusted machine's overseer refuses both
attempts, logs both, and surfaces both, and no work
is exchanged.

The two attempts earn the two reasons the OS-114
acceptance names. The outsider's own signed post is
refused as "untrusted signer". The spoofed-nick
re-post carries no signature and is refused as
"signature absent": a familiar name with no proof is
refused exactly like a stranger. A guard phase proves
the signed variant of the spoof (spoofed nick,
outsider signature) is refused as "untrusted signer"
too, so no spoof shape slips through; the guard is
decision-level only, so the room log holds exactly
the two attempts.

Across the test window (3 ticks, 3 trusted agents
attempting claims at each tick), zero hostile jobs
are claimed. The first tick journals exactly 2
refusal records; later ticks journal nothing new.
Both refusals appear on the brief lines and on the
OS-117 federation feed, naming the outsider machine
in both. Refusal notes name both reasons. The end
state has no claim, progress note, or artifact for
any hostile job, while the trusted control job stays
claimable, so the room is clean, not empty. Inputs
are never mutated, and the trust module carries no
push path.

Signatures in the drill are real HMAC-SHA256 v2
signatures computed with `jobs._sign_job_v2` over
fixture-only secrets derived from labels, never real
crew keys. No keyring file is read or written, no
live bus is touched, and the room itself is plain
fixture dicts.

## Tests

`tests/test_intel_trust_negative.py`: 14 pinning tests, all
passing (see suite count in the commit message).

## What this does NOT prove

- A refusal landing in a live job record on a booted
  test image (no test image in repo; the overseer
  writes the refusal from `refusal_note`, it does not
  write it itself, by the ladder/gate judgment-not-
  hands rule).
- The OS-110 join feeding a real trust list, or the
  OS-113 two-machine drill (neither landed yet), so
  no caller yet fills the trust list from a joined
  machine, and this drill's room is a fixture room,
  not two live machines.
- Dale's OS-115 policy ruling: until it lands, the
  badge policy in this drill is the OS-112 fixture
  policy, reported, not decided.
- The plan/META_OS.md spec line for OS-114: shared
  files are integrator-only under the Oct 27 folders
  rule, so that line is Pax's to add, not Milo's.
- The next Milo task in plan order: OS-119, the Muse
  wake adapter (FND-029 still needs Pax's answer and
  stays skipped).
