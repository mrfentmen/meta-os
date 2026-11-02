# Record shapes — the lines `os-boot` writes (B006)

The crate writes no files. Each "record" is a stdout/stderr line, plus the one git commit
message the merge path creates. Shapes below are copied from the format strings, with the field
that produced each token cited. Examples use values the crate's own tests already produce.

## 1. Registration record — `REGISTERED <nick>: <caps>`

Source: `crates/os-boot/src/cli.rs:263-285` (format at `:279-283`).

```
REGISTERED w1: python,testing
```

| Token | Field | Rule |
|---|---|---|
| `REGISTERED` | literal | fixed |
| `w1` | nick | caller-supplied at `cmd_register`; `run_cli` reads `MOS_NICK` (`cli.rs:559`) |
| `python,testing` | caps | `split_caps` (`cli.rs:257-261`), then **sorted** raw strings (`cli.rs:277-279`) |

## 2. Agent listing — `NO_AGENTS`, or one line per agent

Source: `cli.rs:287-308` (format at `:301-305`).

```
w1: caps=python roles=builder host=h updated=8
```

| Field | Source | Missing value |
|---|---|---|
| `w1` | map key, sorted (`:293-295`) | — |
| `caps` | `AgentRecord.caps` (`:72-80`) | empty string |
| `roles` | `AgentRecord.roles` | empty string |
| `host` | `AgentRecord.host` | empty string |
| `updated` | `AgentRecord.updated` | empty string |

Empty map prints exactly `NO_AGENTS\n` (`:290-292`).

## 3. Dispatch record — `DISPATCHED`, then one DM line each

Source: `cli.rs:310-346` (formats at `:334-342`).

```
DISPATCHED 7
  DM w1: OK sent
```

| Token | Field | Rule |
|---|---|---|
| `7` | job id | returned by `OverseerBackend::dispatch` |
| `  DM ` | literal | two leading spaces |
| `w1` | nick | from the DM triple |
| `OK` / `FAIL` | bool | `ok` from the triple (`:337-341`) |
| `sent` | detail | free text from the backend |

No DMs prints `  (no capable workers registered)\n` (`:340-342`).

## 4. Tick record — four line kinds plus errors

Source: `cli.rs:348-377` (formats at `:356-374`).

```
SWEPT 3
PRUNED w9
VERIFIED 4
ACCEPTANCE_FAILED 5
ERROR boom          # stderr
TICK_CLEAN          # only when all five lists are empty
```

| Line | Field | Destination |
|---|---|---|
| `SWEPT <jid>` | `TickReport.swept` | stdout |
| `PRUNED <nick>` | `.pruned` | stdout |
| `VERIFIED <jid>` | `.verified` | stdout |
| `ACCEPTANCE_FAILED <jid>` | `.failed` | stdout |
| `ERROR <text>` | `.errors` | stderr, and forces exit 2 |
| `TICK_CLEAN` | none | stdout, only when every list is empty (`:371-373`) |

## 5. Verification record — report line then verdict

Source: `cli.rs:379-394`.

```
[PASS] file-exists: a
VERIFIED
```

| Line | Field | Exit |
|---|---|---|
| report | returned by `verify_done` verbatim | — |
| `VERIFIED` / `NOT_VERIFIED` | `ok` bool (`:389-392`) | 0 / 1 |

## 6. Worker record — claim, skip, failure, empty

Source: `cli.rs:396-425`.

```
CLAIMED 1: Build
--- spec ---
do the thing
```

| Shape | Condition | Line |
|---|---|---|
| `SKIP <jid> (req <sorted caps>)` | `matches` false | `:409-413` |
| `CLAIMED <jid>: <title>` + `--- spec ---` + spec | claim ok | `:416-422` |
| `CLAIM_FAILED <jid>` | claim false | `:423` |
| `NO_DISPATCHES` | nothing found at all | `:424-425` |

Note: if dispatches were found but every one was skipped, nothing is printed for the empty
case; `NO_DISPATCHES` is only for an empty poll.

## 7. Review record — header, commits, stat

Source: `cli.rs:433-460` (formats at `:441-456`).

```
branch worker/thing vs main: 1 commits, 1 files
  abc1234 worker commit
 b.txt | 1 +
```

| Token | Field | Rule |
|---|---|---|
| `worker/thing` | `ReviewSummary.branch` | verbatim |
| `main` | `.base` | verbatim |
| `1 commits, 1 files` | `.commit_count`, `.files.len()` | not pluralised |
| `  abc1234 worker commit` | `.commits` line | two leading spaces |
| ` b.txt | 1 +` | `.stat` | printed only when non-empty (`:454-456`) |

## 8. Merge record — `MERGED` plus the commit message

Source: `cli.rs:462-480` (format at `:472-476`); message built at `git.rs:121-124`.

```
MERGED worker/thing -> main: <40-hex>
```

| Token | Field |
|---|---|
| `worker/thing` | branch argument |
| `main` | base argument |
| `<40-hex>` | `rev-parse HEAD` after the merge (`git.rs:125`) |

The commit message is a separate record written into git:

```
Merge worker/thing (MOS approved)
```

Fixed text: `Merge ` + branch + ` (MOS approved)` (`git.rs:123`). No body, no trailers.

## 9. Error record — `ERROR: <message>`

Source: `cli.rs:437-439` (review), `:466-468` (merge); `ERROR <message>` in tick (`:365-367`).

```
ERROR: unknown branch: nope
```

| Token | Field | Exit |
|---|---|---|
| `ERROR:` (review/merge) or `ERROR ` (tick) | literal, note the colon difference | — |
| message | `GitError.0` or tick error string | 2 |

The colon difference is real and easy to miss: review/merge print `ERROR:`, tick prints `ERROR `
without a colon.
