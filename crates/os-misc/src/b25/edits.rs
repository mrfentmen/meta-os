//! B25 edits — port of `os/edits.py` protocol helpers.
//!
//! Wire format: `EDIT <msg_id> <new text>`. Only the original nick
//! may edit; edits append displaced text to history (see b24 store).

use crate::b24::transport::MAX_TEXT;

/// Parse `EDIT <msg_id> <new text>` -> (id, text), else None.
pub fn parse_edit_text(text: &str) -> Option<(String, String)> {
    // `^EDIT ([A-Za-z0-9._-]+)( (.*))?$` DOTALL.
    let body = text.strip_prefix("EDIT ")?;
    if body.is_empty() {
        return None;
    }
    // Reject `EDITED ...` — must be exactly `EDIT `.
    // (strip_prefix already ensures this.)
    let mut parts = body.splitn(2, ' ');
    let id = parts.next()?.trim();
    if id.is_empty() || !id.chars().all(|c| c.is_ascii_alphanumeric() || c == '.' || c == '_' || c == '-') {
        return None;
    }
    let rest = parts.next().unwrap_or("").to_string();
    Some((id.to_string(), rest))
}

/// Validate replacement text (empty / too-long like send).
pub fn validate_edit_text(new_text: &str) -> Result<(), String> {
    if new_text.trim().is_empty() {
        return Err("new text is empty".to_string());
    }
    if new_text.len() > MAX_TEXT {
        return Err(format!(
            "text too long ({} chars; max {MAX_TEXT}) — use --blob for long content",
            new_text.len()
        ));
    }
    Ok(())
}

/// Render one incoming bus line, applying EDIT lines.
/// Returns (rendered, applied_edit_id or None, spoofed or None).
pub fn render_kind(line: &str) -> RenderKind {
    let Some((_, text)) = line.split_once(": ") else {
        return RenderKind::Plain;
    };
    if parse_edit_text(text).is_some() {
        RenderKind::Edit
    } else {
        RenderKind::Plain
    }
}

pub enum RenderKind {
    Plain,
    Edit,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_shapes() {
        assert_eq!(
            parse_edit_text("EDIT 7 new words"),
            Some(("7".into(), "new words".into()))
        );
        assert_eq!(
            parse_edit_text("EDIT build-x-3 fixed"),
            Some(("build-x-3".into(), "fixed".into()))
        );
        assert_eq!(parse_edit_text("hello world"), None);
        assert_eq!(parse_edit_text("EDITED 7 nope"), None);
    }

    #[test]
    fn length_limit() {
        assert!(validate_edit_text(&"x".repeat(super::MAX_TEXT + 1)).is_err());
        assert!(validate_edit_text("   ").is_err());
        assert!(validate_edit_text("ok").is_ok());
    }
}
