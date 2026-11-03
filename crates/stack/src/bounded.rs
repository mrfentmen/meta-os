//! A bounded LIFO stack.
//!
//! The service planner answers "what should run"; this answers "what is on
//! top". It is bounded on purpose: an unbounded stack turns a runaway producer
//! into an out-of-memory kill, and the kill names nothing. A push past the
//! capacity returns the value back inside [`PushError::Overflow`], so the
//! caller still owns what it tried to add, and a pop from empty is
//! [`PopError::Underflow`] rather than a panic or a default value.

/// A stack that refuses to grow past its capacity.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BoundedStack<T> {
    items: Vec<T>,
    capacity: usize,
}

/// A stack that must not be created.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StackError(pub String);

/// The push did not happen; the value comes back to the caller.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PushError<T> {
    Overflow(T),
}

/// There was nothing to pop.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PopError {
    Underflow,
}

impl<T> BoundedStack<T> {
    /// A stack with room for `capacity` items. Zero is refused: a stack that
    /// can never hold anything is a bug wearing a type.
    pub fn new(capacity: usize) -> Result<BoundedStack<T>, StackError> {
        if capacity == 0 {
            return Err(StackError("bounded stack: capacity must be at least 1".to_string()));
        }
        Ok(BoundedStack { items: Vec::with_capacity(capacity.min(1024)), capacity })
    }

    pub fn capacity(&self) -> usize {
        self.capacity
    }

    pub fn len(&self) -> usize {
        self.items.len()
    }

    pub fn is_empty(&self) -> bool {
        self.items.is_empty()
    }

    pub fn is_full(&self) -> bool {
        self.items.len() == self.capacity
    }

    /// Push onto the top. Full returns the value, unchanged and untouched.
    pub fn push(&mut self, item: T) -> Result<(), PushError<T>> {
        if self.is_full() {
            return Err(PushError::Overflow(item));
        }
        self.items.push(item);
        Ok(())
    }

    /// Pop the top. Empty is a named underflow, never a panic.
    pub fn pop(&mut self) -> Result<T, PopError> {
        self.items.pop().ok_or(PopError::Underflow)
    }

    /// The top, without removing it.
    pub fn peek(&self) -> Option<&T> {
        self.items.last()
    }
}
