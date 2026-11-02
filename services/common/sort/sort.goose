// services/common/sort/sort.goose
//
// B-L1-144 — Gap library 6: sorting fixed arrays, in place, without allocating.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// THE GAP THIS FILLS
// ------------------
// STDLIB_GAPS.md marks `std.sort` as **provided**. It sorts host collections, and the arrays in
// this layer are fixed-size `i64[..N]` buffers whose length is a separate variable. Passing one
// to a host sort means materialising a `vec`, which is the allocation this layer exists without.
//
// WHAT IS HERE
// ------------
//   - insertion sort over i64 (stable by construction: equal elements never swap)
//   - insertion sort with a parallel payload array (sort ids, carry records along)
//   - a binary search over a sorted array
//   - `sorted_ok` for tests, because half the value of a sort is proving it happened
//
// WHY INSERTION SORT AND NOT QUICKSORT
// ------------------------------------
// These arrays are at most a few dozen entries (services, agents, segments). Insertion sort is O(n^2)
// with a tiny constant, no recursion, no pivot selection, and it is stable -- which matters for
// boot order and for log segments, where equal keys must keep their arrival order. A quicksort
// over 22 elements would be slower and would need a stack the kernel cannot spare.
//
// The parallel-payload version exists because "sort these ids" is almost always "and keep the
// names with them"; two separate sorts of parallel arrays is how a display ends up with the
// right order and the wrong names.

// ---------------------------------------------------------------------------
// i64 arrays
// ---------------------------------------------------------------------------

// Sort a[0..n) ascending, in place. n is validated against cap and needed nothing else:
// a caller that passes a longer n than the array has is a bug this cannot detect, so the
// signature takes the cap and refuses instead.
fn sort_i64(a: i64[..64]&, n: i64, cap: i64) -> i64 {
    if n < 0 || n > cap { return E_INVAL; }
    var i: i64 = 1;
    while i < n {
        let v = a[i];
        var j = i - 1;
        while j >= 0 && a[j] > v {
            a[j + 1] = a[j];
            j = j - 1;
        }
        a[j + 1] = v;
        i = i + 1;
    }
    return CODE_OK;
}

fn sorted_ok(a: i64[..64]&, n: i64) -> bool {
    if n < 0 { return false; }
    var i: i64 = 1;
    while i < n {
        if a[i - 1] > a[i] { return false; }
        i = i + 1;
    }
    return true;
}

// ---------------------------------------------------------------------------
// Parallel payload
// ---------------------------------------------------------------------------

// Sort keys ascending, moving the payload with them. Stability is what makes this usable for
// boot order: two services with the same order number keep the order they were declared in.
fn sort_pairs(keys: i64[..64]&, payload: i64[..64]&, n: i64, cap: i64) -> i64 {
    if n < 0 || n > cap { return E_INVAL; }
    var i: i64 = 1;
    while i < n {
        let k = keys[i];
        let p = payload[i];
        var j = i - 1;
        // Strictly greater: equal keys do NOT shift, which is the whole of stability.
        while j >= 0 && keys[j] > k {
            keys[j + 1] = keys[j];
            payload[j + 1] = payload[j];
            j = j - 1;
        }
        keys[j + 1] = k;
        payload[j + 1] = p;
        i = i + 1;
    }
    return CODE_OK;
}

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

// Binary search over a sorted array. Returns (index, found); on a miss the index is where the
// value would be inserted. The insertion point is the useful half for the boot-order checker.
fn sort_find(a: i64[..64]&, n: i64, v: i64) -> i64, bool {
    var lo: i64 = 0;
    var hi = n;
    while lo < hi {
        let mid = lo + (hi - lo) / 2;
        if a[mid] == v { return mid, true; }
        if a[mid] < v { lo = mid + 1; } else { hi = mid; }
    }
    return lo, false;
}

// ---------------------------------------------------------------------------
// Byte-string arrays
// ---------------------------------------------------------------------------

// Sort an array of byte strings lexicographically, by their spans. Written for directory
// listings, where the entries are already in a fixed buffer and only their offsets move.
fn sort_spans(offs: i64[..64]&, lens: i64[..64]&, n: i64, buf: const u8[:], cap: i64) -> i64 {
    if n < 0 || n > cap { return E_INVAL; }
    var i: i64 = 1;
    while i < n {
        let o = offs[i];
        let l = lens[i];
        var j = i - 1;
        while j >= 0 && span_greater(buf, offs[j], lens[j], o, l) {
            offs[j + 1] = offs[j];
            lens[j + 1] = lens[j];
            j = j - 1;
        }
        offs[j + 1] = o;
        lens[j + 1] = l;
        i = i + 1;
    }
    return CODE_OK;
}

// Is span A greater than span B, byte by byte? Equal prefixes fall back to length, so "ab" sorts
// before "abc" -- the same rule a directory listing and a config parser both expect.
fn span_greater(buf: const u8[:], ao: i64, al: i64, bo: i64, bl: i64) -> bool {
    var i: i64 = 0;
    while i < al && i < bl {
        let ac = buf[ao + i];
        let bc = buf[bo + i];
        if ac != bc { return ac > bc; }
        i = i + 1;
    }
    return al > bl;
}
