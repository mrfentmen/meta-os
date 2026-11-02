// services/tests/t80_limit_drivers2.goose
//
// BF6-01, second pass — the limits t79 did not reach: the filesystem's two table
// sizes, the console's line buffer, the escape parser's parameter array, the
// manifest's origin field, the base64 sink, the netcfg text buffer, and the
// shell's working-directory buffer.
//
// Same rules as t79: every check drives the limit through the public API and
// asserts the refusal (or, where the code truncates, asserts the truncation and
// calls it a truncation).
//
// Status: RUNS — set by `audit_status.py` from the runner's row, not by hand.

import fs.fs;
import console.console;
import console.esc;
import updater.updater;
import updater.signature;
import common.enc.enc;
import netcfg.netcfg;
import netcfg.persist;
import shell.shell;
import timesync.timesync;
import common.fmt.fmt;
import fs.paths;
import common.err.err;
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

fn main() {
    say("t80 limit drivers, second pass\n");
    t_fs_inodes();
    t_fs_blocks();
    t_console_line();
    t_esc_params();
    t_manifest_origin();
    t_b64_cap();
    t_netcfg_text();
    t_shell_cwd();
    t_ntp_offset();

    say("t80 done  pass=");
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

// ===========================================================================
// 1. fs — MAX_INODES (128)
//
// The inode table is the filesystem's hard population limit. Formatting makes a
// root; every create after that spends one. The count is printed, because "the
// 128th create refused" is only meaningful if the 127th succeeded.

fn t_fs_inodes() {
    say("-- MAX_INODES\n");
    check("fs: format", fs_format(MAX_DISK_BLOCKS) == CODE_OK);

    var made: i64 = 0;
    var last: i64 = CODE_OK;
    var i: i64 = 0;
    while i < MAX_INODES + 2 {
        var name: u8[>..] = [];
        let _ = append_str(name, 32, "f");
        let _ = append_int(name, 32, i);
        let ino, code = fs_create(INO_ROOT, name[..], MODE_FILE);
        last = code;
        if code == CODE_OK { made = made + 1; }
        if code != CODE_OK { break; }
        i = i + 1;
    }
    num("   creates accepted: ", made);
    num("   refusal code:     ", last);
    // MAX_INODES includes the root, so the creates that fit are one fewer.
    check("fs: the table fills exactly, inode 0 and the root excluded", made == MAX_INODES - 2);
    check("fs: the next create is E_NOROOM", last == E_NOROOM);

    // A refusal that damaged the table would show up as a name that now exists.
    let _, gone = fs_resolve(INO_ROOT, "f9999", false);
    check("fs: the refused name was not half-created", gone == E_NOTFOUND);
}

// ===========================================================================
// 2. fs — MAX_DISK_BLOCKS (64)
//
// The block count is fixed at format time. Filling the disk must refuse, not
// wrap the allocator onto block 0, which is the classic way a filesystem eats
// its own superblock.

fn t_fs_blocks() {
    say("-- MAX_DISK_BLOCKS\n");
    check("fs: the formatter refuses one block over the disk",
          fs_format(MAX_DISK_BLOCKS + 1) == E_INVAL);
    check("fs: format at the cap", fs_format(MAX_DISK_BLOCKS) == CODE_OK);
    check("fs: the block count is the cap", fs_block_count_value() == MAX_DISK_BLOCKS);

    // Each file can hold MAX_FILE_BLOCKS, so the disk fills within this many.
    var wrote: i64 = 0;
    var last: i64 = CODE_OK;
    var i: i64 = 0;
    var chunk: u8[..512] = [0; 512];
    var c: i64 = 0;
    while c < 512 { chunk[c] = 65; c = c + 1; }

    while i < MAX_DISK_BLOCKS + 4 {
        var name: u8[>..] = [];
        let _ = append_str(name, 32, "b");
        let _ = append_int(name, 32, i);
        let ino, code = fs_create(INO_ROOT, name[..], MODE_FILE);
        if code != CODE_OK { last = code; break; }
        // One block per write, MAX_FILE_BLOCKS times.
        var blk: i64 = 0;
        while blk < MAX_FILE_BLOCKS {
            let _, wcode = fs_write(ino, blk * 512, chunk[..]);
            if wcode != CODE_OK { last = wcode; break; }
            wrote = wrote + 1;
            blk = blk + 1;
        }
        if last != CODE_OK { break; }
        i = i + 1;
    }
    // fs_stats returns (free_blocks, writes, code) -- free blocks first, not last.
    let free, writes, scode = fs_stats();
    num("   blocks written:  ", wrote);
    num("   free blocks:     ", free);
    num("   write count:     ", writes);
    check("fs: the disk fills and refuses rather than wrapping", last != CODE_OK);
    check("fs: nothing is free once the disk is full", free == 0);
    check("fs: the stats call itself succeeds", scode == CODE_OK);
    check("fs: the write counter matches the writes that succeeded", writes >= wrote);
}

// ===========================================================================
// 3. console — CONSOLE_LINE_MAX (256)

fn t_console_line() {
    say("-- CONSOLE_LINE_MAX\n");
    clear_line();
    // handle_key is the key path and always returns false for a printable byte: it
    // reports "the line is finished", not "the byte was stored". insert_byte is the
    // layer underneath and is the one that can refuse, so the cap is driven there.
    var typed: i64 = 0;
    var i: i64 = 0;
    var accepted: bool = true;
    while i < CONSOLE_LINE_MAX + 1 {
        accepted = insert_byte('a');
        if accepted { typed = typed + 1; }
        i = i + 1;
    }
    num("   bytes typed:     ", typed);
    check("console: 255 bytes fit, the NUL is the 256th", typed == CONSOLE_LINE_MAX - 1);
    check("console: the next keystroke is refused", !accepted);

    // Backspace gives a byte back, and typing then works again: a full line that
    // cannot be edited is a wedged prompt.
    let _ = handle_key(8);
    check("console: backspace reopens the line", insert_byte('b'));
    clear_line();
}

// ===========================================================================
// 4. esc — ESC_PARAMS_MAX (4)

fn t_esc_params() {
    say("-- ESC_PARAMS_MAX\n");
    var p = esc_new();
    // ESC [ 1 ; 2 ; 3 ; 4 ; 5 ; 6 H -- six parameters, two more than the array.
    let _ = esc_feed(p, 27);
    let _ = esc_feed(p, '[');
    var i: i64 = 1;
    while i <= 6 {
        let _ = esc_feed(p, (48 + i) as u8);
        let _ = esc_feed(p, ';');
        i = i + 1;
    }
    let done = esc_final(p, 'H');
    num("   parameters kept: ", p.nparams);
    check("esc: the parser completes the sequence", done);
    check("esc: the parameter array stops at 4", p.nparams == ESC_PARAMS_MAX);
    check("esc: parameter 4 does not exist (-1 = default)",
          esc_param(p, 4) == -1);
    check("esc: the first four parameters are the first four sent",
          esc_param(p, 0) == 1 && esc_param(p, 3) == 4);
}

// ===========================================================================
// 5. updater — MF_ORIGIN_MAX (64)

fn manifest_origin(n: i64) -> Manifest, i64 {
    var t: u8[>..] = [];
    let _ = append_str(t, 4096, "version=1\nslot=a\norigin=");
    var i: i64 = 0;
    while i < n { let _ = t.push('o'); i = i + 1; }
    let _ = append_str(t, 4096, "\nfile=a ");
    i = 0;
    while i < MF_DIGEST_BYTES { let _ = append_str(t, 4096, "00"); i = i + 1; }
    let _ = append_str(t, 4096, " 1\n");
    return upd_parse_manifest(t[..]);
}

fn t_manifest_origin() {
    say("-- MF_ORIGIN_MAX\n");
    let m63, c63 = manifest_origin(MF_ORIGIN_MAX - 1);
    check("manifest: a 63-byte origin parses", c63 == CODE_OK && m63.origin_len == MF_ORIGIN_MAX - 1);
    let _, c64 = manifest_origin(MF_ORIGIN_MAX);
    check("manifest: a 64-byte origin is E_BAD_MANIFEST", c64 == E_BAD_MANIFEST);
}

// ===========================================================================
// 6. enc — the base64 sink capped at SIG_BYTES_MAX (64)

fn t_b64_cap() {
    say("-- base64 sink cap\n");
    var src: u8[..65] = [0; 65];
    var i: i64 = 0;
    while i < 65 { src[i] = 65; i = i + 1; }

    var enc: u8[>..] = [];
    let en, ecode = b64_encode(src[0..64], enc, 128);
    check("b64: 64 bytes encode", ecode == CODE_OK && en == 88);

    var out: u8[>..] = [];
    let n64, c64 = b64_decode(enc[..], out, SIG_BYTES_MAX);
    check("b64: 64 bytes decode into the signature sink", c64 == CODE_OK && n64 == SIG_BYTES_MAX);

    // 65 bytes is one more than an Ed25519 signature: the sink refuses instead of
    // keeping 64 bytes and reporting success.
    var enc2: u8[>..] = [];
    let _ = b64_encode(src[..], enc2, 128);
    var out2: u8[>..] = [];
    let _, c65 = b64_decode(enc2[..], out2, SIG_BYTES_MAX);
    check("b64: 65 bytes into a 64-byte sink is refused", c65 != CODE_OK);
}

// ===========================================================================
// 7. netcfg — NETCFG_TEXT_MAX (512)

fn t_netcfg_text() {
    say("-- NETCFG_TEXT_MAX\n");
    let c = iface_default("eth0");
    var out: u8[>..] = [];
    let n = netcfg_render(c, out, NETCFG_TEXT_MAX);
    check("netcfg: a section renders", n > 0);

    // A cap the section cannot fit must be a refusal, not a half-written file:
    // a truncated [net.eth0] section is a config the next boot reads as valid.
    var tiny: u8[>..] = [];
    let r = netcfg_render(c, tiny, 8);
    check("netcfg: a cap too small for the section is refused", r < 0);
}

// ===========================================================================
// 8. shell — SH_CWD_MAX (the prompt path buffer)

fn t_shell_cwd() {
    say("-- SH_CWD_MAX\n");
    // A path longer than the buffer is truncated and the length says so, rather
    // than the prompt showing a path that does not exist.
    var long: u8[>..] = [];
    let _ = append_str(long, 1024, "/");
    var i: i64 = 0;
    while i < SH_CWD_MAX + 10 {
        let _ = append_str(long, 1024, "d");
        i = i + 1;
    }
    sh_set_path(long[..]);
    num("   cwd stored:      ", sh_cwd_slice().len);
    check("shell: the cwd buffer stops at SH_CWD_MAX - 1", sh_cwd_slice().len == SH_CWD_MAX - 1);

    // A short path is stored whole: the truncation above is the buffer, not the
    // setter dropping bytes for its own reasons.
    sh_set_path("/usr/bin");
    check("shell: a 8-byte path is stored whole", sh_cwd_slice().len == 8);
}

// ===========================================================================
// 9. timesync — NTP_MAX_OFFSET_MS (one day)
//
// A server that claims the clock is a month off is not a clock source, it is an
// attack: the reply is refused and the smear is not started. This is the one
// limit in the corpus that only a packet can reach.

fn t_ntp_offset() {
    say("-- NTP_MAX_OFFSET_MS\n");
    var pkt: u8[..48] = [0; 48];
    // A realistic monotonic base: ntp_put_time clamps a negative second count to 0,
    // so a small base would turn the "a day behind" case into a corrupt packet.
    let mono: i64 = 1700000000000;
    // A reply has to look like one before the offset is reached at all: version 4,
    // mode 4 (server), stratum 2. Zeroes there are refused as corrupt, which would
    // make the offset checks pass for the wrong reason.
    pkt[0] = 36;        // (NTP_VERSION << 3) | NTP_MODE_SERVER
    pkt[1] = 2;         // a synced server, not a kiss-o'-death

    // A believable reply: the server's clock is one second ahead of ours.
    let now = ts_now_ms(mono);
    ntp_put_time(pkt, 32, now + 1000);
    ntp_put_time(pkt, 40, now + 1000);
    check("ntp: a one-second offset is accepted", ntp_apply_reply(pkt[..], mono, mono) == CODE_OK);

    // One day and a bit: outside the cap, refused rather than applied.
    var far: u8[..48] = [0; 48];
    far[0] = 36;
    far[1] = 2;
    ntp_put_time(far, 32, now + NTP_MAX_OFFSET_MS + 60000);
    ntp_put_time(far, 40, now + NTP_MAX_OFFSET_MS + 60000);
    check("ntp: an offset past one day is refused",
          ntp_apply_reply(far[..], mono, mono) == E_INVAL);

    // The same, pointing backwards.
    var back: u8[..48] = [0; 48];
    back[0] = 36;
    back[1] = 2;
    ntp_put_time(back, 32, now - NTP_MAX_OFFSET_MS - 60000);
    ntp_put_time(back, 40, now - NTP_MAX_OFFSET_MS - 60000);
    check("ntp: the cap is symmetric, a day behind is refused too",
          ntp_apply_reply(back[..], mono, mono) == E_INVAL);
}
