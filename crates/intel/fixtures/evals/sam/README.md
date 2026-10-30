# SAM evaluation set: Alerts panel, known-good / known-bad pairs (STR-003)

Two pairs, same panel, opposite states. Each pair is one dashboard
state rendered twice (desktop + phone are separate pairs, not two
views of one pair, so a SAM pass scores each viewport on its own).

| Pair | Good (build-ok) | Bad (build-broken) |
| --- | --- | --- |
| `alerts-panel-desktop` (1280x900) | `alerts-quiet-desktop.png` | `alerts-firing-desktop.png` |
| `alerts-panel-phone` (390x844) | `alerts-quiet-phone.png` | `alerts-firing-phone.png` |

Labels are ground truth from the payloads, not SAM output:

- **Bad:** the DSH-030 submission shots of the intel-alerts panel fed
  the DSH-037 dev-pack alerts payload — five critical open alerts
  from one `watchdog.tick` on a stall/collision/dead-dep fixture
  (presence-stall milo:1, three file-collisions on
  `intel/status.py`, dead-dep 9:3). The files here are byte-identical
  copies of the submission shots; `intel/sam_check.py` enforces that.
- **Good:** the same panel module at this commit, demo mode, fed zero
  alerts plus a live watchdog beat 30s old, rendered by
  `intel/sam_render.py` (Playwright + the repo's cached Chromium,
  the DSH-030/DSH-035 method). Panel reads "All quiet — watchdog
  alive". The render script asserts the panel text and the harness
  snapshot (alerts 0, beat alive) at render time.

## Gate note, stated plainly

STR-003 sits in the SAM stretch, gated by STR-001 (Pax verifies core
statuses) and Dale's GOV-007 go/no-go at the Nov 1 checkpoint —
neither has landed yet. This set is built early, following the
STR-002 (Hana) and STR-005 (Rowan) precedent of landing the
stretch's payload/render pieces before the gate opens. It claims no
gate approval and no SAM verdict: a SAM pass has not been run
against these files, and no SAM output is recorded here.

## NOT proven here

- A SAM verdict on any file in this set (STR-004, Buffy's 20-shot
  set, is where verdicts get scored; this is Milo's 2-pair feeder).
- A live drill capture: the bad halves render a fixture payload, not
  a screenshot taken mid-drill on a live room, and the good halves
  are fresh renders of the quiet state, not a screenshot of a drill
  that stayed quiet.
- The all-quiet state on the demo machine (DEM-018, still open) or
  on a real phone (phone shots use the taller emulated viewport, per
  the DSH-030 note).
- Any SAM behaviour at all: this set is input to a future pass.

## Verify

```
python3 intel/sam_render.py intel/evals/sam   # re-render quiet halves
python3 intel/sam_check.py                    # manifest + PNG + payload checks
python3 -m unittest tests.test_intel_sam_eval -v
```
