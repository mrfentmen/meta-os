# heartbeat — Round 11 record

Source: `services/heartbeat/heartbeat.goose` · Test: **none** (entry-only program) ·
Status: entry-only, no host driver

## 1. Limits — NOT IMPORTABLE

`heartbeat.goose` is a complete program: it defines `main`, imports `os`, and exposes no function
a test can call. A Goose test imports a module and calls its functions; importing this file would
bring in a second `main`, which the corpus forbids. **No test is written, by design, and no
`LOAD` line exists to run.**

The only numeric bound in the file is the literal `n < 3600`: at most 3,600 beats, then the loop
ends. That is a duration cap (one hour at the `sleep(1.0)` interval), not a named limit, and no
test can reach it without an hour of wall clock — the corpus rule forbids waits.

## 2. Refusals — NOT APPLICABLE

The program refuses nothing. It has no arguments, no input parser and no caller. Its only
control decision is the `STOP` sentinel: before each beat it checks `file_exists("STOP")` and
breaks, printing `daemon stopping cleanly`. That is a stop condition, not a refusal with a code.

**Behavioural finding:** the file's header says it appends "one timestamped line per second".
The code appends the bare token `beat` — `append_file("heartbeat.log", "beat")` — with no
timestamp and no newline of its own. Either the header or the write is wrong; the header was
corrected in the README (which did not exist), and the code is left alone because a daemon's
record format is the owner's call.

## 3. Restart — NAMED GAP

There is no supervisor entry for `heartbeat` and no restart drill. On a clean stop the loop
exits and the supervisor would start a fresh process, which resumes appending to
`heartbeat.log`; the file is the only state, and it survives because it is a real host file.
A kill loses nothing but the current second. This is read from the code, not run — no ledger
entry, no restart transcript.

## 4. Contract — NAMED GAP

`heartbeat.goose` imports `os` only: `file_exists`, `append_file`, `print`, `sleep`. It calls no
service and no kernel syscall directly.

| direction | other service | call | in the matrix? |
|---|---|---|---|
| out | none | `os` stdio/filesystem only | **no row** — `callmatrix_audit.py` lists `heartbeat` in `NOT_SERVICES`, so its absence is deliberate, not drift |
| in | none | nothing calls it | n/a |

`FINDING (by design, recorded so it is not rediscovered): heartbeat is a program living under
services/. It is in the call-matrix audit's NOT_SERVICES set with hello, echo and mcp-host. If the
image lane expects it to be a supervised service, that expectation is not represented in the
matrix.

## 5. Load — NOT APPLICABLE

No request volume exists: the program writes one token per second and caps itself at 3,600.
`LOAD heartbeat ops=0 ok=0 refused=0 n/a=entry-only daemon` would be the line if a test existed
to print it; no test exists, and this record does not invent a run.

## 6. README truth pass — PROVEN

There was **no `services/heartbeat/README.md`**. One now exists and states:

- it is an entry-only program, not a library, and cannot be imported by a test;
- what it actually writes (`beat`, not a timestamped line), and where;
- the 3,600-beat cap and the `STOP` sentinel as the stop mechanism (no signal API in the stdlib);
- the one-hour-at-one-beat-per-second duration, and that a committed `STOP` file in the directory
  makes a run from that directory exit immediately;
- that it is not in the call matrix, deliberately, and is not a supervised service today.
