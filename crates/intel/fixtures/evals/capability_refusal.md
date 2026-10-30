# OS-081 eval: capability refusal enforcement (Milo)

A fixture crew process attempts actions inside and outside
its grant. The OS-080 capability files do not exist yet
(Pax, not landed), so the grants are plain dicts in the
OS-080 shape, supplied by the caller; no capability file
is read or written anywhere in this task.

## What the drill proves

- Allowed: a bus post with bus_post on, a network reach
  with network on, a file write inside the grant paths.
  All three journal nothing.
- Refused, reason capability not granted: a bus post and
  a spend with their flags off, naming bus_post and spend.
- Refused, reason write path outside grant: a write to a
  path outside the grant, naming write:<path>; a dot-dot
  write escaping the grant, naming the normalized path;
  and a segment-prefix trick (crew/milo2 against
  crew/milo/) that never matches.
- Refused, never silently allowed: a write with no path,
  a process with no grant file (default deny, and the
  refusal still names the attempting process), and an
  unknown action.
- Tick: one refusal record per refused attempt, allowed
  attempts silent, a duplicate attempt inside one tick
  deduped, a second tick silent, inputs never mutated.
- Alert record: kind capability-refusal, severity warning,
  status open, id equal to the dedupe key, explanation
  naming identity, action, and missing capability, built
  through intel.store.build_alert_record in the drill.
- Brief: one line per refusal naming identity, action,
  and missing capability, so the watchdog surfaces the
  refusal like any other alert.
- No push path: the module never performs the action,
  never moves a claim, never writes a job record, never
  posts to the bus, and imports no push, bus, or Redis
  code, so a refusal judged here can never ring a phone.

## What is NOT proven here

- A refusal on a booted test image (no test image in
  repo), and the OS layer actually refusing a live
  process action (the mechanical half is Pax OS-080
  plus the OS layer that loads the grant file).
- The dashboard banner for the refusal (Rowan OS-084,
  not landed) and the policy defaults the grant ships
  with (Dale OS-082, not landed).
- The DEMO.md Shot 8b staging itself: the drill is
  the decision and record half, not the demo shot.
- The plan/META_OS.md spec line (shared files
  integrator-only under the folders rule, Pax's to add).

## Run

`python3 intel/drills/capability_refusal.py` (5/5 phases PASS)
`python3 -m unittest tests.test_intel_capability` (14 tests)
