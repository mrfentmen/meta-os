# OpenCode tasks 100: progress report (Mac side)

Baselines from the task list (sandbox): node 1933 run / 1877 pass / 56 fail
(known WKWebView set); cargo 1412 pass / 0 fail; queue python 110 OK;
officina 49 OK; worlds packs 9 of 9 OK; OS loop harness 12 of 12.

## Section 1: Pull main and prove it on the Mac (OC-001 to OC-010)

- OC-001 DONE. Fetched origin; worktree /tmp/mac-tasks on branch
  opencode/mac-tasks at main tip 0b8fa7f (README front page rebuild).
- OC-002 DONE. cargo test --workspace: 1412 pass, 0 fail. Matches baseline.
- OC-003 DONE. npm test: 1933 run, 1877 pass, 56 fail. All 56 are
  tests/native-* (zero non-native failures). Matches baseline exactly.
- OC-004 DONE with a failure to record: queue python suite does not
  collect on this Mac. pytest: 4 collection errors; unittest fallback:
  29 collected, 25 pass, 4 import errors. Root cause is the same one
  from MAC RUN 3: server/queue/trio_store.py line 41 imports
  dynamic_credentials from /opt/muse/skills/... which does not exist
  on this Mac. Baseline 110 OK is sandbox-only until that import is
  optional. test_queue.py and test_orchestrator.py partially run (25 OK).
- OC-005 DONE. officina: 49 passed. Matches baseline.
- OC-006 DONE. worlds pack validator (os/worlds/validate_pack.py):
  9 of 9 packs OK, 0 failures. Matches baseline.
- OC-007 DONE with one failure: os/os/loop-tests/metaos-loop.test.sh
  gives 11 pass, 1 fail; the failing scenario is "green cycle".
  Reproduced by hand: the driver runs the agent fine but dies at step 9
  with queue-mark-failed, because it closes the task with
  sed -i "0,/.../s//.../" — the 0,/regex/ address is GNU sed only and
  macOS ships BSD sed, so the substitution errors. Linux-ism in the
  driver, exposed by running the harness on the Mac. Recorded, not fixed.
- OC-008 DONE. Web app on :8080 serves /manifest.webmanifest (200)
  and the referenced /icon-180.png (200). No 404 on referenced assets.
  (Unreferenced guesses like /favicon.ico 404 — not used by the page.)
- OC-009 DONE. AI Focus clicked in the running app: inspector shows the
  honest empty-state line ("no flagged incidents in this session yet...
  AI Focus flies to the newest one"). Proof: oc-proofs/oc-009-ai-focus.png.
  Side note: the live NYCTMC list loaded (972 cameras online) and the
  Fires/Radar layer buttons are present.
- OC-010 this section of the report.
