// services/tests/t119_fs_r11.goose
//
// Round 11, fs — the refusal catalogue, the two limits that are crossed rather than named,
// and the depth boundary the design document states imprecisely.
//
// t65_fs is the functional suite (75 checks) and t82_fs_deep attacks corruption and the name
// and block boundaries. This file adds what neither covers: format's lower and upper edges,
// every refusal that is reachable from a host driver with its exact code, inode exhaustion
// (MAX_INODES crossed, not named), and the real path-depth boundary (15 components resolve,
// the 16th is E_NOROOM -- DESIGN.md says "16", which is off by the root).
//
// Status: WRITTEN — the coordinator runs it; this file makes no claim about its own result.

import fs.fs;
import fs.paths;
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

fn load_line(ops: i64, ok: i64, refused: i64) {
    say("LOAD fs ops=");
    var b: u8[>..] = [];
    let _ = append_int(b, 32, ops);
    say(b[..]);
    say(" ok=");
    var b2: u8[>..] = [];
    let _ = append_int(b2, 32, ok);
    say(b2[..]);
    say(" refused=");
    var b3: u8[>..] = [];
    let _ = append_int(b3, 32, refused);
    say(b3[..]);
    say("\n");
}

// A name of `n` letters, for the boundary cases.
fn name_of(n: i64) -> u8[>..] {
    var s: u8[>..] = [];
    var i: i64 = 0;
    while i < n { let _ = s.push(0x6E); i = i + 1; }   // 'n'
    return s;
}

// "d0".."d15", "f0".."f125": one letter prefix plus a decimal index.
fn nm(prefix: u8, i: i64, out: u8[..8]&) -> i64 {
    out[0] = prefix;
    if i < 10 {
        out[1] = (0x30 + i) as u8;
        return 2;
    }
    out[1] = (0x30 + (i / 10)) as u8;
    out[2] = (0x30 + (i % 10)) as u8;
    return 3;
}

fn push_seg(path: u8[>..]&, s: const u8[:]) {
    path.push(0x2F);                                   // '/'
    var i: i64 = 0;
    while i < s.len { path.push(s[i]); i = i + 1; }
}

// ===========================================================================
// 1. format's edges
// ===========================================================================
fn t_format_edges() {
    say("-- (1) format edges\n");
    check("format: zero blocks is E_INVAL", fs_format(0) == E_INVAL);
    check("format: nine blocks is E_INVAL (the layout needs 14)",
          fs_format(9) == E_INVAL);
    check("format: one past MAX_DISK_BLOCKS is E_INVAL",
          fs_format(MAX_DISK_BLOCKS + 1) == E_INVAL);
    check("format: exactly MAX_DISK_BLOCKS is accepted",
          fs_format(MAX_DISK_BLOCKS) == CODE_OK);
}

// ===========================================================================
// 2. create's refusals
// ===========================================================================
fn t_create_refusals() {
    say("-- (2) create refusals\n");
    let f, cf = fs_create(INO_ROOT, "plain", MODE_FILE);
    check("create: a legal file", cf == CODE_OK && f > 0);

    let _, c_empty = fs_create(INO_ROOT, "", MODE_FILE);
    check("create: an empty name is E_INVAL", c_empty == E_INVAL);

    let _, c_kind = fs_create(INO_ROOT, "bad", 99);
    check("create: an unknown kind is E_INVAL", c_kind == E_INVAL);

    let _, c_under_file = fs_create(f, "child", MODE_FILE);
    check("create: a file cannot be a parent (E_INVAL)", c_under_file == E_INVAL);

    let over = name_of(MAX_NAME + 1);
    let _, c_over = fs_create(INO_ROOT, over[..], MODE_FILE);
    check("create: a name of MAX_NAME+1 is E_INVAL", c_over == E_INVAL);
}

// ===========================================================================
// 3. reads, writes and truncates against the wrong kind of inode
// ===========================================================================
fn t_type_refusals() {
    say("-- (3) type refusals\n");
    let d, cd = fs_create(INO_ROOT, "dir", MODE_DIR);
    check("create: a legal directory", cd == CODE_OK && d > 0);
    let f, cf = fs_create(INO_ROOT, "file", MODE_FILE);
    check("create: a file beside it", cf == CODE_OK && f > 0);

    var out: u8[>..] = [];
    let _, r_dir = fs_read(d, 0, out, 8);
    check("read: a directory is E_INVAL", r_dir == E_INVAL);

    var one: u8[..1] = [0; 1];
    one[0] = 0x41;
    let _, w_dir = fs_write(d, 0, one[..]);
    check("write: a directory is E_INVAL", w_dir == E_INVAL);

    check("truncate: a directory is E_INVAL", fs_truncate(d) == E_INVAL);

    let _, r_neg = fs_read(f, -1, out, 8);
    check("read: a negative offset is E_INVAL", r_neg == E_INVAL);

    let _, w_sparse = fs_write(f, 1, one[..]);
    check("write: an offset past the size is E_INVAL (no holes)", w_sparse == E_INVAL);

    let _, r_missing = fs_read(120, 0, out, 8);
    check("read: a free inode is E_INVAL, not a silent short read", r_missing == E_INVAL);
}

// ===========================================================================
// 4. unlink and rename refusals, and the success they guard
// ===========================================================================
fn t_unlink_rename() {
    say("-- (4) unlink and rename\n");
    let c_missing = fs_unlink(INO_ROOT, "nope");
    check("unlink: a name that is not there is E_INVAL", c_missing == E_INVAL);

    let d, cd = fs_create(INO_ROOT, "full", MODE_DIR);
    check("unlink: the directory to fill", cd == CODE_OK && d > 0);
    let _, ck = fs_create(d, "kid", MODE_FILE);
    check("unlink: a file inside it", ck == CODE_OK);
    let c_nonempty = fs_unlink(INO_ROOT, "full");
    check("unlink: a non-empty directory is E_STATE", c_nonempty == E_STATE);

    let _, ca = fs_create(INO_ROOT, "a", MODE_FILE);
    let _, cb = fs_create(INO_ROOT, "b", MODE_FILE);
    check("rename: two files to work with", ca == CODE_OK && cb == CODE_OK);

    let c_ren_missing = fs_rename(INO_ROOT, "gone", "x");
    check("rename: a missing source is E_INVAL", c_ren_missing == E_INVAL);

    let c_ren_dup = fs_rename(INO_ROOT, "a", "b");
    check("rename: an existing target is E_STATE", c_ren_dup == E_STATE);

    let c_ren_ok = fs_rename(INO_ROOT, "a", "c");
    check("rename: a free target succeeds", c_ren_ok == CODE_OK);

    let _, c_old = fs_resolve(INO_ROOT, "/a", false);
    check("rename: the old name is gone", c_old == E_NOTFOUND);
    let _, c_new = fs_resolve(INO_ROOT, "/c", false);
    check("rename: the new name resolves", c_new == CODE_OK);
}

// ===========================================================================
// 5. path refusals and the real depth boundary
// ===========================================================================
fn t_paths() {
    say("-- (5) path refusals\n");
    check("format: clean for the path cases", fs_format(MAX_DISK_BLOCKS) == CODE_OK);

    let _, c_empty = fs_resolve(INO_ROOT, "", false);
    check("resolve: an empty path is E_INVAL", c_empty == E_INVAL);

    let over = name_of(MAX_NAME + 1);
    var p13: u8[>..] = [];
    p13.push(0x2F);
    var k: i64 = 0;
    while k < over.len { p13.push(over[k]); k = k + 1; }
    let _, c13 = fs_resolve(INO_ROOT, p13[..], false);
    check("resolve: a 13-byte component is E_INVAL", c13 == E_INVAL);

    // Fifteen nested directories: each component is a push onto the resolver's 16-slot
    // chain, the root occupying slot one. So 15 names resolve and the 16th is E_NOROOM.
    var path: u8[>..] = [];
    var parent = INO_ROOT;
    var i: i64 = 0;
    var built = true;
    while i < 15 {
        var n: u8[..8] = [0; 8];
        let nl = nm(0x64, i, n);                       // 'd'
        let d, dc = fs_create(parent, n[..nl], MODE_DIR);
        if dc != CODE_OK { built = false; }
        parent = d;
        push_seg(path, n[..nl]);
        i = i + 1;
    }
    check("resolve: fifteen directories were built", built);

    let _, c15 = fs_resolve(INO_ROOT, path[..], true);
    check("resolve: fifteen components resolve", c15 == CODE_OK);

    var n16: u8[..8] = [0; 8];
    let nl16 = nm(0x64, 15, n16);
    let _, c_mk16 = fs_create(parent, n16[..nl16], MODE_DIR);
    check("resolve: the sixteenth directory is created", c_mk16 == CODE_OK);
    push_seg(path, n16[..nl16]);

    let _, c16 = fs_resolve(INO_ROOT, path[..], true);
    check("resolve: sixteen components are E_NOROOM (DESIGN's '16' counts the root)",
          c16 == E_NOROOM);
}

// ===========================================================================
// 6. MAX_INODES is crossed, not named
// ===========================================================================
fn t_inode_exhaustion() {
    say("-- (6) inode exhaustion\n");
    check("format: clean for exhaustion", fs_format(MAX_DISK_BLOCKS) == CODE_OK);

    var created: i64 = 0;
    var last: i64 = CODE_OK;
    var i: i64 = 0;
    while i < 200 {
        var n: u8[..8] = [0; 8];
        let nl = nm(0x66, i, n);                       // 'f'
        let _, c = fs_create(INO_ROOT, n[..nl], MODE_FILE);
        if c != CODE_OK { last = c; break; }
        created = created + 1;
        i = i + 1;
    }
    check("inodes: every inode after the root is used before the table refuses",
          created == MAX_INODES - 2);
    check("inodes: the next create is E_NOROOM, not a silent overwrite", last == E_NOROOM);

    // The directory's own 160-entry cap is never reached this way: 126 files fill the inode
    // table first, so the directory limit is structurally unreachable and is recorded as such.
    check("inodes: the directory limit is not the binding one here", created < 160);
}

// ===========================================================================
// 7. truncate gives the block back, and the load shape
// ===========================================================================
fn t_truncate_and_load() {
    say("-- (7) truncate frees, then load\n");
    check("format: clean for truncate", fs_format(MAX_DISK_BLOCKS) == CODE_OK);

    let f, cf = fs_create(INO_ROOT, "trunc", MODE_FILE);
    check("truncate: the file exists", cf == CODE_OK && f > 0);

    var chunk: u8[..512] = [0; 512];
    var i: i64 = 0;
    while i < 512 { chunk[i] = 0x41; i = i + 1; }
    let n, cw = fs_write(f, 0, chunk[..]);
    check("truncate: one block was written", cw == CODE_OK && n == 512);

    let free_before, _, _ = fs_stats();
    check("truncate: succeeds", fs_truncate(f) == CODE_OK);
    let free_after, _, _ = fs_stats();
    check("truncate: the block is back in the free count", free_after == free_before + 1);

    // Load shape: ten times a normal batch of small writes and reads on one file.
    let lf, lcf = fs_create(INO_ROOT, "load", MODE_FILE);
    check("load: the file exists", lcf == CODE_OK && lf > 0);
    var small: u8[..16] = [0; 16];
    i = 0;
    while i < 16 { small[i] = 0x62; i = i + 1; }

    var ops: i64 = 0;
    var ok: i64 = 0;
    var refused: i64 = 0;
    var out: u8[>..] = [];
    while ops < 200 {
        let wn, wc = fs_write(lf, 0, small[..]);
        out.clear();
        let rn, rc = fs_read(lf, 0, out, 16);
        if wc == CODE_OK && rc == CODE_OK && wn == 16 && rn == 16 {
            ok = ok + 1;
        } else {
            refused = refused + 1;
        }
        ops = ops + 1;
    }
    check("load: 200 write+read pairs all held", ok == 200);

    say("t119 done  pass=");
    var pb: u8[>..] = [];
    let _ = append_int(pb, 32, t_pass);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    let _ = append_int(fb, 32, t_fail);
    say(fb[..]);
    say("\n");
    load_line(ops, ok, refused);
}

fn main() {
    say("t119 fs r11\n");
    t_format_edges();
    t_create_refusals();
    t_type_refusals();
    t_unlink_rename();

    check("format: reset before paths", fs_format(MAX_DISK_BLOCKS) == CODE_OK);
    t_paths();

    t_inode_exhaustion();
    t_truncate_and_load();

    if t_fail > 0 { sys_exit(1); }
}
