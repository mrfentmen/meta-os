# Round 13 — Nuntius summary (Sections Q–R)

| section | state | counts | evidence |
|---|---|---|---|
| Nuntius relay | **COMPLETE** | 25 / 25; **25 tests pass**, 8 findings | `os-build/round13/nuntius/SECTION_Q.md` |
| Nuntius board | **COMPLETE** | 25 / 25; **25 tests pass**, 4 findings, DOM dumps in `dom/` | `os-build/round13/nuntius/SECTION_R.md` |

## Cases added

- Relay: 25 cases, 25 pass. Board: 25 cases, 25 pass. Both drive the live loopback service, and the board render cases keep the served HTML plus the JSON the viewer draws in `os-build/round13/nuntius/dom/`.
- Findings that matter: no backlog trim, no rate limit, no duplicate detection, and a colon in a nick makes a line mean one author to the server and another to a first-colon reader (R13-413).
- The relay log prints the configured port, not the bound port (R13-423); the board does the same (R13-447).

Round 13 task: R13-497.
