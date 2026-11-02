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
    /// Job spec text. The shape-only parser leaves this empty; the
    /// contradiction guard reads it, so a fuller parse fills it in.
    pub spec: String,
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
        out.push(PlanJob { key, title, files: Vec::new(), deps: Vec::new(), max_attempts: 3, spec: String::new() });
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

fn is_word_char(b: u8) -> bool {
    b.is_ascii_alphanumeric() || b == b'_'
}

/// Read one whitespace-delimited word at `pos` (after skipping
/// whitespace). Returns the word and the index just past it.
fn next_word(lower: &str, mut pos: usize) -> Option<(&str, usize)> {
    let bytes = lower.as_bytes();
    while pos < bytes.len() && bytes[pos].is_ascii_whitespace() {
        pos += 1;
    }
    if pos >= bytes.len() {
        return None;
    }
    let start = pos;
    while pos < bytes.len() && !bytes[pos].is_ascii_whitespace() {
        pos += 1;
    }
    Some((&lower[start..pos], pos))
}

/// Port of Python's `_file_op_paths`: literal file-operation paths
/// for `verbs` in a spec, lowercased, trailing `.,;:!?"'` stripped.
/// No regex crate is used, so the two Python patterns
/// `\b(create)\s+(the\s+)?(new\s+)?file\s+(\S+)` and the
/// `\b(delete|remove)` twin are hand-scanned: a verb counts only
/// with a word boundary before it and whitespace after it, the
/// optional `the`/`new` each need trailing whitespace, and a failed
/// match restarts one byte later, the way finditer retries.
fn file_op_paths(spec: &str, verbs: &[&str]) -> Vec<String> {
    let lower = spec.to_lowercase();
    let bytes = lower.as_bytes();
    let mut out = Vec::new();
    let mut i = 0;
    while i < bytes.len() {
        // Verbs are ASCII; skipping a non-ASCII byte also keeps every
        // `lower[i..]` slice on a char boundary (byte indexes inside
        // a multi-byte character would panic on slicing).
        if !bytes[i].is_ascii() {
            i += 1;
            continue;
        }
        let mut verb_end = None;
        for v in verbs {
            if lower[i..].starts_with(v)
                && (i == 0 || !is_word_char(bytes[i - 1]))
                && i + v.len() < bytes.len()
                && bytes[i + v.len()].is_ascii_whitespace()
            {
                verb_end = Some(i + v.len());
                break;
            }
        }
        let mut pos = match verb_end {
            Some(p) => p,
            None => {
                i += 1;
                continue;
            }
        };
        // Optional `the`, then optional `new`, each with whitespace after.
        for opt in ["the", "new"] {
            if let Some((word, end)) = next_word(&lower, pos) {
                if word == opt && end < bytes.len() && bytes[end].is_ascii_whitespace() {
                    pos = end;
                }
            }
        }
        let (path, path_end) = match next_word(&lower, pos) {
            Some((word, end)) if word == "file" && end < bytes.len() && bytes[end].is_ascii_whitespace() => {
                match next_word(&lower, end) {
                    Some((p, pend)) => (p.trim_end_matches(['.', ',', ';', ':', '!', '?', '"', '\'']), pend),
                    None => {
                        i += 1;
                        continue;
                    }
                }
            }
            _ => {
                i += 1;
                continue;
            }
        };
        if !path.is_empty() {
            out.push(path.to_string());
        }
        // Resume past the match, as finditer does after a match.
        i = path_end;
    }
    out
}

/// DSP-023: guard a parsed plan against file-level create-vs-delete.
///
/// Only literal wording ("create file <path>" vs "delete/remove file
/// <path>") on a file the job itself owns counts; content edits and
/// single-direction plans pass. Returns `Err` naming the path and
/// both job keys when one job creates a file another deletes (or one
/// job does both), so a contradictory plan never reaches approval.
/// The parser stays shape-only: a contradictory plan still parses,
/// and only this guard rejects it. Posts nothing; pure check.
/// (Python returns the plan unchanged; here, like the other guards,
/// success is `Ok(())`.)
pub fn check_no_contradiction(plan: &Plan) -> Result<(), PlanError> {
    // (original-case path, creator key, deleter key), first-seen order.
    let mut ops: Vec<(String, Option<String>, Option<String>)> = Vec::new();
    for job in &plan.jobs {
        // Owned paths, deduplicated by lowercase; a later spelling of
        // the same lowercase path replaces the original, as Python's
        // `owned[path.lower()] = path` does.
        let mut owned: Vec<(String, String)> = Vec::new();
        for path in &job.files {
            let lower = path.to_lowercase();
            if let Some(slot) = owned.iter_mut().find(|(l, _)| *l == lower) {
                slot.1 = path.clone();
            } else {
                owned.push((lower, path.clone()));
            }
        }
        let owned_lowers: Vec<&str> = owned.iter().map(|(l, _)| l.as_str()).collect();
        let mut created: Vec<String> = file_op_paths(&job.spec, &["create"])
            .into_iter()
            .filter(|p| owned_lowers.contains(&p.as_str()))
            .collect();
        created.sort();
        created.dedup();
        let mut deleted: Vec<String> = file_op_paths(&job.spec, &["delete", "remove"])
            .into_iter()
            .filter(|p| owned_lowers.contains(&p.as_str()))
            .collect();
        deleted.sort();
        deleted.dedup();
        for path in created {
            let original = owned.iter().find(|(l, _)| *l == path).unwrap().1.clone();
            let slot = match ops.iter_mut().find(|(p, _, _)| *p == original) {
                Some(s) => s,
                None => {
                    ops.push((original.clone(), None, None));
                    ops.last_mut().unwrap()
                }
            };
            if slot.1.is_none() {
                slot.1 = Some(job.key.clone());
            }
        }
        for path in deleted {
            let original = owned.iter().find(|(l, _)| *l == path).unwrap().1.clone();
            let slot = match ops.iter_mut().find(|(p, _, _)| *p == original) {
                Some(s) => s,
                None => {
                    ops.push((original.clone(), None, None));
                    ops.last_mut().unwrap()
                }
            };
            if slot.2.is_none() {
                slot.2 = Some(job.key.clone());
            }
        }
    }
    for (path, creator, deleter) in &ops {
        if let (Some(creator), Some(deleter)) = (creator, deleter) {
            if creator == deleter {
                return Err(fail(format!(
                    "plan job '{creator}' contradicts itself on '{path}': it both creates and deletes the file; drop one of the two operations"
                )));
            }
            return Err(fail(format!(
                "plan job '{deleter}' contradicts plan job '{creator}' on '{path}': one deletes the file the other creates; drop one of the two jobs"
            )));
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
                PlanJob { key: "a".into(), title: "A".into(), files: vec!["f.py".into()], deps: vec![], max_attempts: 3, spec: String::new() },
                PlanJob { key: "b".into(), title: "B".into(), files: vec![], deps: vec!["a".into()], max_attempts: 3, spec: String::new() },
            ],
        }
    }

    fn cplan(jobs: Vec<PlanJob>) -> Plan {
        Plan { goal: "g".into(), jobs }
    }

    fn cjob(key: &str, files: Vec<&str>, spec: &str) -> PlanJob {
        PlanJob { key: key.into(), title: key.into(), files: files.iter().map(|s| s.to_string()).collect(), deps: vec![], max_attempts: 3, spec: spec.into() }
    }

    #[test]
    fn self_contradiction_fires() {
        let p = cplan(vec![cjob("both", vec!["intel/x.py"], "Steps: create file intel/x.py, then delete file intel/x.py.")]);
        let err = check_no_contradiction(&p).unwrap_err();
        assert!(err.0.contains("contradicts itself"), "got: {err}");
        assert!(err.0.contains("intel/x.py"), "got: {err}");
    }

    #[test]
    fn cross_job_contradiction_names_both_keys() {
        let p = cplan(vec![
            cjob("create-note", vec!["intel/notes/scratch.md"], "Steps: create the new file intel/notes/scratch.md."),
            cjob("delete-note", vec!["intel/notes/scratch.md"], "Steps: remove file intel/notes/scratch.md."),
        ]);
        let err = check_no_contradiction(&p).unwrap_err();
        assert!(err.0.contains("contradicts"), "got: {err}");
        assert!(err.0.contains("intel/notes/scratch.md"), "got: {err}");
        assert!(err.0.contains("create-note"), "got: {err}");
        assert!(err.0.contains("delete-note"), "got: {err}");
    }

    #[test]
    fn content_edits_and_single_direction_pass() {
        let p = cplan(vec![cjob("edit", vec!["intel/brief.py"], "Add a line to intel/brief.py and remove the old helper from intel/brief.py.")]);
        assert!(check_no_contradiction(&p).is_ok());
        let p = cplan(vec![
            cjob("make", vec!["intel/a.py"], "Steps: create file intel/a.py."),
            cjob("drop", vec!["intel/b.py"], "Steps: delete file intel/b.py."),
        ]);
        assert!(check_no_contradiction(&p).is_ok());
    }

    #[test]
    fn unowned_path_mention_does_not_fire() {
        let p = cplan(vec![cjob("mention", vec!["intel/a.py"], "Steps: create file intel/a.py. Note: delete file intel/b.py is out of scope for this job.")]);
        assert!(check_no_contradiction(&p).is_ok());
    }

    #[test]
    fn case_and_punctuation_tolerant() {
        let p = cplan(vec![cjob("both", vec!["Intel/X.py"], "CREATE FILE intel/x.py, then DELETE FILE intel/x.py!")]);
        assert!(check_no_contradiction(&p).is_err());
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
