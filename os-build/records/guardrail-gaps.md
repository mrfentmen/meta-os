# crates/guardrail — behaviours the Rust port does not carry (B161)

Each entry is a task for the owner, not something this slice ports.
"Rust" names `crates/guardrail/src/lib.rs`; "Python" names the original
under `server/queue/`.

## G1 — A corrupt or unreadable ledger must refuse, not reset

- Python: `spark_guardrail.py:36-41` opens and `json.load`s an existing
  file; an unreadable file, bad JSON, or a missing key raises
  (`KeyError`/`TypeError` at 53/71/98) and the caller never sends.
- Rust: `load_state` returns `Default` on every error (57-62), so a
  damaged ledger reads as $0 and `check` passes.
- Done when: `load_state` returns a typed error for an existing-but-
  broken file, and the caller surfaces it as a refusal.

## G2 — A failed ledger write must fail the record

- Python: `_save_state` (44-46) raises; `record` propagates.
- Rust: `save_state` discards both the serialize and write results
  (64-68); `record` returns normally (86-103).
- Done when: `record` returns `Result` and a write failure is visible.

## G3 — The row timestamp must be the call time

- Python: `datetime.now(timezone.utc).isoformat()` (74).
- Rust: literal `2026-10-30T00:00:00Z` (92).
- Done when: the row carries the actual UTC time in the Python/Node
  `+00:00` form (`server/budget.mjs:125` documents the shape).

## G4 — The prompt must carry the `region` field

- Python: `spark_gen.py:109-112` puts `"region": {"x","y","w","h"} or
  null` inside each observation.
- Rust: the observation shape at 146 has no `region` key.
- Done when: the emitted shape contains the region object/null.

## G5 — The Region paragraph

- Python: `spark_gen.py:126-129` explains 0-1000 relative coordinates
  and when to use null.
- Rust: absent from `build_prompt` (139-160).
- Done when: the paragraph is in the prompt text.

## G6 — The Assessment rule and visible-marks paragraphs

- Python: strongest-supported-category rule at 130-133; visible marks
  (tattoos, scars, birthmarks, blood) at 134-143, with the explicit
  "never infer identity, a name, or a cause" limit.
- Rust: both absent.
- Done when: both paragraphs are present verbatim in behaviour.

## G7 — The vigiles crowd note

- Python: `spark_gen.py:144-150` defines "crowd gathered" as stationary
  and ordinary pedestrian traffic as "normal activity".
- Rust: absent (the function has no product branch).
- Done when: `build_prompt` appends the note for `product == "vigiles"`.

## G8 — The process lock

- Python: `_lock = threading.Lock()` (24) held across load/modify/save
  in `record` (68-73).
- Rust: no lock around the read-modify-write (86-103).
- Done when: concurrent records cannot lose an update (a file lock for
  cross-process safety, not just a `Mutex`).

## G9 — `remaining_usd` rounding

- Python: `round(..., 4)` (100); Node: `Math.round(x*10000)/10000`
  (`server/budget.mjs:154`).
- Rust: raw subtraction (105-113).
- Done when: the status field rounds to 4 dp.

## G10 — Usage-map aliases and the default ledger path

- Python: `estimate(usage)` accepts `prompt_tokens`/`input_tokens` and
  `completion_tokens`/`output_tokens` (60-64); `load_state(path=None)`
  defaults to `spark_guardrail_state.json` beside the module (26-27).
- Rust: `estimate` takes two `u64`s (80); there is no default path —
  every call supplies one (57, 64, 86).
- Done when: callers can pass a usage map and omit the path, with the
  repo-relative default documented.
