# Round 11 — the one shape every service record takes

Every service gets the same six-task pass (R11-001..228) and every worker writes the same two
artifacts. This file exists so 12 workers produce one result instead of 12 dialects.

## What a worker owns

For each assigned service `<svc>`:

1. **One test:** `services/tests/t<NNN>_<svc>_r11.goose` — the number is assigned in the brief.
   One file, one service, its own `main`, its own counters.
2. **One record:** `os-build/layer1/r11/<svc>.md`, six sections in the fixed order below.
3. **One README truth pass:** `services/<svc>/README.md`, rewritten in place.

Nothing else. Do not touch `services/callmatrix/callmatrix.goose`, `os-build/layer1/LIMITS.md`
(generated), any other service, `kernel/`, or another worker's test file.

## The test file

Model it on `services/tests/t97_agent_surface.goose` and `t76_demo_session.goose`: same `say`,
`check`, `t_pass`/`t_fail` pattern. Requirements:

- imports the service module(s) it tests, nothing from another service except through its public
  functions;
- every assertion prints `ok   <what was asserted>` or `FAIL <what was asserted>`;
- ends with a line the runner parses: `pass=<N> fail=<M>`;
- `if t_fail > 0 { sys_exit(1); }`;
- **exactly one load line**, after the assertions:
  `LOAD <svc> ops=<n> ok=<n> refused=<n>`
  where `ops` is ten times a normal request batch for that service, `ok` the calls that returned
  `CODE_OK`, `refused` the calls that returned a refusal code. If load is meaningless for the
  service, print `LOAD <svc> ops=0 ok=0 refused=0 n/a=<reason>` — do not invent a number.
- No sleeps, no wall-clock waits: a test must finish on a host in under a second.

If a service cannot be imported (it is an entry-only `main`, e.g. a stdio program), **do not
force it**. Write no test, and make section 1 of the record say `NOT IMPORTABLE` with the exact
reason and the file path. A missing test with a reason is honest; a test that imports nothing is
not.

## The record: `os-build/layer1/r11/<svc>.md`

Fixed order, fixed headings. Every section opens with one of exactly three words:
**PROVEN**, **NAMED GAP**, **NOT APPLICABLE**. "Proven" requires a test name and what it asserts.
A gap is named, never softened.

```markdown
# <svc> — Round 11 record

Source: `services/<svc>/...` · Test: `services/tests/t<NNN>_<svc>_r11.goose` · Status: RUNS|TYPECHECKS|WRITTEN

## 1. Limits — PROVEN | NAMED GAP
| constant | value | in | outcome | evidence |
...
Outcome is one of: driven by this test (say what crosses the edge), already driven by
`tests/tXX` (LIMITS.md row), not a limit (bit flag / unread declaration), unreachable on the
host (name the structural bound). Every row that LIMITS.md lists for this service must appear.

## 2. Refusals — PROVEN | NAMED GAP
| refusal | code | the test assertion that expects it |
Only the refusals this service can actually make. If a refusal path cannot be reached from a
host driver, that is a row with "unreachable" and the structural reason.

## 3. Restart — PROVEN | NAMED GAP
What the supervisor does on exit, what state survives a restart and what is lost. If continuity
was not run, say so and name the loss in one sentence. Do not claim a restart you did not run.

## 4. Contract — PROVEN | NAMED GAP
| direction | other service | call | in the matrix? |
Every call in and out. Read the matrix row from `services/callmatrix/callmatrix.goose`
(`SVC_<NAME>` and `cm_set(...)`). A call the matrix does not carry is written here as
`FINDING: <call> not in matrix` — that is the finding for room 1, and it stays in this file.

## 5. Load — PROVEN | NAMED GAP
One sentence on what the load loop does and which limit it approaches, then the exact marker
line on its own:

```
<!--RUN-->
```

The coordinator runs the test and replaces the marker with the real `LOAD <svc> ops=... ok=...
refused=...` line from the transcript. No worker writes a number here: a number nobody ran is
the exact failure this round exists to remove.

## 6. README truth pass — PROVEN
Bulleted: each stale sentence found, and what it says now. Rewrite the README; do not annotate
it ("was X, now Y" belongs in this record, not in the README).
```

## The README truth pass

Read `services/<svc>/README.md` against the code and the measured run rows
(`os-build/layer1/SERVICE_RUNS.md`, `os-build/layer1/FINISH_STATUS.md`) and fix:

- a status line that says WRITTEN or "not COMPILED" when the service is RUNS (check the row);
- a dependency list naming an import the file no longer has, or missing one it has;
- a failure list that omits a refusal code the code returns, or names one it cannot;
- a "Not verified" section claiming no compilation when a driver has run.

Keep the section structure. A README that was already true is left alone and the record says so.

## Status words used by the coordinator

- **PROVEN** — a named test asserts it and the run exited 0 (the coordinator supplies the run).
- **NAMED GAP** — not exercised; the reason is structural and written down.
- **NOT APPLICABLE** — the service cannot have this property (e.g. no state to restart).
