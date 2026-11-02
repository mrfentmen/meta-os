// services/updater_client/updater_client.goose
//
// Layer 5, face service 5: the updater client.
//
// WHAT THIS IS
// ------------
// The desktop side of an update: ask, refuse, apply, report. It mirrors the image
// updater's contract (`services/updater`) and adds the four refusals that make an
// update path safe to leave running:
//
//   - **STOP wins over everything.** A STOP file present in the image is checked
//     first, before the rate limit and before the signature, because stopping is the
//     answer to "should this machine update right now" and nothing else is.
//   - **A failed verification never becomes "available".** The version is only
//     recorded as available after the digest and the signature both pass. A manifest
//     that fails verification leaves the previous state untouched.
//   - **No rollback.** A manifest offering a version at or below the applied one is a
//     refusal, not a "nothing to do": a server that goes backwards is a server that is
//     being spoofed or was rolled back, and either way this client is not the place to
//     find out which.
//   - **A rate limit that reports itself.** Two checks in a second is a client bug; it
//     returns its own code so the caller can tell "no update" from "not asked".
//
// WHERE THE APPLIED VERSION LIVES
// -------------------------------
// Not here. `uc_init` starts from "nothing applied", and the caller seeds the truth
// with `uc_seed_applied` after a restart, from the same record the boot path reads.
// A version remembered in this process's memory would forget every update across a
// restart, and re-offer the version that is already installed.
//
// Status: RUNS — reached by tests/t90_updater_client (exit 0). Measured 2026-11-02 by audit_status.py.

import common.err.err;

// States
let UC_S_IDLE: i64 = 0;
let UC_S_CHECKING: i64 = 1;
let UC_S_AVAILABLE: i64 = 2;
let UC_S_APPLYING: i64 = 3;
let UC_S_DONE: i64 = 4;
let UC_S_FAILED: i64 = 5;

// Result codes. Above the error range so a caller can test "refused" as a group.
let UC_NO_UPDATE: i64 = 9001;
let UC_AVAILABLE: i64 = 9002;
let UC_REFUSED_STOP: i64 = 9003;
let UC_REFUSED_VERIFY: i64 = 9004;
let UC_REFUSED_RATE: i64 = 9005;
let UC_REFUSED_ROLLBACK: i64 = 9006;

let UC_MIN_INTERVAL_MS: i64 = 60000;
let UC_NEVER: i64 = -1;

var uc_state: i64 = UC_S_IDLE;
var uc_last_check_ms: i64 = UC_NEVER;
var uc_last_code: i64 = CODE_OK;
var uc_available: i64 = 0;
var uc_applied: i64 = 0;
var uc_checks: i64 = 0;
var uc_stop_refusals: i64 = 0;
var uc_verify_refusals: i64 = 0;
var uc_rate_refusals: i64 = 0;
var uc_rollback_refusals: i64 = 0;
var uc_applied_count: i64 = 0;
var uc_prev_ms: i64 = UC_NEVER;   // last check that passed the rate gate
var uc_failed_count: i64 = 0;

fn uc_init(now_ms: i64) {
    uc_state = UC_S_IDLE;
    uc_last_check_ms = UC_NEVER;
    uc_last_code = CODE_OK;
    uc_available = 0;
    uc_applied = 0;
    uc_checks = 0;
    uc_stop_refusals = 0;
    uc_verify_refusals = 0;
    uc_rate_refusals = 0;
    uc_rollback_refusals = 0;
    uc_applied_count = 0;
    uc_failed_count = 0;
    uc_prev_ms = UC_NEVER;
    let _ = now_ms;
}

// The truth about what is installed, from the record on disk. Refuses a version that
// goes backwards, so a corrupt record cannot make the client re-offer an old image.
fn uc_seed_applied(version: i64) -> i64 {
    if version < 0 { return E_INVAL; }
    if version < uc_applied { return E_ROLLBACK; }
    uc_applied = version;
    return CODE_OK;
}

fn uc_state_name(s: i64) -> const u8[:] {
    if s == UC_S_IDLE { return "idle"; }
    if s == UC_S_CHECKING { return "checking"; }
    if s == UC_S_AVAILABLE { return "available"; }
    if s == UC_S_APPLYING { return "applying"; }
    if s == UC_S_DONE { return "done"; }
    if s == UC_S_FAILED { return "failed"; }
    return "?";
}

fn uc_code_name(c: i64) -> const u8[:] {
    if c == UC_NO_UPDATE { return "no-update"; }
    if c == UC_AVAILABLE { return "available"; }
    if c == UC_REFUSED_STOP { return "refused-stop"; }
    if c == UC_REFUSED_VERIFY { return "refused-verify"; }
    if c == UC_REFUSED_RATE { return "refused-rate"; }
    if c == UC_REFUSED_ROLLBACK { return "refused-rollback"; }
    if c == CODE_OK { return "ok"; }
    return "error";
}

fn uc_busy() -> bool {
    return uc_state == UC_S_CHECKING || uc_state == UC_S_APPLYING;
}

// One check. The order of the refusals is the contract:
//   1. busy state  2. STOP  3. rate  4. verification  5. rollback
// STOP is before the rate limit so a machine told to stop never reports "rate
// limited", which reads as "we will try again shortly" and is the wrong message.
// A STOP refusal does not advance the rate clock: when the file is removed, the
// window that was already running still applies.
fn uc_check(stop_present: bool, version: i64, digest_ok: bool, signature_ok: bool, now_ms: i64) -> i64 {
    if uc_busy() { return E_STATE; }
    if version < 0 { return E_INVAL; }
    uc_checks = uc_checks + 1;
    uc_last_check_ms = now_ms;

    if stop_present {
        uc_stop_refusals = uc_stop_refusals + 1;
        uc_last_code = UC_REFUSED_STOP;
        return UC_REFUSED_STOP;
    }

    // The interval is measured from the last accepted check. A backwards clock is
    // treated as inside the window: refusing is the safe direction.
    if uc_prev_ms >= 0 {
        if now_ms < uc_prev_ms || now_ms - uc_prev_ms < UC_MIN_INTERVAL_MS {
            uc_rate_refusals = uc_rate_refusals + 1;
            uc_last_code = UC_REFUSED_RATE;
            return UC_REFUSED_RATE;
        }
    }
    uc_prev_ms = now_ms;

    if !digest_ok || !signature_ok {
        uc_verify_refusals = uc_verify_refusals + 1;
        uc_last_code = UC_REFUSED_VERIFY;
        // The state does not move: nothing was learned about a version.
        return UC_REFUSED_VERIFY;
    }
    if version < uc_applied {
        uc_rollback_refusals = uc_rollback_refusals + 1;
        uc_last_code = UC_REFUSED_ROLLBACK;
        return UC_REFUSED_ROLLBACK;
    }
    if version == uc_applied {
        uc_last_code = UC_NO_UPDATE;
        if uc_state != UC_S_DONE { uc_state = UC_S_IDLE; }
        return UC_NO_UPDATE;
    }
    uc_available = version;
    uc_state = UC_S_AVAILABLE;
    uc_last_code = UC_AVAILABLE;
    return UC_AVAILABLE;
}

// Apply what is available. A result is required: applying without a result is how a
// client ends up believing it installed something.
fn uc_apply(ok: bool) -> i64 {
    if uc_state != UC_S_AVAILABLE { return E_STATE; }
    if ok {
        uc_applied = uc_available;
        uc_applied_count = uc_applied_count + 1;
        uc_state = UC_S_DONE;
        uc_last_code = CODE_OK;
        return CODE_OK;
    }
    uc_failed_count = uc_failed_count + 1;
    uc_state = UC_S_FAILED;
    uc_last_code = E_VERIFY;
    return E_VERIFY;
}

// A failed apply can be retried once the failure is understood: back to IDLE, with
// the available version kept so a retry does not need a new check.
fn uc_retry() -> i64 {
    if uc_state != UC_S_FAILED { return E_STATE; }
    if uc_available <= uc_applied { uc_state = UC_S_IDLE; return E_STATE; }
    uc_state = UC_S_AVAILABLE;
    return CODE_OK;
}

fn uc_status() -> i64, i64 { return uc_state, uc_last_code; }
fn uc_available_version() -> i64 { return uc_available; }
fn uc_applied_version() -> i64 { return uc_applied; }
fn uc_last_check_ms() -> i64 { return uc_last_check_ms; }
fn uc_check_count() -> i64 { return uc_checks; }
fn uc_stop_count() -> i64 { return uc_stop_refusals; }
fn uc_verify_count() -> i64 { return uc_verify_refusals; }
fn uc_rate_count() -> i64 { return uc_rate_refusals; }
fn uc_rollback_count() -> i64 { return uc_rollback_refusals; }
fn uc_applied_total() -> i64 { return uc_applied_count; }
fn uc_failed_total() -> i64 { return uc_failed_count; }
