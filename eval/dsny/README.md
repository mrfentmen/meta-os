# Meta DSNY eval — first slice

The DSNY world pack (`os/worlds/dsny/`) is status `spec` on main:
a definition only — PACK.md plus pack.json, no runtime code at all.
Before this slice, `eval/` had no DSNY harness at all, so there was
no DSNY baseline for "whatever raises eval scores" to be measured
against. This is that first harness. It scores the pack's own
contract — not a real sanitation department, a real route, or any
live dispatch.

## What it checks (11 scenarios, all from committed material)

| ID | Check | Source |
| --- | --- | --- |
| DSNY-VAL-01 | Committed validator `os/worlds/validate_pack.py` accepts `os/worlds/dsny/pack.json` (exit 0) | pack.json |
| DSNY-WATCH-01 | 4 watchers, 4 agents, every `serves` entry resolves to a watcher | pack.json |
| DSNY-ALERT-01 | 6 alert kinds, severity/privacy/urgency inside the shared sets, urgency ranks 1–4 exactly once | pack.json |
| DSNY-PRIV-01 | An alert crosses the bus exactly when its privacy class is summary — here, only storm-status-summary crosses | pack.json |
| DSNY-PRIV-02 | Both cross-world sends declare the same non-empty `never_carries` list (worker names, crew assignments and time entries, truck fault details, individual route payload details, home addresses) | pack.json |
| DSNY-XWORLD-01 | Cross-world declarations checked both ways against nypd, fdny, ems, mta, doe, dep, hospital packs | pack.json (all eight) |
| DSNY-XWORLD-02 | Other packs' dsny declarations checked for a matching dsny side | pack.json (all eight) |
| DSNY-FIRST-01 | 6 firstboot fields, all labelled; all 6 required, none optional | pack.json |
| DSNY-STATUS-01 | Status honestly `spec`, version 0.1.0; `os/worlds/dsny/` holds PACK.md and pack.json only, no runtime key | pack.json + directory |
| DSNY-PRIVCLASSES-01 | Privacy classes match: 4 local_only items that never move, 3 bus_summary items that may ride | pack.json |
| DSNY-DOC-01 | PACK.md names the same 4 agent nicks, 6 alert kinds, the road-clearing-status send kind, and carries the SPEC, NOT BUILT label | PACK.md |

## The cross-world picture (named, not hidden, not patched)

DSNY-XWORLD-01 passes when the measurement matches committed reality,
and on the dsny pack's own declarations that reality is gappy:

- Receives, 0/2 reciprocated: nypd sends `scene-safety-summary` to
  fdny only, never to dsny; mta sends `service-status-summary` to
  dsny, not the `service-diversion` dsny declares receiving from mta.
- Sends, 1/2 reciprocated: mta does declare receiving
  `road-clearing-status` from dsny. The nypd send is unreciprocated:
  nypd declares no `road-clearing-status` receive from dsny at all.

DSNY-XWORLD-02 looks from the other side, and that is where the
remaining gaps sit:

- Unmatched inbound: mta sends `service-status-summary` to dsny and
  doe sends `school-status-summary` to dsny, but dsny declares
  neither receive.
- Unmatched outbound: doe and dep both declare receiving
  `road-clearing-status` from dsny, but dsny sends that kind to nypd
  and mta only, never to doe or dep.
- Whether receipts should be added, or source packs should drop or
  redirect their sends, is a pack-owner decision for Pax; this
  harness does not invent either side, and a future change on either
  side would change these scenarios' expected values, which is the
  point of measuring them.

No runtime smoke — the pack ships no runtime, and none was invented.
