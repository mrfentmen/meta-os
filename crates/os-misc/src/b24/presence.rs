//! B24 presence — port of `os/presence.py`.
//!
//! Renders one nick per line for every nick with a live heartbeat,
//! or `NO_ONE_ONLINE`. `nick (status)` and `nick [holder]` suffixes
//! match the Python exactly.

use std::collections::HashMap;

/// Render the presence listing.
pub fn render_presence(
    nicks: &[String],
    statuses: &HashMap<String, String>,
    holders: &HashMap<String, String>,
) -> String {
    if nicks.is_empty() {
        return "NO_ONE_ONLINE".to_string();
    }
    let mut lines = vec![];
    for n in nicks {
        let mut line = n.clone();
        if let Some(h) = holders.get(n) {
            if !h.is_empty() {
                line.push_str(&format!(" [{h}]"));
            }
        }
        if let Some(s) = statuses.get(n) {
            if !s.is_empty() {
                line.push_str(&format!(" ({s})"));
            }
        }
        lines.push(line);
    }
    lines.join("\n")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_means_no_one() {
        assert_eq!(
            render_presence(&[], &HashMap::new(), &HashMap::new()),
            "NO_ONE_ONLINE"
        );
    }

    #[test]
    fn suffix_shapes() {
        let nicks = vec!["milo".to_string()];
        let mut st = HashMap::new();
        st.insert("milo".to_string(), "heads down".to_string());
        let mut holders = HashMap::new();
        holders.insert("milo".to_string(), "host-a".to_string());
        assert_eq!(
            render_presence(&nicks, &st, &holders),
            "milo [host-a] (heads down)"
        );
    }
}
