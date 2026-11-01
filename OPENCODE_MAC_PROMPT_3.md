# MAC RUN 3 — Native rebuild, camera, and the first live flagged chain

Repo: mrfentmen/meta-os, branch main. Pull main first and work from the
fresh tip. Rounds 1 and 2 are in MAC_RUN_REPORT.md — this run covers what
they could not: the WKWebView native build, the Mac camera, and the full
flagged-incident chain firing live for the first time.

Ground rules:
- Report everything in MAC_RUN_REPORT_3.md at repo root and push it,
  with screenshots under mac-run-3/. Label every section VERIFIED,
  FAILED, or UNVERIFIED. Never present a guess as a result.
- Do not fix the 56 red native tests. That is a separate decision.
  Report the exact failure count if you run the suites.
- The dispatch endpoint is simulated by design. Verify the receipt is a
  sim- receipt; never point dispatch anywhere else.
- Spark key: ~/Desktop/hackathon key.txt, LINE 1 ONLY. Put it in the
  environment as SPARK_API_KEY. Never print it, log it, or commit it.
  The Mac has no TRIO_UPSTASH_HOST; the queue falling back to the
  labelled local store is expected, note it and move on.

## 1. Native build (WKWebView shell)
Build the native app from the current tip (same route as round 2).
Expected: ContentView.swift is the WKWebView host that loads the web
Command view; backend unchanged. If the build fails, paste the exact
compiler errors into the report and mark this section FAILED, then
continue with section 4 against the web app directly in a browser.

## 2. Start the stack
bash run-stack.sh with SPARK_API_KEY set. Confirm the app answers on
:8080 and the queue on :8935. Note the mode it reports (live Spark vs
labelled offline / NOT CONFIGURED).

## 3. Camera and permission
Launch the native app. Click Start Camera. If macOS shows the camera
permission dialog, click Allow. If you cannot click the system dialog,
STOP this section and write in the report exactly what the user must
click — do not work around TCC.
With the camera live, confirm an in-app live assessment completes
(point the camera at the room; expect a baseline category) and record
the assessment summary + latency in the report.

## 4. STAGED FLAG — the full chain, live
Stage a Medicus scene in front of the camera: a person lying still on
the floor in clear view (or the film mannequin laid down). Hold it for
at least two patrol cycles. Then record, step by step:
- PATROL: the flag — category returned, product, timestamp.
- REVIEW: the second independent reading and its verdict (confirmed or
  unconfirmed).
- ORCHESTRATOR: the decision taken and its bounds.
- INVESTIGATION: which other lenses / neighbours were called and what
  they returned.
- EVIDENCE: files written under the crew data dir (names + sizes),
  whether face detection reported boxes or "unavailable" (cv2 present
  on this machine? say so), and the BOLO block: descriptions and any
  "Visible marks:" lines that survived the absence filter.
- RESPONSE: the dispatch package sent to /dispatch-simulated and the
  sim- receipt id.
If the chain stalls, capture exactly where (logs, queue state) and mark
the remaining steps UNVERIFIED. Do not force or fake a flag. If the
camera path cannot flag, say so and also try the same staged still
through the web console's camera if available.
Yellow tier: a two-tier ruling (small = yellow review-only, big = red)
landed 2026-10-31 and may or may not be merged when you run. If it is
in the tip, also verify one yellow case records without investigation
or dispatch. If it is not in the tip, skip this — do not implement it.

## 5. Command view with human eyes
Open the Command view in a real browser window (Safari or Chrome GUI —
headless GL output was garbage in round 2 and does not count).
Screenshot and confirm each: (a) 3D map renders with extruded
buildings; (b) camera pins present; (c) clicking a building opens its
popup; (d) clicking a camera shows the ground ring + inspector;
(e) camera wall tiles. Save screenshots as mac-run-3/map-*.png.
Anything you cannot see, mark UNVERIFIED with the reason.

## 6. Logo and Map button
In Console view at the default window size: does the spinning ASCII
logo read as one clean loop (not stretched, not buried behind panels)?
Is the "Map" button in the topbar easy to find? Screenshot both views
(mac-run-3/console.png, mac-run-3/mapview.png) and answer plainly.

## 7. Suites (quick pass)
npm test and the Python queue tests. Report pass/fail counts exactly.
The known 56 native failures are expected — count them, do not fix.

## 8. Report
Write MAC_RUN_REPORT_3.md: one section per item above, each labelled
VERIFIED / FAILED / UNVERIFIED with the evidence (ids, file names,
receipt ids, screenshot names). Commit the report + mac-run-3/ and
push to main.
