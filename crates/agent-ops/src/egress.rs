//! Audited egress guard (no-evasion subset).
//!
//! Agents fetch remote data; the network is where cost, leaks, and
//! blocks live. This gate routes every outbound request through an
//! explicit allowlist and appends an audit record. Decisions are pure
//! logic over (method, host, policy) — enforcement lives with the
//! caller (MCP host / fetch wrapper), which must refuse what this
//! module denies.
//!
//! Deliberately NOT included: rotating proxies, CAPTCHA solving, or
//! fingerprint spoofing. Those are access-control evasion, not
//! infrastructure, and this module will not provide them.

/// One outbound request, as declared by the caller.
#[derive(Debug, Clone)]
pub struct Request {
    pub method: String,
    pub host: String,
    pub path: String,
}

/// Policy: exact or suffix host allowlist + method rules.
#[derive(Debug, Clone)]
pub struct Policy {
    /// Lowercase hosts, or ".suffix" entries matching subdomains.
    pub allow_hosts: Vec<String>,
    /// If false, only GET/HEAD pass even on allowed hosts.
    pub allow_writes: bool,
}

impl Policy {
    /// Empty-allowlist default: deny everything. There is no implicit
    /// "allow localhost": callers add "localhost"/"127.0.0.1" explicitly.
    pub fn deny_all() -> Self {
        Policy { allow_hosts: Vec::new(), allow_writes: false }
    }
}

/// The verdict for one request.
#[derive(Debug, PartialEq)]
pub enum Verdict {
    Allow { reason: String },
    Deny { reason: String },
}

fn host_allowed(policy: &Policy, host: &str) -> bool {
    let h = host.to_ascii_lowercase();
    // Reject credential/userinfo smuggling and trailing-dot tricks.
    if h.contains('@') || h.contains("..") || h.ends_with('.') {
        return false;
    }
    policy.allow_hosts.iter().any(|a| {
        let a = a.to_ascii_lowercase();
        if let Some(suffix) = a.strip_prefix('.') {
            h == *suffix || h.ends_with(&format!(".{}", suffix))
        } else {
            h == a
        }
    })
}

/// Route one request. Pure: no I/O, no network.
pub fn check(policy: &Policy, req: &Request) -> Verdict {
    if !host_allowed(policy, &req.host) {
        return Verdict::Deny { reason: format!("host not allowlisted: {}", req.host) };
    }
    let m = req.method.to_ascii_uppercase();
    if (m == "GET" || m == "HEAD") || policy.allow_writes {
        Verdict::Allow { reason: format!("{} {}", m, req.host) }
    } else {
        Verdict::Deny { reason: format!("writes disabled: {}", m) }
    }
}

/// One audit line. Callers append these to their ledger (JSONL).
#[derive(Debug)]
pub struct AuditLine {
    pub at_secs: u64,
    pub method: String,
    pub host: String,
    pub path: String,
    pub verdict: String,
}

pub fn audit_line(at_secs: u64, req: &Request, verdict: &Verdict) -> AuditLine {
    let v = match verdict {
        Verdict::Allow { .. } => "allow",
        Verdict::Deny { .. } => "deny",
    };
    AuditLine { at_secs, method: req.method.clone(), host: req.host.clone(), path: req.path.clone(), verdict: v.to_string() }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn pol() -> Policy {
        Policy {
            allow_hosts: vec!["registry.example".into(), ".artifacts.example".into()],
            allow_writes: false,
        }
    }

    #[test]
    fn exact_and_suffix_hosts_allowed() {
        let p = pol();
        assert!(matches!(
            check(&p, &Request { method: "GET".into(), host: "registry.example".into(), path: "/v".into() }),
            Verdict::Allow { .. }
        ));
        assert!(matches!(
            check(&p, &Request { method: "GET".into(), host: "dl.artifacts.example".into(), path: "/f".into() }),
            Verdict::Allow { .. }
        ));
    }

    #[test]
    fn unlisted_and_evil_hosts_denied() {
        let p = pol();
        for h in ["evil.example", "registry.example.evil.example", "user@registry.example", "registry.example."] {
            assert!(
                matches!(
                    check(&p, &Request { method: "GET".into(), host: h.into(), path: "/".into() }),
                    Verdict::Deny { .. }
                ),
                "host should be denied: {}",
                h
            );
        }
    }

    #[test]
    fn writes_need_opt_in() {
        let p = pol();
        assert!(matches!(
            check(&p, &Request { method: "POST".into(), host: "registry.example".into(), path: "/".into() }),
            Verdict::Deny { .. }
        ));
        let mut w = pol();
        w.allow_writes = true;
        assert!(matches!(
            check(&w, &Request { method: "POST".into(), host: "registry.example".into(), path: "/".into() }),
            Verdict::Allow { .. }
        ));
    }

    #[test]
    fn deny_all_default_denies_localhost_too() {
        let p = Policy::deny_all();
        assert!(matches!(
            check(&p, &Request { method: "GET".into(), host: "127.0.0.1".into(), path: "/".into() }),
            Verdict::Deny { .. }
        ));
    }
}
