// services/tests/t82_fs_deep.goose
//
// Round 7 B, fs — corruption, edges, and what a re-mount recovers.
//
// t65_fs is the filesystem's functional suite (76 checks). This file attacks it:
// garbage on the superblock, a plausible-but-wrong version with a correct CRC,
// names at the boundary, and a mount cycle that has to preserve the data or say
// it did not.

import fs.fs;
import fs.paths;
import fs.fsck;
import storage.storage;
import common.hash.hash;
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

fn num(label: const u8[:], v: i64) {
    say(label);
    var b: u8[>..] = [];
    let _ = append_int(b, 32, v);
    say(b[..]);
    say("\n");
}

fn put32(b: u8[..512]&, off: i64, v: i64) {
    b[off] = (v & 0xff) as u8;
    b[off + 1] = ((v >> 8) & 0xff) as u8;
    b[off + 2] = ((v >> 16) & 0xff) as u8;
    b[off + 3] = ((v >> 24) & 0xff) as u8;
}

fn name_of(n: i64) -> u8[>..] {
    var s: u8[>..] = [];
    var i: i64 = 0;
    while i < n { let _ = s.push('n'); i = i + 1; }
    return s;
}

// ===========================================================================
// (a) Failure injection

fn t_inject() {
    say("-- (a) failure injection\n");
    check("fs: format", fs_format(MAX_DISK_BLOCKS) == CODE_OK);

    // Unmounted is a state, not a corrupt disk: every call must say E_STATE and
    // not quietly operate on a stale table.
    check("fs: umount", fs_umount() == CODE_OK);
    let _, c_unmounted = fs_create(INO_ROOT, "x", MODE_FILE);
    check("fs: create while unmounted is E_STATE", c_unmounted == E_STATE);
    check("fs: sync while unmounted is E_STATE", fs_sync() == E_STATE);
    let _, c_resolve_unmounted = fs_resolve(INO_ROOT, "/", false);
    check("fs: resolve while unmounted fails", c_resolve_unmounted != CODE_OK);

    // Garbage on block 0: no magic, so mount must refuse before it reads any
    // field it would otherwise trust.
    var junk: u8[..512] = [0; 512];
    let _ = storage_write(SB_LBA, junk);
    check("fs: a wiped superblock is refused at mount", fs_mount() == E_INVAL);

    // The harder case: the magic is intact, the fields are plausible, the version
    // is wrong, and the CRC is correct. A mount that only checked the CRC would
    // accept a filesystem it does not know how to read.
    check("fs: re-format", fs_format(MAX_DISK_BLOCKS) == CODE_OK);
    var blk: u8[..512] = [0; 512];
    check("fs: read the superblock back", storage_read(SB_LBA, blk) == CODE_OK);
    put32(blk, 8, 99);                                  // FS_VERSION + 98
    let crc = crc32(blk[0..44]) as u32;
    put32(blk, 44, crc as i64);
    let _ = storage_write(SB_LBA, blk);
    check("fs: a wrong version with a valid CRC is E_STATE", fs_mount() == E_STATE);

    // A single flipped byte in a field the CRC covers must be caught by the CRC,
    // not by luck: this is the difference between detecting corruption and
    // sometimes reading it.
    check("fs: re-format after corruption", fs_format(MAX_DISK_BLOCKS) == CODE_OK);
    var blk2: u8[..512] = [0; 512];
    let _ = storage_read(SB_LBA, blk2);
    blk2[36] = (blk2[36] + 1) as u8;                    // free-block count, off by one
    let _ = storage_write(SB_LBA, blk2);
    check("fs: a changed field with a stale CRC is E_VERIFY", fs_mount() == E_VERIFY);

    // Back to a good filesystem for the rest of the file.
    check("fs: final re-format", fs_format(MAX_DISK_BLOCKS) == CODE_OK);

    // A duplicate name is refused rather than shadowed.
    let f1, c1 = fs_create(INO_ROOT, "dup", MODE_FILE);
    check("fs: first create", c1 == CODE_OK && f1 > 0);
    let _, c2 = fs_create(INO_ROOT, "dup", MODE_FILE);
    check("fs: a duplicate name is E_STATE", c2 == E_STATE);

    // A path that walks through a file is not a directory walk.
    let f2, c3 = fs_create(INO_ROOT, "plain", MODE_FILE);
    check("fs: second create", c3 == CODE_OK && f2 > 0);
    let _, c_walk = fs_resolve(INO_ROOT, "/plain/inside", false);
    check("fs: resolving through a file fails", c_walk != CODE_OK);
}

// ===========================================================================
// (b) Boundary sweep — MAX_NAME at -1, exact, +1

fn t_boundary() {
    say("-- (b) boundary sweep\n");
    check("fs: re-format for the sweep", fs_format(MAX_DISK_BLOCKS) == CODE_OK);

    let n_short = name_of(MAX_NAME - 1);
    let _, c_short = fs_create(INO_ROOT, n_short[..], MODE_FILE);
    check("fs: a name of MAX_NAME-1 is accepted", c_short == CODE_OK);

    let n_exact = name_of(MAX_NAME);
    let _, c_exact = fs_create(INO_ROOT, n_exact[..], MODE_FILE);
    check("fs: a name of exactly MAX_NAME is accepted", c_exact == CODE_OK);

    let n_over = name_of(MAX_NAME + 1);
    let _, c_over = fs_create(INO_ROOT, n_over[..], MODE_FILE);
    check("fs: a name of MAX_NAME+1 is E_INVAL", c_over == E_INVAL);

    // The block boundary: MAX_FILE_BLOCKS fit, one more does not.
    let f, cf = fs_create(INO_ROOT, "blocks", MODE_FILE);
    check("fs: create the block file", cf == CODE_OK && f > 0);
    var chunk: u8[..512] = [0; 512];
    var i: i64 = 0;
    while i < 512 { chunk[i] = 65; i = i + 1; }

    var wrote: i64 = 0;
    i = 0;
    while i < MAX_FILE_BLOCKS {
        let _, cw = fs_write(f, i * 512, chunk[..]);
        if cw == CODE_OK { wrote = wrote + 1; }
        i = i + 1;
    }
    check("fs: MAX_FILE_BLOCKS blocks are written", wrote == MAX_FILE_BLOCKS);
    let _, c6 = fs_write(f, MAX_FILE_BLOCKS * 512, chunk[..]);
    check("fs: the block after MAX_FILE_BLOCKS is refused", c6 != CODE_OK);
}

// ===========================================================================
// (c) Restart semantics — umount/mount is the closest thing to a restart

fn t_restart() {
    say("-- (c) restart semantics\n");
    check("fs: re-format for the restart test", fs_format(MAX_DISK_BLOCKS) == CODE_OK);

    let f, cf = fs_create(INO_ROOT, "persist", MODE_FILE);
    check("fs: create the file that has to survive", cf == CODE_OK && f > 0);
    var text: u8[>..] = [];
    let _ = append_str(text, 64, "survives a remount");
    let _, cw = fs_write(f, 0, text[..]);
    check("fs: write before the remount", cw == CODE_OK);

    let free_before, _, _ = fs_stats();
    check("fs: sync before the remount", fs_sync() == CODE_OK);
    check("fs: umount", fs_umount() == CODE_OK);

    // A mount is the filesystem's restart: every piece of state is rebuilt from
    // the disk, so a value that only lived in a global must come back wrong.
    check("fs: mount", fs_mount() == CODE_OK);
    let free_after, _, _ = fs_stats();
    num("   free blocks before: ", free_before);
    num("   free blocks after:  ", free_after);
    check("fs: the free-block count is what the superblock said", free_after == free_before);

    let ino, cres = fs_resolve(INO_ROOT, "/persist", false);
    check("fs: the file is still there after the remount", cres == CODE_OK && ino == f);

    var out: u8[>..] = [];
    let n, crd = fs_read(f, 0, out, 64);
    check("fs: the contents read back", crd == CODE_OK && n == text.len);
    var same = true;
    if n != text.len { same = false; }
    else {
        var i: i64 = 0;
        while i < n {
            if out[i] != text[i] { same = false; }
            i = i + 1;
        }
    }
    check("fs: and they are byte-identical", same);

    // fsck agrees the filesystem is clean after the cycle -- a remount that left
    // an orphan would show up here, not in a resolve.
    var rep = report_init();
    let problems, rc = fsck_run(rep);
    num("   fsck problems: ", problems);
    check("fs: fsck runs on the remounted image", rc == CODE_OK);
    check("fs: no problems after a clean write/umount/mount cycle", problems == 0);
}

fn main() {
    say("t82 fs deep\n");
    t_inject();
    t_boundary();
    t_restart();

    say("t82 done  pass=");
    var pb: u8[>..] = [];
    let _ = append_int(pb, 32, t_pass);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    let _ = append_int(fb, 32, t_fail);
    say(fb[..]);
    say("\n");
    if t_fail > 0 { sys_exit(1); }
}
