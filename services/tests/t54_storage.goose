// services/tests/t54_storage.goose
//
// B-L1-54 — test program for the storage contract and its RAM backend (B-L1-25).
//
// Status: RUNS — tests/t54_storage: 26 checks, 0 failures. Measured 2026-11-02 by audit_status.py.
//
// WHAT IS UNDER TEST
// ------------------
// The block contract: 512-byte blocks, numbered from 0, every access bounds-checked. The
// backend is RAM, which is real storage rather than a mock -- it holds bytes and gives them
// back, and it is volatile, which the service reports instead of hiding (`storage_volatile`).
//
// The cases are the ones that turn into data loss later:
//   - writing a block and reading it back byte-for-byte (the only positive case);
//   - a block that was never written reading as zeroes, not as whatever the buffer held
//     (an uninitialised read is how a service leaks another service's data);
//   - out-of-range blocks refused on read AND on write (a write past the end is the one
//     that corrupts something else);
//   - a different block stays untouched, so a backend that ignores the LBA fails here.

import storage.storage;
import common.fmt.fmt;
import common.sys.sys;

var t_pass: i64 = 0;
var t_fail: i64 = 0;

fn say(s: const u8[:]) { let _ = sys_write_serial(s); }

fn check(name: const u8[:], cond: bool) {
    if cond { t_pass = t_pass + 1; say("ok   "); }
    else { t_fail = t_fail + 1; say("FAIL "); }
    say(name);
    say("\n");
}

fn fill_512(b: u8[..512]&, v: u8) {
    var i: i64 = 0;
    while i < 512 {
        b[i] = v;
        i = i + 1;
    }
}

fn is_all(b: u8[..512]&, v: u8) -> bool {
    var i: i64 = 0;
    while i < 512 {
        if b[i] != v { return false; }
        i = i + 1;
    }
    return true;
}

fn main() {
    say("t54 storage + ram\n");

    check("init", storage_init(8) == CODE_OK);
    let blocks, writes0, code0 = storage_stats();
    check("block count is what was asked for", blocks == 8 && code0 == CODE_OK);

    // The backend states what it is: RAM, so volatile. Reporting otherwise would make a
    // service believe its records survive a power cut.
    check("backend reports volatile", storage_volatile());

    // --- bounds ---
    check("lba 0 valid", storage_lba_ok(0));
    check("last lba valid", storage_lba_ok(blocks - 1));
    check("one past the end invalid", storage_lba_ok(blocks) == false);
    check("negative lba invalid", storage_lba_ok(-1) == false);

    var blk: u8[..512] = [0; 512];

    // --- read before write is zeroes ---
    fill_512(blk, 255);
    check("read unwritten block", storage_read(3, blk) == CODE_OK);
    check("unwritten block is zeroes, not a copy of the caller's buffer", is_all(blk, 0));

    // --- write and read back ---
    fill_512(blk, 65);
    check("write block 1", storage_write(1, blk) == CODE_OK);
    var back: u8[..512] = [0; 512];
    check("read block 1", storage_read(1, back) == CODE_OK);
    check("round trip byte-exact", is_all(back, 65));

    // A different block must be unaffected: a backend that ignores the LBA fails here.
    check("block 2 still zero", storage_read(2, back) == CODE_OK && is_all(back, 0));

    // --- overwrite ---
    fill_512(blk, 66);
    check("overwrite block 1", storage_write(1, blk) == CODE_OK);
    check("overwrite visible", storage_read(1, back) == CODE_OK && is_all(back, 66));

    // --- out of range, on both paths ---
    fill_512(blk, 67);
    check("write past the end refused", storage_write(blocks, blk) == E_BAD_BLOCK);
    var junk: u8[..512] = [0; 512];
    check("read past the end refused", storage_read(blocks, junk) == E_BAD_BLOCK);
    check("negative write refused", storage_write(-1, blk) == E_BAD_BLOCK);
    check("negative read refused", storage_read(-1, junk) == E_BAD_BLOCK);

    // The refused write must not have landed anywhere: block 0 is still zero.
    check("refused write landed nowhere", storage_read(0, junk) == CODE_OK && is_all(junk, 0));

    // --- the write counter moves only for real writes ---
    let _, w0, _ = storage_stats();
    fill_512(blk, 69);
    let _ = storage_write(4, blk);
    let _, w1, _ = storage_stats();
    check("writes counted", w1 == w0 + 1);
    // A refused write must not be counted as a write: a counter that counts attempts reads
    // as progress when nothing is being stored.
    let _ = storage_write(blocks + 5, blk);
    let _, w2, _ = storage_stats();
    check("refused write not counted", w2 == w1);

    // --- sealing ---
    // Sealing is the read-only state the updater relies on. It must report success and then
    // actually refuse a write; a seal that reports success and still accepts writes is
    // worse than no seal at all.
    let seal = storage_seal();
    check("seal succeeds", seal == CODE_OK);
    fill_512(blk, 70);
    check("write after seal refused", storage_write(1, blk) == E_READ_ONLY);
    check("read after seal still works", storage_read(1, back) == CODE_OK);
    check("sealed data unchanged", is_all(back, 66));

    var r: u8[>..] = [];
    let _ = append_int(r, 32, t_pass);
    say("passed ");
    say(r);
    say("\n");
    if t_fail != 0 { say("FAILURES\n"); sys_exit(1); }
    say("t54 done\n");
    sys_exit(0);
}
