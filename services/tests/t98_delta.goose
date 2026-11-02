// services/tests/t98_delta.goose
//
// The updater's component deltas (B-L1-122): plan, apply, verify, and the format's edge.
//
// WHY THIS FILE EXISTS
// --------------------
// `delta_plan`, `delta_verify`, `delta_ops_max`, `delta_op_name` and `delta_plan_line` were all
// listed by the dead-code census as functions nothing calls. The risk in a delta is not that it
// fails to apply -- it is that it applies *wrongly*, produces bytes that are one byte short, and
// the machine is written with them anyway. So the driver checks the refusals as hard as the
// success path: base that does not match, offset past the base, literal past the pool, unknown
// operation kind, output shorter than the declared length.
//
// Status: RUNS — set by `audit_status.py` from the runner's row, not by hand.

import updater.delta;
import updater.updater;
import common.err.err;
import common.fmt.fmt;
import common.hash.hash;
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

fn lit(s: const u8[:], out: u8[>..]&) -> i64 {
    var i: i64 = 0;
    while i < s.len { out.push(s[i]); i = i + 1; }
    return s.len;
}

fn same_len(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

// A distinguishable digest, so "equal" is not a coincidence of zeros. Returned whole because a
// fixed-width array cannot be handed to a helper as a reference and written in place.
fn digest_of(seed: u8) -> u8[..32] {
    var d: u8[..32] = [0; 32];
    var i: i64 = 0;
    while i < 32 {
        d[i] = seed + (i as u8);
        i = i + 1;
    }
    return d;
}

fn empty_file(path: const u8[:]) -> DeltaFile {
    var f: DeltaFile = DeltaFile {
        path: [0; 32],
        path_len: 0,
        base_len: 0,
        base_digest: [0; 32],
        new_len: 0,
        new_digest: [0; 32],
        ops: [DeltaOp { .. }; 4],
        nops: 0,
    };
    var i: i64 = 0;
    while i < path.len && i < 32 {
        f.path[i] = path[i];
        i = i + 1;
    }
    f.path_len = path.len;
    return f;
}

fn op(kind: i64, from_off: i64, from_len: i64, fill: i64, lit_off: i64, lit_len: i64) -> DeltaOp {
    return DeltaOp { kind: kind, from_off: from_off, from_len: from_len, fill: fill, lit_off: lit_off, lit_len: lit_len };
}

fn main() {
    say("t98 updater delta\n");

    // ======================================================================
    // 1. the format's own words
    // ======================================================================
    check("delta_ops_max: four operations per component", delta_ops_max() == 4);
    check("delta_op_name: copy", same_len(delta_op_name(0), "copy"[..4]));
    check("delta_op_name: literal", same_len(delta_op_name(1), "literal"[..7]));
    check("delta_op_name: fill", same_len(delta_op_name(2), "fill"[..4]));
    check("delta_op_name: an unknown kind is not given a name", same_len(delta_op_name(9), "?"[..1]));

    // ======================================================================
    // 2. one file, applied: copy, literal, fill, in that order
    // ======================================================================
    // base "abcdefgh" -> "abcde" + "XY" + "z"
    var base: u8[>..] = [];
    let _bn = lit("abcdefgh", base);

    var content: u8[>..] = [];
    let cn = lit("abcdeXYz", content);

    var pool: u8[>..] = [];
    let _pn = lit("XY", pool);

    var f = empty_file("vmlinuz");
    f.base_len = 8;
    f.new_len = 8;
    f.base_digest = digest_of(0x10);
    f.new_digest = digest_of(0x20);           // replaced below with the real digest
    f.nops = 3;
    f.ops[0] = op(DL_COPY, 0, 5, 0, 0, 0);
    f.ops[1] = op(DL_LITERAL, 0, 0, 0, 0, 2);
    f.ops[2] = op(DL_FILL, 0, 1, 0x7A, 0, 0);   // 'z'

    var out: u8[>..] = [];
    let produced, ac = delta_apply(f, base[..], pool[..], out, 64);
    check("delta_apply: the operations produce the new bytes", ac == CODE_OK && produced == 8);
    check("delta_apply: the bytes are right", out.len == 8 && out[0] == 0x61 && out[4] == 0x65
          && out[5] == 0x58 && out[6] == 0x59 && out[7] == 0x7A);

    // The declared length is checked against what the operations actually produced: a delta
    // that stops one byte early must not be accepted for a longer file.
    var short = f;
    short.new_len = 9;
    var out2: u8[>..] = [];
    let _, shortc = delta_apply(short, base[..], pool[..], out2, 64);
    check("delta_apply: output shorter than the declared length is corrupt", shortc == E_CORRUPT);

    // The base must be exactly the base: a file of the wrong length is not a candidate.
    var out3: u8[>..] = [];
    let _, wrongbase = delta_apply(f, base[..5], pool[..], out3, 64);
    check("delta_apply: a base of the wrong length is refused", wrongbase == E_ROLLBACK);

    // Capacity is checked before every write, so a slot that cannot hold the result is not
    // half-written.
    var out4: u8[>..] = [];
    let _, capc = delta_apply(f, base[..], pool[..], out4, 4);
    check("delta_apply: a slot too small for the result is refused", capc == E_NOROOM);

    // ======================================================================
    // 3. a delta is data from outside: every offset is checked
    // ======================================================================
    var over = f;
    over.ops[0] = op(DL_COPY, 6, 5, 0, 0, 0);     // 6+5 > 8
    var o5: u8[>..] = [];
    let _, overc = delta_apply(over, base[..], pool[..], o5, 64);
    check("delta_apply: a copy past the end of the base is corrupt", overc == E_CORRUPT);

    var negative = f;
    negative.ops[0] = op(DL_COPY, -1, 2, 0, 0, 0);
    var o6: u8[>..] = [];
    let _, negc = delta_apply(negative, base[..], pool[..], o6, 64);
    check("delta_apply: a negative source offset is corrupt", negc == E_CORRUPT);

    var badlit = f;
    badlit.ops[1] = op(DL_LITERAL, 0, 0, 0, 1, 4);   // pool holds 2 bytes
    var o7: u8[>..] = [];
    let _, badlitc = delta_apply(badlit, base[..], pool[..], o7, 64);
    check("delta_apply: a literal past the pool is corrupt", badlitc == E_CORRUPT);

    var unknown = f;
    unknown.ops[2] = op(9, 0, 1, 0, 0, 0);
    var o8: u8[>..] = [];
    let _, unkc = delta_apply(unknown, base[..], pool[..], o8, 64);
    check("delta_apply: an unknown operation is refused, not ignored", unkc == E_UNSUPPORTED);

    // ======================================================================
    // 4. verify: the digest is what the caller writes on
    // ======================================================================
    // A real digest of the produced bytes, so this is the true positive case rather than a
    // comparison against a digest that was itself made up.
    var good: u8[>..] = [];
    if !sha256(content[..], good, 32) { say("     sha256 failed\n"); }
    var gi: i64 = 0;
    while gi < 32 {
        f.new_digest[gi] = good[gi];
        gi = gi + 1;
    }
    var got: u8[..32] = [0; 32];
    check("delta_verify: the produced bytes match the declared digest",
          delta_verify(f, content[..], got) == CODE_OK);
    check("delta_verify: the digest is handed back to the caller", good.len == 32 && same_len(got[..32], good[..32]));

    var tampered: u8[>..] = [];
    let _tn = lit("abcdeXYy", tampered);           // one byte changed
    var got2: u8[..32] = [0; 32];
    check("delta_verify: one changed byte fails verification",
          delta_verify(f, tampered[..], got2) == E_VERIFY);

    // ======================================================================
    // 5. plan: what it promises the caller
    // ======================================================================
    // Fixed-width arrays must be given a value at declaration: the compiler refuses a table it
    // cannot prove is initialised, which is the right answer for a manifest.
    var files: DeltaFile[..8] = [DeltaFile { .. }; 8];
    var lens: i64[..8] = [0; 8];
    var digs: u8[..32][..8] = [[0; 32]; 8];

    files[0] = f;
    lens[0] = 8;
    digs[0] = f.base_digest;

    var second = empty_file("initrd");
    second.base_len = 4;
    second.new_len = 4;
    second.base_digest = digest_of(0x30);
    second.nops = 1;
    second.ops[0] = op(DL_LITERAL, 0, 0, 0, 0, 2);
    files[1] = second;
    lens[1] = 4;
    digs[1] = digest_of(0x30);

    let p, pc = delta_plan(files, 2, lens, digs, 1);
    check("delta_plan: a matching base plans a write and a reboot", pc == CODE_OK
          && p.action == UPD_APPLY_REBOOT && p.slot == 1 && p.files == 2);
    check("delta_plan: nothing refused", p.refused == 0);
    check("delta_plan: bytes to write is the sum of the new lengths", p.bytes_to_write == 12);
    check("delta_plan: bytes shipped is the literal pool only", p.bytes_shipped == 4);
    check("delta_plan: savings is the difference", p.savings == 8);

    var want: u8[>..] = [];
    let wl = lit("delta plan: slot=1 files=2 write=12 ship=4 saved=8 refused=0", want);
    var line: u8[>..] = [];
    var pl = delta_plan_line(p, line, 256);
    check("delta_plan_line: the exact plan line", pl && line.len == wl
          && same_len(line[..], want[..]));

    // A plan with a refused component still returns the numbers, so the log can name what
    // moved -- but the code says it must not be applied.
    lens[1] = 5;
    let pr, prc = delta_plan(files, 2, lens, digs, 1);
    check("delta_plan: a mismatched base length is refused", prc == E_ROLLBACK && pr.refused == 1);
    check("delta_plan: a refused plan is not an apply", pr.action == UPD_APPLY_NONE);
    check("delta_plan: a refused plan still reports the whole size",
          pr.bytes_to_write == 12 && pr.savings == 8);

    lens[1] = 4;
    digs[1] = digest_of(0x31);                     // right length, wrong bytes
    let pd, pdc = delta_plan(files, 2, lens, digs, 1);
    check("delta_plan: a mismatched base digest is refused", pdc == E_ROLLBACK && pd.refused == 1);

    let pzero, pzeroc = delta_plan(files, 0, lens, digs, 0);
    check("delta_plan: no files is not a plan", pzeroc == E_INVAL);
    let pover, poverc = delta_plan(files, 9, lens, digs, 0);
    check("delta_plan: more files than the manifest allows is refused", poverc == E_NOROOM);

    say("t98 done  pass=");
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
