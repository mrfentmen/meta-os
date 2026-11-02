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
    /// Job capability requirements. The shape-only parser leaves this
    /// empty; the detail renderer reads it, so a fuller parse fills
    /// it in.
    pub req: Vec<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Plan {
    pub goal: String,
    /// Plan summary sentence. The shape-only parser leaves this empty;
    /// the summary renderers read it, so a fuller parse fills it in.
    pub summary: String,
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
        out.push(PlanJob { key, title, files: Vec::new(), deps: Vec::new(), max_attempts: 3, spec: String::new(), accept: Vec::new(), req: Vec::new() });
    }
    Ok(Plan { goal: goal.to_string(), summary: String::new(), jobs: out })
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

/// One attempt-budget clamp, ported from the `clamps` entries
/// `plan_summary` renders: the job key plus the requested and
/// clamped `max_attempts` values.
#[derive(Debug, Clone, PartialEq)]
pub struct PlanClamp {
    pub key: String,
    pub requested: i64,
    pub clamped: i64,
}

/// Python `repr` for a short string: single quotes, with backslash
/// and single quote escaped. Plan keys are identifiers in practice,
/// so no other escaping is needed here.
fn repr_str(s: &str) -> String {
    let mut out = String::from("'");
    for c in s.chars() {
        if c == '\'' || c == '\\' {
            out.push('\\');
        }
        out.push(c);
    }
    out.push('\'');
    out
}

/// Render a parsed plan as a human-readable summary string, ported
/// from `dispatch.py::plan_summary`. First line is the plan's
/// summary, then one line per job in plan order ("- key: title
/// (attempts N)"), then one line per clamp ("clamped: job 'key':
/// max_attempts 99 -> 5"). With no clamps there is no clamp section
/// at all. Pure string building; posts nothing and touches no
/// state. Python's dict-shape failures are unrepresentable here:
/// `Plan` always carries a jobs list.
pub fn plan_summary(plan: &Plan, clamps: &[PlanClamp]) -> String {
    let mut lines = vec![plan.summary.clone()];
    for job in &plan.jobs {
        lines.push(format!(
            "- {}: {} (attempts {})",
            job.key, job.title, job.max_attempts
        ));
    }
    for clamp in clamps {
        lines.push(format!(
            "clamped: job {}: max_attempts {} -> {}",
            repr_str(&clamp.key),
            clamp.requested,
            clamp.clamped
        ));
    }
    lines.join("\n")
}

/// Render a parsed plan as one plain-English paragraph (DSP-025),
/// ported from `dispatch.py::plan_paragraph`. The paragraph is the
/// dashboard form of a plan: the plan's summary sentence first,
/// then every job named once, in posting order, each with the files
/// it owns in parentheses — "First, ..., then ..., and finally ...".
/// A one-job plan reads "It does ...". A single paragraph with no
/// newlines, so the dashboard panel can show the whole plan without
/// a multi-line block. The paragraph never names a likely claimant:
/// a parsed plan carries no claimant field, and inventing one would
/// break the brief lane's ground rule that a brief never invents a
/// fact. Errors when an explicit order does not cover exactly the
/// plan's jobs, so a paragraph can never silently drop a job. Pure
/// string building; posts nothing.
pub fn plan_paragraph(plan: &Plan, order: Option<&[String]>) -> Result<String, PlanError> {
    use std::collections::HashMap;
    let mut by_key: HashMap<&str, &PlanJob> = HashMap::new();
    for job in &plan.jobs {
        by_key.insert(job.key.as_str(), job);
    }
    let default_order: Vec<String> = plan.jobs.iter().map(|j| j.key.clone()).collect();
    let order: &[String] = match order {
        Some(o) => o,
        None => &default_order,
    };
    let mut sorted_order: Vec<&str> = order.iter().map(|s| s.as_str()).collect();
    sorted_order.sort_unstable();
    let mut sorted_keys: Vec<&str> = by_key.keys().copied().collect();
    sorted_keys.sort_unstable();
    if sorted_order != sorted_keys {
        return Err(fail("plan: posting order must cover exactly the plan's jobs"));
    }
    let mut summary = plan.summary.trim().to_string();
    if !summary.is_empty() && !summary.ends_with('.') {
        summary.push('.');
    }
    let mut clauses: Vec<String> = Vec::new();
    for key in order {
        let job = by_key[key.as_str()];
        if job.files.is_empty() {
            clauses.push(job.title.clone());
        } else {
            clauses.push(format!("{} (in {})", job.title, job.files.join(", ")));
        }
    }
    if clauses.is_empty() {
        return Ok(summary);
    }
    let body = if clauses.len() == 1 {
        format!("It does {}.", clauses[0])
    } else if clauses.len() == 2 {
        format!("First, {}, then {}.", clauses[0], clauses[1])
    } else {
        format!(
            "First, {}, then {}, and finally {}.",
            clauses[0],
            clauses[1..clauses.len() - 1].join(", then "),
            clauses[clauses.len() - 1]
        )
    };
    Ok(if summary.is_empty() {
        body
    } else {
        format!("{summary} {body}")
    })
}

/// Render a parsed plan in full for the DSP-006 dry-run, ported
/// from `dispatch.py::render_plan_detail`. First line is the plan's
/// summary, second line is the posting order ("jobs in posting
/// order: base -> api -> panel -> docs"), then one block per job in
/// posting order: title and attempt budget on the header line, then
/// files, deps ("none" when empty), req ("none" when the job names
/// no capability), and accept lines, each comma/semicolon joined on
/// its own line. Clamp lines (same shape as plan_summary) close the
/// output; warning lines (DSP-013 plan_size_warnings output, empty
/// by default) close the output after the clamp lines, so a large
/// plan's guard message is visible in the dry-run too. Errors when
/// the order does not cover exactly the plan's jobs, so a dry-run
/// can never render a partial plan. Posts nothing; pure string
/// building.
pub fn render_plan_detail(plan: &Plan, order: &[String], clamps: &[PlanClamp], warnings: &[String]) -> Result<String, PlanError> {
    use std::collections::HashMap;
    let mut by_key: HashMap<&str, &PlanJob> = HashMap::new();
    for job in &plan.jobs {
        by_key.insert(job.key.as_str(), job);
    }
    let mut sorted_order: Vec<&str> = order.iter().map(|s| s.as_str()).collect();
    sorted_order.sort_unstable();
    let mut sorted_keys: Vec<&str> = by_key.keys().copied().collect();
    sorted_keys.sort_unstable();
    if sorted_order != sorted_keys {
        return Err(fail("plan: posting order must cover exactly the plan's jobs"));
    }
    let mut lines = vec![
        plan.summary.clone(),
        format!("jobs in posting order: {}", order.join(" -> ")),
    ];
    for key in order {
        let job = by_key[key.as_str()];
        lines.push(format!("- {key}: {} (attempts {})", job.title, job.max_attempts));
        lines.push(format!("  files: {}", job.files.join(", ")));
        lines.push(format!("  deps: {}", if job.deps.is_empty() { "none".to_string() } else { job.deps.join(", ") }));
        lines.push(format!("  req: {}", if job.req.is_empty() { "none".to_string() } else { job.req.join(", ") }));
        lines.push(format!("  accept: {}", job.accept.join("; ")));
    }
    for clamp in clamps {
        lines.push(format!(
            "clamped: job {}: max_attempts {} -> {}",
            repr_str(&clamp.key),
            clamp.requested,
            clamp.clamped
        ));
    }
    for warning in warnings {
        lines.push(warning.clone());
    }
    Ok(lines.join("\n"))
}

/// DSP-013 size limits: 12 jobs, 40 distinct files.
pub const MAX_PLAN_JOBS: usize = 12;
pub const MAX_PLAN_FILES: usize = 40;

/// DSP-013 size warnings for a parsed plan. Pure function: one warning
/// per breached limit, jobs warning first, or an empty list inside both
/// limits. A plan at exactly a limit triggers nothing. Distinct files are
/// counted by path, so one path owned twice still counts once. The
/// Python original raises PlanError on a malformed plan shape; the typed
/// `Plan` here cannot carry that shape, so there is no error case.
pub fn plan_size_warnings(plan: &Plan) -> Vec<String> {
    use std::collections::HashSet;
    let mut warnings = Vec::new();
    if plan.jobs.len() > MAX_PLAN_JOBS {
        warnings.push(format!(
            "plan size guardrail: {} jobs exceeds the {}-job limit; this plan needs a second \
             confirmation before posting. Split suggestion: break it into smaller plans of at most {} \
             jobs each (for example one plan per dependency chain), posted in dependency order, and approve \
             each part separately",
            plan.jobs.len(),
            MAX_PLAN_JOBS,
            MAX_PLAN_JOBS
        ));
    }
    let mut files: HashSet<&str> = HashSet::new();
    for job in &plan.jobs {
        for path in &job.files {
            files.insert(path.as_str());
        }
    }
    if files.len() > MAX_PLAN_FILES {
        warnings.push(format!(
            "plan size guardrail: {} files exceeds the {}-file limit; this plan needs a second \
             confirmation before posting. Split suggestion: break it into smaller plans touching \
             at most {} files each, posted in dependency order, and approve each part separately",
            files.len(),
            MAX_PLAN_FILES,
            MAX_PLAN_FILES
        ));
    }
    warnings
}

/// Second-confirmation prompt for a large plan. Names the job count and
/// the distinct file count. The `warnings` argument mirrors the Python
/// original, which accepts `plan_size_warnings` output only to keep the
/// caller from recomputing it; the prompt itself is built from the
/// counts, so the argument is ignored here too. Pure string building;
/// posts nothing.
pub fn large_plan_prompt(plan: &Plan, _warnings: Option<&[String]>) -> String {
    use std::collections::HashSet;
    let mut files: HashSet<&str> = HashSet::new();
    for job in &plan.jobs {
        for path in &job.files {
            files.insert(path.as_str());
        }
    }
    format!(
        "This plan is large ({} jobs, {} files) and needs a second confirmation. Post it anyway? [y/N] ",
        plan.jobs.len(),
        files.len()
    )
}

/// Full read-only validation pipeline, ported from
/// `dispatch.py::validated_plan`, over a typed `Plan`.
///
/// Runs, in Python's order: file-overlap, contradiction, dependency
/// graph (posting order), then attempt-budget clamping. Returns the
/// clamped plan, its posting order, and the clamp reports (one per
/// job whose budget actually changed, in plan order). Raises the
/// first failing check's error, so the plan a human approves is
/// exactly the plan the gates passed. Posts nothing.
///
/// Two honest gaps against the Python original, kept visible rather
/// than papered over: Python takes plan JSON text and strict-parses
/// it first, while this takes an already-shaped `Plan` — the JSON
/// text parse is still owed as its own slice. And the clamp range
/// here is this branch's existing `clamp_attempt_budgets` (1..10),
/// not Python's 1..5; that divergence predates this slice and is
/// flagged for Milo/Pax, not silently changed here.
pub fn validated_plan(mut plan: Plan) -> Result<(Plan, Vec<String>, Vec<PlanClamp>), PlanError> {
    check_file_overlap(&plan)?;
    check_no_contradiction(&plan)?;
    let order = check_dep_graph(&plan)?;
    let requested: Vec<(String, i64)> = plan.jobs.iter().map(|j| (j.key.clone(), j.max_attempts)).collect();
    clamp_attempt_budgets(&mut plan);
    let clamps: Vec<PlanClamp> = requested
        .into_iter()
        .zip(plan.jobs.iter())
        .filter_map(|((key, requested), job)| {
            if job.max_attempts != requested {
                Some(PlanClamp { key, requested, clamped: job.max_attempts })
            } else {
                None
            }
        })
        .collect();
    Ok((plan, order, clamps))
}

/// Validate a plan and render it for a dry run, ported from
/// `dispatch.py::dry_run_plan`.
///
/// Runs `validated_plan`, then renders the clamped plan with
/// `render_plan_detail` (size warnings included). Returns the detail
/// string, or the first failing check's error — a dry run shows
/// either the full valid plan or an error, never a partial plan.
/// Posts nothing, claims nothing, writes no record.
pub fn dry_run_plan(plan: Plan) -> Result<String, PlanError> {
    let (plan, order, clamps) = validated_plan(plan)?;
    let warnings = plan_size_warnings(&plan);
    render_plan_detail(&plan, &order, &clamps, &warnings)
}

/// The single job key of the DSP-017 fallback plan.
pub const FALLBACK_JOB_KEY: &str = "fallback-job";

/// Build the DSP-017 fallback plan for a raw goal, ported from
/// `dispatch.py::fallback_plan`.
///
/// Returns a single-job plan: summary, title, and spec are all
/// marked FALLBACK, and the spec carries the raw goal verbatim
/// after the FALLBACK marker, so the job is the goal itself,
/// not a paraphrase of it. The job carries no files, no deps,
/// and no accept lines — Spark supplied nothing usable to derive
/// them from, and this function invents neither. The DSP-007
/// approval gate is where a human decides whether the raw-goal
/// job posts as-is. The title is the goal's first non-empty
/// line, trimmed, truncated to 97 chars plus `...` when it runs
/// over 100 chars. An empty or whitespace-only goal is refused
/// with `PlanError`. Posts nothing.
///
/// Rust adaptation, stated not hidden: Python's fallback dict
/// has no goal field, while this crate's `Plan` requires one,
/// so `goal` is filled with the raw goal verbatim — the same
/// handling `parse_plan` gives its goal argument. Truncation
/// counts Unicode scalar values, matching Python's slicing.
pub fn fallback_plan(goal: &str) -> Result<Plan, PlanError> {
    if goal.trim().is_empty() {
        return Err(fail("fallback plan: goal must be a non-empty string"));
    }
    let first_line = goal
        .lines()
        .find(|l| !l.trim().is_empty())
        .map(|l| l.trim())
        .unwrap_or("");
    let title_line = if first_line.chars().count() > 100 {
        let mut t: String = first_line.chars().take(97).collect();
        t.push_str("...");
        t
    } else {
        first_line.to_string()
    };
    Ok(Plan {
        goal: goal.to_string(),
        summary: "FALLBACK plan: Spark returned malformed JSON twice, so no structured plan was produced; this single job carries the raw goal as its spec"
            .to_string(),
        jobs: vec![PlanJob {
            key: FALLBACK_JOB_KEY.to_string(),
            title: format!("FALLBACK: {title_line}"),
            files: Vec::new(),
            deps: Vec::new(),
            max_attempts: 3,
            spec: format!(
                "FALLBACK: Spark returned malformed JSON twice, so no structured plan was produced. Raw goal, verbatim:\n\n{goal}"
            ),
            accept: Vec::new(),
            req: Vec::new(),
        }],
    })
}

/// Build the interactive approval prompt for a plan, ported from
/// `dispatch.py::approval_prompt`.
///
/// Names the job count ("Post this plan (4 jobs)? [y/N] "), so the
/// human answers about this plan, not in the abstract. Pure string
/// building; posts nothing.
pub fn approval_prompt(plan: &Plan) -> String {
    format!("Post this plan ({} jobs)? [y/N] ", plan.jobs.len())
}

/// Decide whether a validated plan may be posted (DSP-007), ported
/// from `dispatch.py::request_approval`.
///
/// The single gate between a plan and the DSP-008 poster. Returns
/// true only when a human has approved, by exactly one of two routes:
/// `approve` (the caller already holds a human approval, CLI
/// --approve flag or dashboard approve action), or `confirm`, a prompt
/// function called once with [`approval_prompt`] — only a trimmed,
/// case-insensitive "y" or "yes" approves, any other answer denies,
/// and a closed prompt denies instead of crashing. With no flag and
/// no prompt there is no human in the loop, so the answer is false:
/// non-interactive runs must pass --approve explicitly, and a default
/// never approves.
///
/// DSP-013 second confirmation: when [`plan_size_warnings`] is
/// non-empty, the first approval alone is not enough. The plan also
/// needs a second confirmation, by exactly one of two routes:
/// `confirm_large` (the caller already holds it, CLI --confirm-large
/// flag), or the `confirm` function called a second time with
/// [`large_plan_prompt`], answered y/yes. Any other second answer, a
/// closed prompt on the second call, or no second confirmation at all
/// denies the large plan, even when the first approval passed.
/// Never posts, never claims, never touches job state, and never
/// mutates the plan: approval is a decision, not a side effect.
///
/// Rust adaptations, stated not hidden: Python's `confirm` is a
/// prompt function (input) whose `EOFError` denies; here `confirm`
/// returns `None` for a closed prompt, which denies the same way.
/// Python raises `PlanError` on a malformed plan shape; the typed
/// `Plan` here cannot carry that shape, so there is no error case —
/// the same note the size-warning port carries.
pub fn request_approval(
    plan: &Plan,
    approve: bool,
    confirm: Option<&mut dyn FnMut(&str) -> Option<String>>,
    confirm_large: bool,
) -> bool {
    fn is_yes(answer: &str) -> bool {
        let a = answer.trim().to_ascii_lowercase();
        a == "y" || a == "yes"
    }
    let mut confirm = confirm;
    let first = if approve {
        true
    } else {
        match confirm.as_mut() {
            None => return false,
            Some(f) => match f(&approval_prompt(plan)) {
                Some(answer) => is_yes(&answer),
                None => false,
            },
        }
    };
    if !first {
        return false;
    }
    let warnings = plan_size_warnings(plan);
    if warnings.is_empty() {
        return true;
    }
    if confirm_large {
        return true;
    }
    match confirm.as_mut() {
        None => false,
        Some(f) => match f(&large_plan_prompt(plan, Some(&warnings))) {
            Some(answer) => is_yes(&answer),
            None => false,
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn plan() -> Plan {
        Plan {
            goal: "g".into(),
            summary: String::new(),
            jobs: vec![
                PlanJob { key: "a".into(), title: "A".into(), files: vec!["f.py".into()], deps: vec![], max_attempts: 3, spec: String::new(), accept: vec![], req: vec![] },
                PlanJob { key: "b".into(), title: "B".into(), files: vec![], deps: vec!["a".into()], max_attempts: 3, spec: String::new(), accept: vec![], req: vec![] },
            ],
        }
    }

    fn cplan(jobs: Vec<PlanJob>) -> Plan {
        Plan { goal: "g".into(), summary: String::new(), jobs }
    }

    fn cjob(key: &str, files: Vec<&str>, spec: &str) -> PlanJob {
        PlanJob { key: key.into(), title: key.into(), files: files.iter().map(|s| s.to_string()).collect(), deps: vec![], max_attempts: 3, spec: spec.into(), accept: vec![], req: vec![] }
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
        PlanJob { key: key.into(), title: key.into(), files: files.iter().map(|s| s.to_string()).collect(), deps: vec![], max_attempts: 3, spec: String::new(), accept: accept.iter().map(|s| s.to_string()).collect(), req: vec![] }
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

    #[test]
    fn summary_lines_jobs_in_plan_order() {
        let mut p = plan();
        p.summary = "Do the thing".into();
        assert_eq!(
            plan_summary(&p, &[]),
            "Do the thing\n- a: A (attempts 3)\n- b: B (attempts 3)"
        );
    }

    #[test]
    fn summary_clamps_appended_and_empty_summary_keeps_first_line() {
        let mut p = plan();
        p.summary = "Do the thing".into();
        let clamps = vec![PlanClamp { key: "b".into(), requested: 99, clamped: 10 }];
        assert_eq!(
            plan_summary(&p, &clamps),
            "Do the thing\n- a: A (attempts 3)\n- b: B (attempts 3)\nclamped: job 'b': max_attempts 99 -> 10"
        );
        let p = plan();
        assert_eq!(
            plan_summary(&p, &[]),
            "\n- a: A (attempts 3)\n- b: B (attempts 3)"
        );
    }

    #[test]
    fn paragraph_two_jobs_adds_period_and_files() {
        let mut p = plan();
        p.summary = "Ship the fix".into();
        assert_eq!(
            plan_paragraph(&p, None).unwrap(),
            "Ship the fix. First, A (in f.py), then B."
        );
    }

    #[test]
    fn paragraph_one_job_and_empty_plan() {
        let mut p = cplan(vec![cjob("only", vec![], "")]);
        p.summary = String::new();
        assert_eq!(plan_paragraph(&p, None).unwrap(), "It does only.");
        let mut p = cplan(vec![]);
        p.summary = "Nothing to do".into();
        assert_eq!(plan_paragraph(&p, None).unwrap(), "Nothing to do.");
    }

    #[test]
    fn paragraph_three_jobs_finally_form_and_explicit_order() {
        let mut p = cplan(vec![
            cjob("a", vec!["f.py"], ""),
            cjob("b", vec![], ""),
            cjob("c", vec![], ""),
        ]);
        p.summary = "Do it.".into();
        assert_eq!(
            plan_paragraph(&p, None).unwrap(),
            "Do it. First, a (in f.py), then b, and finally c."
        );
        let order = vec!["c".to_string(), "a".to_string(), "b".to_string()];
        assert_eq!(
            plan_paragraph(&p, Some(&order)).unwrap(),
            "Do it. First, c, then a (in f.py), and finally b."
        );
    }

    #[test]
    fn paragraph_partial_order_refused() {
        let p = plan();
        let order = vec!["a".to_string()];
        let err = plan_paragraph(&p, Some(&order)).unwrap_err();
        assert!(err.0.contains("posting order"), "got: {err}");
    }

    #[test]
    fn detail_renders_blocks_clamps_and_warnings_in_posting_order() {
        let p = Plan {
            goal: "g".into(),
            summary: "Do the thing".into(),
            jobs: vec![
                PlanJob { key: "base".into(), title: "Base".into(), files: vec!["a.py".into(), "b.py".into()], deps: vec![], max_attempts: 3, spec: String::new(), accept: vec!["file-exists: a.py".into(), "tests-pass: tests/test_a.py".into()], req: vec!["cap-x".into()] },
                PlanJob { key: "api".into(), title: "Api".into(), files: vec![], deps: vec!["base".into()], max_attempts: 5, spec: String::new(), accept: vec![], req: vec![] },
            ],
        };
        let order = vec!["api".to_string(), "base".to_string()];
        let clamps = vec![PlanClamp { key: "api".into(), requested: 99, clamped: 10 }];
        let warnings = vec!["plan size guardrail: too big".to_string()];
        assert_eq!(
            render_plan_detail(&p, &order, &clamps, &warnings).unwrap(),
            "Do the thing\njobs in posting order: api -> base\n- api: Api (attempts 5)\n  files: \n  deps: base\n  req: none\n  accept: \n- base: Base (attempts 3)\n  files: a.py, b.py\n  deps: none\n  req: cap-x\n  accept: file-exists: a.py; tests-pass: tests/test_a.py\nclamped: job 'api': max_attempts 99 -> 10\nplan size guardrail: too big"
        );
    }

    #[test]
    fn detail_partial_order_refused() {
        let p = plan();
        let order = vec!["a".to_string()];
        let err = render_plan_detail(&p, &order, &[], &[]).unwrap_err();
        assert!(err.0.contains("posting order"), "got: {err}");
    }

    #[test]
    fn size_warnings_empty_inside_limits() {
        assert!(plan_size_warnings(&plan()).is_empty());
    }

    #[test]
    fn size_warnings_exact_limit_quiet() {
        let mut jobs = Vec::new();
        for i in 0..12 {
            let mut job = cjob(&format!("j{i}"), vec![], "");
            job.files = (0..4).map(|k| format!("f{k}.py")).collect();
            jobs.push(job);
        }
        // 12 jobs, but only 4 distinct files shared across them.
        assert!(plan_size_warnings(&cplan(jobs)).is_empty());
        // 12 jobs, 40 distinct files: still exactly at both limits.
        let mut jobs = Vec::new();
        for i in 0..12 {
            let mut job = cjob(&format!("j{i}"), vec![], "");
            if i == 0 {
                job.files = (0..40).map(|k| format!("f{k}.py")).collect();
            }
            jobs.push(job);
        }
        assert!(plan_size_warnings(&cplan(jobs)).is_empty());
    }

    #[test]
    fn size_warnings_job_limit_names_count_and_limit() {
        let jobs: Vec<PlanJob> = (0..13).map(|i| cjob(&format!("j{i}"), vec![], "")).collect();
        let warnings = plan_size_warnings(&cplan(jobs));
        assert_eq!(warnings.len(), 1);
        assert_eq!(
            warnings[0],
            "plan size guardrail: 13 jobs exceeds the 12-job limit; this plan needs a second \
             confirmation before posting. Split suggestion: break it into smaller plans of at most 12 \
             jobs each (for example one plan per dependency chain), posted in dependency order, and approve \
             each part separately"
        );
    }

    #[test]
    fn size_warnings_file_limit_counts_distinct_paths_once() {
        let mut job = cjob("big", vec![], "");
        job.files = (0..41).map(|k| format!("f{k}.py")).collect();
        job.files.push("f0.py".into());
        job.files.push("f0.py".into());
        let warnings = plan_size_warnings(&cplan(vec![job]));
        assert_eq!(warnings.len(), 1);
        assert!(
            warnings[0].starts_with("plan size guardrail: 41 files exceeds the 40-file limit;"),
            "got: {}",
            warnings[0]
        );
    }

    #[test]
    fn size_warnings_both_breaches_jobs_first() {
        let mut jobs: Vec<PlanJob> = (0..13).map(|i| cjob(&format!("j{i}"), vec![], "")).collect();
        jobs[0].files = (0..41).map(|k| format!("f{k}.py")).collect();
        let warnings = plan_size_warnings(&cplan(jobs));
        assert_eq!(warnings.len(), 2);
        assert!(warnings[0].contains("13 jobs"), "got: {}", warnings[0]);
        assert!(warnings[1].contains("41 files"), "got: {}", warnings[1]);
    }

    #[test]
    fn large_plan_prompt_names_counts_and_second_confirmation() {
        assert_eq!(
            large_plan_prompt(&plan(), None),
            "This plan is large (2 jobs, 1 files) and needs a second confirmation. Post it anyway? [y/N] "
        );
        let warnings = plan_size_warnings(&plan());
        assert_eq!(
            large_plan_prompt(&plan(), Some(&warnings)),
            "This plan is large (2 jobs, 1 files) and needs a second confirmation. Post it anyway? [y/N] "
        );
    }

    #[test]
    fn validated_plan_returns_clamped_plan_order_and_clamps() {
        let mut p = plan();
        p.jobs[1].max_attempts = 99;
        let (clamped, order, clamps) = validated_plan(p).unwrap();
        assert_eq!(order, vec!["a".to_string(), "b".to_string()]);
        assert_eq!(clamped.jobs[1].max_attempts, 10);
        assert_eq!(clamps, vec![PlanClamp { key: "b".into(), requested: 99, clamped: 10 }]);
    }

    #[test]
    fn validated_plan_first_failure_wins() {
        let mut p = plan();
        p.jobs[1].files = vec!["f.py".into()];
        p.jobs[1].deps = vec![];
        let err = validated_plan(p).unwrap_err();
        assert!(err.0.contains("file overlap"), "got: {}", err.0);
    }

    #[test]
    fn validated_plan_cycle_errors() {
        let mut p = plan();
        p.jobs[0].deps = vec!["b".into()];
        p.jobs[1].deps = vec!["a".into()];
        p.jobs[1].files = vec!["g.py".into()];
        let err = validated_plan(p).unwrap_err();
        assert!(err.0.contains("dependency cycle"), "got: {}", err.0);
    }

    #[test]
    fn dry_run_plan_renders_clamped_detail() {
        let mut p = plan();
        p.summary = "Do the thing".into();
        p.jobs[0].max_attempts = 99;
        assert_eq!(
            dry_run_plan(p).unwrap(),
            "Do the thing\njobs in posting order: a -> b\n- a: A (attempts 10)\n  files: f.py\n  deps: none\n  req: none\n  accept: \n- b: B (attempts 3)\n  files: \n  deps: a\n  req: none\n  accept: \nclamped: job 'a': max_attempts 99 -> 10"
        );
    }

    #[test]
    fn dry_run_plan_error_propagates() {
        let mut p = plan();
        p.jobs[1].files = vec!["f.py".into()];
        p.jobs[1].deps = vec![];
        assert!(dry_run_plan(p).is_err());
    }

    #[test]
    fn fallback_plan_single_job_carries_raw_goal_verbatim() {
        let p = fallback_plan("Fix the leak\nsecond line").unwrap();
        assert_eq!(p.jobs.len(), 1);
        let j = &p.jobs[0];
        assert_eq!(j.key, "fallback-job");
        assert_eq!(j.title, "FALLBACK: Fix the leak");
        assert_eq!(
            j.spec,
            "FALLBACK: Spark returned malformed JSON twice, so no structured plan was produced. Raw goal, verbatim:\n\nFix the leak\nsecond line"
        );
        assert!(j.files.is_empty());
        assert!(j.deps.is_empty());
        assert_eq!(j.max_attempts, 3);
        assert!(j.accept.is_empty());
        assert_eq!(
            p.summary,
            "FALLBACK plan: Spark returned malformed JSON twice, so no structured plan was produced; this single job carries the raw goal as its spec"
        );
    }

    #[test]
    fn fallback_plan_title_skips_blank_lines_and_truncates_at_100() {
        let p = fallback_plan("\n  \nDo the thing").unwrap();
        assert_eq!(p.jobs[0].title, "FALLBACK: Do the thing");
        let long = "x".repeat(101);
        let p = fallback_plan(&long).unwrap();
        assert_eq!(p.jobs[0].title, format!("FALLBACK: {}...", "x".repeat(97)));
        let exact = "y".repeat(100);
        let p = fallback_plan(&exact).unwrap();
        assert_eq!(p.jobs[0].title, format!("FALLBACK: {exact}"));
    }

    #[test]
    fn fallback_plan_empty_goal_refused() {
        let err = fallback_plan("   \n  ").unwrap_err();
        assert!(err.0.contains("fallback plan: goal must be a non-empty string"), "got: {err}");
    }

    fn large_plan() -> Plan {
        // 13 jobs over the 12-job limit, so plan_size_warnings is non-empty.
        let jobs = (0..13)
            .map(|i| cjob(&format!("j{i}"), vec![], "Steps: create file intel/a.py."))
            .collect();
        cplan(jobs)
    }

    #[test]
    fn approval_prompt_names_the_job_count() {
        assert_eq!(approval_prompt(&plan()), "Post this plan (2 jobs)? [y/N] ");
    }

    #[test]
    fn approval_flag_approves_without_prompt() {
        let mut calls = 0;
        let mut confirm = |_: &str| {
            calls += 1;
            Some("y".to_string())
        };
        assert!(request_approval(&plan(), true, Some(&mut confirm), false));
        assert_eq!(calls, 0);
    }

    #[test]
    fn approval_interactive_yes_variants_approve() {
        for answer in ["y", "Y", "yes", "YES", "  y  ", "Yes"] {
            let mut confirm = |_: &str| Some(answer.to_string());
            assert!(
                request_approval(&plan(), false, Some(&mut confirm), false),
                "answer {answer:?} should approve"
            );
        }
    }

    #[test]
    fn approval_interactive_other_answers_deny() {
        for answer in ["n", "N", "no", "", "maybe", "ye", "yep"] {
            let mut confirm = |_: &str| Some(answer.to_string());
            assert!(
                !request_approval(&plan(), false, Some(&mut confirm), false),
                "answer {answer:?} should deny"
            );
        }
    }

    #[test]
    fn approval_prompt_passed_to_confirm_once_for_small_plan() {
        let mut seen: Vec<String> = Vec::new();
        let mut confirm = |prompt: &str| {
            seen.push(prompt.to_string());
            Some("n".to_string())
        };
        assert!(!request_approval(&plan(), false, Some(&mut confirm), false));
        assert_eq!(seen.len(), 1);
        assert_eq!(seen[0], approval_prompt(&plan()));
    }

    #[test]
    fn approval_closed_prompt_denies_instead_of_crashing() {
        let mut confirm = |_: &str| None;
        assert!(!request_approval(&plan(), false, Some(&mut confirm), false));
    }

    #[test]
    fn approval_no_prompt_and_no_flag_denies() {
        assert!(!request_approval(&plan(), false, None, false));
    }

    #[test]
    fn approval_gate_does_not_mutate_the_plan() {
        let before = plan();
        let mut confirm = |_: &str| Some("y".to_string());
        assert!(request_approval(&before, true, Some(&mut confirm), false));
        let mut confirm = |_: &str| Some("y".to_string());
        assert!(request_approval(&before, false, Some(&mut confirm), false));
        assert_eq!(before, plan());
    }

    #[test]
    fn approval_large_plan_first_approval_alone_denies() {
        // Flag route, no second confirmation held, no prompt: denied.
        assert!(!request_approval(&large_plan(), true, None, false));
        // Prompt route, first yes, second no: denied, prompt called twice.
        let mut seen: Vec<String> = Vec::new();
        let mut answers = ["y", "n"].iter();
        let mut confirm = |prompt: &str| {
            seen.push(prompt.to_string());
            answers.next().map(|a| a.to_string())
        };
        assert!(!request_approval(&large_plan(), false, Some(&mut confirm), false));
        assert_eq!(seen.len(), 2);
        assert_eq!(seen[1], large_plan_prompt(&large_plan(), Some(&plan_size_warnings(&large_plan()))));
    }

    #[test]
    fn approval_large_plan_second_confirmation_approves() {
        assert!(request_approval(&large_plan(), true, None, true));
        let mut answers = ["y", "yes"].iter();
        let mut confirm = |_: &str| answers.next().map(|a| a.to_string());
        assert!(request_approval(&large_plan(), false, Some(&mut confirm), false));
    }

    #[test]
    fn approval_large_plan_closed_second_prompt_denies() {
        let mut answers = [Some("y".to_string()), None].into_iter();
        let mut confirm = |_: &str| answers.next().flatten();
        assert!(!request_approval(&large_plan(), false, Some(&mut confirm), false));
    }

    #[test]
    fn approval_first_no_skips_second_prompt() {
        let mut seen: Vec<String> = Vec::new();
        let mut confirm = |prompt: &str| {
            seen.push(prompt.to_string());
            Some("n".to_string())
        };
        assert!(!request_approval(&large_plan(), false, Some(&mut confirm), false));
        assert_eq!(seen.len(), 1);
    }
}
