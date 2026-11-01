// services/tests/t65_fs.goose
//
// B-L1-85 — FS round trip: format, files, directories, paths, remount, checker.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// WHAT THIS PROVES, AND WHAT IT CANNOT
// ------------------------------------
// It proves the filesystem does what it says within one process, over the RAM backend: the
// bytes come back, directory entries resolve, hostile paths are refused with the right
// code, a remount finds the data, and the checker is clean on a tree it just built.
//
// It CANNOT prove persistence across a process, because the backend is RAM (DESIGN.md §7),
// and it cannot prove crash safety, because nothing here interrupts a write. Both are
// stated in the report rather than implied by a green test.
//
// The negative cases get as much space as the positive ones on purpose: a filesystem that
// works when used correctly and silently mangles `..` is a demo, not a filesystem.

import fs.fs;
import fs.paths;
import fs.fsck;
import common.bytes.bytes;
import common.err.err;
import common.fmt.fmt;
import common.sys.sys;

var t_pass: i64 = 0;
var t_fail: i64 = 0;

fn say(s: const u8[:]) { let _ = sys_write_serial(s); }

fn check(name: const u8[:], cond: bool) {
    if cond { t_pass++; say("ok   "); }
    else { t_fail++; say("FAIL "); }
    say(name);
    say("\n");
}

// Resolve and compare in one place, so the path cases read as one line each instead of
// four. Returns the code for callers that want to assert on it.
fn resolves_to(start: i64, path: const u8[:], want: i64) -> bool {
    let ino, code = fs_resolve(start, path, false);
    return code == CODE_OK && ino == want;
}

fn resolve_fails(start: i64, path: const u8[:], want_code: i64) -> bool {
    let ino, code = fs_resolve(start, path, false);
    if code == CODE_OK { return false; }
    if want_code != 0 && code != want_code { return false; }
    return ino == 0;
}

fn main() {
    say("t65 filesystem\n");

    // --- format ---
    check("format 64 blocks", fs_format(64) == CODE_OK);
    check("format with no room refuses", fs_format(8) == E_INVAL);
    check("format too big for the disk refuses", fs_format(200) == E_INVAL);

    // fs_format leaves the FS mounted; unmount and mount properly, because mount
    // validation is half of what a superblock is for.
    check("umount", fs_umount() == CODE_OK);
    let _, unmounted_code = fs_resolve(0, "/", false);
    check("reads fail while unmounted", unmounted_code == E_STATE);
    check("mount", fs_mount() == CODE_OK);

    let free0, _w0, st0 = fs_stats();
    check("stats after mount", st0 == CODE_OK);
    check("free blocks = 64 - 10 reserved", free0 == 54);

    var root = fs_root();
    check("root is a directory", ino_is_dir(root));

    // --- one file, the long way round ---
    let f_ino, f_code = fs_create_path(root, "/hello", MODE_FILE);
    check("create /hello", f_code == CODE_OK && f_ino > 0);
    let dup_ino, dup_code = fs_create_path(root, "/hello", MODE_FILE);
    check("create duplicate refuses", dup_code != CODE_OK && dup_ino == 0);

    let wc = fs_write(f_ino, 0, "hello world");
    check("write 11 bytes", wc == 11);
    var buf: u8[>..] = [];
    let rc = fs_read(f_ino, 0, buf, 64);
    check("read back 11", rc == 11 && buf.len == 11);
    check("bytes match", by_eq(buf[..], "hello world"));

    let ac = fs_write(f_ino, 11, " again");
    check("append 6", ac == 6);
    var buf2: u8[>..] = [];
    let rc2 = fs_read(f_ino, 0, buf2, 64);
    check("read back 17", rc2 == 17);
    check("append landed at the end", by_eq(buf2[..], "hello world again"));

    var tail: u8[>..] = [];
    let rc3 = fs_read(f_ino, 12, tail, 8);
    check("offset read", rc3 == 5 && by_eq(tail[..], "again"));

    var past: u8[>..] = [];
    let rc4 = fs_read(f_ino, 999, past, 8);
    check("read past EOF is empty success", rc4 == 0 && past.len == 0);

    let sw, swc = fs_write(f_ino, 500, "x");
    check("write past EOF refuses (no sparse files)", swc == E_INVAL && sw == 0);

    // --- directories ---
    let d_ino, d_code = fs_create_path(root, "/etc", MODE_DIR);
    check("mkdir /etc", d_code == CODE_OK && d_ino > 0);
    let h_ino, h_code = fs_create_path(root, "/etc/hostname", MODE_FILE);
    check("create /etc/hostname", h_code == CODE_OK && h_ino > 0);
    check("write into a subdirectory file", fs_write(h_ino, 0, "meta-os") == 7);
    let _, over_code = fs_create_path(root, "etc", MODE_DIR);
    check("mkdir over an existing name refuses", over_code != CODE_OK);

    // --- listing ---
    check("root has 2 entries", fs_dirent_count(root) == 2);
    var name0: u8[>..] = [];
    let i0, k0, found0 = fs_readdir(root, 0, name0, 16);
    check("readdir 0 found", found0 && i0 > 0);
    check("readdir 0 name", by_eq(name0[..], "hello"));
    check("readdir 0 kind is file", k0 == MODE_FILE);
    var name1: u8[>..] = [];
    let i1, k1, found1 = fs_readdir(root, 1, name1, 16);
    check("readdir 1 name", found1 && by_eq(name1[..], "etc"));
    check("readdir 1 kind is dir", k1 == MODE_DIR);
    var name2: u8[>..] = [];
    let _, _, found2 = fs_readdir(root, 2, name2, 16);
    check("readdir past the end stops", !found2);

    // --- rename ---
    check("rename", fs_rename(root, "hello", "greeting") == CODE_OK);
    check("renamed file resolves", resolves_to(root, "/greeting", f_ino));
    check("old name is gone", resolve_fails(root, "/hello", E_NOTFOUND));

    // --- paths: the hostile set ---
    check("resolve /", resolves_to(root, "/", root));
    check("empty path refuses", resolve_fails(root, "", E_INVAL));
    check("//etc///hostname collapses", resolves_to(root, "//etc///hostname", h_ino));
    check("trailing slash on a dir is fine", resolves_to(root, "/etc/", d_ino));
    check("trailing slash on a file is refused", resolve_fails(root, "/greeting/", E_INVAL));
    check("/.. stays at root", resolves_to(root, "/..", root));
    check("/../.. stays at root", resolves_to(root, "/../..", root));
    check("/etc/.. is root", resolves_to(root, "/etc/..", root));
    check("cannot escape upward", resolves_to(root, "/../../etc", d_ino));
    check("missing name is NOTFOUND", resolve_fails(root, "/nope", E_NOTFOUND));
    check("walking through a file is refused", resolve_fails(root, "/greeting/x", E_INVAL));
    check("13-byte component is refused", resolve_fails(root, "/abcdefghijklm", E_INVAL));
    check("a dot file is an ordinary name", resolve_fails(root, "/.hidden", E_NOTFOUND));

    // Depth: 17 components that do not exist. Any of the three honest refusals is
    // acceptable; silently resolving would not be.
    let deep: const u8[:] = "/a/a/a/a/a/a/a/a/a/a/a/a/a/a/a/a/a";
    check("deep path refuses", resolve_fails(root, deep, 0));

    // --- kind enforcement ---
    check("want_dir on a file refuses", !want_dir_ok(root, "/greeting"));
    check("want_dir on a dir is fine", want_dir_ok(root, "/etc"));

    // --- unlink rules ---
    check("rmdir a non-empty dir refuses", fs_unlink(root, "etc") == E_STATE);
    check("unlink missing name refuses", fs_unlink(root, "nope") == E_INVAL);
    check("unlink the file", fs_unlink_path(root, "/greeting") == CODE_OK);
    check("entry is gone", resolve_fails(root, "/greeting", E_NOTFOUND));
    check("root cannot be unlinked", fs_unlink_path(root, "/..") != CODE_OK);

    // --- size limit ---
    var big: u8[>..] = [];
    var i: i64 = 0;
    while i < 2600 { big.push('x'); i++; }
    let big_ino, big_code = fs_create_path(root, "/big", MODE_FILE);
    check("create /big", big_code == CODE_OK);
    let bw, bwc = fs_write(big_ino, 0, big[..]);
    check("2600 bytes refuses (5 blocks = 2560)", bwc == E_NOROOM && bw == 0);
    let bw2 = fs_write(big_ino, 0, big[0..2560]);
    check("2560 bytes fits exactly", bw2 == 2560);

    // --- remount finds everything ---
    check("umount before remount", fs_umount() == CODE_OK);
    check("remount", fs_mount() == CODE_OK);
    let rt, rt_code = fs_resolve(root, "/etc/hostname", false);
    check("file survives remount", rt_code == CODE_OK && rt == h_ino);
    var back: u8[>..] = [];
    let rbc = fs_read(rt, 0, back, 16);
    check("contents survive remount", rbc == 7 && by_eq(back[..], "meta-os"));

    // --- the checker on a clean tree ---
    var rep = report_init();
    let problems, ccode = fsck_run(rep);
    check("fsck runs", ccode == CODE_OK);
    check("fsck is clean", problems == 0 && fsck_clean(rep));
    check("fsck saw the inodes", rep.reachable_inodes >= 4);

    // --- the checker on a planted leak ---
    // A block marked used that no inode points at: exactly the state a crash between
    // "allocate the block" and "record it" leaves behind.
    check("plant a leak", fs_set_bitmap(60, true) == CODE_OK);
    var rep2 = report_init();
    let p2, c2 = fsck_run(rep2);
    check("fsck sees the leak", c2 == CODE_OK && p2 >= 1 && rep2.leaks == 1);
    check("fsck_fix repairs it", fsck_fix(rep2) == CODE_OK && rep2.fixed == 1);
    var rep3 = report_init();
    let p3, c3 = fsck_run(rep3);
    check("clean again after the fix", c3 == CODE_OK && p3 == 0 && fsck_clean(rep3));

    // --- filling the disk stops with an error, not a crash ---
    var slot: i64 = 0;
    var made: i64 = 0;
    var stopped: bool = false;
    while slot < 40 && !stopped {
        var nm: u8[>..] = [];
        let _ = append_str(nm, 16, "/f");
        let _ = append_int(nm, 16, slot);
        let f_ok, f_c = fs_create_path(root, nm[..], MODE_FILE);
        if f_c != CODE_OK {
            stopped = true;
        } else {
            made++;
            let w2, w3 = fs_write(f_ok, 0, big[0..512]);
            if w3 != CODE_OK { stopped = true; }
        }
        slot++;
    }
    check("the disk fills and refuses politely", stopped && made < 40);

    say("t65 done  pass=");
    var pb: u8[>..] = [];
    let _ = append_int(pb, 32, t_pass);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    let _ = append_int(fb, 32, t_fail);
    say(fb[..]);
    say("\n");
    if t_fail > 0 { let _ = sys_exit(1); }
}

fn want_dir_ok(start: i64, path: const u8[:]) -> bool {
    let ino, code = fs_resolve(start, path, true);
    return code == CODE_OK && ino > 0;
}
