//! Port of `os/intel/dispatch.py` — plan validation gates.
//!
//! The dry-run validates the Spark plan through every gate and posts
//! nothing; posting needs human approval (see `b09_core::cli`). Gates:
//! required string fields, unknown-field rejection, file-overlap,
//! dependency-graph (unknown deps + cycles), attempt-budget clamping,
//! secret scanning. [`PlanError`] is the typed refusal.

#[derive(Debug, Clone, PartialEq)]
pub struct PlanError(pub String);

impl std::fmt::Display for PlanError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "plan: {}", self.0)
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct PlanJob {
    pub key: String,
    pub title: String,
    pub files: Vec<String>,
    pub deps: Vec<String>,
    pub max_attempts: i64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Plan {
    pub goal: String,
    pub jobs: Vec<PlanJob>,
}

fn fail(msg: impl Into<String>) -> PlanError {
    PlanError(msg.into())
}

/// Structural parse: goal + jobs with required strings; unknown job fields
/// are rejected by the caller passing `unknown` explicitly.
pub fn parse_plan(goal: &str, jobs: Vec<(String, String)>, unknown: &[String]) -> Result<Plan, PlanError> {
    if goal.trim().is_empty() {
        return Err(fail("missing goal"));
    }
    if !unknown.is_empty() {
        return Err(fail(format!("unknown fields: {}", unknown.join(", "))));
    }
    let mut out = Vec::new();
    for (key, title) in jobs {
        if key.trim().is_empty() || title.trim().is_empty() {
            return Err(fail("job needs key + title"));
        }
        out.push(PlanJob { key, title, files: Vec::new(), deps: Vec::new(), max_attempts: 3 });
    }
    Ok(Plan { goal: goal.to_string(), jobs: out })
}

/// Two jobs touching the same file overlap (unless explicitly ordered by deps).
pub fn check_file_overlap(plan: &Plan) -> Result<(), PlanError> {
    use std::collections::HashMap;
    let mut owners: HashMap<&str, &str> = HashMap::new();
    for j in &plan.jobs {
        for f in &j.files {
            if let Some(prev) = owners.insert(f.as_str(), j.key.as_str()) {
                // overlap allowed only when dep-ordered either way
                let ordered = plan.jobs.iter().find(|x| x.key == prev).is_some_and(|p| p.deps.contains(&j.key))
                    || j.deps.iter().any(|d| d == prev);
                if !ordered {
                    return Err(fail(format!("file overlap on {f}: {prev} vs {}", j.key)));
                }
            }
        }
    }
    Ok(())
}

/// Unknown deps and dependency cycles are refused.
pub fn check_dep_graph(plan: &Plan) -> Result<Vec<String>, PlanError> {
    use std::collections::{HashMap, HashSet};
    let keys: HashSet<&str> = plan.jobs.iter().map(|j| j.key.as_str()).collect();
    for j in &plan.jobs {
        for d in &j.deps {
            if !keys.contains(d.as_str()) {
                return Err(fail(format!("unknown dep {d} in {}", j.key)));
            }
        }
    }
    // Kahn's algorithm for topological order
    let mut indeg: HashMap<&str, usize> = keys.iter().map(|k| (*k, 0)).collect();
    for j in &plan.jobs {
        for d in &j.deps {
            *indeg.get_mut(j.key.as_str()).unwrap() += 1;
            let _ = d;
        }
    }
    let mut dependents: HashMap<&str, Vec<&str>> = HashMap::new();
    for j in &plan.jobs {
        for d in &j.deps {
            dependents.entry(d.as_str()).or_default().push(j.key.as_str());
        }
    }
    let mut ready: Vec<&str> = indeg.iter().filter(|(_, &n)| n == 0).map(|(k, _)| *k).collect();
    let mut order = Vec::new();
    while let Some(k) = ready.pop() {
        order.push(k.to_string());
        if let Some(nexts) = dependents.get(k) {
            for n in nexts {
                let e = indeg.get_mut(n).unwrap();
                *e -= 1;
                if *e == 0 {
                    ready.push(n);
                }
            }
        }
    }
    if order.len() != plan.jobs.len() {
        return Err(fail("dependency cycle"));
    }
    Ok(order)
}

/// Clamp attempt budgets into [1, 10]; missing (0) becomes the default 3.
pub fn clamp_attempt_budgets(plan: &mut Plan) {
    for j in &mut plan.jobs {
        if j.max_attempts <= 0 {
            j.max_attempts = 3;
        } else if j.max_attempts > 10 {
            j.max_attempts = 10;
        }
    }
}

/// Refuse plans whose text looks like it carries a secret.
pub fn check_no_secrets(text: &str) -> Result<(), PlanError> {
    for marker in ["BEGIN PRIVATE KEY", "sk-live", "api_token"] {
        if text.contains(marker) {
            return Err(fail("plan carries a possible secret"));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn plan() -> Plan {
        Plan {
            goal: "g".into(),
            jobs: vec![
                PlanJob { key: "a".into(), title: "A".into(), files: vec!["f.py".into()], deps: vec![], max_attempts: 3 },
                PlanJob { key: "b".into(), title: "B".into(), files: vec![], deps: vec!["a".into()], max_attempts: 3 },
            ],
        }
    }

    #[test]
    fn topo_order_ok() {
        assert_eq!(check_dep_graph(&plan()).unwrap(), vec!["a".to_string(), "b".to_string()]);
    }

    #[test]
    fn unknown_dep_refused() {
        let mut p = plan();
        p.jobs[0].deps.push("ghost".into());
        assert!(check_dep_graph(&p).is_err());
    }

    #[test]
    fn cycle_refused() {
        let mut p = plan();
        p.jobs[0].deps.push("b".into());
        assert!(check_dep_graph(&p).is_err());
    }

    #[test]
    fn overlap_refused_unless_ordered() {
        let mut p = plan();
        p.jobs[1].files.push("f.py".into());
        // b deps on a, so ordered overlap is allowed
        assert!(check_file_overlap(&p).is_ok());
        p.jobs[1].deps.clear();
        assert!(check_file_overlap(&p).is_err());
    }

    #[test]
    fn budgets_clamped() {
        let mut p = plan();
        p.jobs[0].max_attempts = 0;
        p.jobs[1].max_attempts = 99;
        clamp_attempt_budgets(&mut p);
        assert_eq!((p.jobs[0].max_attempts, p.jobs[1].max_attempts), (3, 10));
    }
}
