# OC1B §10 live-camera runs (Mac, tree 94010c76, 2026-11-02 ~16:12-16:15Z)

Module: server/queue/livecams.py (own fetcher). Key: SPARK_API_KEY from env (length-only proof in §9).
Pax's tracked pair server/queue/livecam_records/live-frame.jpg + live-reading.json (Bay Pkwy, sandbox route) untouched; every run below saved as a NEW dated file with --out to a scratch dir then copied in.

## Runs (frame + reading committed under server/queue/livecam_records/)

- OC1B-228/229 Brooklyn/vigiles: --assess-one --area Brooklyn --division vigiles
  frame live-20261102-161313-3-ave-60-st-brooklyn-vigiles.jpg (15,955 bytes, JPEG magic, sha 034b2f813ae195f9, camera "3 Ave @ 60 St", fetched 16:13:13Z)
  reading category "normal activity" — summary "Quiet street scene under elevated tracks with parked vehicles and no visible pedestrians or incidents."
- OC1B-230 byte/timestamp check (Brooklyn): JPEG magic FFD8 + 15,955 nonzero bytes; on-image caption "2026-11-02 11:13:29" (ET) = fetch minute — CURRENT, not a stale still. Viewed the frame: elevated structure, parked cars right, green lights, no people — matches the reading.
- OC1B-231 Manhattan/vigiles: 1 Ave @ 110 St, 25,315 bytes
  live-20261102-161335-1-ave-110-st-manhattan-vigiles.jpg/json — "normal activity": "Busy city street with normal vehicular traffic and parked cars, no visible disturbance or person in need." On-image caption 11:13:50, current. Frame viewed: matches.
- OC1B-232 Manhattan/ignis: same camera minutes later, 25,003 bytes
  live-20261102-161347-1-ave-110-st-manhattan-ignis.jpg/json — "no hazard visible": "No smoke, flames, or fire indicators are visible in this clear daytime street scene." Frame viewed: same street, clear — matches.
- OC1B-233 Queens/medicus: Belt Pkwy @ Guy R Brewer Blvd, 22,736 bytes
  live-20261102-161359-belt-pkwy-guy-brewer-queens-medicus.jpg/json — "normal activity": "Multi-lane highway with moving traffic in both directions; no persons, collisions, or obstructions visible." Scene-awareness wording check over the full reading JSON: no "diagnos", "severity", "treatment", "prescri", "dosage", "cause of", "etiology" — PASS, no diagnosis/cause/severity/treatment language. On-image caption "Mon Nov 2 2026 11:14:07 AM ... Facing North", current. Frame viewed: highway, matches.
- OC1B-234 Bronx/vigiles: WEBSTER AVE @ NEREID AVE, 34,852 bytes
  live-20261102-161409-webster-nereid-bronx-vigiles.jpg/json — "normal activity": "Aerial view shows a single vehicle on an otherwise empty road surrounded by trees; no incident visible." Caption 11:14:22, current. Frame viewed: one white car, tree-lined road — matches.
- OC1B-235 Staten Island/ignis: area HAS online cameras (100 in list) — Amboy Rd @ Annadale Rd, 23,968 bytes
  live-20261102-161421-amboy-annadale-staten-island-ignis.jpg/json — "no hazard visible": "No smoke, flame, or fire indicators visible in the daytime street camera view." Caption "Facing East 11/02/26 11:14:36 AM", current. Frame viewed: matches. No substitution needed.
- OC1B-236 --name "Belt Pkwy": picked " Belt Pkwy @  Guy R Brewer Blvd " (Queens), 22,491 bytes
  live-20261102-161426-belt-pkwy-namefilter-vigiles.jpg/json — "normal activity". Determinism: 18 name matches in the 975-list; pick() sorts by name and takes the first — picked == sort-first, and two repeat pick() calls return the same camera. PROVEN deterministic.
- OC1B-237 --count 3 Brooklyn snapshots (fetch only, no assess):
  live-20261102-161430-3-ave-60-st-brooklyn-snap1.jpg (16,092 bytes, JPEG),
  live-20261102-161430-3-ave-63rd-st-brooklyn-snap2.jpg (18,961 bytes, JPEG),
  live-20261102-161430-3-ave-65-st-ent.-eb-bqe-gowanus-brooklyn-snap3.jpg (26,954 bytes, JPEG).
  Third snap viewed: highway interchange with signage, caption "2026-11-02 11:15:02 AM", current.

## Contract / honesty checks

- OC1B-238 v2 contract: all 7 readings carry product, timestamp, observations, assessment, processing + assessment carries category, summary, uncertainty, requires_human_review (false on every baseline) + processing.model muse-spark-1.3. 7/7 PASS (checked programmatically).
- OC1B-239 description-vs-frame: all 7 assessed views compared by eye against their frames (notes above) — NO reading describes something its frame does not show. Zero flags, nothing edited. (3 fetch-only snaps carry no reading.)
- OC1B-240 refusal 1: --list --api-url http://127.0.0.1:9/unreachable -> exit 1, NO frame file. Wording note: the list stage raises urllib URLError (connection refused), NOT LiveCamError — LiveCamError governs the parse/snapshot stages. Loud failure + nothing produced either way; module-owner wording wart named, not hidden. Full traceback in /tmp (session scratch).
- OC1B-241 refusal 2: fetch_snapshot on b'<html>error page</html>' -> LiveCamError "snapshot for 'Fake' is not an image (23 bytes, starts b'<html>error page')" — an error page is never assessed as a frame. PROVEN.
- OC1B-242 offline tests: tests.queue-python.test_livecams 12/12 OK on the Mac.
- OC1B-243 spend: 7 spark_gen assess calls at Spark rates $0.006334 + $0.006742 + $0.004908 + $0.004870 + $0.005854 + $0.005256 + $0.004239 = $0.038203 (~$0.038 est, Spark-rate estimate). Snapshots + list + refusals cost $0. Guardrail total after §10: $0.1352 of $75.
- OC1B-245 flags: ZERO flags across 7 assessed runs (5 baseline "normal activity" vigiles/medicus + 2 "no hazard visible" ignis). An all-baseline section is a valid result, stated as one.
- OC1B-246 handoff: no flags -> nothing to hand to §13. No-follow line stands.
- OC1B-247 sources: every fetch went to https://webcams.nyctmc.org/api/cameras (list + per-camera /image). No EarthCam/Skyline/Windy source touched anywhere in this section. Attested.
- OC1B-248 failures: (1) OC1B-240 wording wart (URLError, not LiveCamError, at list stage — same loud-refusal property). (2) None other: no fetch errors, no refused frames, no offline areas (Staten Island had 100 online cameras).
- OC1B-249 verdict: the module's OWN fetcher is PROVEN end to end on the Mac — 975-list, 7 assessed readings over 5 areas x 3 divisions, 3-frame snapshot set, deterministic name filter, both refusals loud with nothing produced, 12/12 offline tests. The single wording wart (240) is named above and does not touch the proven path.
