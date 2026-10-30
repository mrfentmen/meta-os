//! B24 watch_nick — port of `os/watch_nick.py`.
//!
//! Checks the bus for any message from `<nick>`. Fires exactly once:
//! first detection prints `<NICK>_JOINED` and records a flag file;
//! otherwise `<NICK>_NOT_JOINED`. Flag files live next to the store dir.

/// Decide the watch_nick outcome from already-fetched bus messages.
pub fn nick_joined(messages: &[String], watch: &str, display_names: &[String]) -> bool {
    let want = watch.trim().to_lowercase();
    if want.is_empty() {
        return false;
    }
    let mut targets = vec![want.clone()];
    for d in display_names {
        targets.push(d.to_lowercase());
    }
    messages.iter().any(|m| {
        if let Some((from, _)) = m.split_once(':') {
            targets.contains(&from.trim().to_lowercase())
        } else {
            false
        }
    })
}

/// Flag-file name for a watch (`{watch}_reported` + room suffix).
pub fn flag_name(watch: &str, room: &str) -> String {
    let upper = watch.trim().to_uppercase();
    if room.is_empty() {
        format!(".{upper}_reported")
    } else {
        format!(".{upper}_reported_{room}")
    }
}

/// Render the CLI line for the outcome.
pub fn render_outcome(watch: &str, joined: bool) -> String {
    let upper = watch.trim().to_uppercase();
    if joined {
        format!("{upper}_JOINED")
    } else {
        format!("{upper}_NOT_JOINED")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn matches_canonical_or_display() {
        let msgs = vec!["Milo: hi".to_string(), "pax: yo".to_string()];
        assert!(nick_joined(&msgs, "milo", &vec!["Milo The Builder".into()]));
        assert!(!nick_joined(&msgs, "hana", &vec![]));
        assert!(!nick_joined(&msgs, "   ", &vec![]));
    }

    #[test]
    fn flag_and_render_shapes() {
        assert_eq!(flag_name("milo", ""), ".MILO_reported");
        assert_eq!(flag_name("milo", "build-x"), ".MILO_reported_build-x");
        assert_eq!(render_outcome("milo", true), "MILO_JOINED");
        assert_eq!(render_outcome("milo", false), "MILO_NOT_JOINED");
    }
}
