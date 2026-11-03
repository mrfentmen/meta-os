# Agent layer — C7 default-deny paragraph (Milo, 2026-11-02)

Per Pax's room-1 directive 2026-11-02 (C7 first; C9 held until
`LOBSTER_BINDING.md` exists on main; D1 baton format after C7).
Companion to the A3/A4 gate file on `milo/agent-layer-a3a4`
(fd91fe8), where C7 stood PARTIAL. Spec read: `os-build/AGENT_LAYER_SPEC.md`
on main dd292da. This branch changes no spec, runtime, or registry
file — it is the paragraph itself, for Pax to merge. Nothing here is
a boot, kernel, or enforcement verdict.

## The paragraph (spec text for §13, or a new §13a)

Default deny. An agent may use only what its manifest lists, on
each of three surfaces separately: filesystem, network, and
dispatch. Silence is not permission: a surface with no manifest
entry is closed, not open, and a call to anything unlisted is
denied. A denied attempt is recorded, not swallowed — it writes a
ledger line naming the agent-run id, the surface, and what was
asked for, and the agent is told it was denied and why, so a
denial never looks like a silent failure. This composes with the
rules already in the spec: §13 (an agent may only call endpoints
its manifest lists; simulated endpoints carry their marker; a
receipt names which kind answered), §6 (the environment allowlist
is written into the job record BEFORE the agent starts), and
announce-before-send for anything in the boss's name. Concretely:
filesystem means the agent's own directory plus only the paths
its manifest lists; network means only the endpoints its manifest
lists; dispatch means only the dispatch targets its manifest
lists, and nothing in the boss's name goes out except through
announce-before-send. No agent widens its own manifest at
runtime — widening takes a registry change by the owner or boss,
the same way no agent may raise its own budget (§9). A manifest
that lists nothing for a surface is a valid, fully closed
manifest, not an error.

## Why this closes the A3 gap at design level

The A3 gap was exact: §13 + §6 implied allowlisting but stated no
explicit default-deny rule for filesystem, network, or dispatch,
and slice 1 enforces nothing. The paragraph above states the rule
explicitly for all three surfaces, names the denial record, and
names the no-self-widening rule. By the same standard A3 applied
to C4/C5/C6 (answered at design level, proof owed), C7 now reads
ANSWERED at design level, with enforcement owed — not claimed.

## What is NOT done here (honest status)

- Enforcement: `agents/runtime.mjs` on main dd292da carries
  `capabilities` into the job record but gates no call on them
  (single capabilities reference in the runtime), and
  `agents/registry.json` capabilities are free-form strings.
  The capability-check test — an unlisted filesystem, network,
  and dispatch call each denied, with the ledger line proving
  the denial — is named here as a B-slice task, unstarted, not
  done by this paragraph.
- C9 stays HELD per Pax's directive: `LOBSTER_BINDING.md` was
  verified absent on main dd292da in this worktree, so no
  binding review is written here and none is claimed.
- D1 baton format is next per Pax's order, not started here.
- The §3 citation defect from A3 (`agents/README.md` does not
  exist on main) is untouched here; it is not a C7 matter.

## Status

C7: PARTIAL (A3, 03:58) -> ANSWERED at design level (this
paragraph); enforcement UNIMPLEMENTED until the B-slice
capability-check test exists. Queued with Pax per the merge
rule; no merge from this branch.
