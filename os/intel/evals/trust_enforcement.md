# OS-112: signed-job trust list enforcement (Milo eval note)

## What was built

`intel/trust.py` judges every open job before any local
agent may claim it. A job signed by a trusted crew with
a valid HMAC-SHA256 v2 signature is claimable. The same
job unsigned, signed by an untrusted kid, carrying a
bad, expired, or legacy v1 signature is refused at claim
time, with one journal record per refused job (dedupe
`trust-refusal:<job>`) and the exact refusal text for
the job record. Badge claims clamp to the local policy
in the same decision, and every dropped badge is named
in the record. When no badge policy is stated, claims
pass through and the decision says the policy is unset
instead of inventing one; OS-115 (Dale's federation
policy ruling) is the decision that fills it in.

## Drill result

`intel/drills/trust_enforcement.py`: 9 phases, ALL PASS
(transcript: `intel/evals/trust_enforcement.log`). The
trusted job is claimable with its driver badge dropped
and named; unsigned, untrusted-kid, transplanted,
expired, and legacy v1 jobs are each refused with the
exact reason their case earns; a job under a spoofed
crew nick is refused on its signature, proving a nick
is never authority; a tick journals 2 refusals and
nothing for the trusted job, a second tick journals
nothing, inputs are never mutated, and the module
carries no push path. Signatures in the drill are real
HMAC-SHA256 v2 signatures computed with
`jobs._sign_job_v2` over fixture-only secrets.

## Tests

`tests/test_intel_trust.py`: 14 pinning tests, all
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
  machine.
- Dale's OS-115 policy ruling: until it lands, the
  unset-badge-policy case is reported, not decided.
- The OS-114 negative test itself (the untrusted
  machine joining and re-posting under a spoofed
  nick as a room-level drill): the spoofed-nick case
  is proven at the decision level here, and OS-114
  is the next Milo task in plan order.
- The plan/META_OS.md spec line for OS-112: shared
  files are integrator-only under the Oct 27 folders
  rule, so that line is Pax's to add, not Milo's.
