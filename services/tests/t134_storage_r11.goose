// services/tests/t134_storage_r11.goose
//
// Round 11 (R11-181..186) — the storage contract's refusals and its edges.
// t54 proves the positive path (write, read back, unwritten reads as zeroes).
// This driver is the refusal catalogue and the two bounds t54 only sampled:
// init's range, the LBA edge on both calls, the sealed device, and the wipe that
// is the only durability a RAM backend can honestly offer.
//
// It also drives ten times a normal block batch and prints the LOAD line.
//
// Status: written, run pending (the coordinator runs it and fills r11/storage.md §5).

import storage.storage;
import common.err.err;
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

fn say_int(n: i64) {
    var b: u8[>..] = [];
    let _ = append_int(b, 32, n);
    say(b[..]);
}

fn fill_blk(b: u8[..512]&, v: u8) {
    var i: i64 = 0;
    while i < 512 {
        b[i] = v;
        i = i + 1;
    }
}

fn all(b: u8[..512]&, v: u8) -> bool {
    var i: i64 = 0;
    while i < 512 {
        if b[i] != v { return false; }
        i = i + 1;
    }
    return true;
}

fn main() {
    say("t134 storage round 11\n");

    var blk: u8[..512] = [0; 512];

    // ------------------------------------------------------------------
    // 1. before init: one code, not a crash and not a zero-filled "success"
    // ------------------------------------------------------------------
    check("read before init is E_NO_DEVICE", storage_read(0, blk) == E_NO_DEVICE);
    check("write before init is E_NO_DEVICE", storage_write(0, blk) == E_NO_DEVICE);
    check("seal before init is E_NO_DEVICE", storage_seal() == E_NO_DEVICE);
    check("wipe before init is E_NO_DEVICE", storage_wipe() == E_NO_DEVICE);
    let db, dw, dc = storage_stats();
    check("stats before init is E_NO_DEVICE", db == 0 && dw == 0 && dc == E_NO_DEVICE);

    // ------------------------------------------------------------------
    // 2. init bounds: zero and one past RAM_BLOCKS are refused, the edge is not
    // ------------------------------------------------------------------
    check("init(0) is E_INVAL", storage_init(0) == E_INVAL);
    check("init(65) is E_INVAL", storage_init(65) == E_INVAL);
    check("init(-1) is E_INVAL", storage_init(-1) == E_INVAL);
    check("init(64) is accepted", storage_init(64) == CODE_OK);

    let blocks, writes0, code0 = storage_stats();
    check("stats: the block count asked for", blocks == 64 && code0 == CODE_OK);
    check("stats: no writes yet", writes0 == 0);

    check("BLOCK_SIZE is 512", BLOCK_SIZE == 512);
    check("RAM_BLOCKS is 64", RAM_BLOCKS == 64);
    check("RAM_BYTES is BLOCK_SIZE * RAM_BLOCKS", RAM_BYTES == BLOCK_SIZE * RAM_BLOCKS);

    // ------------------------------------------------------------------
    // 3. the LBA edge, read and write agreeing, and a refusal changes nothing
    // ------------------------------------------------------------------
    fill_blk(blk, 90);
    check("write(-1) is E_BAD_BLOCK", storage_write(-1, blk) == E_BAD_BLOCK);
    check("write(64) is E_BAD_BLOCK", storage_write(64, blk) == E_BAD_BLOCK);
    check("read(-1) is E_BAD_BLOCK", storage_read(-1, blk) == E_BAD_BLOCK);
    check("read(64) is E_BAD_BLOCK", storage_read(64, blk) == E_BAD_BLOCK);
    check("read(63) is the last valid block", storage_read(63, blk) == CODE_OK);

    let b1, w1, c1 = storage_stats();
    check("a refused write is not counted", b1 == 64 && w1 == 0 && c1 == CODE_OK);

    // ------------------------------------------------------------------
    // 4. bytes move, and only the addressed block moves
    // ------------------------------------------------------------------
    fill_blk(blk, 90);
    check("write block 0", storage_write(0, blk) == CODE_OK);
    fill_blk(blk, 0);
    check("read block 0", storage_read(0, blk) == CODE_OK);
    check("block 0 is byte-for-byte what was written", all(blk, 90));

    fill_blk(blk, 17);
    check("write block 1", storage_write(1, blk) == CODE_OK);
    fill_blk(blk, 0);
    check("block 1 reads as 17s", storage_read(1, blk) == CODE_OK && all(blk, 17));
    fill_blk(blk, 0);
    check("block 0 did not change", storage_read(0, blk) == CODE_OK && all(blk, 90));

    let b2, w2, c2 = storage_stats();
    check("two accepted writes are counted", b2 == 64 && w2 == 2 && c2 == CODE_OK);

    // ------------------------------------------------------------------
    // 5. sealed: writes refuse, reads still work, the counter does not move
    // ------------------------------------------------------------------
    check("seal", storage_seal() == CODE_OK);
    fill_blk(blk, 34);
    check("write to a sealed device is E_READ_ONLY", storage_write(2, blk) == E_READ_ONLY);
    fill_blk(blk, 0);
    check("a sealed device still reads", storage_read(0, blk) == CODE_OK && all(blk, 90));
    let b3, w3, c3 = storage_stats();
    check("a refused sealed write is not counted", b3 == 64 && w3 == 2 && c3 == CODE_OK);

    // wipe is the only reset a volatile store promises, and it unseals
    check("wipe", storage_wipe() == CODE_OK);
    let b4, w4, c4 = storage_stats();
    check("wipe resets the write count", b4 == 64 && w4 == 0 && c4 == CODE_OK);
    fill_blk(blk, 0);
    check("wipe zeroes the blocks", storage_read(0, blk) == CODE_OK && all(blk, 0));
    check("wipe unseals", storage_write(0, blk) == CODE_OK);
    check("the backend states it is volatile", storage_volatile());

    // ------------------------------------------------------------------
    // 6. ten times a normal batch: 5 rounds x 64 writes + 64 reads
    // ------------------------------------------------------------------
    var w_ok: i64 = 0;
    var r_ok: i64 = 0;
    var refused: i64 = 0;
    var round: i64 = 0;
    while round < 5 {
        var i: i64 = 0;
        while i < 64 {
            fill_blk(blk, (i % 7) as u8);
            if storage_write(i, blk) == CODE_OK { w_ok = w_ok + 1; }
            else { refused = refused + 1; }
            if storage_read(i, blk) == CODE_OK { r_ok = r_ok + 1; }
            else { refused = refused + 1; }
            i = i + 1;
        }
        round = round + 1;
    }
    check("load: every write accepted", w_ok == 320);
    check("load: every read accepted", r_ok == 320);

    say("LOAD storage ops=");
    say_int(w_ok + r_ok + refused);
    say(" ok=");
    say_int(w_ok + r_ok);
    say(" refused=");
    say_int(refused);
    say("\n");

    say("t134 done  pass=");
    say_int(t_pass);
    say(" fail=");
    say_int(t_fail);
    say("\n");
    if t_fail > 0 { sys_exit(1); }
}
