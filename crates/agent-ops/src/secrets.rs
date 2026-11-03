//! Universal secrets manager: temporary, scoped, revocable credentials.
//!
//! Agents authenticate to external services WITHOUT ever holding
//! permanent passwords or API keys. They request a lease for a
//! service+scope; the manager mints a short-lived token, audits every
//! issue/use/revoke, and kills leases on expiry or explicit revoke.
//! Token VALUES are opaque handles — this module never stores the
//! underlying secret (the vault behind it does; out of scope here).

use std::collections::HashMap;

/// A live lease on a credential.
#[derive(Debug, Clone)]
pub struct Lease {
    pub token: String,
    pub service: String,
    pub scope: String,
    pub agent: String,
    pub issued_at: u64,
    pub expires_at: u64,
    pub uses: u64,
    pub max_uses: u64,
    pub revoked: bool,
}

/// Audit event kinds.
#[derive(Debug, PartialEq)]
pub enum SecretEvent {
    Issued,
    Used,
    Expired,
    Revoked,
}

/// Manager state. Callers persist it; nothing here touches the fs.
#[derive(Debug, Default)]
pub struct Vault {
    leases: HashMap<String, Lease>,
    counter: u64,
}

impl Vault {
    pub fn new() -> Self {
        Vault::default()
    }

    /// Mint a lease. ttl_secs and max_uses both bind; breath mints
    /// nothing (ttl 0 or uses 0 is rejected).
    pub fn issue(
        &mut self,
        service: &str,
        scope: &str,
        agent: &str,
        now: u64,
        ttl_secs: u64,
        max_uses: u64,
    ) -> Result<(String, SecretEvent), String> {
        if ttl_secs == 0 || max_uses == 0 {
            return Err("ttl and max_uses must be positive".into());
        }
        self.counter += 1;
        let token = format!("lease-{}-{}", now, self.counter);
        self.leases.insert(
            token.clone(),
            Lease {
                token: token.clone(),
                service: service.into(),
                scope: scope.into(),
                agent: agent.into(),
                issued_at: now,
                expires_at: now + ttl_secs,
                uses: 0,
                max_uses,
                revoked: false,
            },
        );
        Ok((token, SecretEvent::Issued))
    }

    /// Consume one use of a lease. Expired/exhausted/revoked leases
    /// fail CLOSED and report which.
    pub fn use_lease(&mut self, token: &str, now: u64) -> Result<&Lease, (SecretEvent, String)> {
        let l = self.leases.get_mut(token).ok_or((SecretEvent::Revoked, "unknown token".into()))?;
        if l.revoked {
            return Err((SecretEvent::Revoked, "lease revoked".into()));
        }
        if now >= l.expires_at {
            return Err((SecretEvent::Expired, "lease expired".into()));
        }
        if l.uses >= l.max_uses {
            return Err((SecretEvent::Expired, "use budget exhausted".into()));
        }
        l.uses += 1;
        Ok(l)
    }

    /// Immediate revocation.
    pub fn revoke(&mut self, token: &str) -> Result<SecretEvent, String> {
        match self.leases.get_mut(token) {
            Some(l) => {
                l.revoked = true;
                Ok(SecretEvent::Revoked)
            }
            None => Err("unknown token".into()),
        }
    }

    /// Sweep expired leases; returns tokens reaped.
    pub fn sweep(&mut self, now: u64) -> Vec<String> {
        let dead: Vec<String> = self
            .leases
            .iter()
            .filter(|(_, l)| !l.revoked && now >= l.expires_at)
            .map(|(t, _)| t.clone())
            .collect();
        for t in &dead {
            self.leases.remove(t);
        }
        dead
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lease_lifecycle() {
        let mut v = Vault::new();
        let (tok, ev) = v.issue("github", "repo:read", "coder", 100, 60, 3).unwrap();
        assert_eq!(ev, SecretEvent::Issued);
        assert!(v.use_lease(&tok, 110).is_ok());
        assert!(v.use_lease(&tok, 120).is_ok());
        assert!(v.use_lease(&tok, 130).is_ok());
        // Fourth use exhausts the budget.
        assert!(v.use_lease(&tok, 140).is_err());
    }

    #[test]
    fn expiry_closes() {
        let mut v = Vault::new();
        let (tok, _) = v.issue("mail", "send", "notifier", 100, 10, 99).unwrap();
        assert!(matches!(v.use_lease(&tok, 111), Err((SecretEvent::Expired, _))));
        assert_eq!(v.sweep(200), vec![tok]);
    }

    #[test]
    fn revocation_is_immediate() {
        let mut v = Vault::new();
        let (tok, _) = v.issue("mail", "send", "notifier", 100, 999, 99).unwrap();
        v.revoke(&tok).unwrap();
        assert!(matches!(v.use_lease(&tok, 101), Err((SecretEvent::Revoked, _))));
    }

    #[test]
    fn zero_ttl_or_uses_rejected() {
        let mut v = Vault::new();
        assert!(v.issue("s", "r", "a", 1, 0, 1).is_err());
        assert!(v.issue("s", "r", "a", 1, 1, 0).is_err());
    }
}
