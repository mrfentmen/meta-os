//! B26 admin — port of `os/admin.py` pure rules.
//!
//! Admin is enforced by tooling + HMAC audit log, not by Redis.
//! Secret never appears on the bus/spec/commit.

pub const MAX_DISPLAY: usize = 32;

/// Validate a display name (ports `_validate_display`).
pub fn validate_display(display: &str) -> Result<String, String> {
    let d = display.trim();
    if d.is_empty() {
        return Err("display name is empty".to_string());
    }
    if d.len() > MAX_DISPLAY {
        return Err(format!("display name too long (max {MAX_DISPLAY} chars)"));
    }
    if d.contains(':') || d.contains('\n') || d.contains('\r') {
        return Err("display name may not contain ':' or newlines".to_string());
    }
    Ok(d.to_string())
}

/// Validate a rekey digest (64 hex chars).
pub fn validate_rekey_digest(digest: &str) -> Result<String, String> {
    let d = digest.trim().to_lowercase();
    if d.len() != 64 || !d.chars().all(|c| c.is_ascii_hexdigit()) {
        return Err("new-sha256 must be 64 hex chars (sha256 of the new secret)".to_string());
    }
    Ok(d)
}

/// Canonical envelope bytes for HMAC (v/cmd/args/actor/ts/nonce,
/// sorted keys, compact separators).
pub fn canonical_envelope(v: u8, cmd: &str, args_json: &str, actor: &str, ts: i64, nonce: &str) -> String {
    format!("{{\"actor\":\"{actor}\",\"args\":{args_json},\"cmd\":\"{cmd}\",\"nonce\":\"{nonce}\",\"ts\":{ts},\"v\":{v}}}")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn display_shapes() {
        assert!(validate_display("").is_err());
        assert!(validate_display(&"x".repeat(33)).is_err());
        assert!(validate_display("a:b").is_err());
        assert_eq!(validate_display("  Milo  ").unwrap(), "Milo");
    }

    #[test]
    fn rekey_and_envelope() {
        assert!(validate_rekey_digest(&"ab".repeat(32)).is_ok());
        assert!(validate_rekey_digest("xyz").is_err());
        let c = canonical_envelope(1, "init", "{}", "milo", 1, "n");
        assert!(c.contains("\"v\":1"));
    }
}
