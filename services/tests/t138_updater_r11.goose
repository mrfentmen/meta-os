// services/tests/t138_updater_r11.goose
//
// Round 11, updater (R11-205..210): the plan's premises, the record's refusals, and the
// history cap.
//
// The earlier drivers: t58 proves a manifest parses and a record encodes; t79/t80 drive the
// limit constants. This one is about what the updater REFUSES and why — a manifest with one
// bad line, a plan that would overwrite the running slot, a record with a torn header — and
// about the in-memory history keeping only the newest four, with the safe slot coming from
// the newest CONFIRMED record and never from a guess.
//
// Digest values here are format-shaped, not the digest of the content: this driver tests
// refusal and record structure, not SHA-256 (that is t58's job).
//
// Status: RUNS after the coordinator's native run; written 2026-11-02.

import updater.updater;
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

fn lit(s: const u8[:], out: u8[..4096]&) -> i64 {
    if s.len > 4096 { return -1; }
    var i: i64 = 0;
    while i < s.len { out[i] = s[i]; i = i + 1; }
    return s.len;
}

fn main() {
    say("t138 updater r11\n");

    var text: u8[..4096] = [0; 4096];
    var n: i64 = 0;

    // ======================================================================
    // 1. a well-formed manifest, and the plan it justifies
    // ======================================================================
    n = lit("version = 0.2.0\norigin = https://updates.invalid/meta-os\nslot = b\nfile = bin/console.c 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 18432\n", text);
    var m, mcode = upd_parse_manifest(text[..n]);
    check("parse: a clean manifest is accepted", mcode == CODE_OK);
    check("parse: version is five bytes", m.version_len == 5);
    check("parse: slot b is SLOT_B", m.slot == SLOT_B);
    check("parse: one file", m.count == 1);
    check("parse: the size is the decimal on the line", m.files[0].size == 18432);
    check("parse: the digest became 32 bytes", m.files[0].digest_len == MF_DIGEST_BYTES);

    var plan, pcode = upd_plan(m, SLOT_A);
    check("plan: inactive slot is writable", pcode == CODE_OK);
    check("plan: action is SLOT", plan.action == UPD_APPLY_SLOT);
    check("plan: target is the manifest's slot", plan.target_slot == SLOT_B);
    check("plan: bytes are the sum", plan.bytes == 18432);
    check("plan: one file", plan.files == 1);

    let _, same_slot = upd_plan(m, SLOT_B);
    check("plan: installing over the running slot is E_STATE", same_slot == E_STATE);
    let _, bad_active = upd_plan(m, 7);
    check("plan: an active slot that is neither A nor B is E_INVAL", bad_active == E_INVAL);

    // A zero-byte file parses and then cannot be planned: parse checks shape, plan checks
    // that there is something to write.
    n = lit("version = 1\nslot = b\nfile = a 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 0\n", text);
    var zm, zmc = upd_parse_manifest(text[..n]);
    check("parse: a zero-byte file is shape-legal", zmc == CODE_OK);
    let _, zpc = upd_plan(zm, SLOT_A);
    check("plan: a zero-byte file is E_BAD_MANIFEST", zpc == E_BAD_MANIFEST);

    // ======================================================================
    // 2. one bad line rejects the whole document
    // ======================================================================
    n = lit("version = 1\nslot = b\nlicense = mit\nfile = a 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 1\n", text);
    let _, c_unknown = upd_parse_manifest(text[..n]);
    check("refuse: an unknown key", c_unknown == E_BAD_MANIFEST);

    n = lit("version = 1\nslot = b\nthis line has no equals\n", text);
    let _, c_noeq = upd_parse_manifest(text[..n]);
    check("refuse: a line with no '='", c_noeq == E_BAD_MANIFEST);

    n = lit("version = 1\nslot = b\nfile = a 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 1\nfile = a 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 1\n", text);
    let _, c_dup = upd_parse_manifest(text[..n]);
    check("refuse: a duplicate path", c_dup == E_BAD_MANIFEST);

    n = lit("version = 1\nslot = b\nfile = ../etc/passwd 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 1\n", text);
    let _, c_dotdot = upd_parse_manifest(text[..n]);
    check("refuse: a path containing '..'", c_dotdot == E_BAD_MANIFEST);

    n = lit("version = 1\nslot = b\nfile = aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 1\n", text);
    let _, c_longpath = upd_parse_manifest(text[..n]);
    check("refuse: a path at MF_PATH_MAX (32) is one too many", c_longpath == E_BAD_MANIFEST);

    n = lit("version = 1\nslot = b\nfile = a 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a0 1\n", text);
    let _, c_shorthex = upd_parse_manifest(text[..n]);
    check("refuse: a 63-character digest", c_shorthex == E_BAD_MANIFEST);

    n = lit("version = 1\nslot = b\nfile = a 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 12x\n", text);
    let _, c_badsize = upd_parse_manifest(text[..n]);
    check("refuse: a size that is not decimal", c_badsize == E_BAD_MANIFEST);

    n = lit("version = 1\nfile = a 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 1\n", text);
    let _, c_noslot = upd_parse_manifest(text[..n]);
    check("refuse: no slot", c_noslot == E_BAD_MANIFEST);

    n = lit("slot = b\nfile = a 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 1\n", text);
    let _, c_nover = upd_parse_manifest(text[..n]);
    check("refuse: no version", c_nover == E_BAD_MANIFEST);

    n = lit("version = 1\nslot = b\n", text);
    let _, c_nofile = upd_parse_manifest(text[..n]);
    check("refuse: no file", c_nofile == E_BAD_MANIFEST);

    n = lit("version = 1234567890123456\nslot = b\nfile = a 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 1\n", text);
    let _, c_longver = upd_parse_manifest(text[..n]);
    check("refuse: a version at MF_VERSION_MAX (16) is one too many", c_longver == E_BAD_MANIFEST);

    n = lit("version = 1\norigin = \nslot = b\nfile = a 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 1\n", text);
    let _, c_noorigin = upd_parse_manifest(text[..n]);
    check("refuse: an empty origin", c_noorigin == E_BAD_MANIFEST);

    n = lit("version = 1\nslot = b\nfile = a 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 1\nfile = b 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 1\nfile = c 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 1\nfile = d 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 1\nfile = e 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 1\nfile = f 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 1\nfile = g 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 1\nfile = h 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 1\nfile = i 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 1\n", text);
    let _, c_ninth = upd_parse_manifest(text[..n]);
    check("refuse: a ninth file at MF_MAX_FILES (8)", c_ninth == E_BAD_MANIFEST);

    // ======================================================================
    // 3. verification refuses before it hashes when the size is wrong
    // ======================================================================
    var vcs: ContentSet = ContentSet { .. };
    vcs.len[0] = 3;
    vcs.slots[0] = 0x61;
    vcs.slots[1] = 0x62;
    vcs.slots[2] = 0x63;
    var abc: u8[..3] = [0; 3];
    abc[0] = 0x61;
    abc[1] = 0x62;
    abc[2] = 0x63;
    let vcode = upd_verify_file(m, 0, abc[..]);
    check("verify: a 3-byte body for an 18432-byte file is E_VERIFY", vcode == E_VERIFY);
    let vind = upd_verify_file(m, 5, abc[..]);
    check("verify: an index past the count is E_INVAL", vind == E_INVAL);
    let _, vac = upd_verify_all(m, vcs);
    check("verify_all: the size refusal surfaces as E_VERIFY", vac == E_VERIFY);

    // ======================================================================
    // 4. the record: encode, decode, and every way a torn block is refused
    // ======================================================================
    var rec = upd_record_make(plan, 1234);
    check("record: the writer never confirms its own write", rec.state == R_PENDING);
    check("record: it carries the plan's target", rec.slot == SLOT_B && rec.files == 1
          && rec.bytes == 18432);
    check("record: the version is carried", rec.version_len == 5);

    var blk: u8[..512] = [0; 512];
    check("record: encodes to 512 bytes", upd_record_encode(rec, blk) == UPD_REC_BYTES);
    check("record: the magic is MOSU", blk[0] == 0x4D && blk[1] == 0x4F
          && blk[2] == 0x53 && blk[3] == 0x55);

    var out: UpdRecord = UpdRecord { seq: 0, state: 0, slot: 0, version: [0; 16],
                                     version_len: 0, files: 0, bytes: 0, applied_ms: 0 };
    check("record: decodes", upd_record_decode(blk[..], out) == CODE_OK);
    check("record: every field survives the round trip",
          out.seq == rec.seq && out.state == R_PENDING && out.slot == SLOT_B
          && out.files == 1 && out.bytes == 18432 && out.applied_ms == 1234
          && out.version_len == 5);

    var blk2: u8[..512] = [0; 512];
    var i: i64 = 0;
    while i < 512 { blk2[i] = blk[i]; i = i + 1; }
    blk2[0] = 0;
    check("refuse: a block without the magic is E_CORRUPT",
          upd_record_decode(blk2[..], out) == E_CORRUPT);

    i = 0;
    while i < 512 { blk2[i] = blk[i]; i = i + 1; }
    blk2[10] = blk2[10] + 1;
    check("refuse: one changed header byte is E_CORRUPT (torn write)",
          upd_record_decode(blk2[..], out) == E_CORRUPT);

    var shortblk: u8[..100] = [0; 100];
    check("refuse: a block shorter than 512 bytes is E_CORRUPT",
          upd_record_decode(shortblk[..], out) == E_CORRUPT);

    // ======================================================================
    // 5. history: four records, newest confirmed wins, no record means no guess
    // ======================================================================
    check("history: starts empty", upd_record_count() == 0);
    var p: i64 = 0;
    while p < 5 {
        var r = upd_record_make(plan, p);
        upd_record_push(r);
        p = p + 1;
    }
    check("history: keeps exactly UPD_REC_KEEP (4)", upd_record_count() == UPD_REC_KEEP);
    check("history: a PENDING record is not a safe slot", upd_record_safe_slot() == SLOT_NONE);

    let _ = upd_record_confirm(SLOT_A, 100);
    check("history: a CONFIRMED record names the safe slot", upd_record_safe_slot() == SLOT_A);
    let _ = upd_record_confirm(SLOT_B, 200);
    check("history: the newest CONFIRMED wins", upd_record_safe_slot() == SLOT_B);

    // ======================================================================
    // 6. load: 100 manifests, half of them one bad line
    // ======================================================================
    var ops: i64 = 0;
    var okc: i64 = 0;
    var refused: i64 = 0;
    var k: i64 = 0;
    while k < 100 {
        if k % 2 == 0 {
            n = lit("version = 1\nslot = b\nfile = a 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 8\n", text);
            let _, lc = upd_parse_manifest(text[..n]);
            if lc == CODE_OK { okc = okc + 1; } else { refused = refused + 1; }
        } else {
            n = lit("version = 1\nslot = b\nlicense = mit\n", text);
            let _, bc = upd_parse_manifest(text[..n]);
            if bc == E_BAD_MANIFEST { refused = refused + 1; } else { okc = okc + 1; }
        }
        ops = ops + 1;
        k = k + 1;
    }
    check("load: 50 accepted and 50 refused, on purpose", okc == 50 && refused == 50);

    say("LOAD updater ops=");
    var ob: u8[>..] = [];
    let _ = append_int(ob, 32, ops);
    say(ob[..]);
    say(" ok=");
    var kb: u8[>..] = [];
    let _ = append_int(kb, 32, okc);
    say(kb[..]);
    say(" refused=");
    var rb: u8[>..] = [];
    let _ = append_int(rb, 32, refused);
    say(rb[..]);
    say("\n");

    say("t138 done  pass=");
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
