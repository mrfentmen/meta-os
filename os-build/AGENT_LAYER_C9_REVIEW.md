# AGENT LAYER GATE — C9 (Lobster binding review vs the plan doc)

Gate: Milo, 2026-11-02. Task: A3 C9, left OPEN in the A3/A4
gate (milo/agent-layer-a3a4) because no `LOBSTER_BINDING.md`
existed on main then. Pax's 04:27 sequencing: C9 plan-doc review
comes after D1, before the C7 capability-check test as the
B-slice. D1 landed 04:33 (milo/agent-layer-d1). This review is
against the plan doc only, per that sequencing: the doc itself
states NOT BUILT, and nothing here claims a binding exists.

Document reviewed: `os-build/layer1/LOBSTER_BINDING.md`
(BF4-10) on main e942f01. Spec checked:
`os-build/AGENT_LAYER_SPEC.md` and `os-build/AGENT_LAYER_TASKS.md`
on the same tip. No spec, task, registry, or runtime file is
changed here. Pax merges; Milo gates.

Verdict words: CONFIRMED = the plan doc's claim reproduces on
main e942f01. CORRECTED = the claim is wrong as written, with
the correction stated. GAP = the plan omits something the build
will need. OPEN = still unproven, follow-up named.

## Evidence check — the plan doc's table, reproduced

| # | Plan-doc claim | On main e942f01 | Verdict |
|---|---|---|---|
| 1 | Lobster source in this repo: zero files | `find . -name '*.lobster'` in the worktree returns 10+ files: `lobster/hello.lobster`, `memory.lobster`, `budget.lobster`, `agent-call.lobster`, `bus-send.lobster`, `bus-recv.lobster`, `identity.lobster`, `scheduled.lobster`, `shim.lobster`, plus `failures/`. | CORRECTED — see note below. The doc's core point survives the correction, but the row as written is false. |
| 2 | Goose callable surface: one symbol per service, `export "svc_entry" fn service_main() -> i32`, no arguments, returns a code | `grep -n 'export' services/*/entry.goose` reproduces exactly that shape for bootlog, console, logd, time, and (with one nuance) example. | CONFIRMED, with nuance: `services/example/entry.goose` takes `boot: BootInfo&` — an entry argument, but boot info, not a callable function argument. No service exports a second, argument-taking function. |
| 3 | Anything a host could call with arguments: nothing | `grep -rn '^export fn' services/` returns nothing, and the only `export` lines in entry files are the `svc_entry` lines above. | CONFIRMED. |
| 4 | Lobster build step for services: none; only `mcp/mcp_client.py` mentions lobster among scripts | `grep -rln 'lobster' os-build/ --include='*.sh' --include='*.py'` returns `os-build/mcp/mcp_client.py` and `os-build/boot-test.sh` — one more hit than the doc names, and neither is a build step for services. | CONFIRMED in substance (no build step exists); the "only" is off by one file, immaterial. |
| 5 | `lobster` binary present at `/opt/homebrew/bin/lobster` | That is a Mac path (Del's machine). It cannot be verified from this Linux VM and is not in the repo. | OPEN — Mac-side claim, taken as stated, not verified here. |
| 6 | The spec never cites Lobster as a binding | `grep -i lobster os-build/AGENT_LAYER_SPEC.md os-build/AGENT_LAYER_TASKS.md` returns nothing. | CONFIRMED. This is the key scoping fact for C9 (see verdict). |

Note on row 1: the existing `lobster/*.lobster` files are
standalone agent scripts, not a host binding — none defines a
callable service surface, and none contains `svc_call` or
`svc_entry`. So the doc's conclusion ("nothing in the repository
that a Lobster program could call" at the ABI level) still
holds; only its "zero files" evidence row is wrong. The
correction matters because it changes the follow-up: the work
is not "introduce Lobster to the repo", it is "give the existing
Lobster programs a way to call services".

## The plan's four steps, assessed

| Step | Assessment |
|---|---|
| 1. Export two functions from one service, prove the C symbol with `nm` | Sound and cheap, as the doc says. No Lobster involved. This is the correct first commit if BF4-10 is picked up. |
| 2. Dispatcher + C driver under `run_native.sh`'s shim | Sound. `os-build/layer1/run_native.sh` exists on main, so the "round trip through the C ABI" half has a place to run. Worth committing on its own, as the doc says. |
| 3. Build Lobster from source with the dispatcher as a builtin | The expensive step, correctly identified as the blocker. The doc's own reason for not starting it stands: it is a C++ toolchain build outside this repo, and starting it without a ruled ABI (Pax's 2026-11-02 decision, cited by the doc) risks baking the wrong calling convention into a host binary. Do not start step 3 until that ABI ruling exists. |
| 4. Write `host_roundtrip.lobster`, run it, commit the transcript | Sound as the closing proof. Until then BF4-10 stays NOT BUILT, and this review does not move it. |

Two gaps the plan does not name:

1. **Permission model (C7).** The sketched `svc_call("logd.log_info", ...)`
   resolves a service function by string name. Under this job's
   C7 default-deny gate (milo/agent-layer-c7-default-deny), an
   unlisted name must be denied and the denial ledger-logged.
   The plan names no allowlist for `svc_call`, no denial
   behaviour, and no ledger line. A builtin that resolves any
   string would widen the agent's reach past its manifest.
   Follow-up: the allowlist + denial rule must be part of the
   step-3 design, not added after.
2. **The subprocess route already demonstrated.** `lobster/agent-call.lobster`
   already calls a Goose process — via `launch_subprocess` over
   stdin/stdout (MCP host), with requests in `req-*.json` files
   composed by shell heredocs because Lobster string literals
   cannot contain JSON braces. That is a real Lobster-to-Goose
   call, and the plan doc does not discuss it. It is NOT a host
   binding (process spawn, not an ABI call; Mac paths
   `/Users/test/...` hard-coded; the composing step is shell,
   not the agent), so it does not satisfy BF4-10 as written —
   but it is the cheapest honest round-trip shape if a builtin
   ever stalls, and any step-3 design should say why the
   builtin beats it rather than ignoring it.

One citation flagged, not disproven: the plan's "Goose's
`export "name" fn` supports this (spec#41)" cites a Goose spec
section that is not in this repo (no Goose spec doc found on
main). The export syntax itself is confirmed by the entry
files, but the spec#41 reference is unverified here.

## Verdict on C9 itself

C9 as A3 framed it — "Lobster binding review vs Buffy's
LOBSTER_BINDING.md: gaps" — is now ANSWERED at review level:
the plan doc is honest about NOT BUILT, its core evidence
reproduces (with the row-1 correction above), its step order
is sound, and its blocker (step 3 needs a ruled ABI) is real.

But C9 does NOT close as an agent-layer spec item, for the
scoping reason in evidence row 6: the agent-layer spec never
cites Lobster, and the agent host in the spec is the node
runtime (`agents/runtime.mjs`), not Lobster. BF4-10 is a
layer-1 services item that happens to be reviewed here. So:

- As an **agent-layer gate item**, C9 should be retired or
  re-homed to layer 1 when Pax merges this branch — the spec
  has no Lobster binding to review, and keeping C9 open on the
  agent-layer scoreboard would imply a spec gap that does not
  exist.
- As a **build item**, BF4-10 stays NOT BUILT until steps 1–4
  run, in order, with step 3 gated on Pax's ABI ruling. Steps 1
  and 2 may proceed before that ruling; step 3 may not.
- The C7 permission gap (allowlist + denial for `svc_call`)
  and the row-1 correction (Lobster scripts exist; none is a
  binding) should travel with BF4-10, not be dropped when C9
  is re-homed.

## What this gate did NOT do

- No change to the spec, the tasks file, the registry, the
  runtime, any service, or any Lobster program. One new file
  only: this review.
- No Lobster build, no Goose export, no dispatcher, no round
  trip — nothing built, nothing mocked, nothing claimed as
  built. The plan doc's NOT BUILT status is endorsed, not
  overturned.
- No kernel verdict, no boot verdict, no Mac check. The
  `/opt/homebrew/bin/lobster` claim is unverified here.
- Scoreboard note for Pax's merge-time step (not edited here,
  to avoid colliding with concurrent scoreboard edits): when
  this branch merges, the A3 C9 row should move from OPEN to
  "REVIEWED against the plan doc (plan sound, NOT BUILT,
  step 3 blocked on ABI ruling; C7 allowlist gap named);
  recommend re-home BF4-10 to layer 1 / retire C9 from the
  agent-layer scoreboard".
