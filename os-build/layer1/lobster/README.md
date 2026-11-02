# The Lobster pack — READY TO RUN, deliberately not run (BF6-04 / Round 7 F1–F4)

Four files, one status: **NOT RUN.** Nothing in this folder has been compiled,
executed, or observed. The pack is complete in the only sense this lane can
honestly claim: every step is written down with its command and its expected
output, so the first person with a Lobster host can run it without a decision.

| File | What it is |
|---|---|
| `HOST_REQUIREMENTS.md` | what a host must provide: the ten syscalls, the entry symbol, the dispatcher shape, the code vocabulary |
| `CALLER.lobster` | the caller skeleton — the shape the host must satisfy, marked NOT COMPILED |
| `RUNBOOK.md` | the four steps, the exact commands, the expected output, and how each failure reads |

## Why it stops here, in one paragraph

A host call needs a *function* to call. Every service exports exactly one symbol,
`svc_entry`, which takes no arguments and returns an exit code; `grep -rn '^export
fn' services/` finds nothing else. So the missing piece is in this lane (a callable
export and a dispatcher), not in Lobster. `LOBSTER_BINDING.md` has the measurement
table and the four-step order of work; this folder is that order, made runnable.

## The rule this pack keeps

No transcript, no claim. `os-build/logs/L3-lobster-roundtrip.txt` does not exist,
so no report may say a Lobster caller reached a service — not in a summary, not in
a demo, not in a status line. When that file exists and contains both the service's
own serial line and the caller's return value, the status moves to RUNS and the
claim becomes legal.
