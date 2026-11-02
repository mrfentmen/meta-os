# Gap records — R13-017 heartbeat

## R13-017-G1 — no manifest entry

- **Claim:** `heartbeat` has a service manifest entry.
- **Reality:** `services/MANIFEST.md` does not mention `heartbeat`; `callmatrix_audit.py` lists it
  in `NOT_SERVICES` alongside `hello`, `echo` and `mcp-host`.
- **Evidence:** `grep -nEi 'heartbeat' services/MANIFEST.md` returns no matches;
  `os-build/layer1/callmatrix_audit.py:52`.
- **Impact:** nothing records an owner, service id or supervision state for the daemon. The
  README says this is deliberate, but the manifest therefore cannot be used as the inventory.
- **Owner:** services manifest; program classification.

## R13-017-G2 — header comment claims a timestamp the code does not write

- **Claim:** `heartbeat.goose` “Appends one timestamped line per second”.
- **Reality:** line 14 calls `append_file("heartbeat.log", "beat")`; there is no timestamp, no
  newline and no line separator. The result is the repeated token `beat`.
- **Evidence:** `services/heartbeat/heartbeat.goose:1-3` versus `:14`.
- **Impact:** anyone reading the header to build a parser will expect timestamped lines and get a
  single concatenated token. The README already flags the comment as wrong.
- **Owner:** heartbeat header comment.
