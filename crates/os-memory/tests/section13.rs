//! CB2-311..313 — allocation ledger edges.

use os_memory::AllocationLedger;

#[test]
fn alloc_zero() {
    let mut ledger = AllocationLedger::new();
    ledger.allocate(0);
    assert_eq!(ledger.outstanding(), 0);
    assert!(ledger.release(0).is_ok());
    assert_eq!(ledger.outstanding(), 0);
}

#[test]
fn double_free_refused() {
    let mut ledger = AllocationLedger::new();
    ledger.allocate(10);
    assert!(ledger.release(10).is_ok());
    let err = ledger.release(10).expect_err("second free must refuse");
    assert!(err.0.contains("exceeds outstanding"), "named error: {}", err.0);
    assert_eq!(ledger.outstanding(), 0, "a refused free does not underflow");
}

#[test]
fn usage_accounting() {
    let mut ledger = AllocationLedger::new();
    ledger.allocate(100);
    ledger.allocate(50);
    assert_eq!(ledger.outstanding(), 150);
    ledger.release(30).unwrap();
    assert_eq!(ledger.outstanding(), 120);
    ledger.release(120).unwrap();
    assert_eq!(ledger.outstanding(), 0);
}
