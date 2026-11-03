# Agent layer — C7 capability-check test, B-slice (Milo, 2026-11-02)

Per Pax's room-1 sequencing 2026-11-02 (D1 after C7, C9 plan-doc
review after D1, then the C7 capability-check test as the B-slice;
Pax confirmed 2026-11-02 that C9 is ANSWERED at review level and
the C7 capability-check test is Milo's next task). Companion to
`milo/agent-layer-c7-default-deny` (6d6c3c0), where the C7 paragraph
named this test as unstarted. Spec read: `os-build/AGENT_LAYER_SPEC.md`
§13/§6 on main 83d9079; runtime read: `agents/runtime.mjs` (slice 1,
146 lines) on the same main. This branch changes no spec, runtime,
registry, or test file — it is the test specification plus a
verified RED state, for Pax to merge. Nothing here is a boot,
kernel, or enforcement verdict.

## The test, specified exactly

Proposed placement: `tests/agents-capability-check.test.mjs`,
same `node:test` + real-child style as `tests/agents-runtime.test.mjs`
(no mocks; the agent under test is a real spawned child). Three
cases, one per C7 surface, plus the ledger assertion that is common
to all three:

1. Filesystem: an agent whose manifest lists no filesystem path
   attempts to read a path outside its own directory. Assert the
   read is denied, the agent is told it was denied and why, and
   the run ledger carries a denial line naming the agent-run id,
   the surface (`filesystem`), and what was asked for.
2. Network: an agent whose manifest lists no endpoint attempts to
   call an unlisted endpoint. Assert denial, agent told why, and
   the same ledger line with surface `network`.
3. Dispatch: an agent whose manifest lists no dispatch target
   attempts to send to an unlisted target. Assert denial, agent
   told why, and the same ledger line with surface `dispatch`.

Pass bar: all three cases denied + all three ledger lines present.
A run that denies without recording, or records without telling
the agent, fails — C7 requires both, so a denial must never look
like a silent failure.

## Verified RED state (this run, worktree on main 83d9079)

Filesystem case reproduced against the real runtime, scratch
script only (not committed): an agent with `capabilities: []`
whose command reads a file outside its run directory exited 0,
the read succeeded (`unlisted-content` recovered verbatim), the
brief carried `capabilities: []`, and the ledger held only
`spawn` + `exit` — no denial line. That is the C7 violation in
miniature: a manifest-empty agent did an unlisted filesystem read
and nothing recorded it.

Network and dispatch are RED by absence, verified statically on
the same main: `agents/runtime.mjs` contains no mediated
filesystem, network, or dispatch call at all (its only capability
reference is the brief line carrying `capabilities` into the job
record), and `agents/baton.mjs` contains no dispatch or
capability reference. There is no call surface for a test to deny
through — the spawned child runs unconfined (full inherited
environment, caller-chosen working directory).

## Precondition for a greenable test (not guessed here)

Two gaps must close before this test can go green, and neither is
decided by this branch:

- Manifest schema: `agents/registry.json` capabilities today are
  free-form strings (`gate-1`, `dispatch`, `watch`), not
  per-surface lists. "Unlisted path / endpoint / target" cannot
  even be expressed until the manifest gains per-surface lists
  (filesystem paths, network endpoints, dispatch targets).
- Mediation: the runtime must expose mediated calls (or a
  sandbox boundary) that check the manifest before the call
  happens. A test written against direct child calls could never
  pass without confinement, so no test file is landed here — a
  red test file against an API that does not exist would error
  rather than fail, which proves nothing.

## Status

C7 capability-check test: SPECIFIED (this branch) + proven RED
(filesystem reproduced, network/dispatch RED by absence);
GREEN owed on the two preconditions above. Queued with Pax per
the merge rule; no merge from this branch. Pax: please call the
next step — design the mediated-call API + per-surface manifest
first, or land the red test file as-is as a failing guard?
