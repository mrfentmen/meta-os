# Record — the bitmap frame allocator, from the code

Scope: `kernel/src/memory.rs`, allocator only. The mapper and heap are separate records; this
one does not describe them. Every claim cites a line range from `main` on 2026-11-02.

## What it is

A bitmap over the usable frames of the bootloader's memory map
(`kernel/src/memory.rs`, lines 343-360). One bit per usable frame, in `MemoryMap` order; a set
bit means allocated. The bitmap is caller-owned, like the map and the heap buffer: the module
never allocates its own bookkeeping.

- `required_bitmap_words(total_frames)` (line 364) is how a caller sizes it. A bitmap too small
  silently shrinks the usable pool rather than corrupting anything — `covered` is clamped to
  the bitmap (`new`, line 371), and frames past coverage are never handed out.

## Allocation

`allocate` (lines 409-430) scans words for the first not-`u64::MAX` word, takes the lowest set
bit of its complement, sets it, increments `used`, and returns that frame's physical address
from the map.

- **Lowest free frame first**, not a free list: allocation is O(words) and deterministic, which
  is why boot logs from two runs report the same counters.
- If the first free bit found is at or past `covered`, it returns `None` immediately: free bits
  past coverage can only exist in the last partial word, and later indices are larger, so
  nothing later can be valid.
- Exhaustion and coverage exhaustion are reported the same way — `None`. The caller cannot
  tell "no memory" from "bitmap too small", which is deliberate but worth knowing.

## Deallocation

`deallocate` (lines 432-450) returns `false` **and changes nothing** for three cases: the
address is not a usable frame start, it is past coverage, or the bit is already clear (double
free refused). Otherwise it clears the bit and decrements `used`.

- Double free is refused rather than counted, so `used` cannot go negative or drift.
- The allocator cannot detect a *wrong* free (a valid frame the caller did not own). That is
  caller error, not something this design can see.

## Counters and what they mean

`total_frames` (usable in the whole map), `covered_frames` (what the bitmap can manage),
`used_frames`, `free_frames` = covered − used (lines 386-407). The boot log's
`mem allocator: 127199 covered frames, 127199 free` is these counters at init.

## What has not been tested

- No test for allocate/free/allocate returning the same lowest frame.
- No stress that allocates every covered frame and asserts the next call returns `None`.
- No double-free test at the bitmap level (the code path is written and refuses; nothing calls
  it with a duplicate today).
- No test that a deliberately undersized bitmap clamps `covered` instead of overrunning.

All four are unblocked to write, but they live in `kernel/src` (Rowan's lane), so they are
proposals: `os-build/ROWAN_PROPOSALS.md` items 4-5.
