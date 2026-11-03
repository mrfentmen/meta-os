// CB-031 — spending exactly the cap succeeds; one unit over fails.
use os_budget::{spend_allowed, Value};

#[test]
fn spend_to_exactly_cap_is_allowed() {
    assert!(spend_allowed(&Value::Int(90), &Value::Int(100), 10));
}

#[test]
fn spend_one_unit_over_cap_is_refused() {
    assert!(!spend_allowed(&Value::Int(90), &Value::Int(100), 11));
}

#[test]
fn negative_amount_and_unusable_cap_are_refused() {
    assert!(!spend_allowed(&Value::Int(10), &Value::Int(100), -1));
    assert!(!spend_allowed(&Value::Int(10), &Value::Int(0), 0));
    assert!(!spend_allowed(&Value::Int(-1), &Value::Int(100), 0));
}
