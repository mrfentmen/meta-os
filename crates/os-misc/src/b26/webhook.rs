//! B26 webhook — port of `os/webhook.py`.
//!
//! URL is never stored/logged (lives only in argv/environ).
//! Delivery retried with backoff (1s, 2s, 4s, 8s); after 5 failures
//! the offset is NOT advanced so the message retries next run.

pub const MAX_ATTEMPTS: usize = 5;
pub const BACKOFFS: [u64; 4] = [1, 2, 4, 8];

/// Literal URL or env var name holding one. Never logs the value.
pub fn resolve_url(spec: &str, env_get: &dyn Fn(&str) -> Option<String>) -> Result<String, String> {
    let s = spec.trim();
    if s.starts_with("http://") || s.starts_with("https://") {
        return Ok(s.to_string());
    }
    match env_get(s) {
        Some(v) if !v.trim().is_empty() => {
            let v = v.trim().to_string();
            if v.starts_with("http://") || v.starts_with("https://") {
                Ok(v)
            } else {
                Err(format!("env var {s:?} does not hold an http(s) URL"))
            }
        }
        _ => Err(format!("env var {s:?} is not set or empty")),
    }
}

pub fn validate_interval(interval: f64) -> Result<(), String> {
    if interval <= 0.0 {
        return Err("--interval must be positive".to_string());
    }
    Ok(())
}

/// Webhook payload for one bus line.
pub fn payload_for(nick: &str, text: &str, room_label: &str, ts: i64) -> String {
    fn esc(s: &str) -> String {
        s.replace('\\', "\\\\").replace('"', "\\\"")
    }
    format!(
        "{{\"nick\":\"{}\",\"text\":\"{}\",\"room\":\"{}\",\"ts\":{ts}}}",
        esc(nick),
        esc(text),
        esc(room_label)
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn resolve_shapes() {
        let env = |k: &str| if k == "HOOK" { Some("https://x.test/h".into()) } else { None };
        assert_eq!(resolve_url("https://a.b/c", &env).unwrap(), "https://a.b/c");
        assert_eq!(resolve_url("HOOK", &env).unwrap(), "https://x.test/h");
        assert!(resolve_url("MISSING", &env).is_err());
        assert!(validate_interval(10.0).is_ok());
        assert!(validate_interval(0.0).is_err());
        assert_eq!(MAX_ATTEMPTS, 5);
        assert_eq!(BACKOFFS, [1, 2, 4, 8]);
    }
}
