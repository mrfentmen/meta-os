// CB-034 — allocation accounting never goes negative under
// release-heavy sequences; an over-release is refused.
use os_memory::AllocationLedger;

#[test]
fn release_heavy_sequence_stops_at_zero() {
    let mut ledger = AllocationLedger::new();
    ledger.allocate(10);
    ledger.release(7).unwrap();
    assert_eq!(ledger.outstanding(), 3);
    assert!(ledger.release(4).is_err());
    assert_eq!(ledger.outstanding(), 3);
    ledger.release(3).unwrap();
    assert_eq!(ledger.outstanding(), 0);
    assert!(ledger.release(1).is_err());
    assert_eq!(ledger.outstanding(), 0);
}

#[test]
fn zero_release_is_a_no_op() {
    let mut ledger = AllocationLedger::new();
    ledger.allocate(5);
    ledger.release(0).unwrap();
    assert_eq!(ledger.outstanding(), 5);
}
