"""Relay Intelligence — the Muse Spark layer on the muse-relay bus.

Modules:
  store        intel Redis records and key layout (FND-004)
  spark_client the one Spark gateway: agent transport (dispatch to a
               resident crew agent through the job queue) + HTTP
               transport, retries, budget caps, spend ledger
               (FND-005/006/007)
  spark_agent  the resident-agent side of the agent transport:
               registers the spark capability, claims spark-complete
               jobs, generates via a caller-supplied callable, writes
               the result key, finishes with the digest commit
  ingest       read-only snapshot of bus + queue + presence (FND-014)
  brief        briefing engine (BRF workstream)
  dispatch     plain-English goal -> signed job specs (DSP workstream)
  watchdog     silent-failure detectors (WDG workstream)
  alerts       alert record lifecycle helpers
  integration  the INT-001 integration environment: room, job and
               capability namespaces, export block (no side effects)

Importing this package has no side effects: no network, no Redis, no
env requirements. Submodules talk to Redis only when called, through
relay_common, exactly like the rest of the repo.
"""

__all__ = [
    "store",
    "spark_client",
    "spark_agent",
    "ingest",
    "brief",
    "dispatch",
    "watchdog",
    "alerts",
    "integration",
]
