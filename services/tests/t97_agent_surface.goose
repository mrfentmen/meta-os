// services/tests/t97_agent_surface.goose
//
// The agent host's limits and lines: the quota table (B-L1-116), the channel's reporting
// surface (B-L1-117), and the stop/down-line wrappers on the lifecycle.
//
// WHY THIS FILE EXISTS
// --------------------
// The dead-code census listed nine functions in `agenthost/quota.goose` and three in
// `agenthost/channel.goose` that nothing calls, plus `ah_stop` and `ah_down_line`. A quota table
// nothing charges is not a limit; it is a struct with numbers in it. This driver makes the
// limits real by asking for calls until the answer is `E_QUOTA`, and asserts the exact health
// line an operator reads, because a status line that drifts is worse than none.
//
// Status: RUNS — set by `audit_status.py` from the runner's row, not by hand.

import agenthost.agenthost;
import agenthost.quota;
import agenthost.channel;
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

fn lit(s: const u8[:], out: u8[..256]&) -> i64 {
    var i: i64 = 0;
    while i < s.len { out[i] = s[i]; i = i + 1; }
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

// Run a status writer into a growable buffer and hand back the line.
fn line_of(kind: i64, qs: Quotas&, c: Channel&, h: i64, out: u8[..256]&) -> i64 {
    var b: u8[>..] = [];
    if kind == 0 {
        if !quota_status(qs, h, b, 256) { return -1; }
    } else {
        if !ch_status(c, b, 256) { return -1; }
    }
    var i: i64 = 0;
    while i < b.len { out[i] = b[i]; i = i + 1; }
    return b.len;
}

fn main() {
    say("t97 agent host surface\n");

    // Two real agents: limits are keyed on handles the host resolves, so the table has to be
    // populated before any quota means anything.
    let a_h, a_c = ah_spawn("alpha", CAP_MSG | CAP_STORE_WRITE, 0);
    let b_h, b_c = ah_spawn("beta", CAP_MSG, 0);
    let c_h, c_c = ah_spawn("gamma", CAP_STORE_WRITE, 0);
    check("spawn: three agents", a_c == CODE_OK && b_c == CODE_OK && c_c == CODE_OK);
    ah_start(a_h, 0);
    ah_start(b_h, 0);
    ah_start(c_h, 0);

    // ======================================================================
    // 1. a quota attaches to a live handle, and only to a live one
    // ======================================================================
    var qs = quota_new();
    check("quota_new: an empty table", qs.count == 0);

    // A handle the host does not resolve is not a legal target. `ah_slot_of` only checks the
    // arithmetic range, so anything that used it here would accept a fabricated handle and
    // report a limit nobody is subject to.
    let bogus = quota_set(qs, 99999, quota_default());
    check("quota_set: a handle the host does not resolve is refused", bogus == E_NO_AGENT);
    check("quota_set: a handle of zero is refused", quota_set(qs, 0, quota_default()) == E_NO_AGENT);

    // An impossible quota is refused rather than silently producing a limit that never resets.
    let bad_window = Quota { call_rate: 10, window_ms: 0, storage_bytes: 0 };
    check("quota_set: a rate with no window is refused", quota_set(qs, a_h, bad_window) == E_INVAL);
    let neg = Quota { call_rate: -1, window_ms: 1000, storage_bytes: 0 };
    check("quota_set: a negative rate is refused", quota_set(qs, a_h, neg) == E_INVAL);
    check("quota_set: no row was created by a refused quota", qs.count == 0);

    // ======================================================================
    // 2. calls: the limit, the reset, and the clock that goes backwards
    // ======================================================================
    let tight = Quota { call_rate: 3, window_ms: 1000, storage_bytes: 100 };
    check("quota_set: attaches to a live agent", quota_set(qs, a_h, tight) == CODE_OK);
    check("quota_set: the row count follows", qs.count == 1);

    check("quota_call: first call allowed", quota_call(qs, a_h, 0) == CODE_OK);
    check("quota_call: second call allowed", quota_call(qs, a_h, 0) == CODE_OK);
    check("quota_call: third call allowed", quota_call(qs, a_h, 0) == CODE_OK);
    check("quota_call: fourth call in the window is refused", quota_call(qs, a_h, 0) == E_QUOTA);
    check("quota_call: the refusal is refused again", quota_call(qs, a_h, 10) == E_QUOTA);

    // Exactly at the boundary the window resets: the window is closed at `window_ms`, not after.
    check("quota_call: a new window reopens the limit", quota_call(qs, a_h, 1000) == CODE_OK);

    // A clock that jumps backwards starts a new window instead of denying until it catches up.
    // A stuck window would deny an agent forever, which is the worse failure.
    check("quota_call: a backwards clock starts a new window",
          quota_call(qs, a_h, 500) == CODE_OK);

    let get_q, get_ok = quota_get(qs, a_h);
    check("quota_get: returns the row that was set", get_ok && get_q.call_rate == 3
          && get_q.window_ms == 1000 && get_q.storage_bytes == 100);
    let no_q, no_ok = quota_get(qs, b_h);
    check("quota_get: an agent with no row reports no row", !no_ok && no_q.call_rate == 60);

    // An agent with no row is unlimited: the table is opt-in, and failing closed on a missing
    // row would turn "the supervisor forgot to configure me" into an outage.
    var k: i64 = 0;
    var all_ok = true;
    while k < 200 {
        if quota_call(qs, b_h, 0) != CODE_OK { all_ok = false; }
        k = k + 1;
    }
    check("quota_call: an agent with no row is unlimited", all_ok);

    // ======================================================================
    // 3. storage: charged, refused, and given back
    // ======================================================================
    check("quota_storage: under the limit is charged", quota_storage(qs, a_h, 60) == CODE_OK);
    check("quota_storage: over the limit is refused", quota_storage(qs, a_h, 60) == E_QUOTA);
    // A refusal must not charge: 60 is used, one more byte would be 61 of 100 and is allowed,
    // so the boundary is only testable one byte past the limit.
    check("quota_storage: a refusal charges nothing", quota_storage(qs, a_h, 41) == E_QUOTA);
    check("quota_storage: exactly the limit is allowed", quota_storage(qs, a_h, 40) == CODE_OK);
    check("quota_storage: zero bytes is not a request", quota_storage(qs, a_h, 0) == E_INVAL);
    check("quota_release: gives bytes back", quota_release(qs, a_h, 50) == CODE_OK);
    check("quota_release: the freed bytes can be spent again", quota_storage(qs, a_h, 50) == CODE_OK);
    // Releasing more than was charged never goes negative: a close path that releases twice
    // must not hand the agent a negative balance it can spend as headroom.
    check("quota_release: over-release clamps to zero", quota_release(qs, a_h, 1000) == CODE_OK);
    check("quota_release: zero is not a release", quota_release(qs, a_h, 0) == E_INVAL);
    check("quota_release: an agent with no row releases harmlessly", quota_release(qs, b_h, 10) == CODE_OK);

    // ======================================================================
    // 4. the health line, exactly
    // ======================================================================
    var st: u8[..256] = [0; 256];
    var want: u8[..256] = [0; 256];
    var empty_ch = ch_new();      // status writers need a channel; these lines do not use it

    // gamma has a default row and has been charged nothing.
    check("quota_set: a default row attaches", quota_set(qs, c_h, quota_default()) == CODE_OK);
    let gl = line_of(0, qs, empty_ch, c_h, st);
    let gw = lit("calls 0/60 storage 0/1048576 denied 0/0", want);
    check("quota_status: the exact health line", gl == gw && same_len(st[..gl], want[..gw]));

    // alpha has spent its window, been denied three times for calls and twice for storage.
    let al = line_of(0, qs, empty_ch, a_h, st);
    let aw = lit("calls 1/3 storage 0/100 denied 2/2", want);
    check("quota_status: counters after denials", al == aw && same_len(st[..al], want[..aw]));

    // Unlimited is a word, not a zero: "0 calls" and "unlimited calls" are different facts.
    let open = Quota { call_rate: 0, window_ms: 1000, storage_bytes: 0 };
    check("quota_set: an unlimited quota is legal", quota_set(qs, b_h, open) == CODE_OK);
    let bl = line_of(0, qs, empty_ch, b_h, st);
    let bw = lit("calls 0/unlimited storage 0/unlimited denied 0/0", want);
    check("quota_status: unlimited is spelled out", bl == bw && same_len(st[..bl], want[..bw]));

    let nl = line_of(0, qs, empty_ch, 0, st);
    let nw = lit("no quota", want);
    check("quota_status: no row says so", nl == nw && same_len(st[..nl], want[..nw]));

    let rows, dc, ds = quota_totals(qs);
    check("quota_totals: rows", rows == 3);
    check("quota_totals: denied calls across rows", dc == 2);
    check("quota_totals: denied storage across rows", ds == 2);

    // ======================================================================
    // 5. channel reporting: the four states and one exact line
    // ======================================================================
    var ch = ch_new();
    check("ch_state_name: every state has a name",
          same_len(ch_state_name(0), "queued"[..6])
          && same_len(ch_state_name(1), "delivered"[..9])
          && same_len(ch_state_name(2), "expired"[..7])
          && same_len(ch_state_name(3), "rejected"[..8]));
    check("ch_state_name: an unknown state is not invented", same_len(ch_state_name(9), "rejected"[..8]));

    let mid, sc = ch_send(ch, a_h, b_h, "ping", 0, 1000);
    check("ch_send: a message between two capable agents is queued", sc == CODE_OK && mid > 0);
    check("ch_pending_for: the recipient has one pending", ch_pending_for(ch, b_h) == 1);
    check("ch_pending_for: nobody else has any", ch_pending_for(ch, c_h) == 0);

    let cl = line_of(1, qs, ch, 0, st);
    let cw = lit("queued 1 sent 1 delivered 0 rejected 0 expired 0 full 0", want);
    check("ch_status: the exact channel line", cl == cw && same_len(st[..cl], want[..cw]));

    var body: u8[>..] = [];
    let rid, rc = ch_recv(ch, b_h, 0, body, 64);
    check("ch_recv: delivers the queued message", rc == CODE_OK && rid == mid);
    check("ch_recv: the body is the body", body.len == 4 && body[0] == 0x70);
    check("ch_pending_for: nothing is pending after delivery", ch_pending_for(ch, b_h) == 0);

    let cl2 = line_of(1, qs, ch, 0, st);
    let cw2 = lit("queued 0 sent 1 delivered 1 rejected 0 expired 0 full 0", want);
    check("ch_status: counters follow delivery", cl2 == cw2 && same_len(st[..cl2], want[..cw2]));

    // An expired message leaves the queue and is counted, not dropped silently.
    let _mid2, sc2 = ch_send(ch, a_h, b_h, "late", 0, 100);
    check("ch_send: a second message queues", sc2 == CODE_OK);
    var dry: u8[>..] = [];
    let _rid2, rc2 = ch_recv(ch, b_h, 1000, dry, 64);
    check("ch_recv: past its deadline the message is expired, not delivered", rc2 == CODE_OK && dry.len == 0);
    let _, _, _, expired = ch_stats(ch);
    check("ch_stats: the expiry is counted", expired == 1);

    // ======================================================================
    // 6. the lifecycle wrappers and the line a user sees
    // ======================================================================
    check("ah_stop: a created agent can be stopped before it ever ran",
          ah_stop(c_h, 0) == CODE_OK);
    check("ah_stop: a stopped agent cannot be stopped twice", ah_stop(c_h, 0) == E_STATE);

    var dl: u8[>..] = [];
    check("ah_down_line: writes the user-visible absence", ah_down_line(dl, 64));
    var dw: u8[..256] = [0; 256];
    let dwn = lit("AGENT LAYER DOWN", dw);
    check("ah_down_line: the exact string the console prints",
          same_len(dl[..], dw[..dwn]));

    // ======================================================================
    // 7. the table's capacity, and the row that outlives its agent
    // ======================================================================
    // Reaping an agent does not remove its quota row: `quota_remove` is the caller's job on the
    // reap path. A host that forgets leaves rows behind -- those rows are what make a full
    // table reachable, so the failure is driven rather than argued about.
    var fh_list: i64[..24] = [0; 24];
    var spawned: i64 = 0;
    var i: i64 = 0;
    while i < AH_CAP {
        var name: u8[..8] = [0; 8];
        name[0] = 0x66;                                  // 'f'
        name[1] = 0x30 + ((i / 10) as u8);
        name[2] = 0x30 + ((i % 10) as u8);
        let fh, fc = ah_spawn(name[..3], CAP_STORE_WRITE, 0);
        if fc == CODE_OK {
            fh_list[spawned] = fh;
            spawned = spawned + 1;
            let _ = quota_set(qs, fh, quota_default());
            let _ = ah_start(fh, 0);
        }
        i = i + 1;
    }
    let after_spawn, after_code = ah_spawn("overflow", CAP_STORE_WRITE, 0);
    check("spawn: the table is full at AH_CAP", after_code == E_NO_SPACE && after_spawn == 0);

    // Reap them all: the slots come back, the quota rows do not, because quota_remove is the
    // caller's job on the reap path and this caller has not done it.
    var j: i64 = 0;
    while j < spawned {
        let _ = ah_stop(fh_list[j], 0);
        let _ = ah_reap(fh_list[j]);
        j = j + 1;
    }
    let gg, ggc = ah_spawn("late", CAP_STORE_WRITE, 0);
    check("spawn: reaping frees a slot", ggc == CODE_OK);
    let late_set = quota_set(qs, gg, quota_default());
    check("quota_set: with every row taken by reaped agents, the new one is refused",
          late_set == E_NOROOM);

    // Removing rows is what reopens the table, and the removed handle stops being limited.
    check("quota_remove: a row can be dropped", quota_remove(qs, a_h) == CODE_OK);
    check("quota_remove: twice is not found", quota_remove(qs, a_h) == E_NOTFOUND);
    let rows2, _, _ = quota_totals(qs);
    check("quota_remove: the row count falls", rows2 == 23);

    say("t97 done  pass=");
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
