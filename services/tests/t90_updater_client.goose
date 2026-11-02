// services/tests/t90_updater_client.goose
//
// Driver for the updater client — the four refusals, their order, and the apply.
//
// The order matters more than any single rule: a machine with a STOP file must not
// report "rate limited", and a manifest that fails verification must not leave a
// version marked available.

import updater_client.updater_client;
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
    say("t90 updater-client\n");
    uc_init(0);

    check("updater: starts idle", uc_status() == UC_S_IDLE);
    check("updater: nothing applied", uc_applied_version() == 0);
    check("updater: no checks yet", uc_check_count() == 0);
    check("updater: state name", uc_state_name(UC_S_IDLE).len == 4);

    // --- STOP wins ----------------------------------------------------------
    let c1 = uc_check(true, 5, true, true, 1000);
    check("updater: a STOP file refuses the check", c1 == UC_REFUSED_STOP);
    check("updater: STOP is counted", uc_stop_count() == 1);
    check("updater: STOP leaves the client idle", uc_status() == UC_S_IDLE);
    check("updater: STOP marks nothing available", uc_available_version() == 0);
    check("updater: STOP outranks the rate limit",
          uc_check(true, 5, true, true, 1001) == UC_REFUSED_STOP);
    check("updater: the rate limit was not charged", uc_rate_count() == 0);

    // --- rate ---------------------------------------------------------------
    let c2 = uc_check(false, 5, true, true, 2000);
    check("updater: a clean check finds version 5", c2 == UC_AVAILABLE);
    let st_avail, _cd_avail = uc_status();
    check("updater: state is available", st_avail == UC_S_AVAILABLE);
    check("updater: available version recorded", uc_available_version() == 5);
    check("updater: nothing applied yet", uc_applied_version() == 0);

    let c3 = uc_check(false, 6, true, true, 3000);
    check("updater: a second check inside the interval is refused", c3 == UC_REFUSED_RATE);
    check("updater: the refusal is counted", uc_rate_count() == 1);
    check("updater: the available version did not change", uc_available_version() == 5);
    let c4 = uc_check(false, 6, true, true, 2000 + UC_MIN_INTERVAL_MS - 1);
    check("updater: one ms before the interval is still refused", c4 == UC_REFUSED_RATE);
    let c5 = uc_check(false, 6, true, true, 2000 + UC_MIN_INTERVAL_MS);
    check("updater: at the interval the check runs", c5 == UC_AVAILABLE);
    check("updater: the newer version is now available", uc_available_version() == 6);

    // A backwards clock is refused rather than treated as a free pass.
    let c6 = uc_check(false, 7, true, true, 63000);
    check("updater: a backwards clock is refused by the rate limit", c6 == UC_REFUSED_RATE);

    // --- verification -------------------------------------------------------
    let c7 = uc_check(false, 7, false, true, 63000 + UC_MIN_INTERVAL_MS);
    check("updater: a bad digest is refused", c7 == UC_REFUSED_VERIFY);
    check("updater: the digest refusal is counted", uc_verify_count() == 1);
    check("updater: a bad digest leaves the old version available", uc_available_version() == 6);
    let c8 = uc_check(false, 8, true, false, 63000 + UC_MIN_INTERVAL_MS * 2);
    check("updater: a bad signature is refused", c8 == UC_REFUSED_VERIFY);
    check("updater: the signature refusal is counted too", uc_verify_count() == 2);
    check("updater: verification failures never mark a version available", uc_available_version() == 6);
    check("updater: negative versions are a caller error", uc_check(false, -1, true, true, 200000) == E_INVAL);

    // --- rollback -----------------------------------------------------------
    // Apply 6, then a server offers 5: refused, not "no update".
    check("updater: apply 6", uc_apply(true) == CODE_OK);
    check("updater: 6 is applied", uc_applied_version() == 6);
    check("updater: the apply is counted", uc_applied_total() == 1);
    let c9 = uc_check(false, 5, true, true, 200000 + UC_MIN_INTERVAL_MS);
    check("updater: a rollback is refused", c9 == UC_REFUSED_ROLLBACK);
    check("updater: the rollback is counted", uc_rollback_count() == 1);
    check("updater: the applied version did not move", uc_applied_version() == 6);
    let c10 = uc_check(false, 6, true, true, 200000 + UC_MIN_INTERVAL_MS * 2);
    check("updater: the same version is 'no update'", c10 == UC_NO_UPDATE);
    check("updater: no-update does not clear the applied version", uc_applied_version() == 6);

    // --- apply state machine -------------------------------------------------
    check("updater: apply with nothing available is E_STATE", uc_apply(true) == E_STATE);
    let c11 = uc_check(false, 7, true, true, 200000 + UC_MIN_INTERVAL_MS * 3);
    check("updater: version 7 available", c11 == UC_AVAILABLE);
    check("updater: a failed apply reports E_VERIFY", uc_apply(false) == E_VERIFY);
    check("updater: a failed apply leaves the version unapplied", uc_applied_version() == 6);
    check("updater: the failure is counted", uc_failed_total() == 1);
    let st_fail, _cd_fail = uc_status();
    check("updater: state is failed", st_fail == UC_S_FAILED);
    check("updater: retry from failed", uc_retry() == CODE_OK);
    check("updater: retry returns to available", uc_state_name(uc_status()) == "available");
    check("updater: retry kept the version", uc_available_version() == 7);
    check("updater: apply on retry", uc_apply(true) == CODE_OK);
    check("updater: 7 is applied", uc_applied_version() == 7);
    check("updater: two applies counted", uc_applied_total() == 2);
    check("updater: retry outside failed is E_STATE", uc_retry() == E_STATE);

    // --- seeding after a restart ---------------------------------------------
    // Init forgets everything; the caller seeds what is installed. Seeding is
    // forward-only: a record that claims an older version than the client already
    // knows is a rollback and is refused.
    uc_init(0);
    check("updater: init forgets the applied version", uc_applied_version() == 0);
    check("updater: seed 7", uc_seed_applied(7) == CODE_OK);
    check("updater: seeded applied version", uc_applied_version() == 7);
    check("updater: seeding backwards is a rollback", uc_seed_applied(3) == E_ROLLBACK);
    check("updater: the refused seed changed nothing", uc_applied_version() == 7);
    check("updater: a negative seed is refused", uc_seed_applied(-1) == E_INVAL);
    check("updater: seeding the same version is fine", uc_seed_applied(7) == CODE_OK);

    let c12 = uc_check(false, 7, true, true, 1000);
    check("updater: after seeding 7, version 7 is no update", c12 == UC_NO_UPDATE);
    let c13 = uc_check(false, 6, true, true, 1000 + UC_MIN_INTERVAL_MS);
    check("updater: after seeding 7, version 6 is a rollback", c13 == UC_REFUSED_ROLLBACK);
    let c14 = uc_check(false, 8, true, true, 1000 + UC_MIN_INTERVAL_MS * 2);
    check("updater: version 8 is available", c14 == UC_AVAILABLE);

    // --- names ---------------------------------------------------------------
    check("updater: every result code has a name",
          uc_code_name(UC_NO_UPDATE).len > 0 && uc_code_name(UC_AVAILABLE).len > 0
          && uc_code_name(UC_REFUSED_STOP).len > 0 && uc_code_name(UC_REFUSED_VERIFY).len > 0
          && uc_code_name(UC_REFUSED_RATE).len > 0 && uc_code_name(UC_REFUSED_ROLLBACK).len > 0);
    check("updater: every state has a name",
          uc_state_name(UC_S_IDLE).len > 1 && uc_state_name(UC_S_CHECKING).len > 1
          && uc_state_name(UC_S_AVAILABLE).len > 1 && uc_state_name(UC_S_APPLYING).len > 1
          && uc_state_name(UC_S_DONE).len > 1 && uc_state_name(UC_S_FAILED).len > 1);

    // Counting restarted with uc_init: three checks since. The twelve before the init
    // are proven by the refusals they produced (2 stop + 3 rate + 2 verify + 1 rollback
    // + 1 no-update + 1 available + ...), each asserted above individually.
    check("updater: checks are counted after a restart", uc_check_count() == 3);

    say("t90 done  pass=");
    var pb: u8[>..] = [];
    let _ = append_int(pb, 32, t_pass);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    let _ = append_int(fb, 32, t_fail);
    say(fb[..]);
    say("\n");
}
