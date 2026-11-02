# Service README audit (E3, 2026-11-02; gap closed 2026-11-02)

Measured by walking `services/*/` and checking for a `README.md`:

**42 directories. 36 have a README. 6 do not.**

The round's target was 25, so the count was met at 29. The seven real services the
first pass named as documentation debt — `board`, `dashboard`, `dock`, `notify`,
`settings`, `updater_client`, `wallpaper` — now have one, written against the
drivers that run them.

## The seven that were added

Each README states what the service is, the rules that carry it, its public
surface, what it deliberately does not do, and the driver that proves it. Each
driver was re-run on merged `main` before the status line was written:

| service | README | driver, `run_native.sh` |
|---|---|---|
| `settings` | yes | `t86_settings` — `RUNS=1 FAILS=0` |
| `wallpaper` | yes | `t87_wallpaper` — `RUNS=1 FAILS=0` |
| `dock` | yes | `t88_dock` — `RUNS=1 FAILS=0` |
| `dashboard` | yes | `t89_dashboard` — `RUNS=1 FAILS=0` |
| `updater_client` | yes | `t90_updater_client` — `RUNS=1 FAILS=0` |
| `board` | yes | `t91_board` — `RUNS=1 FAILS=0` |
| `notify` | yes | `t95_notify` — `RUNS=1 FAILS=0` |

## The six without one, and why

| directory | reason |
|---|---|
| `services/build` | a `.gitignore` only; not a service |
| `services/common` | library root: 15 library directories, no single service |
| `services/echo` | a standalone program: no `svc_entry`, not in the boot table. Documented in its source header and called as a child process by the Lobster host |
| `services/heartbeat` | same: a daemon-shaped program, documented in its header |
| `services/hello` | three-line sample, documented by the file itself |
| `services/mcp-host` | same as `echo`: a program, documented in its header |

The four programs are deliberately out of the call matrix too; the reason and the
check behind it are in `CALLMATRIX_DRIFT.md` ("The four programs the auditor used
to call unknown"), so the two lists agree rather than needing to be reconciled.

## What this does not claim

A README's presence is not a review of its contents. The 36 that exist were
checked for size, and the seven added in this pass were written from the source
headers, the function surface and a run of their drivers. Nobody has read all 36
end to end in this lane, and the docs for services that changed after their README
was written are not re-verified here.
