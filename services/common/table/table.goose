// services/common/table/table.goose
//
// B-L1-143 — Gap library 5: a fixed-capacity open-addressed table.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// THE GAP THIS FILLS
// ------------------
// STDLIB_GAPS.md lists `dictionary` (12 symbols) and `slot_pool` (15) as **provided**, and they
// are -- as host collections. A dictionary keyed by string allocates per entry, and the services
// here have a fixed budget and no allocator. This is the same idea with the allocation removed:
// 32 slots, keys up to 31 bytes, linear probing, no deletion tombstones.
//
// WHY LINEAR PROBING AND NOT CHAINING
// -----------------------------------
// Chaining needs a node per entry, which means either allocation or a second fixed pool plus a
// free list. Linear probing needs one array and one comparison loop, and at 32 slots with a
// bounded load factor the clustering is irrelevant. Simplicity is the feature.
//
// NO DELETION
// -----------
// There is no `tbl_remove`. Tombstones are where hand-written hash tables go wrong (lookup
// stops at a tombstone, or fills the table with them), and nothing in this layer deletes a key
// from a live table -- the tables are built at start-up and read for the life of the process.
// When a real need appears it gets add/remove with a generation counter, not a tombstone.
//
// HASH: FNV-1a, 64-bit
// --------------------
// Chosen because it is four lines, has no table, and its distribution is good enough for 32
// slots of short keys. It is NOT cryptographic and nothing here treats it as such.

let TBL_SLOTS: i64 = 32;
let TBL_KEY_MAX: i64 = 32;

struct Entry {
    hash: i64,           // 0 = empty slot. FNV-1a of a real key is never 0 in practice; if it
                         // ever is, the key is stored in the next slot, which costs one probe.
    key: u8[..32],
    key_len: i64,
    value: i64,
}

struct Table {
    entries: Entry[..32],
    count: i64,
    probes: i64,         // total probes across all lookups: the health line's load measure
    misses: i64,
}

fn tbl_new() -> Table {
    var t: Table;
    var i: i64 = 0;
    while i < TBL_SLOTS {
        t.entries[i] = Entry { hash: 0, key: tbl_zero_key(), key_len: 0, value: 0 };
        i++;
    }
    t.count = 0;
    t.probes = 0;
    t.misses = 0;
    return t;
}

fn tbl_zero_key() -> u8[..32] {
    var k: u8[..32];
    var i: i64 = 0;
    while i < TBL_KEY_MAX { k[i] = 0; i++; }
    return k;
}

fn tbl_hash(key: const u8[:]) -> i64 {
    // FNV-1a, masked to 63 bits so the value is never negative and never 0.
    var h: i64 = 1469598103934665603;
    var i: i64 = 0;
    while i < key.len {
        h = h ^ (key[i] as i64);
        h = (h * 1099511628211) & 0x7FFFFFFFFFFFFFFF;
        i++;
    }
    if h == 0 { return 1; }
    return h;
}

// Insert or replace. Returns (slot, code): E_INVAL for an empty or oversized key, E_NOROOM
// when the table is full (32 entries, no eviction -- eviction is a policy the caller owns).
fn tbl_put(t: Table&, key: const u8[:], value: i64) -> i64, i64 {
    if key.len == 0 || key.len > TBL_KEY_MAX - 1 { return -1, E_INVAL; }
    let h = tbl_hash(key);
    var i = h % TBL_SLOTS;
    var n: i64 = 0;
    while n < TBL_SLOTS {
        t.probes = t.probes + 1;
        if t.entries[i].hash == 0 {
            var e: Entry;
            e.hash = h;
            e.key = tbl_zero_key();
            var k: i64 = 0;
            while k < key.len { e.key[k] = key[k]; k++; }
            e.key_len = key.len;
            e.value = value;
            t.entries[i] = e;
            t.count = t.count + 1;
            return i, CODE_OK;
        }
        if t.entries[i].hash == h && tbl_key_eq(t.entries[i], key) {
            t.entries[i].value = value;
            return i, CODE_OK;
        }
        i = (i + 1) % TBL_SLOTS;
        n++;
    }
    return -1, E_NOROOM;
}

// Look up. Returns (value, found). A miss is counted, because a table that misses constantly is
// either too small or being used as a list.
fn tbl_get(t: Table&, key: const u8[:]) -> i64, bool {
    if key.len == 0 || key.len > TBL_KEY_MAX - 1 { return 0, false; }
    let h = tbl_hash(key);
    var i = h % TBL_SLOTS;
    var n: i64 = 0;
    while n < TBL_SLOTS {
        t.probes = t.probes + 1;
        if t.entries[i].hash == 0 { t.misses = t.misses + 1; return 0, false; }
        if t.entries[i].hash == h && tbl_key_eq(t.entries[i], key) { return t.entries[i].value, true; }
        i = (i + 1) % TBL_SLOTS;
        n++;
    }
    t.misses = t.misses + 1;
    return 0, false;
}

fn tbl_has(t: Table&, key: const u8[:]) -> bool {
    let _, found = tbl_get(t, key);
    return found;
}

fn tbl_key_eq(e: Entry&, key: const u8[:]) -> bool {
    if e.key_len != key.len { return false; }
    var i: i64 = 0;
    while i < key.len {
        if e.key[i] != key[i] { return false; }
        i++;
    }
    return true;
}

// (entries, probe total, misses) -- probe total over entries is the load factor in practice.
fn tbl_stats(t: Table&) -> i64, i64, i64 {
    return t.count, t.probes, t.misses;
}

// Iterate in slot order. Returns the next occupied slot at or after `from`, or -1.
// Slot order is not insertion order: a caller that needs insertion order stores it in the value.
fn tbl_next_slot(t: Table&, from: i64) -> i64 {
    var i = from;
    if i < 0 { i = 0; }
    while i < TBL_SLOTS {
        if t.entries[i].hash != 0 { return i; }
        i++;
    }
    return -1;
}

// Copy the key of a slot into the caller's buffer. False for an empty slot or no room.
fn tbl_key_copy(t: Table&, slot: i64, out: u8[>..]&, cap: i64) -> bool {
    if slot < 0 || slot >= TBL_SLOTS { return false; }
    if t.entries[slot].hash == 0 { return false; }
    let n = t.entries[slot].key_len;
    if out.len + n > cap { return false; }
    var i: i64 = 0;
    while i < n { out.push(t.entries[slot].key[i]); i++; }
    return true;
}
