# Round 11, Part 2 — Aegis, what actually ran

Run date 2026-11-02. Every number below is from a command in this session. Raw reports are
local-only for now: `SECRETS.md`/`.json` are not committed because a secret report is a list
of places to look, and the triage below is not finished.

| task | result | evidence |
|---|---|---|
| R11-229 OSV sweep | **BLOCKED** — no OSV MCP server reachable; 23 manifests collected, 0 versioned refs queried, 0 findings | `os-build/aegis/SWEEP.md`, `r11/run-sweep.txt` (exit 3) |
| R11-230 secret-hygiene count | **RUN** — 2,427 files read; **4 confirmed**, 5 review, 0 allowlisted; counts only, no values copied here | `os-build/aegis/SECRETS.md` (local) |
| R11-231 OSINT v1 | **NOT RUN** — needs certificate-transparency/DNS network access; no result invented | — |
| R11-232 OPSEC checklist | **RUN** — 0 findings across private IP, email, internal host, machine name | `os-build/aegis/OPSEC.md` |
| R11-233 unicode-confusable scan | **NOT RUN** | — |
| R11-234 KEV cross-check | **BLOCKED** by 229: no dependency findings to check | — |
| R11-235..240 | **NOT DONE** — hosted registration, lifecycle drill, watch review, alarm split, README, second sweep | — |

Surface check also ran clean: 7 files, 0 hits (`os-build/aegis/SURFACE.md`).

## The one thing that must not wait

The 4 confirmed matches are GitHub-token shaped. They may be fixtures, public examples, or
live credentials; the scan cannot tell. Treat them as live until triaged: rotate the tokens
if they are real, and only then mark the rows allowlisted. This is the highest-severity item
this round produced.
