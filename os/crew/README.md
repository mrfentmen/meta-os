# Crew folders

Ruling (Del, 2026-10-27): every agent works inside their own named
folder under `crew/`. Nobody writes in another agent's folder.

| Folder | Owner |
| --- | --- |
| `crew/pax/` | Pax (coordinator / integrator) |
| `crew/rowan/` | Rowan (dashboard / world view) |
| `crew/hana/` | Hana (briefings) |
| `crew/milo/` | Milo (watchdog) |
| `crew/buffy/` | Buffy (volume / docs / fixtures) |

Rules:

- Your folder is yours: your working files, your notes, your lane
  output staging. No other agent edits, moves, or deletes anything
  in it.
- Project code still lives in the project tree (`intel/`,
  `dashboard/`, `os/`, `worlds/`, `tests/`, `plan/`) under the
  existing lane ownership in the lane push protocol. The crew
  folders do not replace lane ownership; they give every agent a
  private area that can never be clobbered.
- Shared files (top-level `README.md`, `plan/`, anything not owned
  by one lane) are integrator-only: Pax. This is the failure that
  bit us twice on 2026-10-27 (README sections overwritten by a
  lane push, repaired same-run both times); the folder rule plus
  this shared-file rule close it.
- Push discipline is unchanged: read the live tip before pushing,
  diff every path, take the push lease, one commit per batch with
  lane paths only, read back after pushing.
