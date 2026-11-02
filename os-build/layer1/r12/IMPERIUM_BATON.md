# Imperium baton pass — R12-021

Run at 2026-11-02T15:04:12.198Z. **PASS**

| item | value |
|---|---|
| killed mid-run | true |
| baton at kill | queue starting; done: (none) |
| resume exit | 0 in 244 ms |
| dispatches in run dir | **1** |
| final stages | queue up, agent ran, dispatch accepted |

One dispatch-log line means the continuation did not re-send the package. The SQLite store and
the baton live inside the same run directory, so the resumed pass reads the work it already
did instead of starting over.

## Limits

- Simulated loopback dispatch only; no real service contacted.
- No model call, no assessment.
