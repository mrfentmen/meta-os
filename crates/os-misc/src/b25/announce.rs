//! B25 announce — port of `os/announce.py`.
//!
//! Announcer nick stored at `muse-bus:announce:<room-key>`.
//! Filter is client-side only (honest limits in the Python doc).

/// Redis key holding the announcer nick for a room bus key.
pub fn announce_key(room_key: &str) -> String {
    format!("muse-bus:announce:{room_key}")
}

/// Split messages into (kept, skipped) for an announce room.
/// No announcer -> everything kept (caller warns `--announce` no-op).
pub fn announce_filter(
    announcer: Option<&str>,
    messages: &[String],
) -> (Vec<String>, usize) {
    let Some(ann) = announcer.filter(|a| !a.is_empty()) else {
        return (messages.to_vec(), 0);
    };
    let prefix = format!("{ann}:");
    let kept: Vec<String> = messages.iter().filter(|m| m.starts_with(&prefix)).cloned().collect();
    let skipped = messages.len() - kept.len();
    (kept, skipped)
}

/// Enforce the set/clear gate. Returns error string or None.
/// `claim_holder`: Some(holder) when we lost the nick claim.
/// `mods`: room mod set (empty = anyone may set).
pub fn gate(
    nick: &str,
    claim_holder: Option<&str>,
    mods: &[String],
) -> Option<String> {
    if let Some(h) = claim_holder {
        return Some(format!(
            "you don't hold the nick claim for '{nick}' (held by '{h}') — can't change announce mode"
        ));
    }
    if !mods.is_empty() && !mods.iter().any(|m| m == nick) {
        let list = mods.join(", ");
        return Some(format!(
            "only room mods can change announce mode (mods: {list})"
        ));
    }
    None
}

pub const CONVENTION_WARNING: &str = "WARNING: announce mode is a client-side convention, not access control — poll.py/watch.py --announce honor it, but any other client sees everything, and nicks are unauthenticated.";

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn filter_keeps_announcer_only() {
        let msgs = vec![
            "tester: ship it".to_string(),
            "bob: wait".to_string(),
            "tester: monday".to_string(),
        ];
        let (kept, skipped) = announce_filter(Some("tester"), &msgs);
        assert_eq!(kept, vec!["tester: ship it".to_string(), "tester: monday".to_string()]);
        assert_eq!(skipped, 1);
    }

    #[test]
    fn filter_no_announcer_keeps_all() {
        let msgs = vec!["bob: hi".to_string()];
        assert_eq!(announce_filter(None, &msgs), (msgs.clone(), 0));
    }

    #[test]
    fn gate_shapes() {
        assert!(gate("tester", Some("host-a"), &[]).is_some());
        assert!(gate("tester", None, &["alice".into()]).is_some());
        assert!(gate("alice", None, &["alice".into()]).is_none());
        assert!(gate("tester", None, &[]).is_none());
    }
}
