# dns — the resolver client

Status: **WRITTEN** (not COMPILED — no Goose toolchain on this Mac). Layer 4,
service 16. Pure: bytes in, bytes out, no cache and no timers.

## Scope

One A-record lookup, built from RFC 1035 §4.1.2. AAAA and everything else wait until
IPv6 exists anywhere in this stack — an untested parser for records nothing can use is
liability, not coverage.

## The compression pointer is the whole problem

A name may point at bytes earlier in the packet. That makes a naive parser trivially
crashable and a careless one infinitely loopable — a pointer to itself is a valid-looking
encoding that never terminates. Three guards, because one of them will be the one that
matters:

1. **Every pointer must point strictly backwards.** Forward or same-offset is refused.
   Forward can loop and can read sections the packet has not finished writing; same-offset
   is a one-instruction infinite loop.
2. **Jump count capped** at `DNS_MAX_JUMPS` (32).
3. **Name length capped** at the format's own 255 bytes.

`dns_read_name` returns the offset where parsing **continues**, not where the pointer
led — a caller that continued at the target would re-read records already consumed.

## Refusals, and why each exists

| Check | Reason |
|---|---|
| reply id != query id | otherwise we answer somebody else's question |
| `QR` bit clear | not a response |
| `QDCOUNT != 1` | not a shape this parser understands |
| label length > 63 | the length byte's top two bits are the pointer marker; 64..191 are not lengths |
| A record `rdlength != 4` | a different record pretending to be A, or malformed |
| `ANCOUNT < 1` | name does not resolve |

An empty label (leading or doubled dot) is refused at build time rather than emitted: a
zero-length label **is** the root terminator, so one in the middle makes the query
malformed by construction.

## Bug found while writing it

The query builder reused the loop counter from the 12-byte header loop, so the name loop
started at offset 12 and **silently dropped the first twelve characters of every
hostname**. The reset to 0 is now commented where it sits, because it looks redundant
and is not.

Not compiled, not run.
