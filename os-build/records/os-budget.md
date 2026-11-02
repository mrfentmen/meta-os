# `crates/os-budget` — behaviour record (B061)

Read from `crates/os-budget/src/lib.rs` on 2026-11-02. Every claim
below names a line range in that file. The crate is one `lib.rs`
(3,527 lines before this lane's tests); `Cargo.toml` declares no
dependencies and no binaries.

Line-number note: the ranges were read before this lane's two small
edits. The `build_rows_from_path` seam adds 13 lines at the old 1433
(so ranges at or after 1433 shift +13), the empty-job check adds 3
lines at the old 2059 (ranges after 2059 shift a further +3), and one
unit test was appended at EOF. Function names are the stable anchor;
the section ranges below are the pre-edit reading.

Status words: **LIVE** = reachable from a public function;
**TESTED** = a `#[cfg(test)]` case pins it; **UNPORTED** = the Python
original does it and the Rust does not (see `os-budget-gaps.md`).

## 1. Value model — lines 46–213

What it does: a std-only stand-in for the Python dict/list scalars the
source modules pass around (`Value`, line 52). Dicts keep insertion
order, matching Python's order-sensitive `repr` (line 49 comment).
Constructors `v_str` (63), `v_int` (68), `v_dict` (73).

Accessors on `Value` (77–179):

- `get` (79): first key match in a dict, else None. It does not search
  lists or coerce.
- `as_text` (87): a trimmed non-empty string, else None; empty text is
  not a value (mirrors `disk_audit._text`, Python line 52).
- `as_str_list` (104): list of non-empty strings; a bare non-empty
  string becomes a one-item list; every other shape becomes empty.
- `usable_int` (133): `Int` only; `Bool` is refused, because Python
  `bool` is an `int` and would otherwise slip through (comment 129–132).
- `usable_number` (143): `Int` or `Float`, never `Bool`.
- `py_num_str` (157): Python `str()` shape — integral floats keep
  `.0`, bools print `True`/`False`, null prints `None`.
- `py_repr` (174): Python `repr()` shape — single quotes, `\\n`, `\\r`,
  `\\t`, escaped quote and backslash.

What it refuses: nothing raises. Unknown shapes return `None` or an
empty vector; `py_repr` on a dict includes nested values at any depth.

What it writes down: nothing (pure values).

`py_float_str` (181) prints integral finite floats with one decimal
and other floats via Rust `Display`; `py_str_repr` (192) is the
single-quoted Python string form.

## 2. Budgets — lines 215–345 (Python `os/intel/budgets.py`, OS-085)

What it does:

- `env_int_value` (217) parses one env integer, returning the default
  for None, blank, unparseable, or out-of-range input. Pure over the
  raw string so tests never mutate the process environment (comment
  213–216).
- `budget_warn_percent` (239) reads `WATCHDOG_BUDGET_WARN_PERCENT`,
  default 80, range 1–100. Python computes it once at import
  (`budgets.py:79`); the Rust reads it per call — documented as
  equivalent for every caller here (comment 232–238).
- `spend_ratio` (251): spent/cap, or None when either side is not a
  usable int, cap ≤ 0, or spent < 0.
- `at_warning` (263): band `[warn_percent, 100%)`. At cap it is false:
  the hold is the louder signal (comment 256–262).
- `at_cap` (275): spent ≥ cap, overspend included.
- `claim_allowed` (284): `!at_cap`; unbudgeted lanes allow claims.
- `budget_state` (290): `"capped"`, `"warning"`, `"ok"`, or
  `"unbudgeted"` (non-dict or cap-less).
- `budgets_from_snapshot` (313): the usable dicts under `"budgets"`;
  skips non-list values, non-dict items, and entries without a
  non-empty string lane.
- `hold_entry` (331): OS-079 entry `{lane, spent, cap, held}` where
  `held = at_cap(...)`.

What it refuses: every malformed figure is treated as unbudgeted —
never as zero spend or zero cap (comments 228–231, 301–305).

What it writes down: the `hold_entry` dict, which the brief renderer
reads later.

## 3. Forecast and preemption — lines 347–550 (Python `os/intel/forecast.py`, OS-091)

Constants: `FORECAST_DAY_HOURS = 24` (348), low confidence under 4
(350), high at 12 (352).

What it does:

- `project_end_of_day` (358): `spent * day / elapsed`, with elapsed at
  or past the day projecting to spent itself. None when spent is
  negative/non-numeric, or elapsed/day is not positive.
- `confidence_for` (380): `low < 4 ≤ medium < 12 ≤ high`; `"unknown"`
  for unusable or non-positive elapsed.
- `format_hours` (396): integral floats print as ints (`8`), matching
  `forecast._format_hours`.
- `forecast_entry` (419): builds `ForecastEntry` (409) with lane,
  spent, cap, projected, `over_cap = projected > cap`, confidence, and
  the basis string. None when lane is empty, cap ≤ 0, spent < 0, or
  the projection is impossible.
- `forecast_lines` (462): one plain line per usable entry; projected
  spend is truncated with `as i64` (the comment at 493–495 notes the
  projection is never negative, so this is a floor). Empty list → no
  lines. Lines start with `Budget forecast for lane ...` and are not
  bullets.
- `preempt_decision` (513): `"pause"` only for status `running`,
  priority `low`, lane state `warning`; `"resume"` only for status
  `paused` in lane state `ok`/`unbudgeted`; everything else None.
- `preempt_record` (536): `{job, lane, action, reason}`.

What it refuses: no guessed action, no forecast from no ledger, no
preemption at cap.

What it writes down: `ForecastEntry` values in memory, the forecast
line text, and the preempt journal dict.

## 4. Brief-measure helpers — lines 552–1140 (mirrors `intel/brief.py`, `intel/spark_client.py`)

This section exists because the two cost checks measure prompts
through the brief path (comment 552–573). It is a faithful mirror,
not a second design; the canonical homes are B09/B10 and B11.

What it does:

- `brief_budget` (558): `onjoin 150`, `ondemand 300`, every other kind
  220. (Python indexes `BRIEF_BUDGETS[kind]` and raises `KeyError` for
  unknown kinds; see the gap list.)
- `estimate_tokens` (572): 0 for empty text, else `max(1, ceil(chars/4))`.
  Characters, not bytes — `dispatch.md` has 3-byte em dashes and the
  comment at 566–571 pins the 11-token difference.
- `message_parts` (581): `(nick, text)` for a dict message or a
  `"nick: text"` bus string; a string without `": "` is all text.
- `match_decision` (604): hand-rolled `DONE|BLOCKED|DECISION:` marker,
  case-insensitive, non-empty text only.
- `extract_decisions` (623), `extract_owners` (646), `extract_blocked`
  (694), `extract_watch_items` (724): the snapshot extractors the
  prompt and template brief read.
- `window_line` (756): dict window → cap record; string → verbatim;
  `window_start` → from-onward line; else "not stated".
- `trim_to_budget` (797): drops trailing bullet lines first, then
  truncates by words with `" (trimmed)"`.
- `cap_snapshot_window` (830): 500 messages / 24 hours cap, keeps
  messages with no numeric ts, accumulates `messages_dropped`, writes
  the `source_window` record.
- `morning_template_brief` (891): the core morning brief, every fact
  from an extractor, first line `TEMPLATE`, then redaction.
- `compose_brief_no_client` (989): cap window → template → trim to the
  kind budget.
- `redact_secrets` (1006): GitHub/sk-/AKIA/Bearer and named
  key/token/secret/password assignments → `[redacted]`. Hex strings
  are deliberately not redacted (comment 1001–1005).

What it refuses: no invented sections; absent records render the
honest empty wording; unknown kind in `compose_brief_no_client`
defaults to morning (989–996).

What it writes down: the brief text and the `source_window` record.

## 5. Demo-day cost check — lines 1142–1530 (Python `os/intel/cost_check.py`, INT-007)

Constants: credit 150 (1146), reserved half 75 (1148), worst output
1024 (1151), dispatch expected 300 (1154), demo goal (1157).

What it does:

- `demo_snapshot` (1178): 5 jobs (2 claimed, 1 blocked, 2 open),
  2 alerts, 3 marker messages.
- `brief_prompt` (1220): instruction + section repr, under the kind
  budget.
- `polish_prompt` (1240): rewrite instruction that forbids changing
  facts.
- `rate_value` (1250): env rate parse, default on blank/bad, source
  label `default` or `env:NAME`.
- `rates` (1269): input/output rates from `META_MODEL_API_*` env vars,
  defaults 3.0 / 15.0.
- `cost` (1289) and `round6` (1294): dollar cost rounded to 6 places.
- `build_rows` (1329): five call-class rows; polish input/output
  measured from the first alert's prompt/explanation; boot row kept
  out of the headline.
- `build_rows_from_disk` (1433): reads
  `<crate>/../../os/intel/prompts/dispatch.md`, maps a read error to
  `Err("cannot read ...")`.
- `cost_totals` (1444): expected/worst headline totals excluding the
  boot row, worst-with-boot, headroom, breakeven multiplier,
  `passed = worst_with_boot < 75 && < 150`. Panics if no boot row
  (line 1449).
- `render_cost_table` (1468): the text table, rates line, budgets,
  PASS/FAIL.
- `run_cost_check` (1521): rows + summary + table + exit code 0/1.

What it refuses: no Spark call and no network (doc comment 1142–1145
and the Python docstring it ports); a missing dispatch file is an
error, not zero rows.

What it writes down: rows, totals, table text; no ledger entry (the
Python docstring says so and the brief-cost renderer repeats it).

## 6. Busy-fixture brief cost — lines 1532–1808 (Python `os/intel/brief_cost_check.py`, BRF-027)

What it does: `busy_snapshot` (1567) builds the 22-job BRF-017 shape
(10 claimed, 6 open, 3 blocked, 3 done; 6 owners; 4 messages;
2 alerts); `measure_brief_cost` (1671) measures one variant;
`build_brief_cost_rows` (1704) returns both; `render_brief_cost_table`
(1717) renders and returns the pass flag; `run_brief_cost_check`
(1769) adds the exit code. `template_brief_record` (1790) builds the
dry-run record `{text, model: "template", spend_id: None, kind}`.

What it refuses: no Spark call; no ledger entry; a breach (worst ≥ 75
or ≥ 150) fails the table.

What it writes down: rows, table text, template record.

## 7. Budget gate and warning detector — lines 1810–1960 (Python `drills/budget_gate.py`, `watchdog` branch)

What it does: `FakeQueue` (1811, impl 1816) posts jobs and claims them
through `claim_allowed`; a refused claim records the hold and leaves
the job open. `budget_warning_alerts` (1866) emits one warning per
lane per tick, dedupe key `budget-warning:<lane>`, with lane/spent/cap/
remaining/explanation/suggested_fix/created_at. `budget_spend_line`
(1922) renders the OS-079 spend line, including `— new claims held`
for `held: true`, and appends the caller's age label.

What it refuses: malformed entries warn nothing; duplicate lanes warn
once; at cap there is no warning (the hold replaces it).

What it writes down: alert dicts and the spend line.

## 8. Cgroup-limits portable parts — lines 1962–2025 (Python `drills/cgroup_limits.py`, OS-035)

Constants: expected slice values (1966), hog target 20 × 10 MB
(1968–1970), 50M test cap (1972).

What it does: `parse_slice` (1976) reads only the `[Slice]` section's
`key=value` pairs; `slice_value` (1995) returns the first matching key;
`slice_file_passes` (2000) requires `CPUQuota=100%` and `MemoryMax=1G`;
`cgroup_gate_missing` (2011) reports missing `cpu`/`memory`
controllers, with `None` meaning an unreadable host.

What it refuses: a mismatched or missing value fails the file phase;
an unreadable controller listing is environment-blocked, modelled as
both controllers missing.

What it writes down: nothing (pure parsing/gate values). The host-only
verify/enforcement phases are unported (gap list).

## 9. Disk audit — lines 2027–2425 (Python `os/mos/disk_audit.py`, OS-128)

What it does: `ArtifactStore` (2041) and `MemoryStore` (2049) traits
define the two stores; `parse_artifact_ref` (2059) accepts
`artifact:<job>/<name>@v<digits>` with the LAST `@v` winning, as the
Python greedy regex does. `audit_goal` (2077) uses the goal key, else
the first `Goal:` line (an empty remainder is None and stops the
scan). `audit_progress_notes` (2101), `audit_remaining_files` (2113),
`audit_job_out` (2125). `audit` (2190) reconstructs every job, checks
every artifact reference against manifest and bytes, checks every
decision key against the shared and claiming agent's journals, and
files a leak `{job, layer, detail}` per failure. `AuditResult` (2170)
carries jobs/decisions/leaks/passed. `FakeStores` (2379) is the
in-memory store pair with error switches.

What it refuses: non-list job records return
`Err("job records must be a list")` (2195); missing id/title/spec,
claimed-without-goal/claim, unparseable/missing/wrong-version/
unreadable artifacts, and missing decisions are leaks; a corrupt
journal is a loud `memory-journal` leak, filed once per agent.

What it writes down: the reconstructed job dict and the leak list.

## 10. Tests — lines 2427–3527

60 `#[cfg(test)]` cases before this lane: budgets/gate 18, forecast 18,
cost_check 3, brief_cost 3, cgroup 4, disk audit 10, value 4. They pin
the Python figures (for example `0.021258 / 0.12789 / 0.143982` at
3003–3026 and the busy-fixture `416/266` and `542/298` at 3063–3096).

## Findings — doc/code disagreements (B064)

1. **The B00 header said “Skeleton only: no logic yet.”** False above
   3,500 lines of port. Fixed in the doc (the header now says the B00
   text is historical). No code changed.
2. **`parse_slice` is documented as mirroring the Python parser**
   (`lib.rs:1972-1975`), but duplicate keys resolve differently: Rust
   keeps the first (`slice_value`, 1995), Python keeps the last
   (`cgroup_limits.py:64-77`). Doc claim too strong; the divergence is
   gap item 17, not fixed.
3. **`FakeQueue` is documented as mirroring `jobs.py`'s outcome
   shape** (`lib.rs:1807-1810`), but an unknown job id returns `true`
   from `claim` instead of raising/refusing. Gap item 7, not fixed.
4. **`Value::py_repr` is documented as Python `repr()`** (`lib.rs:172`),
   but it only escapes `\\`, `'`, `\n`, `\r`, `\t`; Python also
   escapes other control characters. A hostile snapshot could render
   differently. Recorded, not fixed (no caller needs it yet).
5. **The rate line in both cost tables prints `3`, not Python's
   `3.0`** (`lib.rs:1487-1495`, `lib.rs:1736-1744` vs
   `cost_check.py:270-306`, `brief_cost_check.py:188-228`). Gap items
   5–6; not fixed because it changes user-visible output.

## What the crate does not do

- No live ledger, queue, bus, Redis, Spark call, or filesystem store.
- No `main` and no CLI; the Python scripts' printing lives with the
  caller.
- The host-only cgroup enforcement phase is not ported.
- The optional brief sections and WDG-028 watchdog line are not
  ported; comment 574–586 names them.
