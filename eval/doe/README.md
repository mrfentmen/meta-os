# Meta DOE eval — first slice

The DOE world pack (`os/worlds/doe/`) is status `spec` on main:
a definition only — PACK.md plus pack.json, no runtime code at all.
Before this slice, `eval/` had no DOE harness at all, so there was
no DOE baseline for "whatever raises eval scores" to be measured
against. This is that first harness. It scores the pack's own
contract — not a real school, a real classroom, or any live
assignment.

## What it checks (11 scenarios, all from committed material)

| ID | Check | Source |
| --- | --- | --- |
| DOE-VAL-01 | Committed validator `os/worlds/validate_pack.py` accepts `os/worlds/doe/pack.json` (exit 0) | pack.json |
| DOE-WATCH-01 | 4 watchers, 4 agents, every `serves` entry resolves to a watcher | pack.json |
| DOE-ALERT-01 | 5 alert kinds, severity/privacy/urgency inside the shared sets, urgency ranks 1–4 exactly once | pack.json |
| DOE-PRIV-01 | An alert crosses the bus exactly when its privacy class is summary — here, only school-status-summary crosses | pack.json |
| DOE-PRIV-02 | The one cross-world send declares the full non-empty `never_carries` list (student names or any student data, teacher or staff names, personnel records, grades or assessments, home addresses) | pack.json |
| DOE-XWORLD-01 | Cross-world declarations checked both ways against nypd, fdny, ems, mta, dsny, dep, hospital packs | pack.json (all eight) |
| DOE-XWORLD-02 | Other packs' doe declarations checked for a matching doe side | pack.json (all eight) |
| DOE-FIRST-01 | 7 firstboot fields, all labelled; all 7 required, none optional | pack.json |
| DOE-STATUS-01 | Status honestly `spec`, version 0.1.0; `os/worlds/doe/` holds PACK.md and pack.json only, no runtime key | pack.json + directory |
| DOE-PRIVCLASSES-01 | Privacy classes match: 4 local_only items that never move, 3 bus_summary items that may ride | pack.json |
| DOE-DOC-01 | PACK.md names the same 4 agent nicks, 5 alert kinds, the school-status-summary send kind, and carries the SPEC, NOT BUILT label | PACK.md |

## The cross-world picture (named, not hidden, not patched)

DOE-XWORLD-01 passes when the measurement matches committed reality,
and on the doe pack's own declarations that reality is gappy:

- Receives, 1/3 reciprocated: dep does send `water-advisory` to doe.
  The other two are unreciprocated: mta declares no
  `service-diversion` send to doe (its doe-adjacent send is
  `service-status-summary` to dsny), and dsny declares no
  `road-clearing-status` send to doe (its road-clearing-status goes
  to nypd and mta only).
- Sends, 0/1 reciprocated: dsny declares no `school-status-summary`
  receive from doe at all.

DOE-XWORLD-02 looks from the other side, and there the measurement
is empty in both directions — which is itself a finding, not an
assumption:

- Unmatched inbound: none. The only other pack that sends to doe is
  dep (`water-advisory`), and doe declares that receive.
- Unmatched outbound: none. No other pack declares a receive from
  doe at all, so there is no other-side receipt for doe's send to
  match against — the doe-to-dsny gap is already counted in
  XWORLD-01, and counting dsny's missing receive a second time here
  would double-count the same edge.
- Whether receipts should be added, or source packs should drop or
  redirect their sends, is a pack-owner decision for Pax; this
  harness does not invent either side, and a future change on either
  side would change these scenarios' expected values, which is the
  point of measuring them.

No runtime smoke — the pack ships no runtime, and none was invented.
