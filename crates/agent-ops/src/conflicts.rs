//! Conflicting-goal resolution: flag contradictions BEFORE execution.
//!
//! Long-lived agents accumulate constraints ("keep private" vs "deploy
//! public") that can directly contradict. This arbiter compares a new
//! directive against standing constraints and returns either Clear or
//! a Conflict naming both sides. Conflicts go back to the supervisor
//! as a prompt exception — never to silent execution.

/// A standing or incoming constraint.
#[derive(Debug, Clone)]
pub struct Constraint {
    /// Stable id, e.g. "privacy.project-scope".
    pub id: String,
    /// What it demands, in the instruction's own words.
    pub text: String,
    /// Normalized axes this constraint touches, e.g. ["visibility"].
    pub axes: Vec<String>,
    /// The demanded pole per axis, e.g. visibility=private.
    pub poles: Vec<String>,
    /// Who issued it (instruction id) for the exception report.
    pub issued_by: String,
}

/// The arbiter's answer for one incoming directive.
#[derive(Debug, PartialEq)]
pub enum Arbiter {
    Clear,
    Conflict { with: String, axis: String, detail: String },
}

/// Check `incoming` against every standing constraint. First clash wins;
/// the exception carries both instruction ids so the supervisor can ask
/// a human which one stands.
pub fn arbitrate(standing: &[Constraint], incoming: &Constraint) -> Arbiter {
    for s in standing {
        for (ax, pole) in s.axes.iter().zip(s.poles.iter()) {
            for (iax, ipole) in incoming.axes.iter().zip(incoming.poles.iter()) {
                if ax == iax && pole != ipole {
                    return Arbiter::Conflict {
                        with: s.id.clone(),
                        axis: ax.clone(),
                        detail: format!(
                            "'{}' (by {}) demands {}={}, but '{}' (by {}) demands {}={}",
                            incoming.id, incoming.issued_by, iax, ipole, s.id, s.issued_by, ax, pole
                        ),
                    };
                }
            }
        }
    }
    Arbiter::Clear
}

/// Convenience builder for visibility-axis constraints.
pub fn visibility(id: &str, text: &str, private: bool, issued_by: &str) -> Constraint {
    Constraint {
        id: id.into(),
        text: text.into(),
        axes: vec!["visibility".into()],
        poles: vec![if private { "private".into() } else { "public".into() }],
        issued_by: issued_by.into(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn private_vs_deploy_public_clashes() {
        let standing = vec![visibility("scope", "keep the project completely private", true, "user-1")];
        let incoming = visibility("deploy", "deploy the website immediately to a public server", false, "user-9");
        match arbitrate(&standing, &incoming) {
            Arbiter::Conflict { with, axis, .. } => {
                assert_eq!(with, "scope");
                assert_eq!(axis, "visibility");
            }
            Arbiter::Clear => panic!("should have clashed"),
        }
    }

    #[test]
    fn compatible_directives_pass() {
        let standing = vec![visibility("scope", "keep private", true, "user-1")];
        let incoming = visibility("backup", "back up to the private vault nightly", true, "user-2");
        assert_eq!(arbitrate(&standing, &incoming), Arbiter::Clear);
    }

    #[test]
    fn different_axes_do_not_clash() {
        let standing = vec![Constraint {
            id: "cost".into(),
            text: "spend under $10".into(),
            axes: vec!["budget".into()],
            poles: vec!["capped".into()],
            issued_by: "user-1".into(),
        }];
        let incoming = visibility("deploy", "deploy public", false, "user-2");
        assert_eq!(arbitrate(&standing, &incoming), Arbiter::Clear);
    }
}
