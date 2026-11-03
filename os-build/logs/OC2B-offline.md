# OC2B-042 — No-network behaviour (honest degrade chain)

1. Queue: serves `/health` + local store regardless. Jobs file to SQLite
   fallback (Upstash ping fails → LocalSqliteStore, warning on stderr,
   `store_fallback` named in `/health`). Verified live this session.
2. Trio: with no key, named RuntimeError; job lands `status failed` with
   reason — never a fabricated assessment, never a hang.
3. Guardrail: refuses before send at/past $75 (GuardrailStop); patrol
   governor pauses at $5 reserve.
4. Patrol: pauses LOUD — `crew-status.json state=paused-budget` + event;
   no jobs filed while paused.
5. Livecams: assess-one needs the API; offline falls back to the labelled
   fallback subset; the 12/12 offline suite touches no network. Offline
   verdicts are structural only, never presented as live readings.

Nothing retries in a loop; nothing contacts non-loopback (queue binds
127.0.0.1; dispatch endpoint is loopback simulated-labelled only).
