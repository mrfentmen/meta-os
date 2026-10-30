//! Port of `os/intel/wake.py` — sleeping-Muse wake bundles.
//!
//! A Muse that is sleeping (absent presence + no recent progress) gets at
//! most one wake bundle per dedupe key; the bundle quotes the deposited
//! spec text verbatim and never invents acceptance criteria.

pub fn is_sleeping_muse(present: bool, idle_minutes: i64) -> bool {
    !present && idle_minutes >= 15
}

pub fn should_wake(sleeping: bool, already_sent: bool, has_spec: bool) -> bool {
    sleeping && !already_sent && has_spec
}

pub fn dedupe_key(nick: &str, job: &str) -> String {
    format!("wake:{nick}:{job}")
}

pub fn compose_bundle(nick: &str, job: &str, spec_text: &str, acceptance: &[String]) -> String {
    let acc = if acceptance.is_empty() {
        "(no acceptance recorded)".to_string()
    } else {
        acceptance.join("; ")
    };
    format!("WAKE {nick} re: {job}\n{spec_text}\nacceptance: {acc}")
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn wake_gates() {
        assert!(is_sleeping_muse(false, 20));
        assert!(!is_sleeping_muse(true, 99));
        assert!(should_wake(true, false, true));
        assert!(!should_wake(true, true, true));
    }
    #[test]
    fn bundle_quotes_spec() {
        assert!(compose_bundle("m", "j", "spec words", &[]).contains("spec words"));
    }
}
