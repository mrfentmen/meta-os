//! System-wide event intelligence bus (routing core).
//!
//! Applications emit events; agents subscribe and react. This module is
//! the deterministic routing core: typed events, predicate
//! subscriptions, fan-out dispatch with per-subscriber records. Live
//! tailing (files, sockets) is a service wrapper; this core never
//! blocks and never does I/O.

/// One event in the system.
#[derive(Debug, Clone)]
pub struct Event {
    /// e.g. "file.changed", "mail.arrived", "site.down".
    pub kind: String,
    pub summary: String,
    pub at_secs: u64,
}

/// A subscription: kind prefix + optional substring filter.
#[derive(Debug, Clone)]
pub struct Subscription {
    pub subscriber: String,
    pub kind_prefix: String,
    pub contains: String,
}

impl Subscription {
    pub fn matches(&self, e: &Event) -> bool {
        e.kind.starts_with(&self.kind_prefix)
            && (self.contains.is_empty() || e.summary.contains(&self.contains))
    }
}

/// One delivery record.
#[derive(Debug, PartialEq)]
pub struct Delivery {
    pub subscriber: String,
    pub kind: String,
    pub summary: String,
}

/// Fan out one event to all matching subscribers, in subscription order.
pub fn dispatch(subs: &[Subscription], e: &Event) -> Vec<Delivery> {
    subs.iter()
        .filter(|s| s.matches(e))
        .map(|s| Delivery { subscriber: s.subscriber.clone(), kind: e.kind.clone(), summary: e.summary.clone() })
        .collect()
}

/// Fan out a batch, preserving event order.
pub fn dispatch_all(subs: &[Subscription], events: &[Event]) -> Vec<Delivery> {
    let mut out = Vec::new();
    for e in events {
        out.extend(dispatch(subs, e));
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn subs() -> Vec<Subscription> {
        vec![
            Subscription { subscriber: "backup".into(), kind_prefix: "file.".into(), contains: String::new() },
            Subscription { subscriber: "pager".into(), kind_prefix: "site.".into(), contains: "down".into() },
            Subscription { subscriber: "all".into(), kind_prefix: "".into(), contains: String::new() },
        ]
    }

    #[test]
    fn prefix_and_filter_routing() {
        let e = Event { kind: "file.changed".into(), summary: "notes.txt".into(), at_secs: 1 };
        let d = dispatch(&subs(), &e);
        assert_eq!(d.iter().map(|x| x.subscriber.as_str()).collect::<Vec<_>>(), vec!["backup", "all"]);
        let down = Event { kind: "site.down".into(), summary: "example down".into(), at_secs: 2 };
        let d2 = dispatch(&subs(), &down);
        assert_eq!(d2.iter().map(|x| x.subscriber.as_str()).collect::<Vec<_>>(), vec!["pager", "all"]);
        let up = Event { kind: "site.up".into(), summary: "example up".into(), at_secs: 3 };
        let d3 = dispatch(&subs(), &up);
        assert_eq!(d3.iter().map(|x| x.subscriber.as_str()).collect::<Vec<_>>(), vec!["all"]);
    }

    #[test]
    fn batch_preserves_order() {
        let es = vec![
            Event { kind: "a.1".into(), summary: "x".into(), at_secs: 1 },
            Event { kind: "a.2".into(), summary: "y".into(), at_secs: 2 },
        ];
        let s = vec![Subscription { subscriber: "s".into(), kind_prefix: "a.".into(), contains: String::new() }];
        let d = dispatch_all(&s, &es);
        assert_eq!(d.len(), 2);
        assert_eq!(d[0].summary, "x");
        assert_eq!(d[1].summary, "y");
    }
}
