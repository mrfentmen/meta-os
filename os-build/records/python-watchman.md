# Python watchman — behaviour record (B217)

Source: `os/os/watchman/relay_watchman.py` (401 lines). Unit:
`os/os/services/relay-watchman.service`. Every claim below cites the
file and line range it was read from; the code is the authority.

## What it is

A CLI program (not an agent) that reads job records and agent heartbeat
records and emits two kinds of event: `wake` for an open job addressed to
a local sleeping agent, and `nudge` for a claimed job whose local claimer's
heartbeat has gone stale (`relay_watchman.py:184-251`). It has no model
call, no bus post, and no counter input.

## Inputs

| Input | Shape read | Where |
|---|---|---|
| `jobs` | list of dicts; `id` (required), `status`, `addressed_to` / `to`, `claim`, `title` | `tick`, `:184-251` |
| `agents` | dict `nick -> record` **or** list of records; `nick`, `heartbeat_at`, `registered` | `normalize_agents`, `:139-166` |
| `rung_ledger` | set/iterable of rung keys the caller owns | `tick`, `:196` |
| `now` | int/float epoch seconds | `tick`, `:184-185` |
| `heartbeat_stale_seconds` | int, default 300 | `:88`, `:184-185` |

Text fields are stripped and empty becomes `None` (`_text`, `:106-112`).
Only int/float timestamps count; booleans and strings are not times
(`_num`, `:114-121`). `addressed_to` checks `addressed_to` first, then the
legacy `to`, and returns `None` when both are empty (`:123-137`).

## Outputs

- `tick()` returns `(events, new_keys)`; inputs are never mutated
  (`:184-251`).
- Wake event: `{kind: "wake", job_id, agent, title, ts}`; key
  `wake:<job_id>` (`:216-232`, `:176-178`).
- Nudge event: `{kind: "nudge", job_id, agent, heartbeat_age_seconds,
  title, ts}`; key `nudge:<job_id>:<heartbeat>` (`:233-250`, `:180-182`).
- One event per job per cycle; the caller merges `new_keys` into its
  ledger, and the next tick with that ledger is silent (`:196-199`,
  `:219-221`, `:240-242`).

## Refusals and silence (no event, no crash)

| Input | Behaviour | Where |
|---|---|---|
| `jobs` not a list (`None`, dict, str) | empty events, empty keys | `:201-202` |
| job not a dict, or no/empty `id` | skipped | `:204-209` |
| status is anything except `open` / `claimed` (done, cancelled, blocked, failed, unknown, non-string) | silent | `:210-212`, `:249-251` |
| open job with no addressee | silent — not this machine's to wake | `:213-216` |
| addressee not local (unknown or `registered: false`) | silent | `:214-216`, `:160-162` |
| addressee has a fresh heartbeat | silent | `:217-218`, `:168-173` |
| wake already in the ledger | silent (per-job dedupe) | `:219-221` |
| claimed job with no claim / non-local claimer | silent | `:234-236` |
| claimer heartbeat missing (`None`) | silent — a never-seen worker is not nudged | `:237-239` |
| heartbeat age `<=` stale threshold | silent | `:240-242` |
| same `(job, heartbeat)` nudge already in ledger | silent until heartbeat changes | `:243-245` |

## Writes

- State file: `{"rung": [sorted merged keys]}` written atomically via a
  `.tmp` file + `os.replace`, and only when the cycle produced new keys
  (`:284-293`).
- No state file argument, or no new keys: nothing is written (`:284`).
- A pre-existing state file's `rung` list is read, filtered to strings,
  and preserved in the merge (`:275-283`).

## CLI

- `--once` and `--loop` are a required mutually exclusive pair
  (`:315-320`).
- Missing jobs/agents file reads as an empty snapshot with a stderr note
  (`:253-266`); malformed JSON raises and exits 2 under `--once`, and is
  skipped with a note per cycle under `--loop` (`:341-362`).
- `--interval <= 0` or `--heartbeat-stale-seconds < 0` exits 2 before any
  cycle (`:336-340`).
- `--max-cycles N` stops after N cycles (`:351-359`).
- Exit codes: 0 ok, 2 bad input or usage (`:341-347`, `:336-340`).

## Findings (reported, not fixed)

1. **The rung ledger grows without bound.** Wake keys are one per job, and
   nudge keys are one per `(job, heartbeat)` pair (`:176-182`). Nothing
   prunes old job ids, so a long-lived state file grows forever. A
   retention rule needs a product decision.
2. **A future heartbeat is treated as fresh forever.** `is_sleeping` uses
   `now - heartbeat > stale` (`:168-173`), so a heartbeat ahead of `now`
   yields a negative age and never wakes or nudges. This is safe against
   clock skew but means a bad future timestamp silently suppresses events.
3. **`--now 0` means "real time", not epoch 0.** The CLI uses `0` as the
   "unset" sentinel (`:342-345`), so a caller cannot pin the clock to
   epoch 0. Tests pass a non-zero fake clock.
4. **Loop-mode error handling is broader than it reads.** `cycle()` already
   catches `ValueError` and returns `[]` in loop mode (`:353-359`), and the
   outer `try/except ValueError` at `:349-352` is therefore unreachable in
   that path. Harmless, but it hides which handler actually ran.
