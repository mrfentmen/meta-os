//! Digital provenance and evidence tracking.
//!
//! Every artifact an agent produces links back to its inputs: sources,
//! retrievals, timestamps, calculations, the responsible agent, and the
//! verification result. An evidence chain, not a trust-me summary.
//! Verification results are recorded; a broken link fails the chain.

use sha2::{Digest, Sha256};

/// One link: an input that went into an artifact.
#[derive(Debug, Clone)]
pub struct Input {
    /// e.g. "source:annual-report.pdf", "calc:sum(q1..q4)", "tool:fetch".
    pub kind: String,
    /// Content hash (hex sha256 of the bytes as seen).
    pub digest: String,
    pub at_secs: u64,
}

pub fn digest_bytes(bytes: &[u8]) -> String {
    let mut h = Sha256::new();
    h.update(bytes);
    format!("{:x}", h.finalize())
}

/// The chain for one artifact.
#[derive(Debug, Clone)]
pub struct Chain {
    pub artifact: String,
    pub artifact_digest: String,
    pub agent: String,
    pub model: String,
    pub inputs: Vec<Input>,
    /// None = not yet verified.
    pub verification: Option<bool>,
    pub verified_by: Option<String>,
}

impl Chain {
    pub fn new(artifact: &str, artifact_bytes: &[u8], agent: &str, model: &str) -> Self {
        Chain {
            artifact: artifact.into(),
            artifact_digest: digest_bytes(artifact_bytes),
            agent: agent.into(),
            model: model.into(),
            inputs: Vec::new(),
            verification: None,
            verified_by: None,
        }
    }

    pub fn add_input(&mut self, kind: &str, content: &[u8], at_secs: u64) {
        self.inputs.push(Input { kind: kind.into(), digest: digest_bytes(content), at_secs });
    }

    pub fn verify(&mut self, ok: bool, by: &str) {
        self.verification = Some(ok);
        self.verified_by = Some(by.into());
    }

    /// A chain is trustworthy only when verified true AND every input
    /// still hashes to its recorded digest (caller supplies current
    /// bytes per input kind).
    pub fn audit(&self, current: &[(&str, &[u8])]) -> Vec<String> {
        let mut problems = Vec::new();
        match self.verification {
            Some(true) => {}
            Some(false) => problems.push("verification recorded FAILURE".into()),
            None => problems.push("never verified".into()),
        }
        for inp in &self.inputs {
            match current.iter().find(|(k, _)| *k == inp.kind) {
                Some((_, bytes)) if digest_bytes(bytes) == inp.digest => {}
                Some(_) => problems.push(format!("input changed since record: {}", inp.kind)),
                None => problems.push(format!("input missing for re-check: {}", inp.kind)),
            }
        }
        problems
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn chain_verifies_and_detects_drift() {
        let mut c = Chain::new("report.md", b"conclusion: up 4%", "analyst", "m3");
        c.add_input("source:q1.csv", b"1,2,3", 100);
        c.verify(true, "checker");
        assert!(c.audit(&[("source:q1.csv", b"1,2,3")]).is_empty());
        let drift = c.audit(&[("source:q1.csv", b"1,2,4")]);
        assert_eq!(drift, vec!["input changed since record: source:q1.csv"]);
    }

    #[test]
    fn unverified_chain_fails_audit() {
        let c = Chain::new("report.md", b"x", "a", "m");
        assert_eq!(c.audit(&[]), vec!["never verified"]);
        let mut c2 = Chain::new("report.md", b"x", "a", "m");
        c2.verify(false, "checker");
        assert_eq!(c2.audit(&[]), vec!["verification recorded FAILURE"]);
    }
}
