# IMPERIUM — THE JUDGE (boss directive, 2026-11-02)

The boss's words: kill the human in the loop. Introduce a second
agent that judges, and then the information goes to the police —
or the fire department, or the hospital, by service.

## The chain, as built

1. PATROL — the first agent watches a camera and flags a scene
   (unchanged).
2. REVIEW — a second agent reads the same frame independently
   (unchanged).
3. THE JUDGE — a second-stage agent (server/queue/judge.py)
   weighs BOTH readings and rules: confirmed (the flag stands),
   cleared (a look-alike; the incident closes and its person
   evidence is purged), or inconclusive (the flag stays in
   monitoring and nothing is dispatched). The ruling and its
   reasons are recorded on the incident timeline, judged_by
   "imperium-judge". A failed or unreadable judgement is
   inconclusive by construction — the judge never confirms on
   a guess.
4. RESPONSE — a confirmed package routes by division to the
   service that owns the scene and is sent by the agent itself:
   Vigiles -> police, Ignis -> fire department, Medicus ->
   hospital (EMS receiving). Package fields: service (name +
   path), judged_by, dispatch_mode "judge-confirmed".

## What was removed

The human hold, entirely: TRIO_CREW_HUMAN_VERIFY, the per-Crew
human_verify seam, the held-for-verify outcome and package
state. Setting the old env var now changes nothing (a test pins
exactly that). requires_human_review stays in the brief as the
post-hoc AUDIT flag — a human may review the record after the
fact; no human approves, holds, or releases a send.

## The boundary that did NOT move

Every destination is the stack's SIMULATED endpoint for that
service (loopback only; crew.check_dispatch_url still refuses
every non-loopback URL; the receiver accepts only packages
labelled "simulated": true and logs them inside this stack).
The routing is per-service paths on that endpoint
(/dispatch-simulated/police, /fire, /hospital). No real
emergency service is contacted, and no configuration names one.

## Verification (2026-11-02, Pax)

- Queue suite: 128 tests OK (11 new judge tests; the retired-
  policy tests rewritten to the new ruling).
- Live smoke: POST to /dispatch-simulated/fire returned 201
  with a sim- receipt — the receiver takes the service routes.

## Next wiring step (named, not yet built)

The judge's own prompted call as a queue job kind: today the
judge weighs two independent readings with a deterministic,
tested ruling function; judge.build_judge_prompt is written for
the step where the judge reads both assessments in its own
voice and returns a verdict (parse_verdict is its strict
reader, fail-safe to inconclusive). Until that job kind lands,
do not describe the judge as a prompted model call — it is a
ruling stage over two real model readings.
