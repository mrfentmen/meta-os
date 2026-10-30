//! B25 forward — port of `os/forward.py` pure helpers.

/// Parse `FWD <msg_id> <#room>` -> (id, room), else None.
pub fn parse_fwd_text(text: &str) -> Option<(String, String)> {
    let body = text.strip_prefix("FWD ")?;
    let mut parts = body.split_whitespace();
    let id = parts.next()?;
    let room = parts.next()?;
    if parts.next().is_some() {
        return None;
    }
    if id.is_empty()
        || !id
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '.' || c == '_' || c == '-')
    {
        return None;
    }
    let room = room.strip_prefix('#').unwrap_or(room);
    if room.is_empty()
        || !room
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
    {
        // Empty target is rejected by the caller with "target room is empty".
        if room.is_empty() {
            return Some((id.to_string(), String::new()));
        }
        return None;
    }
    Some((id.to_string(), room.to_string()))
}

/// `(orig_nick, forwarder, body)` for `"<orig> (via <fwd>): <body>"`.
pub fn via_parts(text: &str) -> Option<(String, String, String)> {
    let (head, body) = text.split_once("): ")?;
    let (orig, fwd) = head.split_once(" (via ")?;
    if orig.is_empty() || fwd.is_empty() || body.is_empty() {
        return None;
    }
    Some((orig.to_string(), fwd.to_string(), body.to_string()))
}

/// Render wire text for forwarding. Single-hop collapse: when the
/// entry is itself a forward pushed by its own forwarder
/// (`nick == via.forwarder`), keep orig nick, replace forwarder.
pub fn forward_text(entry_nick: &str, entry_text: &str, forwarder: &str) -> String {
    if let Some((orig, fwd, body)) = via_parts(entry_text) {
        if fwd == entry_nick {
            return format!("{orig} (via {forwarder}): {body}");
        }
    }
    format!("{entry_nick} (via {forwarder}): {entry_text}")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fwd_parse_shapes() {
        assert_eq!(
            parse_fwd_text("FWD 7 #news"),
            Some(("7".into(), "news".into()))
        );
        assert_eq!(
            parse_fwd_text("FWD build-x-3 news"),
            Some(("build-x-3".into(), "news".into()))
        );
        assert_eq!(parse_fwd_text("hello"), None);
    }

    #[test]
    fn via_collapse_single_hop() {
        // Prior forward pushed by pax: nick == forwarder -> collapse.
        let t = forward_text("pax", "milo (via pax): ship it", "hana");
        assert_eq!(t, "milo (via hana): ship it");
        // "(via ...)" as content (nick differs) -> new hop.
        let t2 = forward_text("milo", "note (via x): hi", "hana");
        assert_eq!(t2, "milo (via hana): note (via x): hi");
    }
}
