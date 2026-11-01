# common/hex — base16 encode, strict decode (B-L1-70)

`hex_encode` / `hex_decode` / `hex_is_exact` / `hex_eq_ci` / `hex_encoded_len`.

**Why strict:** hex is the wire format for digests in the update manifest and for
byte dumps in audit records. A decoder that tolerates `0x`, separators or
whitespace turns "verify this digest" into "verify this prefix". So `hex_decode`
requires an even length, every character in `[0-9a-fA-F]`, and on any failure it
writes **nothing** and returns `-1`.

**Status:** WRITTEN (not COMPILED, not RUN).

Tests: `services/tests/t64_hex.goose`.
