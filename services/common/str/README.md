# common/str — splitting without allocating (B-L1-69)

Cursor-based splitting of `u8[:]`: `st_sep` (single byte), `st_word` (whitespace
runs), `st_lit_span` (multi-byte, one step at a time), plus span clamping and
ASCII case conversion into caller storage.

**Why a cursor and not a list:** a list of spans has a worst case chosen by the
input. A config line with 100,000 commas makes 100,001 spans, and the fixed
buffer sized for 16 is a crash on data a remote peer sends. `st_next` is O(1) in
field count and the caller stops when it wants.

**Status:** WRITTEN (not COMPILED, not RUN).

**Not here, on purpose:** quoting and escaping (that is the shell argument parser,
B-L1-88), unicode, number parsing (`std.parse_int`), `join`.

Tests: `services/tests/t63_str.goose`.
