# common/bytes — byte-array helpers (B-L1-68)

`u8[:]` comparison, search, copy, fill, trim-as-span, and whole-buffer predicates
(`by_all_hex`, `by_is_blank`, …).

**Why it exists:** `std`'s string functions work on Goose `string`; every service
here passes byte slices, because a record is bytes. This is gap library 1 from
`os-build/layer1/STDLIB_GAPS.md` — the first three gaps in audit order that had no
owner when Wave F closed.

**Status:** WRITTEN (not COMPILED, not RUN).

**Rules it keeps:** no allocation, no abort on caller input (a failed search is
`-1`), no case folding beyond ASCII, no hash (that is `common/hash`).

Tests: `services/tests/t62_bytes.goose`.
