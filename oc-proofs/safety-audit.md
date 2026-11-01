# Safety self-audit (NC-158): NC-149..NC-157 results

- NC-149 secrets sweep (ghp_, github_pat_, sk-ant-, sk-*, AKIA,
  xox[bap]-, AIza, excluding .git/node_modules/target): 0 hits on every
  pattern. No STOP condition (NC-159 not triggered).
- NC-150: zero references to the 4 excluded bus files in labs/,
  hortus-rung3/, oc-proofs/.
- NC-151 dispatch enforcement (read-only): the state machine's terminal
  status is literally "dispatched-simulated" (no real state exists);
  crew.py pins DEFAULT_DISPATCH_URL to 127.0.0.1:8935/dispatch-simulated
  AND validates any override with a loopback check that raises
  ("dispatches ONLY to the local SIMULATED endpoint").
- NC-152: no code path dials emergency services. Grep patterns (911,
  112/999 as numbers, tel: URIs, twilio/pagerduty, emergency+dial):
  only false positives (test IDs like 999, counter 999999). Nothing
  to report.
- NC-153 vendored licenses: labs/molecules + labs/music3d each carry
  vendor/LICENSE-three.txt (three.js r152, MIT, unpkg source+bytes).
  Footnote: design/vendor/three.min.js (round 1) has no license file —
  outside this audit's scope, flagged for whoever touches design/.
- NC-154 footage sources: every indexed clip states its source (own
  render, app capture, sample data, terminal output). Zero unstated.
- NC-155 face check: molecule/music/review shots contain no faces;
  wall-feed night frames show no identifiable people (recorded in the
  J index); all sample face_boxes are empty. Nothing identifies anyone.
- NC-156: "UNIDENTIFIED" default in the renderer + bolo-guard.mjs
  refuses name fields (tested). No labs code writes a name into any
  record (grep).
- NC-157 own absolute paths: the only /opt/muse hits in own files are
  documentation of the sandbox path (diagnosis prose + diff context
  lines). No live code, no /Users/test, no /private/tmp in labs/,
  hortus-rung3/, or oc-proofs/ prose. Nothing to fix.
