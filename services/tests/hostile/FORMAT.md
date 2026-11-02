# Hostile input packs

One file per parser. Each line is a case, and the expected failure is stated next to the bytes:

    CASE <name> | <input> | expect <CODE> | <why this must fail>

`<input>` is either `"quoted text"` (backslash-escaped like a C string, and `\0` means a NUL
byte) or `hex:001122` for bytes that cannot be typed. `expect CODE_OK` means the input is
legal and must be ACCEPTED -- hostile inputs include cases where a strict parser is tempted to
over-refuse.

Rules for these files:

1. A case is added when a parser bug is found, and never removed. A pack that only shrinks is
   a pack that stopped being believed.
2. The expected code is from `services/common/err/err.goose`. "It fails somehow" is not a
   case; the exact code is the contract, because callers branch on it.
3. `why` says what goes wrong if the case is accepted. If it cannot be said in one line, the
   case is not understood yet.
4. These are DATA. They are not executed in this tree yet: no Goose toolchain exists on this
   host (see os-build/layer1/BINDING_NOTES.md). The status of every pack is WRITTEN, NOT RUN,
   and `python3 services/tests/hostile/hostile_check.py` validates the packs themselves
   (format, codes, counts) -- not the parsers.
