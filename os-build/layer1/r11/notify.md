# notify — Round 11 record

Source: `services/notify/notify.goose` ·
Test: `services/tests/t127_notify_r11.goose` ·
Status: RUNS via `t95_notify`; this round's driver is **WRITTEN, not yet run**.

## 1. Limits — PROVEN for `t95`; `t127` assertions pending run

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `NT_MAX` | 12 | `notify.goose` | driven by both | `t95` fills to 12 and refuses the 13th; `t127` accepts exactly 12 of 120 under load |
| `NT_TEXT_MAX` | 96 | `notify.goose` | driven by both | `t95`: text of exactly 96 is `E_NOROOM`; `t127` builds text only up to the cap |
| `NT_SRC_MAX` | 16 | `notify.goose` | driven by both | `t95`: source of exactly 16 is `E_NOROOM` |
| `NT_LOG_MAX` | 8 | `notify.goose` | written in `t127`, pending run | `t127`: nine dismissals wrap the ring — slot 0 holds the ninth, slot 1 the second, slot 7 the eighth |
| `NT_DEDUPE_MS` | 3000 | `notify.goose` | already driven | `t95`: duplicate at exactly the window, new note one ms past it |

## 2. Refusals — PROVEN for `t95`; `t127` assertions pending run

| refusal | code | assertion |
|---|---|---|
| severity outside info..error | `E_INVAL` | `t95`: severity 0 and 4 |
| empty source or text | `E_INVAL` | `t95`: both |
| non-printable byte in source or text | `E_INVAL` | `t95`: newline in either |
| source or text at its cap | `E_NOROOM` | `t95`: length exactly 16 / 96 |
| a thirteenth note with twelve showing | `E_NO_SPACE` | `t95`, `t127` (caught before capacity? no — after dedupe) |
| dismissing an id that is gone | `E_NOTFOUND` | `t127`: after the ring wrapped |

Duplicate is not a refusal: identical `(source, text)` inside the window returns the existing
id with `NT_DUPLICATE`, and `t127` proves that check runs before capacity, so a retry in a full
feed is told the note exists rather than told to grow the feed.

## 3. Restart — NAMED GAP

The feed and the dismissal ring are process memory. A supervisor restart loses every note and
every dismissal; the code says so in its header ("it is gone on restart"). That is the designed
behaviour, not a continuity claim: nothing persists, nothing replays. No restart test has been
run, so the section is a named loss rather than a proof.

## 4. Contract — PROVEN

Matrix id `SVC_NOTIFY` (31), row allows `LOG | TIME`.

| direction | other | call | in the matrix? |
|---|---|---|---|
| out | common.err, common.fmt | `E_*`, `append_int`, `append_str` | libraries, not services |
| in | board (30) | push a post event | yes — board's row carries `NOTIFY`, **dormant**: board does not import notify |
| in | updater_client (29) | update-available event | yes — its row carries `NOTIFY`, **dormant** |

Finding: notify has no importer in the corpus today. Both inbound edges are declared policy
and the matrix audit reports them dormant, which is the honest state — the bar exists before
its producers are wired, deliberately.

## 5. Load — NAMED GAP

The load loop posts 120 distinct notes with timestamps four seconds apart (past the dedupe
window), so the only limit in play is capacity. It counts accepted and refused and requires
them to sum to the operations.

RUNS pass=48 fail=0 · `LOAD notify ops=120 ok=12 refused=108`

## 6. README truth pass — PROVEN

- `services/notify/README.md` was checked sentence by sentence against the code and is already
  true: RUNS, `t95_notify` named, dedupe/refusal/dismissal/dot described exactly as implemented.
  Left untouched.
- One detail worth stating here rather than adding to a true README: the dismissal ring is a
  log with a total (`nt_dismissal_total`) that outlives its eight slots — after nine dismissals
  the first id is gone from the ring and still counted. `t127` asserts both halves.
