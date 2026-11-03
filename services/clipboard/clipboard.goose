// services/clipboard/clipboard.goose
//
// The shared clipboard: one bounded buffer, one owner, a generation counter.
//
// WHY IT IS THIS SMALL
// --------------------
// A clipboard is the easiest place in an OS to grow an accidental IPC bus: it
// is shared, it is mutable, and every app wants "just one more" format. This
// module is deliberately one buffer of bytes with an owner and a generation.
// Text, images and agent handoffs are the callers' problem; the clipboard's job
// is to say exactly what it holds and to refuse what it cannot hold whole.
//
// THE RULES, STATED SO A CALLER CAN CHECK THEM
// --------------------------------------------
// 1. Capacity is CLIP_CAP bytes. A set larger than that is REFUSED with
//    E_NOROOM, and the previous content survives untouched. A truncated
//    clipboard is worse than an old one: paste would silently lose the tail.
// 2. An empty set is invalid (E_INVAL). Clearing is clip_clear, so a copied
//    empty selection cannot look like a successful copy.
// 3. A get into a buffer smaller than the content returns E_NOROOM and writes
//    NOTHING. Partial paste inserts a prefix and calls it the document.
// 4. Only the owner may clear. Owner -1 means nobody claimed it, and anyone may
//    clear that. Overwriting is allowed by any caller on purpose: the clipboard
//    is shared desktop state, and the generation counter is how a reader knows
//    its cached copy is stale.
// 5. clip_generation() increases on every successful set or clear, including a
//    clear, and never resets while the machine runs. A reader that sees the same
//    generation has the same content.
//
// Status: WRITTEN, TYPECHECKED in services/root.goose. Tests: services/tests/
// t141_clipboard.goose. No kernel, no session store, no display: this is a
// Layer 4 library with fixed storage, which is what the rest of this layer is.

import common.err.err;

let CLIP_CAP: i64 = 4096;
let CLIP_NO_OWNER: i64 = -1;

// Fixed storage, not a slice returned to callers: a getter that handed out a
// view of this buffer would let a caller change the clipboard by writing to it.
var clip_buf: u8[..4096] = [0; 4096];
var clip_len: i64 = 0;
var clip_gen: i64 = 0;
var clip_owner: i64 = CLIP_NO_OWNER;

fn clip_cap() -> i64 { return CLIP_CAP; }
fn clip_len_get() -> i64 { return clip_len; }
fn clip_generation() -> i64 { return clip_gen; }
fn clip_owner_get() -> i64 { return clip_owner; }

// Boot-time reset. Not the same as clip_clear: clearing is a user action and
// bumps the generation, while boot starts the counter at zero.
fn clip_init() {
    var i: i64 = 0;
    while i < CLIP_CAP {
        clip_buf[i] = 0;
        i = i + 1;
    }
    clip_len = 0;
    clip_gen = 0;
    clip_owner = CLIP_NO_OWNER;
}

// Replace the clipboard. All-or-nothing: refuse first, write second.
fn clip_set(data: const u8[:], owner: i64) -> i64 {
    if data.len > CLIP_CAP { return E_NOROOM; }
    if data.len == 0 { return E_INVAL; }
    if owner < 0 { return E_INVAL; }
    var i: i64 = 0;
    while i < data.len {
        clip_buf[i] = data[i];
        i = i + 1;
    }
    // Clear the tail so a shorter copy cannot expose the previous, longer one.
    while i < CLIP_CAP {
        clip_buf[i] = 0;
        i = i + 1;
    }
    clip_len = data.len;
    clip_gen = clip_gen + 1;
    clip_owner = owner;
    return CODE_OK;
}

// Read the whole clipboard into the caller's buffer.
// Returns (bytes written, code). On E_NOROOM nothing is written.
fn clip_get(out: u8[>..]&, cap: i64) -> i64, i64 {
    if clip_len == 0 { return 0, E_NOTFOUND; }
    if cap < clip_len { return 0, E_NOROOM; }
    var i: i64 = 0;
    while i < clip_len {
        out.push(clip_buf[i]);
        i = i + 1;
    }
    return clip_len, CODE_OK;
}

// Empty the clipboard. Only the owning session, or anyone when unowned.
fn clip_clear(owner: i64) -> i64 {
    if clip_len == 0 { return E_NOTFOUND; }
    if clip_owner != CLIP_NO_OWNER && owner != clip_owner { return E_DENIED; }
    var i: i64 = 0;
    while i < CLIP_CAP {
        clip_buf[i] = 0;
        i = i + 1;
    }
    clip_len = 0;
    clip_owner = CLIP_NO_OWNER;
    clip_gen = clip_gen + 1;
    return CODE_OK;
}
