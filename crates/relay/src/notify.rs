//! NOTIFY ids from `relay/relay.mjs`:
//! `"ntf-"` + the first 16 hex chars of SHA-256 over
//! `room + "\n" + topic + "\n" + severity + "\n" + text`.
//! The same payload in the same room always yields the same id.

use crate::sha256::{hex_digest, sha256};

/// Deterministic NOTIFY id for one notify payload.
pub fn notify_id(room: &str, topic: &str, severity: &str, text: &str) -> String {
    let basis = format!("{}\n{}\n{}\n{}", room, topic, severity, text);
    let digest = hex_digest(&sha256(basis.as_bytes()));
    format!("ntf-{}", &digest[..16])
}

/// Format a message line exactly as the original stamps it:
/// `"<nick>: <text> [ts:<epoch-seconds>]"`.
pub fn message_line(nick: &str, text: &str, epoch_secs: u64) -> String {
    format!("{}: {} [ts:{}]", nick, text, epoch_secs)
}

/// Format a NOTIFY line exactly as the original stamps it:
/// `"relay: NOTIFY:<id> <severity> [<topic>] <text> [ts:<epoch-seconds>]"`.
pub fn notify_line(id: &str, severity: &str, topic: &str, text: &str, epoch_secs: u64) -> String {
    format!(
        "relay: NOTIFY:{} {} [{}] {} [ts:{}]",
        id, severity, topic, text, epoch_secs
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn id_format_and_determinism() {
        // Mirrors the JS suite: id matches /^ntf-[0-9a-f]{16}$/,
        // and posting the same payload twice yields the same id.
        let id = notify_id(
            "main",
            "trio-result",
            "info",
            "trio job trio-abc product ignis completed: category steam or fog",
        );
        assert!(id.starts_with("ntf-"));
        assert_eq!(id.len(), 20);
        assert!(id[4..].chars().all(|c| c.is_ascii_hexdigit()));
        let again = notify_id(
            "main",
            "trio-result",
            "info",
            "trio job trio-abc product ignis completed: category steam or fog",
        );
        assert_eq!(id, again);
    }

    #[test]
    fn id_matches_node_for_js_suite_payload() {
        // Golden value: Node's crypto SHA-256 for the exact basis the
        // JS suite posts (computed with hashlib, same algorithm).
        assert_eq!(
            notify_id(
                "main",
                "trio-result",
                "info",
                "trio job trio-abc product ignis completed: category steam or fog"
            ),
            "ntf-27c8a8f20499356d"
        );
    }

    #[test]
    fn different_basis_different_id() {
        let a = notify_id("main", "t", "info", "x");
        let b = notify_id("ops", "t", "info", "x");
        let c = notify_id("main", "t", "warning", "x");
        assert_ne!(a, b);
        assert_ne!(a, c);
    }

    #[test]
    fn line_formats() {
        assert_eq!(message_line("pax", "first line", 1793350000), "pax: first line [ts:1793350000]");
        assert_eq!(
            notify_line("ntf-0123456789abcdef", "info", "trio-result", "done", 1793350000),
            "relay: NOTIFY:ntf-0123456789abcdef info [trio-result] done [ts:1793350000]"
        );
    }
}
