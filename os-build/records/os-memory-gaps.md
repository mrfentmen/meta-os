# `crates/os-memory` — Python behaviours not carried yet (B041)

Deliverable is the list, not the port. Each item names the Python source
line(s) it lives in and the Rust spot that differs. The Rust file is
`crates/os-memory/src/lib.rs`; the Python file is `os/mos/memory.py`
unless stated.

## 1. CLI `write` / `write-shared` print the `new_version` flag

- Python: `write()` returns the record with `new_version` added
  (`memory.py:164-193`, flag set at `memory.py:179` and
  `memory.py:191`); `write_shared()` does the same
  (`memory.py:195-218`); `main()` prints that whole dict with
  `json.dumps(..., sort_keys=True)` (`memory.py:319` onward, the
  `write` and `write-shared` branches).
- Rust: the library carries the flag in `WriteOutcome.new_version`
  (`lib.rs:565-574`), but the CLI path prints only
  `outcome.entry.to_journal_line()` (`lib.rs:1050-1058` and
  `lib.rs:1062-1070`), which never contains `new_version`.
- Effect: a caller that parses the CLI's stdout sees a different JSON
  shape from the Python CLI. Task: add the flag to the CLI success
  object (not to the stored journal line).

## 2. `NaN` / `Infinity` in a journal line

- Python: `_read_journal` uses `json.loads` (`memory.py:116-160`), whose
  default accepts `NaN`, `Infinity`, and `-Infinity`.
- Rust: `parse_number` accepts only digits, `.`, and an exponent
  (`lib.rs:180-236`); `N` or `I` is an unexpected character
  (`lib.rs:156-168`), so the line refuses with "does not parse".
- Effect: a journal written by Python with a non-finite float in an
  extra field is readable there and refused here. Task: decide whether
  to accept the three literals in the parser or to declare such a
  journal corrupt; either way the decision belongs in the spec.

## 3. Non-string `text` refusal

- Python: an explicit runtime check raises
  `MemoryError("memory text must be a string")` (`memory.py:174`, and
  the same in `write_shared` at `memory.py:199`).
- Rust: the signature takes `&str` (`lib.rs:812-822`,
  `lib.rs:824-832`), so the refusal is enforced by the type system and
  cannot be exercised at runtime.
- Effect: no behavioural gap for Rust callers; a parity test cannot
  reproduce the Python branch. Recorded, not ported.

## 4. Non-integer `ts` and boolean `ts`

- Python: `write(..., ts=...)` stores whatever it is given
  (`memory.py:183-189`); a bool is an int there, so `ts=True` is stored
  as `true` and reads back as 1.
- Rust: `ts: Option<i64>` (`lib.rs:812-822`) cannot carry a bool or a
  float. The reader still accepts a boolean `ts` from the journal
  (`lib.rs:704-737`), which preserves the Python read behaviour.
- Effect: unrepresentable at the Rust API boundary; documented rather
  than faked.

## 5. A trailing flag with no value

- Python: `argv[argv.index("--author") + 1]` raises `IndexError` when
  `--author` is last (`memory.py:319` onward); the CLI's `except`
  clauses catch only `MemoryError`, `OSError`, and `ValueError`, so this
  is an uncaught traceback and a non-2 exit.
- Rust: `find_flag` returns `None` when there is no following word
  (`lib.rs:1010-1021`), so the write proceeds with an empty author and
  exits 0.
- Effect: a divergence on malformed input. Task: decide the intended
  refusal (probably a usage error, exit 2) and test it.

## 6. `--version` with no value

- Python: same `IndexError` shape as item 5 for `--version`
  (`memory.py:319` onward).
- Rust: `find_flag` returns `None`, so the read takes the latest
  version (`lib.rs:1076-1090`, `lib.rs:1102-1116`).
- Effect: same decision as item 5.

## 7. `MemoryError` is a `ValueError` subclass

- Python: `class MemoryError(ValueError)` (`memory.py:79-81`), so code
  that catches `ValueError` also catches memory refusals.
- Rust: `MemoryError` is a standalone type implementing
  `std::error::Error` (`lib.rs:500-514`).
- Effect: expected language difference, not a behaviour to port; named
  so nobody assumes a shared error hierarchy.

## 8. `mount_paths` returns strings, not `PathBuf`

- Python: returns `str` paths (`memory.py:281` onward).
- Rust: returns `PathBuf` (`lib.rs:588-595`, `lib.rs:947-955`).
- Effect: representation only; same two directories.

## 9. Leading-zero integers

- Python: `json.loads("01")` refuses (extra data).
- Rust: `parse_number` consumes the digit run and `"01".parse::<i64>()`
  accepts it, so the line parses as `Int(1)` (`lib.rs:180-236`).
- Effect: a journal line with a leading zero is accepted here and was
  rejected by the writer that produced it. Task: either normalise the
  number or refuse a leading zero, so the reader cannot be looser than
  the Python writer.

## Not gaps (checked and carried)

- Agent/key validation order and messages (`memory.py:82-114` vs
  `lib.rs:605-657`).
- Journal line shape, including the bool-as-int quirk
  (`memory.py:116-160` vs `lib.rs:676-737`).
- Identical rewrite is a no-op (`memory.py:176-181` vs
  `lib.rs:779-788`).
- Versioning and "never guess" reads (`memory.py:235-280` vs
  `lib.rs:834-893`).
- `read_all` keeps own and shared separate (`memory.py:281-300` vs
  `lib.rs:937-945`).
- `ensure_root` is idempotent (`memory.py:301-317` vs
  `lib.rs:957-966`).
- The brief memory-depth caller (`os/intel/brief.py:1630` and
  `os/intel/brief.py:3001` vs `lib.rs:1261-1440`).
