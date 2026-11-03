//! CB2-341/342/343 — a bounded stack's three rules.
use stack::bounded::{BoundedStack, PopError, PushError, StackError};

#[test]
fn stack_overflow_named() {
    let mut stack: BoundedStack<&str> = BoundedStack::new(2).expect("capacity two");
    assert_eq!(stack.capacity(), 2);
    assert_eq!(stack.push("a"), Ok(()));
    assert_eq!(stack.push("b"), Ok(()));
    assert!(stack.is_full());
    assert_eq!(stack.len(), 2);

    // The third push is refused by name and hands the value back.
    match stack.push("c") {
        Err(PushError::Overflow(value)) => assert_eq!(value, "c", "the caller keeps what it tried to push"),
        other => panic!("a full stack must overflow, got {other:?}"),
    }
    assert_eq!(stack.len(), 2, "a refused push changes nothing");
    assert_eq!(stack.peek(), Some(&"b"), "the top is unchanged");

    // A capacity of zero is not a stack.
    assert_eq!(
        BoundedStack::<u8>::new(0).unwrap_err(),
        StackError("bounded stack: capacity must be at least 1".to_string()),
    );
}

#[test]
fn stack_underflow() {
    let mut stack: BoundedStack<u8> = BoundedStack::new(1).expect("capacity one");
    assert!(stack.is_empty());
    assert_eq!(stack.pop(), Err(PopError::Underflow), "empty is named, not a panic");
    assert_eq!(stack.peek(), None);

    // One successful pop, then underflow again: the state is honest either way.
    stack.push(7).expect("room for one");
    assert_eq!(stack.pop(), Ok(7));
    assert!(stack.is_empty());
    assert_eq!(stack.pop(), Err(PopError::Underflow));
}

#[test]
fn stack_lifo_order() {
    let mut stack: BoundedStack<u8> = BoundedStack::new(5).expect("capacity five");
    for n in 1..=5 {
        stack.push(n).expect("five fit");
    }
    assert!(stack.is_full());

    // Five pops return the values in reverse order: last in, first out.
    let popped: Vec<u8> = (0..5).map(|_| stack.pop().expect("not empty")).collect();
    assert_eq!(popped, vec![5, 4, 3, 2, 1]);
    assert!(stack.is_empty());
    assert_eq!(stack.pop(), Err(PopError::Underflow));

    // Interleaving does not reorder anything either.
    stack.push(10).expect("room after the pops");
    stack.push(20).expect("room after the pops");
    assert_eq!(stack.pop(), Ok(20));
    stack.push(30).expect("room after one pop");
    assert_eq!(stack.pop(), Ok(30));
    assert_eq!(stack.pop(), Ok(10));
}
