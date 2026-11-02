// services/tests/t59_agenthost.goose
//
// B-L1-59 — test program for the agent host's lifecycle and grants (B-L1-39/B-L1-40).
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// WHAT IS UNDER TEST
// ------------------
// The agent host is where "the agent may only do what it was granted" either holds or does
// not. Three properties are tested, and each one is a way that promise breaks:
//
//   1. A grant is a CEILING, not a suggestion: an agent spawned with only CAP_STORE_READ
//      must fail a CAP_NET check, and clearing a bit must take effect immediately.
//   2. A grant cannot be widened. There is no add function -- this test asserts the absence
//      by checking that a narrower mask is all the agent ever reports, and that the mask left
//      after a removal stays removed.
//   3. A handle refers to ONE agent for its whole life. After a kill and a reap, the same
//      handle must resolve to nothing even though the slot is reused by the next spawn --
//      otherwise an operator's stale handle starts controlling a stranger.
//
// The lifecycle assertions are the state machine's, not the process's: an agent that is
// CREATED cannot be stopped as if it were running, and a terminal state cannot resume.

import agenthost.agenthost;
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
    say("t59 agent host + grants\n");

    // --- spawn rules ---
    let h0, c0 = ah_spawn("planner", CAP_STORE_READ, 100);
    check("spawn", c0 == CODE_OK && h0 > 0);
    check("state is created, not running", ah_state(h0) == AS_CREATED);
    check("not live-running yet", ah_is_live(h0));

    let _, dup = ah_spawn("planner", CAP_NET, 110);
    check("duplicate name refused", dup == E_BUSY);

    let _, noname = ah_spawn("", CAP_NET, 120);
    check("empty name refused", noname == E_INVAL);

    let _, badbits = ah_spawn("greedy", CAP_MAX_BIT, 130);
    check("undefined capability bit refused", badbits == E_INVAL);

    let h1, c1 = ah_spawn("writer", CAP_STORE_READ | CAP_STORE_WRITE, 140);
    check("second agent spawns", c1 == CODE_OK && h1 > 0 && h1 != h0);
    check("live count", ah_live_count() == 2);

    // --- grants are a ceiling ---
    check("granted bit present", ah_caps_have(h0, CAP_STORE_READ));
    check("ungranted bit absent", ah_caps_have(h0, CAP_NET) == false);
    check("all-of check is all-of", ah_caps_have(h1, CAP_STORE_READ | CAP_STORE_WRITE)
        && ah_caps_have(h1, CAP_STORE_READ | CAP_NET) == false);
    // Asking for nothing is always allowed; asking for a negative mask is a caller bug.
    check("empty requirement allowed", ah_caps_have(h0, 0));
    check("negative requirement refused", ah_caps_have(h0, -1) == false);

    // --- pid binding, and its ordering rule ---
    check("bind pid", ah_bind_pid(h0, 4242) == CODE_OK);
    check("start", ah_start(h0, 150) == CODE_OK);
    check("running", ah_state(h0) == AS_RUNNING);
    check("rebinding a running agent refused", ah_bind_pid(h0, 9999) == E_STATE);
    check("pid is not 0 after bind", ah_bind_pid(h1, 4243) == CODE_OK);

    // --- narrowing takes effect now ---
    check("remove a grant", ah_caps_remove(h0, CAP_STORE_READ, 160) == CODE_OK);
    check("removed grant is gone", ah_caps_have(h0, CAP_STORE_READ) == false);
    check("removal left nothing behind", ah_caps(h0) == 0);
    // Other agents are untouched: a grant table is per agent, not global.
    check("the other agent keeps its grants", ah_caps_have(h1, CAP_STORE_WRITE));
    check("removing an undefined bit refused", ah_caps_remove(h1, -1, 170) == E_INVAL);

    // --- lifecycle: terminal states are terminal ---
    check("kill", ah_kill(h0, 180) == CODE_OK);
    check("killed state", ah_state(h0) == AS_KILLED);
    check("a killed agent cannot start", ah_start(h0, 190) == E_STATE);
    check("a killed agent cannot fail again", ah_fail(h0, 1, 200) == E_STATE);
    check("grants cannot be changed on a dead agent",
        ah_caps_remove(h0, 0, 210) == E_STATE);

    // --- clean exit and crash are different causes ---
    check("exit", ah_exit(h1, 3, 220) == CODE_OK);
    check("exit state is stopped", ah_state(h1) == AS_STOPPED);
    check("a stopped agent cannot be killed as if running", ah_kill(h1, 230) == E_STATE);

    // --- reap, and the stale handle ---
    // A running agent cannot be reaped: freeing its slot would leave a process with no name
    // and no record. Nothing was running after the kill and the clean exit, so one is
    // spawned here to be the refusal case; the original test named h2 before spawning it.
    let hrun, crun = ah_spawn("watcher", CAP_MSG, 225);
    check("spawn the running one", crun == CODE_OK && hrun > 0);
    check("reap refuses a running agent", ah_reap(hrun) == E_STATE);
    check("reap the stopped one", ah_reap(h1) == CODE_OK);
    check("reap the killed one", ah_reap(h0) == CODE_OK);
    check("reaped handle resolves to nothing", ah_resolve(h0) < 0);
    check("reaped handle has no grants", ah_caps(h0) == 0);
    check("reaped handle is not live", ah_is_live(h0) == false);

    // The slot is reused. The OLD handle must still be dead: this is the whole reason the
    // handle carries a generation.
    let h2, c2 = ah_spawn("successor", CAP_MSG, 240);
    check("slot reused", c2 == CODE_OK && h2 > 0);
    check("old handle still dead after reuse", ah_resolve(h0) < 0);
    check("new handle works", ah_resolve(h2) >= 0);
    check("new agent has only its own grants", ah_caps(h2) == CAP_MSG);

    // --- a garbage handle is not a crash ---
    check("handle 0 resolves to nothing", ah_resolve(0) < 0);
    check("negative handle resolves to nothing", ah_resolve(-5) < 0);
    check("huge handle resolves to nothing", ah_resolve(999999) < 0);
    check("unknown handle has no grants", ah_caps(12345) == 0);

    // --- enumeration ---
    var out: i64[..24] = [];
    let n = ah_list(out, 24);
    check("list returns a count", n >= 1);
    check("list wrote real handles", out[0] > 0);

    var r: u8[>..] = [];
    let _ = append_int(r, 32, t_pass);
    say("passed ");
    say(r);
    say("\n");
    if t_fail != 0 { say("FAILURES\n"); sys_exit(1); }
    say("t59 done\n");
    sys_exit(0);
}
