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
    /// Job accept lines. The shape-only parser leaves this empty; the
    /// accept scorer reads it, so a fuller parse fills it in.
    pub accept: Vec<String>,
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
        out.push(PlanJob { key, title, files: Vec::new(), deps: Vec::new(), max_attempts: 3, spec: String::new(), accept: Vec::new() });
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

/// DSP-026 spec-writing standard: every job spec carries these five
/// parts, in this order, each with real content (not just the label).
pub const SPEC_PART_LABELS: [&str; 5] =
    ["goal", "context", "files", "steps", "out of scope"];

/// Score of one job spec against the DSP-026 standard. `missing` and
/// `empty` list labels in standard order; `files_part_names_owned` is
/// `None` when the Files part is absent or no owned files were given.
#[derive(Debug, Clone, PartialEq)]
pub struct SpecScore {
    pub missing: Vec<String>,
    pub empty: Vec<String>,
    pub files_part_names_owned: Option<bool>,
    pub passes: bool,
}

/// One entry of [`score_plan_specs`]: a [`SpecScore`] tagged with its
/// job key, in plan order.
#[derive(Debug, Clone, PartialEq)]
pub struct JobSpecScore {
    pub key: String,
    pub missing: Vec<String>,
    pub empty: Vec<String>,
    pub files_part_names_owned: Option<bool>,
    pub passes: bool,
}

/// Leftmost whole-word occurrence of `word` at or after `cursor`,
/// like Python's `\bword\b` search. No regex crate is used.
fn find_word_label(lowered: &str, cursor: usize, word: &str) -> Option<(usize, usize)> {
    let bytes = lowered.as_bytes();
    for (off, _) in lowered[cursor..].match_indices(word) {
        let start = cursor + off;
        let end = start + word.len();
        let before_ok = start == 0 || !is_word_char(bytes[start - 1]);
        let after_ok = end == bytes.len() || !is_word_char(bytes[end]);
        if before_ok && after_ok {
            return Some((start, end));
        }
    }
    None
}

/// Leftmost match of Python's `out[ -]of[ -]scope\b` at or after
/// `cursor`. Unlike the single-word labels this pattern has no
/// leading word boundary, so `out` may sit inside a longer word.
fn find_out_of_scope(lowered: &str, cursor: usize) -> Option<(usize, usize)> {
    let bytes = lowered.as_bytes();
    for (off, _) in lowered[cursor..].match_indices("out") {
        let start = cursor + off;
        let mut p = start + 3;
        if p >= bytes.len() || (bytes[p] != b' ' && bytes[p] != b'-') {
            continue;
        }
        p += 1;
        if !lowered[p..].starts_with("of") {
            continue;
        }
        p += 2;
        if p >= bytes.len() || (bytes[p] != b' ' && bytes[p] != b'-') {
            continue;
        }
        p += 1;
        if !lowered[p..].starts_with("scope") {
            continue;
        }
        let end = p + 5;
        if end < bytes.len() && is_word_char(bytes[end]) {
            continue;
        }
        return Some((start, end));
    }
    None
}

/// Score one job spec against the DSP-026 standard. Labels are
/// matched in order, so a spec with the parts shuffled reports the
/// out-of-order part as missing from its expected position. Never
/// refuses: a malformed spec scores every part missing. Pure scoring;
/// posts nothing and never refuses a plan — the parser gate stays
/// shape-only by design. Matching runs on the lowercased copy, so
/// indices below are into that copy (identical to Python's for
/// ASCII specs). Python's non-string-spec branch is unrepresentable
/// here: `spec` is always a string in the typed plan.
pub fn score_spec_parts(spec: &str, files: &[String]) -> SpecScore {
    let lowered = spec.to_lowercase();
    let mut missing: Vec<String> = Vec::new();
    let mut empty: Vec<String> = Vec::new();
    let mut positions: Vec<Option<(usize, usize)>> = Vec::new();
    let mut cursor = 0usize;
    for (i, label) in SPEC_PART_LABELS.iter().enumerate() {
        let found = if i == 4 {
            find_out_of_scope(&lowered, cursor)
        } else {
            find_word_label(&lowered, cursor, label)
        };
        match found {
            Some((start, end)) => {
                positions.push(Some((start, end)));
                cursor = end;
            }
            None => {
                positions.push(None);
                missing.push(label.to_string());
            }
        }
    }
    let strip: &[char] = &[' ', '\t', '\n', ':', ';', ',', '.', '—', '-'];
    for (i, pos) in positions.iter().enumerate() {
        let Some((_, match_end)) = pos else { continue };
        let end = positions[i + 1..]
            .iter()
            .flatten()
            .next()
            .map(|(start, _)| *start)
            .unwrap_or(lowered.len());
        let content = &lowered[*match_end..end];
        if content.trim_matches(strip).trim().is_empty() {
            empty.push(SPEC_PART_LABELS[i].to_string());
        }
    }
    let mut files_part_names_owned = None;
    if let Some((_, files_end)) = &positions[2] {
        if !files.is_empty() {
            let end = positions[3..]
                .iter()
                .flatten()
                .next()
                .map(|(start, _)| *start)
                .unwrap_or(lowered.len());
            let files_part = &lowered[*files_end..end];
            files_part_names_owned = Some(
                files.iter().any(|path| files_part.contains(&path.to_lowercase())),
            );
        }
    }
    let passes = missing.is_empty()
        && empty.is_empty()
        && files_part_names_owned != Some(false);
    SpecScore { missing, empty, files_part_names_owned, passes }
}

/// Score every job spec in a parsed plan (DSP-026), in plan order,
/// one entry per job. Python raises `PlanError` on a malformed plan;
/// the typed `Plan` cannot be malformed that way, so no error case
/// exists here.
pub fn score_plan_specs(plan: &Plan) -> Vec<JobSpecScore> {
    plan.jobs
        .iter()
        .map(|job| {
            let score = score_spec_parts(&job.spec, &job.files);
            JobSpecScore {
                key: job.key.clone(),
                missing: score.missing,
                empty: score.empty,
                files_part_names_owned: score.files_part_names_owned,
                passes: score.passes,
            }
        })
        .collect()
}

/// One parsed accept check: the kind plus its argument, ported from
/// `os/mos/acceptance.py::parse_accept` for the scorer's use (that
/// module itself belongs to a later batch; only the parse step is
/// needed here, never the runner).
#[derive(Debug, Clone, PartialEq)]
enum AcceptCheck {
    FileExists(String),
    Contains(String),
    TestsPass(String),
    CommandOk(String),
}

/// Parse one accept line the way `mos/acceptance.py::parse_accept`
/// parses a single-line text: blank and `#` comment lines yield no
/// checks, and a line with no `:` separator, an unknown kind, an
/// empty argument, or a `contains` without `::` is an error.
/// Kind matching is case-insensitive; the argument keeps its case.
fn parse_accept_line(line: &str) -> Result<Vec<AcceptCheck>, ()> {
    let trimmed = line.trim();
    if trimmed.is_empty() || trimmed.starts_with('#') {
        return Ok(Vec::new());
    }
    let Some((raw_kind, raw_arg)) = trimmed.split_once(':') else {
        return Err(());
    };
    let kind = raw_kind.trim().to_lowercase();
    let arg = raw_arg.trim();
    if arg.is_empty() {
        return Err(());
    }
    match kind.as_str() {
        "file-exists" => Ok(vec![AcceptCheck::FileExists(arg.to_string())]),
        "tests-pass" => Ok(vec![AcceptCheck::TestsPass(arg.to_string())]),
        "command-ok" => Ok(vec![AcceptCheck::CommandOk(arg.to_string())]),
        "contains" => {
            if arg.contains("::") {
                Ok(vec![AcceptCheck::Contains(arg.to_string())])
            } else {
                Err(())
            }
        }
        _ => Err(()),
    }
}

/// One entry of [`score_accept_lines`]: how one job's accept lines
/// scored. `checks` and `parseable` are the same count, kept for
/// symmetry with the spec scorer's shape.
#[derive(Debug, Clone, PartialEq)]
pub struct AcceptScore {
    pub checks: usize,
    pub parseable: usize,
    pub unowned: Vec<String>,
    pub bad_lines: Vec<String>,
    pub passes: bool,
}

/// One entry of [`score_plan_accepts`]: an [`AcceptScore`] tagged
/// with its job key, in plan order.
#[derive(Debug, Clone, PartialEq)]
pub struct JobAcceptScore {
    pub key: String,
    pub checks: usize,
    pub parseable: usize,
    pub unowned: Vec<String>,
    pub bad_lines: Vec<String>,
    pub passes: bool,
}

/// Test-target prefixes for `tests-pass` lines, from
/// `dispatch.py::_ACCEPT_TEST_PREFIXES`.
const ACCEPT_TEST_PREFIXES: [&str; 2] = ["tests.", "tests/"];

/// Score one job's accept lines against the DSP-027 standard.
/// Ownership is checked only when files were given; with no files
/// list every parseable line passes on parse alone. Never raises on
/// malformed input: a bad line is recorded, never fatal. Pure
/// scoring; posts nothing and never refuses a plan. Python's
/// non-list-accept branch is unrepresentable here: `accept` is
/// always a list in the typed plan.
pub fn score_accept_lines(accept: &[String], files: &[String]) -> AcceptScore {
    let mut score = AcceptScore {
        checks: 0,
        parseable: 0,
        unowned: Vec::new(),
        bad_lines: Vec::new(),
        passes: false,
    };
    let owned: Vec<&str> = if files.is_empty() {
        Vec::new()
    } else {
        files.iter().map(|s| s.as_str()).collect()
    };
    for line in accept {
        if line.trim().is_empty() {
            score.bad_lines.push(line.clone());
            continue;
        }
        let checks = match parse_accept_line(line) {
            Ok(checks) => checks,
            Err(()) => {
                score.bad_lines.push(line.clone());
                continue;
            }
        };
        if checks.is_empty() {
            score.bad_lines.push(line.clone());
            continue;
        }
        for check in checks {
            score.checks += 1;
            score.parseable += 1;
            match check {
                AcceptCheck::FileExists(arg) => {
                    if !owned.is_empty() && !owned.contains(&arg.as_str()) {
                        score.unowned.push(arg);
                    }
                }
                AcceptCheck::Contains(arg) => {
                    let path = arg.split("::").next().unwrap_or("").trim();
                    if !owned.is_empty() && !owned.contains(&path) {
                        score.unowned.push(path.to_string());
                    }
                }
                AcceptCheck::TestsPass(arg) => {
                    let target = arg.trim();
                    if !ACCEPT_TEST_PREFIXES.iter().any(|p| target.starts_with(*p)) {
                        score.bad_lines.push(line.clone());
                    }
                }
                AcceptCheck::CommandOk(arg) => {
                    if !owned.is_empty() && !owned.iter().any(|path| arg.contains(*path)) {
                        score.unowned.push(arg);
                    }
                }
            }
        }
    }
    score.passes =
        score.checks >= 1 && score.bad_lines.is_empty() && score.unowned.is_empty();
    score
}

/// Score every job's accept lines in a parsed plan (DSP-027), in
/// plan order, one entry per job. Python raises `PlanError` on a
/// malformed plan; the typed `Plan` cannot be malformed that way,
/// so no error case exists here.
pub fn score_plan_accepts(plan: &Plan) -> Vec<JobAcceptScore> {
    plan.jobs
        .iter()
        .map(|job| {
            let score = score_accept_lines(&job.accept, &job.files);
            JobAcceptScore {
                key: job.key.clone(),
                checks: score.checks,
                parseable: score.parseable,
                unowned: score.unowned,
                bad_lines: score.bad_lines,
                passes: score.passes,
            }
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn plan() -> Plan {
        Plan {
            goal: "g".into(),
            jobs: vec![
                PlanJob { key: "a".into(), title: "A".into(), files: vec!["f.py".into()], deps: vec![], max_attempts: 3, spec: String::new(), accept: vec![] },
                PlanJob { key: "b".into(), title: "B".into(), files: vec![], deps: vec!["a".into()], max_attempts: 3, spec: String::new(), accept: vec![] },
            ],
        }
    }

    fn cplan(jobs: Vec<PlanJob>) -> Plan {
        Plan { goal: "g".into(), jobs }
    }

    fn cjob(key: &str, files: Vec<&str>, spec: &str) -> PlanJob {
        PlanJob { key: key.into(), title: key.into(), files: files.iter().map(|s| s.to_string()).collect(), deps: vec![], max_attempts: 3, spec: spec.into(), accept: vec![] }
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

    fn full_spec() -> String {
        "Goal: add the line. Context: the brief template. Files: intel/brief.py. Steps: add it, run tests. Out of scope: new sections.".into()
    }

    #[test]
    fn spec_full_passes() {
        let s = score_spec_parts(&full_spec(), &["intel/brief.py".to_string()]);
        assert!(s.missing.is_empty(), "got: {s:?}");
        assert!(s.empty.is_empty(), "got: {s:?}");
        assert_eq!(s.files_part_names_owned, Some(true));
        assert!(s.passes);
    }

    #[test]
    fn spec_no_files_given_passes_without_owned_check() {
        let s = score_spec_parts(&full_spec(), &[]);
        assert_eq!(s.files_part_names_owned, None);
        assert!(s.passes);
    }

    #[test]
    fn spec_missing_part_fails() {
        let spec = "Goal: add the line. Context: the brief template. Files: intel/brief.py. Steps: add it, run tests.";
        let s = score_spec_parts(spec, &["intel/brief.py".to_string()]);
        assert_eq!(s.missing, vec!["out of scope".to_string()]);
        assert!(!s.passes);
    }

    #[test]
    fn spec_out_of_order_part_fails() {
        let spec = "Steps: add the line. Goal: add the line. Context: the brief template. Files: intel/brief.py. Out of scope: new sections.";
        let s = score_spec_parts(spec, &["intel/brief.py".to_string()]);
        assert!(!s.passes);
        assert!(s.missing.contains(&"steps".to_string()), "got: {s:?}");
    }

    #[test]
    fn spec_empty_part_fails() {
        let spec = "Goal: add the line. Context: . Files: intel/brief.py. Steps: add it. Out of scope: new sections.";
        let s = score_spec_parts(spec, &["intel/brief.py".to_string()]);
        assert_eq!(s.empty, vec!["context".to_string()]);
        assert!(!s.passes);
    }

    #[test]
    fn spec_title_only_fails() {
        let s = score_spec_parts(
            "Add uptime line to morning brief.",
            &["intel/brief.py".to_string()],
        );
        assert_eq!(
            s.missing,
            vec!["goal", "context", "files", "steps", "out of scope"]
                .iter()
                .map(|l| l.to_string())
                .collect::<Vec<String>>()
        );
        assert!(!s.passes);
    }

    #[test]
    fn spec_files_part_must_name_owned_file() {
        let spec = "Goal: add the line. Context: the brief template. Files: intel/other.py. Steps: add it. Out of scope: new sections.";
        let s = score_spec_parts(spec, &["intel/brief.py".to_string()]);
        assert_eq!(s.files_part_names_owned, Some(false));
        assert!(!s.passes);
    }

    #[test]
    fn spec_hyphenated_out_of_scope_passes() {
        let spec = "Goal: add the line. Context: the brief template. Files: intel/brief.py. Steps: add it. Out-of-scope: new sections.";
        let s = score_spec_parts(spec, &["intel/brief.py".to_string()]);
        assert!(s.passes, "got: {s:?}");
    }

    #[test]
    fn spec_plan_scores_in_plan_order() {
        let p = cplan(vec![
            cjob("one", vec!["intel/brief.py"], &full_spec()),
            cjob("two", vec!["intel/brief.py"], "Add the line."),
        ]);
        let scores = score_plan_specs(&p);
        assert_eq!(scores.len(), 2);
        assert_eq!(scores[0].key, "one");
        assert!(scores[0].passes);
        assert_eq!(scores[1].key, "two");
        assert!(!scores[1].passes);
    }

    fn ajob(key: &str, files: Vec<&str>, accept: Vec<&str>) -> PlanJob {
        PlanJob { key: key.into(), title: key.into(), files: files.iter().map(|s| s.to_string()).collect(), deps: vec![], max_attempts: 3, spec: String::new(), accept: accept.iter().map(|s| s.to_string()).collect() }
    }

    fn accept_lines() -> Vec<String> {
        vec![
            "file-exists: intel/brief.py".into(),
            "tests-pass: tests.test_brief".into(),
            "contains: intel/brief.py :: hello".into(),
            "command-ok: python3 -m py_compile intel/brief.py".into(),
        ]
    }

    #[test]
    fn accept_all_kinds_pass_with_owned_files() {
        let s = score_accept_lines(&accept_lines(), &["intel/brief.py".to_string()]);
        assert_eq!(s.checks, 4);
        assert_eq!(s.parseable, 4);
        assert!(s.unowned.is_empty(), "got: {s:?}");
        assert!(s.bad_lines.is_empty(), "got: {s:?}");
        assert!(s.passes);
    }

    #[test]
    fn accept_no_files_skips_ownership() {
        let s = score_accept_lines(&accept_lines(), &[]);
        assert!(s.passes);
        let s = score_accept_lines(&["file-exists: intel/other.py".to_string()], &[]);
        assert!(s.passes);
    }

    #[test]
    fn accept_unowned_paths_fail() {
        let s = score_accept_lines(&["file-exists: intel/other.py".to_string()], &["intel/brief.py".to_string()]);
        assert_eq!(s.unowned, vec!["intel/other.py".to_string()]);
        assert!(!s.passes);
        let s = score_accept_lines(&["contains: intel/other.py :: hello".to_string()], &["intel/brief.py".to_string()]);
        assert_eq!(s.unowned, vec!["intel/other.py".to_string()]);
        assert!(!s.passes);
        let s = score_accept_lines(&["command-ok: make test".to_string()], &["intel/brief.py".to_string()]);
        assert_eq!(s.unowned, vec!["make test".to_string()]);
        assert!(!s.passes);
    }

    #[test]
    fn accept_bad_lines_fail() {
        let lines = vec![
            "".to_string(),
            "   ".to_string(),
            "no separator here".to_string(),
            "bogus-kind: intel/brief.py".to_string(),
            "file-exists:".to_string(),
            "contains: intel/brief.py".to_string(),
            "# file-exists: intel/brief.py".to_string(),
        ];
        let s = score_accept_lines(&lines, &["intel/brief.py".to_string()]);
        assert_eq!(s.checks, 0);
        assert_eq!(s.bad_lines.len(), 7);
        assert!(!s.passes);
    }

    #[test]
    fn accept_bad_test_prefix_counts_but_fails() {
        let s = score_accept_lines(&["tests-pass: foo.test_brief".to_string()], &["intel/brief.py".to_string()]);
        assert_eq!(s.checks, 1);
        assert_eq!(s.bad_lines, vec!["tests-pass: foo.test_brief".to_string()]);
        assert!(!s.passes);
        let s = score_accept_lines(&["tests-pass: tests/test_brief.py".to_string()], &[]);
        assert!(s.passes);
    }

    #[test]
    fn accept_plan_scores_in_plan_order() {
        let p = cplan(vec![
            ajob("one", vec!["intel/brief.py"], vec!["file-exists: intel/brief.py"]),
            ajob("two", vec!["intel/brief.py"], vec!["file-exists: intel/other.py"]),
        ]);
        let scores = score_plan_accepts(&p);
        assert_eq!(scores.len(), 2);
        assert_eq!(scores[0].key, "one");
        assert!(scores[0].passes);
        assert_eq!(scores[1].key, "two");
        assert!(!scores[1].passes);
    }
}
