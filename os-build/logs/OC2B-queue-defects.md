# OC2B-074 — Queue defects filed (with repro steps)

1. `--version` unsupported on all 4 entry points (queue_service,
   trio_agent, patrol, livecams): `error: unrecognized arguments:
   --version`, exit 2. Repro: `python3 server/queue/<f>.py --version`.
   Impact: OC2B-023 version-string contract UNPROVEN. Owner: OC2.
   Fix shape: one argparse `--version` action per entry (runtime edit,
   deferred to a code batch, named here).
2. No poison-job quarantine: always-failing jobs retry unboundedly —
   no attempt counter, no quarantine state in trio_store, no
   `max-tries` flag on trio_agent. Repro: file a job whose generation
   always fails (e.g. no key), `serve_once` N times, observe N
   failures with no quarantine. Impact: OC2B-070/071 UNPROVEN.
   Owner: OC2. Fix shape: attempts counter on claim + quarantine
   state + review procedure (OC2B-queue-quarantine.md stubbed by
   OC2B-071 doc when implemented).
3. No queue-depth cap / backpressure signal: no max-depth, no 429 /
   wait-told path in queue_service (grep `backpressure|429|max.*depth`
   empty). Repro: file 1000 distinct jobs — all accepted (proven:
   OC2B-queue-disk.txt, 100/100 in 5s). Impact: OC2B-063/064
   UNPROVEN. Owner: OC2. Fix shape: depth gauge + `429 + Retry-After`
   or wait-told response (runtime edit, deferred, named here).

No data-loss, no secret, no crash defect found this session. The live
rides (e2e, 10-job, tampered-400, nokey-refusal, restart survival)
all behaved.
