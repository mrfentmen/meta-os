# Imperium — direct agent-to-police dispatch (no human verify step)

Boss directive, 2026-11-01 ~20:25 EST. Applies to Imperium
(Vigiles / Ignis / Medicus) on Meta OS.

## The bottleneck this removes

Flock Safety already detects. What it does not do is act: a human
still sits in the loop and verifies before law enforcement is
contacted. That human is the bottleneck — slow at 3 PM, absent at
3 AM, and the reason detections age in a queue.

Imperium cuts that step out. When the pipeline confirms a RED
incident, the agent itself messages the police endpoint with the
incident package, picture included. No human verify tap. The human
role moves to post-hoc audit: every package and receipt is in the
append-only record, reviewable after the fact.

This is the design the boss settled on 2026-10-30 and it stands:
fully autonomous loop (patrol, review, investigation, records,
dispatch), zero human taps, operator asleep included. A
human-approval gate exists only as an agency policy setting for a
future deployment that wants one; it is not in this product's flow.

## What the agent sends

On a confirmed RED incident, the Response stage builds and sends
one dispatch package:

- incident id, product (vigiles / ignis / medicus), category
- the observation description in observation language only
- **the picture**: the flagged frame, plus the evidence crop when
  the flagged path captured one
- camera id and location label, timestamp
- the descriptor block (BOLO fields) when the incident carries one

YELLOW incidents never dispatch. They are recorded and shown, per
the standing tier ruling.

## Honesty rule (unchanged, 2026-10-30)

The dispatch is real code end to end: a real package, a real HTTP
request, a real receipt id. The counterparty is the dispatch
receiver service built with this product, labeled SIMULATED in the
package, the receipt, and the UI, and enforced in code: the
dispatch URL check refuses any non-loopback URL
(`crew.check_dispatch_url`). Nothing in this build contacts a real
police system. If a real partner endpoint ever exists, it is a
deployment decision and a URL change, not a code change.

## Status

- Design: SETTLED (2026-10-30), reaffirmed and extended with the
  picture-in-package requirement 2026-11-01.
- Implementation: IN BUILD (auto-send on RED with the picture
  attached; human review as audit record, not a gate).
