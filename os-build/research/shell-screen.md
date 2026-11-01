# Boot screen (OS-205): what a user and an agent see

At power-on the console shows, one line each (already implemented,
Section B + K5 console task):

- `META OS - milestone K6` (what this build is)
- `META OS KERNEL - alive (K1)` (proof of life)
- `mem map:` / `mem summary:` (memory, Section D)
- `uptime Ns ticks N` (once per second, Section C/K5)

For eyes: light gray on black, banner first, rolling log after.
For agents: the SAME facts as structured `KEY=value` records on
serial (OS-208): every status line has a parseable twin, and the
twin is the contract — screens change, fields do not.

Commands (typed at the console, echoed; OS-207/209): `status`,
`help`. Everything else answers `unknown command` and re-lists
help (OS-211). A line longer than 80 cells is truncated with a
marker — the console never wraps into garbage.
