//! Authority and identity: what an agent may do, before it tries.
//!
//! Every agent has an identity, an explicit capability set, and a scope.
//! Permissions delegate down (never up: an agent cannot grant itself or
//! others anything it does not hold), expire automatically, revoke
//! immediately, and every check files an audit record naming the agent,
//! the authorizing instruction, and the outcome.

use std::collections::{HashMap, HashSet};

/// A capability token: what + where + until when.
#[derive(Debug, Clone)]
pub struct Grant {
    /// e.g. "files.read", "net.fetch", "money.spend".
    pub capability: String,
    /// Scope, e.g. a project id or "self". Empty = no scope bound.
    pub scope: String,
    /// Expiry as epoch seconds. u64::MAX = never (operator-held only).
    pub expires_at: u64,
    /// Instruction id that authorized this grant (provenance link).
    pub authorized_by: String,
}

/// An agent's identity and held grants.
#[derive(Debug, Clone)]
pub struct Identity {
    pub agent: String,
    pub grants: Vec<Grant>,
    pub revoked: HashSet<String>,
}

/// The auditable outcome of one check.
#[derive(Debug, PartialEq)]
pub enum AuthZ {
    Allow,
    Deny { reason: String },
}

/// One audit line. Callers append these to the ledger.
#[derive(Debug)]
pub struct AuthRecord {
    pub at_secs: u64,
    pub agent: String,
    pub capability: String,
    pub scope: String,
    pub authorized_by: String,
    pub outcome: &'static str,
}

fn live<'a>(grants: &'a [Grant], revoked: &HashSet<String>, now: u64) -> Vec<&'a Grant> {
    grants.iter().filter(|g| !revoked.contains(&g.capability) && g.expires_at > now).collect()
}

/// Check whether `agent` may use `capability` in `scope` at `now`.
/// Matches: exact capability, or a held "prefix.*" wildcard. Scope must
/// match exactly when the grant names one.
pub fn check(id: &Identity, capability: &str, scope: &str, authorized_by: &str, now: u64) -> (AuthZ, AuthRecord) {
    let rec = |outcome| AuthRecord {
        at_secs: now,
        agent: id.agent.clone(),
        capability: capability.into(),
        scope: scope.into(),
        authorized_by: authorized_by.into(),
        outcome,
    };
    for g in live(&id.grants, &id.revoked, now) {
        let cap_ok = g.capability == capability
            || g.capability.strip_suffix(".*").map(|p| capability.starts_with(p)).unwrap_or(false);
        let scope_ok = g.scope.is_empty() || g.scope == scope;
        if cap_ok && scope_ok {
            return (AuthZ::Allow, rec("allow"));
        }
    }
    (AuthZ::Deny { reason: format!("{} holds no live grant for {} in scope '{}'", id.agent, capability, scope) }, rec("deny"))
}

/// Delegate part of `from`'s authority to a new grant set. Rules:
/// the delegator must hold each capability (live, same scope family),
/// expiry cannot exceed the delegator's own, and "never" expiry
/// cannot be delegated. Returns the new grants or the first violation.
pub fn delegate(from: &Identity, scope: &str, wants: Vec<Grant>, now: u64) -> Result<Vec<Grant>, String> {
    let mut out = Vec::new();
    for w in wants {
        if w.expires_at == u64::MAX {
            return Err(format!("cannot delegate never-expiring grant {}", w.capability));
        }
        let mut ok = false;
        for g in live(&from.grants, &from.revoked, now) {
            let cap_ok = g.capability == w.capability
                || g.capability.strip_suffix(".*").map(|p| w.capability.starts_with(p)).unwrap_or(false);
            let scope_ok = g.scope.is_empty() || g.scope == w.scope || (w.scope == scope && g.scope == scope);
            if cap_ok && scope_ok && g.expires_at >= w.expires_at {
                ok = true;
                break;
            }
        }
        if !ok {
            return Err(format!("delegator lacks {} in scope '{}'", w.capability, w.scope));
        }
        out.push(w);
    }
    Ok(out)
}

/// Immediate revocation by capability name.
pub fn revoke(id: &mut Identity, capability: &str) {
    id.revoked.insert(capability.to_string());
}

/// Capability registry: machine-readable entries agents discover.
#[derive(Debug, Clone)]
pub struct Capability {
    pub name: String,
    pub version: String,
    pub description: String,
    pub needs: Vec<String>,
}

/// Index capabilities by name for discovery.
pub fn index(caps: Vec<Capability>) -> HashMap<String, Capability> {
    caps.into_iter().map(|c| (c.name.clone(), c)).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn op() -> Identity {
        Identity {
            agent: "boss".into(),
            grants: vec![
                Grant { capability: "files.*".into(), scope: "shop".into(), expires_at: 9_999_999_999, authorized_by: "hire".into() },
                Grant { capability: "money.spend".into(), scope: "shop".into(), expires_at: 100, authorized_by: "hire".into() },
            ],
            revoked: HashSet::new(),
        }
    }

    #[test]
    fn wildcard_and_scope() {
        let id = op();
        assert!(matches!(check(&id, "files.read", "shop", "i1", 10).0, AuthZ::Allow));
        assert!(matches!(check(&id, "files.read", "other", "i1", 10).0, AuthZ::Deny { .. }));
    }

    #[test]
    fn expiry_and_revocation() {
        let id = op();
        assert!(matches!(check(&id, "money.spend", "shop", "i1", 50).0, AuthZ::Allow));
        assert!(matches!(check(&id, "money.spend", "shop", "i1", 101).0, AuthZ::Deny { .. }));
        let mut id2 = op();
        revoke(&mut id2, "money.spend");
        assert!(matches!(check(&id2, "money.spend", "shop", "i1", 50).0, AuthZ::Deny { .. }));
    }

    #[test]
    fn delegation_cannot_escalate() {
        let id = op();
        // Narrower scope + sooner expiry: fine.
        let ok = delegate(
            &id,
            "shop",
            vec![Grant { capability: "files.read".into(), scope: "shop".into(), expires_at: 90, authorized_by: "i2".into() }],
            10,
        );
        assert!(ok.is_ok());
        // Capability the delegator lacks: refused.
        let bad = delegate(
            &id,
            "shop",
            vec![Grant { capability: "money.print".into(), scope: "shop".into(), expires_at: 90, authorized_by: "i2".into() }],
            10,
        );
        assert!(bad.is_err());
        // Longer expiry than held: refused.
        let long = delegate(
            &id,
            "shop",
            vec![Grant { capability: "money.spend".into(), scope: "shop".into(), expires_at: 500, authorized_by: "i2".into() }],
            10,
        );
        assert!(long.is_err());
        // Never-expiring: refused.
        let never = delegate(
            &id,
            "shop",
            vec![Grant { capability: "files.read".into(), scope: "shop".into(), expires_at: u64::MAX, authorized_by: "i2".into() }],
            10,
        );
        assert!(never.is_err());
    }

    #[test]
    fn audit_names_agent_and_instruction() {
        let id = op();
        let (_, r) = check(&id, "files.read", "shop", "hire-order-7", 10);
        assert_eq!(r.agent, "boss");
        assert_eq!(r.authorized_by, "hire-order-7");
        assert_eq!(r.outcome, "allow");
    }
}
