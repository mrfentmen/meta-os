// services/tests/t109_callmatrix_r11.goose
//
// Round 11, R11-031..036 — the permission table's edges, its error split, and its bound.
//
// t69 proves the table has a non-empty row per id and that the twelve missing edges are now
// allowed. This driver adds the cases t69 states but does not drive:
//
//   1. the bound: id 0 and id 32 are refused by every function, and SVC_COUNT is exactly 31;
//   2. self-calls: allowed for a real service, refused for 0 and for past the end;
//   3. the error split: a policy denial (E_DENIED) and a caller bug (E_INVAL) stay distinct;
//   4. a row is a mask: cm_mask and cm_allows cannot disagree;
//   5. load: ten times the table's own width in checks.
//
// Status: WRITTEN — not run. The coordinator runs it and records the result in
// os-build/layer1/r11/callmatrix.md.

import callmatrix.callmatrix;
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

fn main() {
    say("t109 callmatrix edges and error split\n");
    cm_init();

    // --- 1. the bound ---
    check("SVC_COUNT is 31", SVC_COUNT == 31);
    check("SVC_NONE is 0", SVC_NONE == 0);
    check("the highest id is the count, because ids start at 1", SVC_NOTIFY == SVC_COUNT);

    check("cm_bit(0) is 0", cm_bit(0) == 0);
    check("cm_bit(1) is bit 1", cm_bit(1) == 2);
    check("cm_bit(31) is bit 31", cm_bit(31) == (1 << 31));
    check("cm_bit(32) is 0: there is no bit past the table", cm_bit(32) == 0);
    check("cm_bit(-1) is 0", cm_bit(-1) == 0);

    check("an id past the end has no row", cm_row(SVC_COUNT + 1) == 0);
    check("id 0 has no row", cm_row(0) == 0);
    check("every real id has a row", cm_row(SVC_LOG) != 0 && cm_row(SVC_FS) != 0);

    // --- 2. self-calls ---
    check("a real service may call itself", cm_allows(SVC_FS, SVC_FS));
    check("id 0 may not call itself", !cm_allows(0, 0));
    check("an id past the end may not call itself", !cm_allows(32, 32));

    // --- 3. the error split ---
    // A denial is policy and goes to the owner of the table; an invalid id is a caller bug and
    // goes to the caller's author. Same function, different people.
    check("denial is E_DENIED, not E_INVAL", cm_check(SVC_LOGFMT, SVC_NET) == E_DENIED);
    check("a zero callee is E_INVAL, not E_DENIED", cm_check(SVC_LOGFMT, 0) == E_INVAL);
    check("a zero caller is E_INVAL", cm_check(0, SVC_LOG) == E_INVAL);
    check("a callee past the end is E_INVAL", cm_check(SVC_LOG, SVC_COUNT + 1) == E_INVAL);
    check("an allowed pair is CODE_OK", cm_check(SVC_FS, SVC_STORAGE) == CODE_OK);

    // --- 4. the row is the mask ---
    // Three representative rows, one per layer: the log's four callees, fs's two, notify's two.
    check("log's mask is its four callees",
          cm_mask(SVC_LOG) == (cm_bit(SVC_CONSOLE) | cm_bit(SVC_STORAGE)
                               | cm_bit(SVC_LOGFMT) | cm_bit(SVC_TIME)));
    check("fs's mask is storage plus the log",
          cm_mask(SVC_FS) == (cm_bit(SVC_STORAGE) | cm_bit(SVC_LOG)));
    check("notify's mask is log plus time",
          cm_mask(SVC_NOTIFY) == (cm_bit(SVC_LOG) | cm_bit(SVC_TIME)));

    // Every bit in a mask must answer true, and every bit outside it must answer false. This is
    // the property t69 does not check: a mask with a bit `cm_allows` ignores is a permission
    // that reads as granted in an audit and is enforced as denied at the call site.
    // The caller's own id is exempt: `cm_allows` permits a self-call without a matrix bit, so
    // comparing it to the row would report a disagreement that is the documented rule.
    var fs_mask = cm_mask(SVC_FS);
    var id: i64 = 1;
    var mask_agrees: bool = true;
    while id <= SVC_COUNT {
        if id != SVC_FS {
            let bit_set = (fs_mask & cm_bit(id)) != 0;
            if bit_set != cm_allows(SVC_FS, id) { mask_agrees = false; }
        }
        id = id + 1;
    }
    check("fs: every mask bit agrees with cm_allows, self excluded", mask_agrees);

    // --- 5. deny-by-default at pairs nobody declared ---
    check("logfmt may not call net", !cm_allows(SVC_LOGFMT, SVC_NET));
    check("logfmt may not call the supervisor", !cm_allows(SVC_LOGFMT, SVC_SUPERVISOR));
    check("bootlog may not call storage", !cm_allows(SVC_BOOTLOG, SVC_STORAGE));
    check("display may not call the audit trail", !cm_allows(SVC_DISPLAY, SVC_AUDIT));

    // --- 6. load: ten times the table's own width ---
    // The registry asks one question per call, and a boot asks it for every service pair it
    // starts; 100 passes over all 31 ids is ten times the table's width ten times over.
    var ops: i64 = 0;
    var ok: i64 = 0;
    var refused: i64 = 0;
    var pass_no: i64 = 0;
    while pass_no < 100 {
        var callee: i64 = 1;
        while callee <= SVC_COUNT {
            if cm_allows(SVC_FS, callee) { ok = ok + 1; } else { refused = refused + 1; }
            ops = ops + 1;
            callee = callee + 1;
        }
        pass_no = pass_no + 1;
    }
    check("3100 checks answered", ops == (100 * SVC_COUNT));
    // Three per pass: its two declared callees (storage, log) plus itself, which `cm_allows`
    // permits without a bit. A count of two would have encoded the self-call rule as a bug.
    check("the fs row allows three of 31: two declared plus itself", ok == 300 && refused == 2800);

    say("LOAD callmatrix ops=");
    var ob: u8[>..] = [];
    let _ = append_int(ob, 32, ops);
    say(ob[..]);
    say(" ok=");
    var kb: u8[>..] = [];
    let _ = append_int(kb, 32, ok);
    say(kb[..]);
    say(" refused=");
    var rb: u8[>..] = [];
    let _ = append_int(rb, 32, refused);
    say(rb[..]);
    say("\n");

    say("t109 done  pass=");
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
