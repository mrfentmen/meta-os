//! CB2-303..305 — budget gate boundaries and cumulative arithmetic.
//!
//! These pin the CURRENT public API: `spend_allowed`, `spend_ratio`,
//! `at_cap`. There is no `remaining()` accessor in this crate, so the
//! remaining-budget test drives the gate across a hand-computed
//! sequence instead of inventing one.

use os_budget::{at_cap, spend_allowed, spend_ratio, v_int};

#[test]
fn budget_limit_boundary() {
    // Exactly the cap is allowed; one unit over is refused.
    assert!(spend_allowed(&v_int(90), &v_int(100), 10));
    assert!(!spend_allowed(&v_int(90), &v_int(100), 11));
    // Spending the whole cap from zero is allowed.
    assert!(spend_allowed(&v_int(0), &v_int(100), 100));
    // An already-capped lane refuses any positive spend.
    assert!(!spend_allowed(&v_int(100), &v_int(100), 1));
    // A zero spend never moves the lane over.
    assert!(spend_allowed(&v_int(100), &v_int(100), 0));
    assert!(!at_cap(&v_int(99), &v_int(100)));
    assert!(at_cap(&v_int(100), &v_int(100)));
    assert!(at_cap(&v_int(101), &v_int(100)));
}

#[test]
fn budget_negative_refused() {
    assert!(!spend_allowed(&v_int(0), &v_int(100), -1));
    assert!(!spend_allowed(&v_int(50), &v_int(100), -50));
    // A negative spent value is not a usable lane, so no ratio.
    assert_eq!(spend_ratio(&v_int(-1), &v_int(100)), None);
}

#[test]
fn budget_remaining_arithmetic() {
    // Hand-computed: cap 100, three spends of 30, then 10, then 1.
    let cap = v_int(100);
    let mut spent: i64 = 0;
    for amount in [30, 30, 30] {
        assert!(spend_allowed(&v_int(spent), &cap, amount));
        spent += amount;
    }
    assert_eq!(spent, 90);
    assert!(spend_allowed(&v_int(spent), &cap, 10), "remaining 10 is spendable");
    spent += 10;
    assert_eq!(spent, 100);
    assert!(!spend_allowed(&v_int(spent), &cap, 1), "remaining 0 refuses 1");
    assert_eq!(spend_ratio(&v_int(spent), &cap), Some(1.0));
}
