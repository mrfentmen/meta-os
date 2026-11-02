// services/fs/fsck.goose
//
// MOSFS01 consistency checker (B-L1-86).
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// WHAT IT CHECKS, AND WHY EACH ONE IS WORTH A CHECK
// -------------------------------------------------
// A filesystem checker is only useful if its findings are ones a real failure produces.
// DESIGN.md §6 lists the four interrupted-update states; this program detects those four
// plus three that a bug in the writer would produce:
//
// | finding      | means                                                        |
// |--------------|--------------------------------------------------------------|
// | LEAK         | a block is marked used but no inode points at it             |
// | HOLE         | a block is pointed at but not marked used                    |
// | DUP          | two inodes point at the same block                           |
// | ORPHAN       | an inode has no directory entry and is not the root          |
// | BAD_ENTRY    | a directory entry names an inode that is free or invalid     |
// | LINKS        | an inode's link count disagrees with the entries naming it   |
// | SIZE         | `size` disagrees with the blocks allocated for it            |
// | RANGE        | a block pointer is outside the data region                   |
//
// It does NOT check the contents of files: a checker that understood every file format
// would be a second implementation of every service.
//
// THE CHECKER TRUSTS NOTHING IT READ
// ---------------------------------
// Every index taken from disk is bounds-checked before use. A checker that crashes on a
// corrupt image is a checker that cannot report the corruption, which is the one occasion
// it exists for.

import common.err.err;
import fs.fs;

let CK_MAX_BLOCKS: i64 = 64;
let CK_MAX_INODES: i64 = 128;
let CK_DIR_ENTS: i64 = 32;
let CK_DIR_PER_BLOCK: i64 = 24;    // queue depth: dirs deep enough for any path this FS allows
let CK_DATA_START: i64 = 10;       // mirrors fs.DATA_START; t65 asserts they agree

struct FsckReport {
    leaks: i64,         // used blocks with no owner
    holes: i64,         // owned blocks not marked used
    dups: i64,          // blocks owned twice
    orphans: i64,       // used inodes with no entry
    bad_entries: i64,   // entries pointing at free/invalid inodes
    link_bad: i64,      // link count mismatch
    size_bad: i64,      // size vs allocated blocks mismatch
    range_bad: i64,     // block pointer outside the data region
    reachable_inodes: i64,
    reachable_blocks: i64,
    fixed: i64,         // repairs applied by fsck_fix
}

var ck_seen_blk: u8[..512] = [0; 512];   // one bit per block: owned by some live inode
var ck_seen_ino: u8[..512] = [0; 512];   // one bit per inode: named by some entry (or the root)
var ck_links: u8[..512] = [0; 512];      // per-inode entry count, capped at 255
var ck_dir_blk: u8[..512] = [0; 512];    // one bit per block: already scanned as a directory
var ck_queue: u8[..512] = [0; 512];      // one bit per inode: already queued for walking

fn ck_zero_marks() {
    var i: i64 = 0;
    while i < 128 {
        ck_seen_blk[i] = 0;
        ck_seen_ino[i] = 0;
        ck_links[i] = 0;
        ck_dir_blk[i] = 0;
        ck_queue[i] = 0;
        i = i + 1;
    }
}

fn ck_set(b: u8[..512]&, n: i64) {
    if n < 0 || n >= 4096 { return; }
    let byte = n / 8;
    let bit = n % 8;
    b[byte] = ((b[byte] as i64) | (1 << bit)) as u8;
}

fn ck_get(b: u8[..512]&, n: i64) -> bool {
    if n < 0 || n >= 4096 { return false; }
    let byte = n / 8;
    let bit = n % 8;
    return ((b[byte] as i64) & (1 << bit)) != 0;
}

fn ck_bump(b: u8[..512]&, n: i64) {
    if n < 0 || n >= 4096 { return; }
    if b[n] < 255 { b[n] = b[n] + 1; }
}

fn report_init() -> FsckReport {
    return FsckReport {
        leaks: 0, holes: 0, dups: 0, orphans: 0, bad_entries: 0,
        link_bad: 0, size_bad: 0, range_bad: 0,
        reachable_inodes: 0, reachable_blocks: 0, fixed: 0,
    };
}

// Walk the tree from the root, marking inodes and blocks. Returns the number of problems
// found during the walk (bad entries, dups, range errors).
fn ck_walk(r: FsckReport&) -> i64 {
    var queue: i64[..24] = [0; 24];
    var ents: i64[..32] = [0; 32];
    var qhead: i64 = 0;
    var qtail: i64 = 0;
    queue[qtail] = fs_root();
    qtail = qtail + 1;
    ck_set(ck_seen_ino, fs_root());
    var problems: i64 = 0;

    while qhead < qtail {
        let dir = queue[qhead];
        qhead = qhead + 1;

        let d, dc = fs_ino_read(dir);
        if dc != CODE_OK { problems = problems + 1; }
        else {
            // Check the directory's own block pointers before walking them.
            var bi: i64 = 0;
            while bi < 5 {
                let lba = ino_block_at(d, bi);
                if lba != 0 {
                    if lba < CK_DATA_START || lba >= fs_block_count_value() {
                        r.range_bad = r.range_bad + 1;
                        problems = problems + 1;
                    } else if ck_get(ck_dir_blk, lba) {
                        // The same block is named as the storage of two directories. The
                        // ownership pass in ck_inodes sees this from the inode side too,
                        // but saying it here names the pair of directories.
                        r.dups = r.dups + 1;
                        problems = problems + 1;
                    } else {
                        // Mark the block as scanned, NOT as owned: ownership is decided
                        // once, in ck_inodes, over every live inode. Marking here as well
                        // made every directory's own block look owned twice, so a clean
                        // tree never passed the checker.
                        ck_set(ck_dir_blk, lba);
                        // Gather the block's entries first: resolving kinds re-reads
                        // `fs_blk`, which would otherwise clobber the block mid-scan.
                        if fs_bread(lba) == CODE_OK {
                            var e: i64 = 0;
                            while e < CK_DIR_ENTS {
                                ents[e] = g16(fs_blk, e * 16);
                                e = e + 1;
                            }
                            e = 0;
                            while e < CK_DIR_ENTS {
                                let ino = ents[e];
                                if ino != 0 {
                                    if ino < 1 || ino >= 128 {
                                        r.bad_entries = r.bad_entries + 1;
                                        problems = problems + 1;
                                    } else if ino_mode_of(ino) == MODE_FREE {
                                        r.bad_entries = r.bad_entries + 1;
                                        problems = problems + 1;
                                    } else {
                                        ck_set(ck_seen_ino, ino);
                                        ck_bump(ck_links, ino);
                                        // A directory named twice (impossible today, since
                                        // links to directories are refused) would otherwise
                                        // be walked twice and double-count its blocks. The
                                        // queue's visited set is separate from the inode
                                        // marks for exactly that reason.
                                        if ino_is_dir(ino) && !ck_queue_seen(ino) {
                                            if qtail < CK_DIR_PER_BLOCK {
                                                queue[qtail] = ino;
                                                qtail = qtail + 1;
                                            }
                                        }
                                    }
                                }
                                e = e + 1;
                            }
                        }
                    }
                }
                bi = bi + 1;
            }
        }
    }
    return problems;
}

// A small visited set for queued directories. It gets its own table: the old version
// borrowed spare bits of the block mark table, which mixed two facts into one word and
// made "was this block reached" depend on how many directories had been queued.
fn ck_queue_seen(ino: i64) -> bool {
    if ck_get(ck_queue, ino) { return true; }
    ck_set(ck_queue, ino);
    return false;
}

// Check every inode against the marks. Returns problems found.
fn ck_inodes(r: FsckReport&) -> i64 {
    var problems: i64 = 0;
    var ino: i64 = 1;
    while ino < 128 {
        let n, code = fs_ino_read(ino);
        if code != CODE_OK { problems = problems + 1; }
        else if n.mode != MODE_FREE {
            let named = ck_get(ck_seen_ino, ino);
            if !named && ino != fs_root() {
                r.orphans = r.orphans + 1;
                problems = problems + 1;
            }
            // Reachable = named by some entry, or the root, which has no entry. Counted
            // here rather than in the walk, because the walk only ever sees directories:
            // the field says "inodes", and a number that counted only directories made
            // the check that reads it false.
            if named || ino == fs_root() { r.reachable_inodes = r.reachable_inodes + 1; }
            // Link count. This filesystem has no hard links: every live inode carries
            // links == 1, and a directory's name in its parent is not a link. So the check
            // is "is it still 1", not "does it equal the number of entries naming it" --
            // the entry count flagged every directory and the root.
            if n.links != 1 {
                r.link_bad = r.link_bad + 1;
                problems = problems + 1;
            }
            // Named twice is still corruption, whatever the link field says: unlinking one
            // name frees the inode and leaves the other entry dangling.
            if named && (ck_links[ino] as i64) > 1 {
                r.link_bad = r.link_bad + 1;
                problems = problems + 1;
            }

            var used: i64 = 0;
            var bi: i64 = 0;
            while bi < 5 {
                let lba = ino_block_at(n, bi);
                if lba != 0 {
                    used = used + 1;
                    if lba < CK_DATA_START || lba >= fs_block_count_value() {
                        r.range_bad = r.range_bad + 1;
                        problems = problems + 1;
                    } else if ck_get(ck_seen_blk, lba) {
                        r.dups = r.dups + 1;
                        problems = problems + 1;
                    } else {
                        ck_set(ck_seen_blk, lba);
                        r.reachable_blocks = r.reachable_blocks + 1;
                    }
                }
                bi = bi + 1;
            }

            // Size vs blocks. A file may use a partly-filled last block, so the legal range
            // is (used-1)*512 < size <= used*512; an empty file must have no blocks.
            if n.mode == MODE_FILE {
                let lo = (used - 1) * 512;
                let hi = used * 512;
                if n.size > hi || n.size <= lo {
                    r.size_bad = r.size_bad + 1;
                    problems = problems + 1;
                }
            }
        }
        ino = ino + 1;
    }
    return problems;
}

// Compare the marks against the on-disk bitmap: leaks and holes.
fn ck_bitmap(r: FsckReport&) -> i64 {
    var problems: i64 = 0;
    if fs_read_bitmap() != CODE_OK { return -1; }
    var lba: i64 = 0;
    while lba < fs_block_count_value() {
        let marked = bitmap_bit_set(lba);
        let reached = ck_get(ck_seen_blk, lba);
        if lba < CK_DATA_START {
            // Reserved region: must always be marked.
            if !marked { r.holes = r.holes + 1; problems = problems + 1; }
        } else if marked && !reached {
            r.leaks = r.leaks + 1;
            problems = problems + 1;
        } else if !marked && reached {
            r.holes = r.holes + 1;
            problems = problems + 1;
        }
        lba = lba + 1;
    }
    return problems;
}

// Run the whole check. Returns (problems, code); `problems == 0` means the image is
// internally consistent, which is not the same as "the files are right" (see the header).
fn fsck_run(r: FsckReport&) -> i64, i64 {
    ck_zero_marks();
    var problems: i64 = 0;
    let w = ck_walk(r);
    if w < 0 { return 0, E_CORRUPT; }
    problems = problems + w;
    let i = ck_inodes(r);
    if i < 0 { return 0, E_CORRUPT; }
    problems = problems + i;
    let b = ck_bitmap(r);
    if b < 0 { return 0, E_CORRUPT; }
    problems = problems + b;
    return problems, CODE_OK;
}

// Is the report clean? One function so "clean" has one definition.
fn fsck_clean(r: FsckReport&) -> bool {
    return r.leaks == 0 && r.holes == 0 && r.dups == 0 && r.orphans == 0 &&
           r.bad_entries == 0 && r.link_bad == 0 && r.size_bad == 0 && r.range_bad == 0;
}

// Repair the three findings that are safe to repair: free orphaned inodes, release leaked
// blocks, and rewrite the superblock's free count. Duplicates and bad entries are NOT
// repaired: choosing which of two owners keeps a block is a decision, not a repair, and a
// checker that guesses is worse than one that reports.
fn fsck_fix(r: FsckReport&) -> i64 {
    if r.dups != 0 || r.bad_entries != 0 || r.range_bad != 0 {
        return E_CORRUPT;      // refuse to "fix" an image with an ambiguity in it
    }
    // Orphans: free them.
    var ino: i64 = 1;
    while ino < 128 {
        let n, code = fs_ino_read(ino);
        if code == CODE_OK && n.mode != MODE_FREE && !ck_get(ck_seen_ino, ino) && ino != fs_root() {
            if fs_release_inode(ino) == CODE_OK { r.fixed = r.fixed + 1; }
        }
        ino = ino + 1;
    }
    // Leaks: clear the bit. A block nobody points at is free, and freeing it is the
    // conservative repair -- the alternative is an unreachable block forever.
    //
    // The bitmap has to be in `fs_blk` before the first question: `bitmap_bit_set` answers
    // from that buffer, and the orphan loop above left an inode block there. Asking without
    // reading first is not a slow path, it is a wrong answer -- every bit came back clear,
    // so the repair freed nothing and reported success.
    if fs_read_bitmap() != CODE_OK { return E_CORRUPT; }
    var lba: i64 = CK_DATA_START;
    while lba < fs_block_count_value() {
        if bitmap_bit_set(lba) && !ck_get(ck_seen_blk, lba) {
            if fs_set_bitmap(lba, false) == CODE_OK { r.fixed = r.fixed + 1; }
        }
        lba = lba + 1;
    }
    // Recompute the free count from the bitmap rather than decrementing a number that may
    // already be wrong.
    let free = count_free_blocks();
    if free >= 0 { fs_set_free_blocks(free); }
    return CODE_OK;
}
