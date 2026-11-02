# OC2B-419/420 live patrol dry run — PASS

One full patrol → review → judge → dispatch pass on a staged frame
set, all model steps live. `server/queue` NOT edited. Staged only:
the snapshot (`test-footage/frames/ignis-fire-2.jpg`, standing in for
`fetch_snapshot`) and the camera record; every assessment, segment,
ruling, and dispatch step is real.

- PATROL assess: production `spark_gen._generate_direct` (Spark
  vision, direct transport) → `vehicle fire`, high priority,
  model `muse-spark-1.3`.
- SEGMENT: `models.segment` (SAM 3.1) on the flag frame → no box
  (`ValueError`, single attempt, recorded as-is in the timeline's
  honest gap: the flag stands without a measured region).
- REVIEW: second real Spark assessment of the same frame via the
  crew's `_run_review`.
- JUDGE: `TRIO_JUDGE_MODEL=1` → the judge's prompted Spark call
  answered: `verdict=confirmed`, **`judge_mode: model`**,
  reasons quoting both readings ("vehicle fire with 0.97-0.98
  confidence", "flames engulfing front hood/engine area", "dark
  smoke column"). This is the `judge_mode: model` live proof (see
  also OC2B-judge-live.md).
- RESPONSE: `crew.routed_dispatch` over a real loopback HTTP server;
  the crew's `check_dispatch_url` guard enforced loopback.

Dispatch went ONLY to the loopback simulated endpoint:

- endpoint: `http://127.0.0.1:50475` (ephemeral port, this run)
- sim server saw: `POST /fire`, 4,953 bytes, incident
  `incident-a59ece55ba7e0a46`
- receipt id: **`sim-oc2b-patrol-001`** (`status:
  received-simulated`), quoted in the incident timeline's dispatch
  step (`sim-receipt.json`, `incident.json` in this dir)
- service route: fire department (`/fire` path)

Model cost of this pass: $0.058133 guardrail delta (2 Spark vision
assessments + 1 Spark judge call; SAM carries no dollar estimate).
No real emergency service was contacted; nothing leaves loopback.
