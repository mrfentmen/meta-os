# COUNTS closeout — what Round 8 left, and what happened to each (E1, 2026-11-02)

`COUNTS.md` closed with **95 constants: 78 proven, 9 not limits, 8 unreachable on the host,
0 unproven** — plus the documentation debt from E3. This is the one-page answer to "what is
still open", with a decision per item rather than a restatement.

## Closed in Round 9

| item | how it closed |
|---|---|
| The seven service READMEs (`board`, `dashboard`, `dock`, `notify`, `settings`, `updater_client`, `wallpaper`) | written from the source headers and the drivers; each driver re-run before its status line was claimed. `README_AUDIT.md` now says 36 of 42 directories. |
| The four programs the call-matrix auditor called unknown | classified as programs, not services, with the checkable reason (`svc_entry`, boot table, imports). No fabricated permissions. |

## Not closed, and why — once each

| item | count | decision |
|---|---|---|
| Dead limit declarations (`ROT_NAME_MAX`, `AK_CAPS`, `EX_NAME_MAX`, `DL_LIT_MAX`, `FS_MAX_DEPTH`, `CK_MAX_BLOCKS`, `CK_MAX_INODES`, `BO_MAX`) | 8 | **Deliberately left.** Each is a constant with no reader and a literal doing the work. Deleting one is a one-line change that removes the only recorded intent to wire it; wiring one changes behaviour in a service another lane owns. Both are Pax's call at merge time, and `COUNTS.md` names the literal for each, so neither choice needs re-deriving. Writing a test that merely mentions a constant would move a number without moving a fact, and is not done. |
| Structurally unreachable limits (`SET_MAX`, `SH_OUT_MAX`, `EX_REC_MAX`, `CFG_TEXT_MAX`, `DL_OPS_MAX`, `STALL_LIMIT`, `DNS_QUERY_MAX`, `DEP_MAX`) | 8 | **Not closable from this lane.** Each needs a bound to change first (a bigger boot table, a 4 KiB-emitting command, a frozen kernel clock). `COUNTS.md` names the change that would make each provable; until then they stay out of the proven count. |
| `MOD_CAPS` | 1 | Not a limit: a modifier bit. Stays flagged as such. |

## Standing gaps this lane still owns

- **STOP is polled, not signalled**, and the ledger has no rotation. Both are recorded in
  `AGENT_HARDENING.md`; both are deliberate, and changing either wants Pax's ruling rather than
  a quiet edit in a lane that is not the agent layer's owner.
- **The Aegis face does not exist.** The sweep, the secret count, the footprint review and the
  OPSEC pass are real; the window that draws them is not, and the spec says it comes after the
  sweep is real — so it is a next step, not an omission.

## The rule this file is written under

A closed item has an artifact behind it; an open item has a reason and an owner. Nothing above
is called done because the list needed to be shorter.
