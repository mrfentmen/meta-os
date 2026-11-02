# Meta Aegis — security sweeps over the boss's own ground

State: **host-side tooling, partially run.** It is not a kernel service, it holds no privileges,
and it has never run under the OS. Last updated 2026-11-02 from the run records in this directory.

## What actually ran

| pass | status | evidence |
|---|---|---|
| manifest inventory | RUN — 23 manifests collected | `SWEEP.md`, `aegis/manifests.mjs` |
| OSV vulnerability sweep | **BLOCKED** — no OSV server configured; 0 references queried, 0 findings, exit 3 | `SWEEP.md`, `r11/run-sweep.txt` |
| secret-hygiene count | RUN — 2,427 files, 4 confirmed / 5 review, counts only | `SECRETS.md` (local), `SECRETS_TRIAGE.md` (reading) |
| OPSEC checklist | RUN — 0 findings | `OPSEC.md`, `OPSEC_CHECKLIST.md` |
| surface scan | RUN — 7 files, 0 hits | `SURFACE.md` |
| OSINT v1 (CT/DNS) | NOT RUN — needs network and the four domain names | `PART2.md` |
| unicode-confusable scan | RUN — hosted loop, names from the gateway and tray | `r11/hosted-receipt.json` |
| findings lifecycle drill | RUN — open, acknowledge, close, plus a refused illegal step | `r11/lifecycle-drill.jsonl` |
| alarm split | RUN — low stays a note, high raises the alarm | `r11/hosted-receipt.json` |
| hosted loop | RUN — `agents/registry.json` entry `aegis`, ledger record in `runs.jsonl` | `runs.jsonl` |

The secret triage is complete: the four confirmed matches are one repeated-character placeholder
in an adversarial eval fixture, and the five review hits are drill/test placeholders. No value is
reproduced here and no credential was validated against a provider. History is still unscanned.

## What is not built

- No CISA KEV cross-check. It needs the KEV feed and a dependency finding; the sweep is blocked,
  so there is nothing to check.
- No second sweep diff. A second run needs the first to have queried something.
- No watch review. `aegis/watch-targets.mjs` builds file targets from repos and pages; it does not
  decide whether a target is still ours or still live, and no target list has been reviewed.
- No quiet/alarm delivery channel. `aegis/alarm.mjs` classifies and renders; nothing sends.
- No history scan. A key removed from the tree is still in the history.

## Run it

```
node aegis/hosted.mjs                 # local passes; writes r11/hosted-receipt.json
AEGIS_OSV_MCP=/path/to/osv-mcp/index.js node aegis/run-sweep.mjs
node aegis/run-opsec.mjs
node aegis/run-secrets.mjs
node aegis/run-surface.mjs
```

`run-sweep.mjs` exits 3 when the server is absent. That is a blocked run, not a passing one; do
not read exit 0 from any other script as proof that the OSV sweep ran.

## The rule this directory is built around

A manifest is not a finding, a missing transport is not a clean bill of health, and a severity
the source did not publish is not filled in. Every report names the source it asked and the
number of references it could not check.
