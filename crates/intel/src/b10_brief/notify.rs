//! Port of `os/intel/notify.py` — notification rendering + queue.
//!
//! `render_line` is the frozen one-line shape; `notify` queues without
//! sending (the bus post belongs to the sender); pending/ack/resolve
//! track lifecycle. Printing a record never leaks secrets.

#[derive(Debug, Clone, PartialEq)]
pub struct Notification {
    pub id: String,
    pub severity: String,
    pub topic: String,
    pub text: String,
}

pub fn render_line(n: &Notification) -> String {
    format!("[{}] {}: {}", n.severity, n.topic, n.text)
}

#[derive(Debug, Default)]
pub struct NotifyQueue {
    pub pending: Vec<Notification>,
}

impl NotifyQueue {
    pub fn notify(&mut self, n: Notification) {
        if !self.pending.iter().any(|e| e.id == n.id) {
            self.pending.push(n);
        }
    }
    pub fn pending(&self) -> &[Notification] {
        &self.pending
    }
    pub fn acknowledge(&mut self, id: &str) -> bool {
        if let Some(i) = self.pending.iter().position(|n| n.id == id) {
            self.pending.remove(i);
            true
        } else {
            false
        }
    }
    pub fn resolve(&mut self, id: &str) -> bool {
        self.acknowledge(id)
    }
    pub fn post_line(n: &Notification) -> String {
        render_line(n)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn frozen_line_shape() {
        let n = Notification { id: "i".into(), severity: "high".into(), topic: "t".into(), text: "x".into() };
        assert_eq!(render_line(&n), "[high] t: x");
    }
    #[test]
    fn dedupes_by_id() {
        let mut q = NotifyQueue::default();
        let n = Notification { id: "i".into(), severity: "l".into(), topic: "t".into(), text: "x".into() };
        q.notify(n.clone());
        q.notify(n);
        assert_eq!(q.pending().len(), 1);
        assert!(q.acknowledge("i"));
    }
}
