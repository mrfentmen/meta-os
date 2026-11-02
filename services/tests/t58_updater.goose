// services/tests/t58_updater.goose
//
// B-L1-58 — test program for the update manifest, the apply plan and the rollback record
// (B-L1-34/B-L1-35/B-L1-36). PLAN ONLY: nothing here applies an update.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// THE POINT OF THIS TEST
// ----------------------
// An updater is the one service whose bugs brick a machine far from help, so its refusals are
// the contract and they are tested first:
//   - a manifest entry with `..` in the path (escaping the update root) is refused;
//   - two entries for one path are refused (an added line would choose what gets installed);
//   - a plan that targets the RUNNING slot is refused (that is what removes the fallback);
//   - a rollback record whose header does not checksum is refused, not read anyway.
//
// Then the positive path: the content really is hashed and matched against the manifest, and
// a single changed byte fails verification. That is the difference between "we checked" and
// "we looked at it".

import updater.updater;
import common.hash.hash;
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

fn main() {
    say("t58 updater plan + rollback\n");

    // The content this "update" carries, and its digest, computed rather than pasted: a
    // pasted digest would test the parser and skip the hash.
    let payload: const u8[:] = "abc";
    var digest: u8[>..] = [];
    check("digest computed", sha256(payload, digest, 32) && digest.len == 32);
    var hex: u8[>..] = [];
    check("digest rendered as hex", to_hex(digest, hex) && hex.len == 64);

    // --- build a manifest around those two facts ---
    var text: u8[>..] = [];
    push_str(text, "version=1.2.3\n");
    push_str(text, "origin=http://updates.invalid/stable\n");
    push_str(text, "slot=b\n");
    push_str(text, "file=kernel/main ");
    push_str(text, hex);
    push_str(text, " 3\n");

    var m, mcode = upd_parse_manifest(text);
    check("manifest parses", mcode == CODE_OK);
    check("version parsed", m.version_len == 5);
    check("one file", m.count == 1);
    check("target slot is b", m.slot == SLOT_B);
    check("file size", m.files[0].size == 3);
    check("digest is bytes, not text", m.files[0].digest_len == 32 && m.files[0].digest[0] == digest[0]);

    // --- refusals in the manifest ---
    var dotdot: u8[>..] = [];
    push_str(dotdot, "version=1\nslot=b\nfile=../../etc/passwd ");
    push_str(dotdot, hex);
    push_str(dotdot, " 3\n");
    var _, dd_code = upd_parse_manifest(dotdot);
    check("path traversal refused", dd_code == E_BAD_MANIFEST);

    var dup: u8[>..] = [];
    push_str(dup, "version=1\nslot=b\nfile=a ");
    push_str(dup, hex);
    push_str(dup, " 3\nfile=a ");
    push_str(dup, hex);
    push_str(dup, " 3\n");
    var _, dup_code = upd_parse_manifest(dup);
    check("duplicate path refused", dup_code == E_BAD_MANIFEST);

    var unknown: u8[>..] = [];
    push_str(unknown, "version=1\nslot=b\nexec=rm -rf /\n");
    var _, un_code = upd_parse_manifest(unknown);
    check("unknown key refused, not ignored", un_code == E_BAD_MANIFEST);

    var noslot: u8[>..] = [];
    push_str(noslot, "version=1\nfile=a ");
    push_str(noslot, hex);
    push_str(noslot, " 3\n");
    var _, ns_code = upd_parse_manifest(noslot);
    check("manifest without a slot refused", ns_code == E_BAD_MANIFEST);

    var baddigest: u8[>..] = [];
    push_str(baddigest, "version=1\nslot=b\nfile=a 00ff 3\n");
    var _, bd_code = upd_parse_manifest(baddigest);
    check("short digest refused", bd_code == E_BAD_MANIFEST);

    // --- verification against content ---
    var cs: ContentSet = ContentSet { slots: [], len: [] };
    cs.len[0] = 3;
    cs.slots[0] = 97;
    cs.slots[1] = 98;
    cs.slots[2] = 99;

    let verified, vcode = upd_verify_all(m, cs);
    check("content verifies", vcode == CODE_OK && verified == 1);

    // A single changed byte must fail: this is the assertion that makes the updater an
    // updater rather than a downloader.
    cs.slots[2] = 100;
    let v2, v2code = upd_verify_all(m, cs);
    check("tampered content refused", v2code != CODE_OK && v2 == 0);

    // --- the apply plan ---
    var plan, pcode = upd_plan(m, SLOT_A);
    check("plan built", pcode == CODE_OK);
    check("plan writes the inactive slot", plan.action == UPD_APPLY_SLOT && plan.target_slot == SLOT_B);
    check("plan counts files and bytes", plan.files == 1 && plan.bytes == 3);
    check("plan records the active slot", plan.active_slot == SLOT_A);
    check("plan carries the version", plan.version_len == 5);

    let _, same_code = upd_plan(m, SLOT_B);
    check("plan onto the running slot refused", same_code == E_STATE);

    let _, bad_slot = upd_plan(m, 7);
    check("plan with an unknown active slot refused", bad_slot == E_INVAL);

    // --- the rollback record ---
    // Written BEFORE anything is applied: a record written afterwards cannot describe a
    // crash in the middle.
    let rec = upd_record_make(plan, 12345);
    check("record is pending, never confirmed", rec.state == R_PENDING);
    check("record names the target slot", rec.slot == SLOT_B);
    check("record counts what will be written", rec.files == 1 && rec.bytes == 3);

    var blk: u8[..512] = [];
    check("record encodes to a blk", upd_record_encode(rec, blk) == UPD_REC_BYTES);
    check("record has a magic", blk[0] == 0x4D && blk[3] == 0x55);

    var back: UpdRecord = UpdRecord {
        seq: 0,
        state: 0,
        slot: 0,
        version: [],
        version_len: 0,
        files: 0,
        bytes: 0,
        applied_ms: 0,
    };
    check("record decodes", upd_record_decode(blk, back) == CODE_OK);
    check("decoded slot matches", back.slot == SLOT_B);
    check("decoded seq matches", back.seq == rec.seq);
    check("decoded bytes match", back.bytes == 3);
    check("decoded timestamp matches", back.applied_ms == 12345);

    // A torn write is caught by the checksum rather than believed.
    blk[12] = (blk[12] + 1) as u8;      // flip the slot field
    var torn: UpdRecord = UpdRecord {
        seq: 0,
        state: 0,
        slot: 0,
        version: [],
        version_len: 0,
        files: 0,
        bytes: 0,
        applied_ms: 0,
    };
    check("corrupt record refused", upd_record_decode(blk, torn) != CODE_OK);

    // A blk with the wrong magic is not our record, whatever the rest says.
    var other: u8[..512] = [];
    check("record decodes from a reset blk?", upd_record_decode(other, torn) != CODE_OK);

    // --- the record is not the plan: nothing applied ---
    // Stated as an assertion so a future edit that "helpfully" writes the slot here fails.
    check("plan action is not APPLY_REBOOT (nothing self-modifies)",
        plan.action != UPD_APPLY_REBOOT);

    var r: u8[>..] = [];
    let _ = append_int(r, 32, t_pass);
    say("passed ");
    say(r);
    say("\n");
    if t_fail != 0 { say("FAILURES\n"); sys_exit(1); }
    say("t58 done\n");
    sys_exit(0);
}

fn push_str(b: u8[>..]&, s: const u8[:]) {
    var i: i64 = 0;
    while i < s.len {
        b.push(s[i]);
        i = i + 1;
    }
}

// Lowercase hex, because the manifest grammar requires exactly 64 lowercase-or-uppercase hex
// characters and a mismatch there reads as "malformed update" rather than "test bug".
fn to_hex(b: const u8[:], out: u8[>..]&) -> bool {
    if b.len != 32 { return false; }
    var i: i64 = 0;
    while i < b.len {
        let v = b[i] as i64;
        out.push(NIB[(v >> 4) & 0xF]);
        out.push(NIB[v & 0xF]);
        i = i + 1;
    }
    return true;
}

let NIB: const u8[:] = "0123456789abcdef";
