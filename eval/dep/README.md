# Meta DEP eval — first slice

The DEP world pack (`os/worlds/dep/`) is status `spec` on main:
a definition only — PACK.md plus pack.json, no runtime code at all.
Before this slice, `eval/` had no DEP harness at all, so there was
no DEP baseline for "whatever raises eval scores" to be measured
against. This is that first harness. It scores the pack's own
contract — not a real utility, a real pump station, or any live
water service.

## What it checks (11 scenarios, all from committed material)

| ID | Check | Source |
| --- | --- | --- |
| DEP-VAL-01 | Committed validator `os/worlds/validate_pack.py` accepts `os/worlds/dep/pack.json` (exit 0) | pack.json |
| DEP-WATCH-01 | 4 watchers, 5 agents, every `serves` entry resolves to a watcher | pack.json |
| DEP-ALERT-01 | 5 alert kinds, severity/privacy/urgency inside the shared sets, urgency ranks 1–4 exactly once | pack.json |
| DEP-PRIV-01 | An alert crosses the bus exactly when its privacy class is summary — here, only water-advisory crosses | pack.json |
| DEP-PRIV-02 | Both cross-world sends declare the full non-empty `never_carries` list (customer names or addresses, individual sample values or lab detail, pump station internal records, field crew rosters and time entries) | pack.json |
| DEP-XWORLD-01 | Cross-world declarations checked both ways against nypd, fdny, ems, mta, dsny, doe, hospital packs | pack.json (all eight) |
| DEP-XWORLD-02 | Other packs' dep declarations checked for a matching dep side | pack.json (all eight) |
| DEP-FIRST-01 | 7 firstboot fields, all labelled; all 7 required, none optional | pack.json |
| DEP-STATUS-01 | Status honestly `spec`, version 0.1.0; `os/worlds/dep/` holds PACK.md and pack.json only, no runtime key | pack.json + directory |
| DEP-PRIVCLASSES-01 | Privacy classes match: 4 local_only items that never move, 3 bus_summary items that may ride | pack.json |
| DEP-DOC-01 | PACK.md names the same 5 agent nicks, 5 alert kinds, the water-advisory send kind, and carries the SPEC, NOT BUILT label | PACK.md |

## The cross-world picture (named, not hidden, not patched)

DEP-XWORLD-01 passes when the measurement matches committed reality,
and on the dep pack's own declarations that reality is gappy on the
receive side and clean on the send side:

- Receives, 0/2 reciprocated: nypd declares no
  `scene-safety-summary` send to dep (its scene-safety-summary goes
  to fdny only), and dsny declares no `road-clearing-status` send to
  dep (its road-clearing-status goes to nypd and mta only).
- Sends, 2/2 reciprocated: doe declares the `water-advisory` receive
  from dep, and mta declares the `water-advisory` receive from dep.

DEP-XWORLD-02 looks from the other side, and there the measurement
is empty in both directions — which is itself a finding, not an
assumption:

- Unmatched inbound: none. No other pack sends to dep at all.
- Unmatched outbound: none. The only other receives from dep (doe
  and mta, both water-advisory) are matched, so there is no
  other-side receipt for dep's sends to match against beyond them.
- Whether receipts should be added, or source packs should drop or
  redirect their sends, is a pack-owner decision for Pax; this
  harness does not invent either side, and a future change on either
  side would change these scenarios' expected values, which is the
  point of measuring them.

No runtime smoke — the pack ships no runtime, and none was invented.
