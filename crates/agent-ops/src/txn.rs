//! Universal transaction manager: recoverable multi-step work.
//!
//! Each operation declares its compensation (how to undo it) and whether
//! it is reversible at all. The coordinator runs steps in order; on
//! failure it walks back the completed steps in reverse, skipping the
//! irreversible ones and REPORTING them (never pretending they undid).
//! Outcome, compensations, and skipped steps are all recorded.

/// One step: do it, and know how to undo it.
#[derive(Debug, Clone)]
pub struct Op {
    pub name: String,
    /// False = e.g. money sent, email delivered. Reported, not undone.
    pub reversible: bool,
}

/// What the step runner returns (the OS supplies the real runner; the
/// coordinator only decides order and compensation).
#[derive(Debug, PartialEq)]
pub enum StepResult {
    Ok,
    Fail { error: String },
}

/// Compensation record for one undone step.
#[derive(Debug, PartialEq)]
pub enum Undo {
    /// Compensation ran clean.
    Undone { op: String },
    /// Irreversible step: left in place, REPORTED.
    LeftInPlace { op: String },
}

/// Full transaction outcome.
#[derive(Debug)]
pub struct TxnOutcome {
    pub committed: bool,
    pub completed: Vec<String>,
    pub undone: Vec<Undo>,
    pub failed_at: Option<String>,
    pub error: Option<String>,
}

/// Run `ops` in order with `run` executing each step and `compensate`
/// undoing one. Pure coordinator: no I/O of its own.
pub fn execute<R, C>(ops: &[Op], mut run: R, mut compensate: C) -> TxnOutcome
where
    R: FnMut(&Op) -> StepResult,
    C: FnMut(&Op) -> bool,
{
    let mut completed: Vec<&Op> = Vec::new();
    for op in ops {
        match run(op) {
            StepResult::Ok => completed.push(op),
            StepResult::Fail { error } => {
                let mut undone = Vec::new();
                for done in completed.iter().rev() {
                    if done.reversible {
                        if compensate(done) {
                            undone.push(Undo::Undone { op: done.name.clone() });
                        } else {
                            undone.push(Undo::LeftInPlace { op: done.name.clone() + " (compensation failed)" });
                        }
                    } else {
                        undone.push(Undo::LeftInPlace { op: done.name.clone() });
                    }
                }
                return TxnOutcome {
                    committed: false,
                    completed: completed.iter().map(|o| o.name.clone()).collect(),
                    undone,
                    failed_at: Some(op.name.clone()),
                    error: Some(error),
                };
            }
        }
    }
    TxnOutcome {
        committed: true,
        completed: completed.iter().map(|o| o.name.clone()).collect(),
        undone: Vec::new(),
        failed_at: None,
        error: None,
    }
}

/// Dry-run preview: names every action and flags the destructive or
/// irreversible ones WITHOUT running anything. This is the simulation
/// engine's file-operation core: show, then commit.
#[derive(Debug)]
pub struct Preview {
    pub steps: Vec<String>,
    pub irreversible: Vec<String>,
}

pub fn preview(ops: &[Op]) -> Preview {
    Preview {
        steps: ops.iter().map(|o| o.name.clone()).collect(),
        irreversible: ops.iter().filter(|o| !o.reversible).map(|o| o.name.clone()).collect(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ops() -> Vec<Op> {
        vec![
            Op { name: "create-site".into(), reversible: true },
            Op { name: "register-domain".into(), reversible: true },
            Op { name: "send-launch-email".into(), reversible: false },
        ]
    }

    #[test]
    fn success_commits_everything() {
        let out = execute(&ops(), |_| StepResult::Ok, |_| true);
        assert!(out.committed);
        assert_eq!(out.completed.len(), 3);
        assert!(out.undone.is_empty());
    }

    #[test]
    fn failure_compensates_in_reverse_and_reports_irreversible() {
        let fail_at = "register-domain";
        let out = execute(
            &ops(),
            |op| {
                if op.name == fail_at {
                    StepResult::Fail { error: "dns down".into() }
                } else {
                    StepResult::Ok
                }
            },
            |_| true,
        );
        assert!(!out.committed);
        assert_eq!(out.failed_at, Some(fail_at.into()));
        assert_eq!(out.undone, vec![Undo::Undone { op: "create-site".into() }]);
    }

    #[test]
    fn irreversible_step_is_reported_not_undone() {
        let out = execute(
            &ops(),
            |op| {
                if op.name == "never-happens" {
                    StepResult::Fail { error: "x".into() }
                } else {
                    StepResult::Ok
                }
            },
            |_| true,
        );
        assert!(out.committed);
        // Now fail AFTER the irreversible step ran.
        let out2 = execute(
            &[Op { name: "send-launch-email".into(), reversible: false }, Op { name: "takedown".into(), reversible: true }],
            |op| {
                if op.name == "takedown" {
                    StepResult::Fail { error: "api".into() }
                } else {
                    StepResult::Ok
                }
            },
            |_| true,
        );
        assert!(!out2.committed);
        assert_eq!(out2.undone, vec![Undo::LeftInPlace { op: "send-launch-email".into() }]);
    }

    #[test]
    fn preview_flags_danger_without_running() {
        let p = preview(&ops());
        assert_eq!(p.steps.len(), 3);
        assert_eq!(p.irreversible, vec!["send-launch-email"]);
    }
}
