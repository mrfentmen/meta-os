# agent3 handoff manifests (copy-only, with sha)
# base for all five: main @ 4bef226a (main has since moved; Pax rebases at merge)

## opencode/agent3-env-ci
- commit ae2cec70… ci: mark known-red steps non-blocking with TRACKED-RELAXED notes — UNCOMPILED
- commit 9d3c769d… ci: Node+Python workflow (npm test, queue suite, verify/check) — UNCOMPILED
- commit fd3aae84… env: add .env.example + ignore real .env files — UNCOMPILED
- 84dae910771b  .env.example
- 96df89b68cd6  .github/workflows/ci.yml
- 0e6a9d4a89db  .gitignore

## opencode/agent3-deploy
- commit 71749787… Deploy Trio demo frontend to meta-trio-demo (Workers static) + §6 log entry + p
- 5a43a4a5a5d8  .gitignore
- 0698b054dd1e  os/docs/DEPLOY_RUNBOOK.md
- 740d51035fdb  os/docs/deploy-trio-frontend.sh

## opencode/agent3-sam-spark
- commit 50a7b338… SAM-regions -> Spark-reasoning eval pipeline (agent3-models)
- acc0bacb16ec  os/intel/sam_spark.py
- 35de378b6d23  os/intel/sam_spark_fixture_run.json
- e81e0bdb8ab5  os/intel/sam_spark_runbook.md
- 154fe432b87f  os/tests/test_intel_sam_spark.py

## opencode/agent3-b04-b22
- commit 3286dc12… B22: worker run_loop + claim-path tests — UNCOMPILED
- commit 98141fba… B04: heartbeat + serve_once + relay hook + ISO timestamps — UNCOMPILED
- f53d981f95f4  crates/agent-runtime/src/lib.rs
- be19ada6120c  crates/agent-runtime/tests/gap_close.rs
- 00b576cc5ece  crates/agent-runtime/tests/section14_registry.rs
- 34901ded1a4f  crates/agent-runtime/tests/serve_heartbeat_relay.rs
- 6ef921118258  crates/os-worker/src/lib.rs
- 4b3d8e007813  crates/os-worker/tests/worker_loop.rs

## opencode/agent3-boot-docker
- commit 507c713b… agent3/boot-docker: boot-to-screen gap audit + Trio stack compose mirror
- 6c18bccaea14  BOOT_READINESS.md
- d6985c59924d  Dockerfile
- 81312a1d3683  docker-compose.yml

