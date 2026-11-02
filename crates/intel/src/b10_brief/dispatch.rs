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

/// True when text is not parseable JSON (DSP-017 classifier), ported
/// from `dispatch.py::_is_malformed_json`.
///
/// Only this failure triggers a retry in `plan_from_spark` and, on
/// the second consecutive failure, the fallback: text that parses
/// as JSON but fails a plan guard is a structured-plan fault, not
/// a malformed answer, and `validated_plan` reports it.
///
/// Rust adaptation, stated not hidden: Python takes any value and
/// counts a non-string answer as malformed (there is no JSON text
/// in it to parse); this function takes `&str`, so a non-string
/// answer never reaches it — the caller maps one to
/// [`SparkAnswer::Malformed`], exactly as `plan_from_spark`'s
/// caller already does. Python parses with `json.loads`; this
/// crate has no JSON dependency, so the check below is a small
/// syntax validator for the same grammar: objects, arrays,
/// strings with escapes (including `\uXXXX`), strict numbers
/// (no leading zeros, no `+1`, no `.5`, no `1.`), the literals
/// `true`/`false`/`null`, and Python's own extensions `NaN`,
/// `Infinity`, and `-Infinity`, which `json.loads` accepts.
/// Trailing text after one value, and trailing commas, are
/// malformed, matching `json.loads`.
pub fn is_malformed_json(text: &str) -> bool {
    let mut parser = JsonParser {
        chars: text.chars().collect(),
        pos: 0,
    };
    parser.skip_ws();
    if !parser.value() {
        return true;
    }
    parser.skip_ws();
    parser.pos != parser.chars.len()
}

/// Minimal JSON-syntax reader for [`is_malformed_json`]: it checks
/// shape only and keeps no values.
struct JsonParser {
    chars: Vec<char>,
    pos: usize,
}

impl JsonParser {
    fn skip_ws(&mut self) {
        while matches!(self.peek(), Some(' ') | Some('\t') | Some('\n') | Some('\r')) {
            self.pos += 1;
        }
    }

    fn peek(&self) -> Option<char> {
        self.chars.get(self.pos).copied()
    }

    fn bump(&mut self) -> Option<char> {
        let c = self.peek();
        if c.is_some() {
            self.pos += 1;
        }
        c
    }

    fn lit(&mut self, s: &str) -> bool {
        let want: Vec<char> = s.chars().collect();
        if self.pos + want.len() > self.chars.len() {
            return false;
        }
        if self.chars[self.pos..self.pos + want.len()] != want[..] {
            return false;
        }
        self.pos += want.len();
        true
    }

    fn value(&mut self) -> bool {
        self.skip_ws();
        match self.peek() {
            Some('{') => self.object(),
            Some('[') => self.array(),
            Some('"') => self.string(),
            Some('t') => self.lit("true"),
            Some('f') => self.lit("false"),
            Some('n') => self.lit("null"),
            Some('N') => self.lit("NaN"),
            Some('I') => self.lit("Infinity"),
            Some('-') => {
                let rest: String = self.chars[self.pos..].iter().collect();
                if rest.starts_with("-Infinity") {
                    self.pos += "-Infinity".len();
                    true
                } else {
                    self.number()
                }
            }
            Some(c) if c.is_ascii_digit() => self.number(),
            _ => false,
        }
    }

    fn object(&mut self) -> bool {
        self.bump(); // '{'
        self.skip_ws();
        if self.peek() == Some('}') {
            self.bump();
            return true;
        }
        loop {
            self.skip_ws();
            if !self.string() {
                return false;
            }
            self.skip_ws();
            if self.bump() != Some(':') {
                return false;
            }
            if !self.value() {
                return false;
            }
            self.skip_ws();
            match self.bump() {
                Some(',') => continue,
                Some('}') => return true,
                _ => return false,
            }
        }
    }

    fn array(&mut self) -> bool {
        self.bump(); // '['
        self.skip_ws();
        if self.peek() == Some(']') {
            self.bump();
            return true;
        }
        loop {
            if !self.value() {
                return false;
            }
            self.skip_ws();
            match self.bump() {
                Some(',') => continue,
                Some(']') => return true,
                _ => return false,
            }
        }
    }

    fn string(&mut self) -> bool {
        if self.bump() != Some('"') {
            return false;
        }
        loop {
            match self.bump() {
                None => return false,
                Some('"') => return true,
                Some('\\') => match self.bump() {
                    Some('"')
                    | Some('\\')
                    | Some('/')
                    | Some('b')
                    | Some('f')
                    | Some('n')
                    | Some('r')
                    | Some('t') => {}
                    Some('u') => {
                        for _ in 0..4 {
                            match self.bump() {
                                Some(c) if c.is_ascii_hexdigit() => {}
                                _ => return false,
                            }
                        }
                    }
                    _ => return false,
                },
                Some(c) if (c as u32) < 0x20 => return false,
                Some(_) => {}
            }
        }
    }

    fn number(&mut self) -> bool {
        if self.peek() == Some('-') {
            self.bump();
        }
        match self.peek() {
            Some('0') => {
                self.bump();
            }
            Some(c) if c.is_ascii_digit() => {
                while matches!(self.peek(), Some(c) if c.is_ascii_digit()) {
                    self.bump();
                }
            }
            _ => return false,
        }
        if self.peek() == Some('.') {
            self.bump();
            match self.peek() {
                Some(c) if c.is_ascii_digit() => {}
                _ => return false,
            }
            while matches!(self.peek(), Some(c) if c.is_ascii_digit()) {
                self.bump();
            }
        }
        if matches!(self.peek(), Some('e') | Some('E')) {
            self.bump();
            if matches!(self.peek(), Some('+') | Some('-')) {
                self.bump();
            }
            match self.peek() {
                Some(c) if c.is_ascii_digit() => {}
                _ => return false,
            }
            while matches!(self.peek(), Some(c) if c.is_ascii_digit()) {
                self.bump();
            }
        }
        true
    }
}

/// One Spark answer, as the caller classifies it (DSP-017).
///
/// Python's `plan_from_spark` takes raw answer text and calls
/// [`is_malformed_json`] on it, so the caller classifies its
/// answer instead: a `Malformed` answer stands in for text that
/// fails [`is_malformed_json`], including a non-string answer,
/// and a `Plan` answer stands in for text that parses and shapes
/// into a plan. The retry/fallback logic below is unchanged.
pub enum SparkAnswer {
    Malformed,
    Plan(Plan),
}

/// A Spark transport failure, as the caller reports it (DSP-017,
/// INT-008). `kind` is the error type name (Python's
/// `type(exc).__name__`, e.g. `RuntimeError`); `detail` is the
/// error message, truncated to 200 characters inside
/// `plan_from_spark` exactly as Python truncates `str(exc)`.
pub struct SparkTransport {
    pub kind: String,
    pub detail: String,
}

/// The result of `plan_from_spark`: the plan (validated, or the
/// DSP-017 fallback), its posting order, its clamp reports, and
/// whether it fell back, with the loud warning when it did
/// (`None` on a clean Spark plan).
pub struct SparkPlan {
    pub plan: Plan,
    pub order: Vec<String>,
    pub clamps: Vec<PlanClamp>,
    pub fallback: bool,
    pub warning: Option<String>,
}

/// Get a plan from Spark, with the DSP-017 fallback, ported from
/// `dispatch.py::plan_from_spark`.
///
/// `complete` is a caller-supplied Spark completion callable,
/// called as `complete(goal)` — the caller wraps the DSP-001
/// prompt construction around it, so this function stays
/// transport-free and testable without a live Spark call. First
/// attempt: call `complete`, and when the answer is malformed,
/// call it once more. When the second answer is malformed too,
/// return the fallback plan instead of raising: the
/// [`fallback_plan`], order `["fallback-job"]`, no clamps,
/// `fallback` true, and the loud FALLBACK warning. The warning
/// is also printed to stderr, so an operator sees it even
/// without reading the return value. When an answer carries a
/// plan, it goes through [`validated_plan`] exactly like a
/// dry-run plan: a guard failure there raises `PlanError` on
/// the first attempt, with no retry and no fallback. INT-008: a
/// Spark transport error raised by `complete` also returns the
/// fallback plan, with a warning that names the endpoint-down
/// failure instead of the malformed-JSON failure, because an
/// endpoint that answers nothing is not a structured-plan fault
/// and the drill requires dispatch to fall back when Spark is
/// down. On success the result carries the validated plan, its
/// order and clamps, `fallback` false, and no warning. Posts
/// nothing, claims nothing, touches no job state: the fallback
/// only becomes a job when a caller posts it through the
/// DSP-007 gate and the DSP-008 poster.
///
/// Rust adaptation, stated not hidden: Python's `complete`
/// returns raw text (or raises, or returns a non-string), and
/// malformedness is judged inside this function with
/// [`is_malformed_json`]; here the caller classifies the answer
/// into [`SparkAnswer`] with that same function. A non-string
/// answer maps to `SparkAnswer::Malformed`, matching Python's
/// rule that there is no JSON text in it to parse.
pub fn plan_from_spark(
    goal: &str,
    complete: &mut dyn FnMut(&str) -> Result<SparkAnswer, SparkTransport>,
) -> Result<SparkPlan, PlanError> {
    if goal.trim().is_empty() {
        return Err(fail("dispatch from Spark: goal must be a non-empty string"));
    }
    let fallback = |warning: String| -> Result<SparkPlan, PlanError> {
        eprintln!("{warning}");
        Ok(SparkPlan {
            plan: fallback_plan(goal)?,
            order: vec![FALLBACK_JOB_KEY.to_string()],
            clamps: Vec::new(),
            fallback: true,
            warning: Some(warning),
        })
    };
    for attempt in 1..=2 {
        match complete(goal) {
            Err(transport) => {
                let detail: String = transport.detail.chars().take(200).collect();
                return fallback(format!(
                    "WARNING: FALLBACK plan — Spark endpoint is down ({}: {}), so no structured plan was produced. This single FALLBACK job carries the raw goal as its spec; a human must approve it (DSP-007) before anything posts, and nothing malformed was posted.",
                    transport.kind, detail
                ));
            }
            Ok(SparkAnswer::Malformed) => {
                if attempt == 1 {
                    continue;
                }
                return fallback(
                    "WARNING: FALLBACK plan — Spark returned malformed JSON twice for this goal, so no structured plan was produced. This single FALLBACK job carries the raw goal as its spec; a human must approve it (DSP-007) before anything posts, and nothing malformed was posted."
                        .to_string(),
                );
            }
            Ok(SparkAnswer::Plan(plan)) => {
                let (plan, order, clamps) = validated_plan(plan)?;
                return Ok(SparkPlan {
                    plan,
                    order,
                    clamps,
                    fallback: false,
                    warning: None,
                });
            }
        }
    }
    unreachable!("plan_from_spark: every attempt returns");
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

/// One frozen-format announcement line for a plan (DSP-010), ported
/// from `dispatch.py::format_dispatch_announcement`.
///
/// Returns `"DISPATCH:<id> -> <n> jobs"` for a dispatch record
/// stored by `post_plan`, or `None` when the record cannot carry a
/// line. `<n>` is the number of jobs actually posted, never the
/// number planned. An id that is blank or contains whitespace yields
/// `None`, because the FND-020 freeze requires ids with no spaces,
/// and an empty jobs list yields `None`, because there is nothing
/// posted to announce. Pure: it posts nothing, claims nothing, and
/// writes no record.
///
/// Rust adaptations, stated not hidden: Python takes an untyped
/// record dict, so a non-dict record, a non-string id, or a
/// non-list jobs value also yields `None`; the typed inputs here
/// cannot carry those shapes, so there is no case for them. Ported
/// oddity, not fixed: the line says "1 jobs", never "1 job" —
/// Python formats the count unconditionally.
pub fn format_dispatch_announcement(id: &str, jobs: &[String]) -> Option<String> {
    if id.is_empty() || id.chars().any(|ch| ch.is_whitespace()) {
        return None;
    }
    if jobs.is_empty() {
        return None;
    }
    Some(format!("DISPATCH:{} -> {} jobs", id, jobs.len()))
}

/// Status order for the show counts line (DSP-016): these statuses
/// first, in this order, then any other status alphabetically.
pub const SHOW_STATUS_ORDER: [&str; 7] = [
    "open", "claimed", "done", "blocked", "cancelled", "failed-final", "missing",
];

/// One job entry of a `show_dispatch` report (DSP-016), as the record
/// stores it plus its current queue state. `deps` are the posted dep
/// job ids exactly as the record stores them; the renderer translates
/// them back to plan keys.
#[derive(Debug, Clone, PartialEq)]
pub struct DispatchShowJob {
    pub key: String,
    pub id: String,
    pub title: String,
    pub files: Vec<String>,
    pub deps: Vec<String>,
    pub status: String,
    pub claim: String,
}

/// A `show_dispatch` report (DSP-016): the dispatch id, the record's
/// summary, the jobs in posting order, and the per-status counts.
/// `counts` is carried, not computed: `show_dispatch` counts the
/// statuses it reads, and this renderer only orders them.
///
/// Rust adaptation, stated not hidden: Python takes one untyped
/// report dict and reads `counts` with a default of empty; the typed
/// report here always carries its counts, so a missing-counts report
/// is the empty-counts report, which renders as "0 jobs".
#[derive(Debug, Clone, PartialEq)]
pub struct DispatchShowReport {
    pub id: String,
    pub summary: String,
    pub jobs: Vec<DispatchShowJob>,
    pub counts: Vec<(String, usize)>,
}

/// Render a show_dispatch report as plain lines (DSP-016).
///
/// First line names the dispatch id; the summary line follows when
/// the record carries one. Then one line per job in posting order:
/// key -> job id, title, the files and deps as posted, and the job's
/// current state. Plan-local dep ids translate back to plan keys so
/// the deps read like the plan, not like queue ids; a dep id outside
/// the plan prints as-is. Claimed jobs name their claim nick; a
/// missing job says so in its state word. The last line counts jobs
/// per status in the fixed order, then any other status
/// alphabetically, so the shape of a half-finished plan is visible at
/// a glance. Pure string building; it reads no queue and writes
/// nothing.
pub fn render_dispatch_show(report: &DispatchShowReport) -> String {
    let mut lines = vec![format!("dispatch {}:", report.id)];
    if !report.summary.is_empty() {
        lines.push(format!("  summary: {}", report.summary));
    }
    for job in &report.jobs {
        let files = if job.files.is_empty() {
            "none".to_string()
        } else {
            job.files.join(", ")
        };
        let deps = if job.deps.is_empty() {
            "none".to_string()
        } else {
            job.deps
                .iter()
                .map(|dep| {
                    // Last job wins, matching Python's id -> key dict build.
                    report
                        .jobs
                        .iter()
                        .rev()
                        .find(|j| &j.id == dep)
                        .map(|j| j.key.as_str())
                        .unwrap_or(dep.as_str())
                })
                .collect::<Vec<_>>()
                .join(", ")
        };
        let state = if job.status == "claimed" && !job.claim.is_empty() {
            format!("claimed by {}", job.claim)
        } else {
            job.status.clone()
        };
        lines.push(format!(
            "  {} -> {}: {} (files: {}; deps: {}) now: {}",
            job.key, job.id, job.title, files, deps, state
        ));
    }
    let mut ordered: Vec<(&str, usize)> = Vec::new();
    for fixed in SHOW_STATUS_ORDER {
        if let Some((_, n)) = report.counts.iter().find(|(s, _)| s == fixed) {
            ordered.push((fixed, *n));
        }
    }
    let mut rest: Vec<(&str, usize)> = report
        .counts
        .iter()
        .filter(|(s, _)| !SHOW_STATUS_ORDER.contains(&s.as_str()))
        .map(|(s, n)| (s.as_str(), *n))
        .collect();
    rest.sort_by(|a, b| a.0.cmp(b.0));
    ordered.extend(rest);
    if ordered.is_empty() {
        lines.push("  counts: 0 jobs".to_string());
    } else {
        let parts: Vec<String> = ordered
            .iter()
            .map(|(s, n)| format!("{n} {s}"))
            .collect();
        lines.push(format!("  counts: {}", parts.join(", ")));
    }
    lines.join("\n")
}

/// One job entry of a dispatch record as `post_plan` stores it (DSP-008):
/// the plan key, the posted job id, title, files, and posted dep job ids.
/// The job's current queue state is not stored here; the caller reads it fresh.
#[derive(Debug, Clone, PartialEq)]
pub struct DispatchRecordJob {
    pub key: String,
    pub id: String,
    pub title: String,
    pub files: Vec<String>,
    pub deps: Vec<String>,
}

/// Build a `show_dispatch` report from a stored dispatch record (DSP-016).
///
/// `state_of` reads one job's current queue state fresh and returns
/// `(status, claim)`; it returns `None` when the job id is no longer in
/// the queue. Classification mirrors Python's `show_dispatch`: a missing
/// job is "missing" with an empty claim; a claimed job carries its claim
/// nick; every other state carries an empty claim. `counts` counts each
/// status seen, in first-seen order (the renderer orders them).
/// Read-only: it posts, claims, cancels, and stores nothing.
///
/// Rust adaptations, stated not hidden: Python reads the record from
/// `intel.store` and the states from `jobs.job_get`, and raises
/// `ShowError` when the record is missing; this builder takes the
/// record jobs and the state lookup as arguments, so a missing record
/// is the caller's error, not this function's. Python's report also
/// carries room, created_at, latency_ms, order, and per-job
/// max_attempts and req; the existing `DispatchShowReport` omits them,
/// so this builder does not invent them.
pub fn build_dispatch_show_report(
    id: &str,
    summary: &str,
    jobs: &[DispatchRecordJob],
    state_of: impl Fn(&str) -> Option<(String, String)>,
) -> DispatchShowReport {
    let mut out = Vec::new();
    let mut counts: Vec<(String, usize)> = Vec::new();
    for job in jobs {
        let (status, claim) = match state_of(&job.id) {
            None => ("missing".to_string(), String::new()),
            Some((status, claim)) => {
                if status == "claimed" {
                    (status, claim)
                } else {
                    (status, String::new())
                }
            }
        };
        if let Some((_, n)) = counts.iter_mut().find(|(s, _)| *s == status) {
            *n += 1;
        } else {
            counts.push((status.clone(), 1));
        }
        out.push(DispatchShowJob {
            key: job.key.clone(),
            id: job.id.clone(),
            title: job.title.clone(),
            files: job.files.clone(),
            deps: job.deps.clone(),
            status,
            claim,
        });
    }
    DispatchShowReport {
        id: id.to_string(),
        summary: summary.to_string(),
        jobs: out,
        counts,
    }
}

/// A `show_dispatch` run failed before any job was read (DSP-016).
/// The message is the full Python `ShowError` text, so callers and
/// tests see the same words Python raises.
#[derive(Debug, Clone, PartialEq)]
pub struct ShowError(pub String);

impl std::fmt::Display for ShowError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

/// Show a posted plan as posted vs current job states (DSP-016).
///
/// `record` is the stored dispatch record's jobs, or `None` when
/// there is no record for this id. A missing record raises
/// `ShowError` before any job is read: `state_of` is never called.
/// A present record builds through `build_dispatch_show_report`,
/// so the classification, counts, and read-only promise are the
/// builder's. `state_of` reads one job's current queue state fresh
/// and returns `(status, claim)`; it returns `None` when the job
/// id is no longer in the queue.
///
/// Rust adaptations, stated not hidden: Python reads the record
/// from `intel.store` and the states from `jobs.job_get`; this
/// wrapper takes the record and the state lookup as arguments,
/// so store and queue access stay with the caller. Python's
/// report also carries room, created_at, latency_ms, order, and
/// per-job max_attempts and req; the existing `DispatchShowReport`
/// omits them, so this wrapper does not invent them. Python
/// formats the id with `!r`; this message uses plain single
/// quotes, which matches for ordinary ids.
pub fn show_dispatch(
    id: &str,
    summary: &str,
    record: Option<&[DispatchRecordJob]>,
    state_of: impl Fn(&str) -> Option<(String, String)>,
) -> Result<DispatchShowReport, ShowError> {
    match record {
        None => Err(ShowError(format!(
            "dispatch show failed: no dispatch record '{id}' (nothing touched)"
        ))),
        Some(jobs) => Ok(build_dispatch_show_report(id, summary, jobs, state_of)),
    }
}

/// An undo run failed before any job was touched (DSP-011).
/// The message is the full Python `UndoError` text, so callers and
/// tests see the same words Python raises.
#[derive(Debug, Clone, PartialEq)]
pub struct UndoError(pub String);

impl std::fmt::Display for UndoError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

/// One job entry in an undo report: a cancelled job, or a job
/// reported missing (DSP-011).
#[derive(Debug, Clone, PartialEq)]
pub struct UndoJob {
    pub key: String,
    pub id: String,
    pub title: String,
}

/// One claimed job left untouched by an undo (DSP-011), with its claim nick.
#[derive(Debug, Clone, PartialEq)]
pub struct UndoClaimedJob {
    pub key: String,
    pub id: String,
    pub title: String,
    pub claim: String,
}

/// One non-claimed job left untouched by an undo (DSP-011), with its status.
#[derive(Debug, Clone, PartialEq)]
pub struct UndoOtherJob {
    pub key: String,
    pub id: String,
    pub title: String,
    pub status: String,
}

/// The report of an `undo_dispatch` run (DSP-011): cancelled jobs,
/// claimed jobs left untouched, other jobs left untouched, and jobs
/// missing from the queue, each in record order.
#[derive(Debug, Clone, PartialEq)]
pub struct UndoReport {
    pub id: String,
    pub cancelled: Vec<UndoJob>,
    pub untouched_claimed: Vec<UndoClaimedJob>,
    pub untouched_other: Vec<UndoOtherJob>,
    pub missing: Vec<UndoJob>,
}

fn undo_classify(
    report: &mut UndoReport,
    key: String,
    job_id: String,
    title: String,
    fields: Option<(String, String)>,
) {
    match fields {
        None => report.missing.push(UndoJob {
            key,
            id: job_id,
            title,
        }),
        Some((status, claim)) if status == "claimed" => {
            report.untouched_claimed.push(UndoClaimedJob {
                key,
                id: job_id,
                title,
                claim,
            })
        }
        Some((status, _claim)) => report.untouched_other.push(UndoOtherJob {
            key,
            id: job_id,
            title,
            status,
        }),
    }
}

/// Undo a posted plan: cancel its unclaimed jobs (DSP-011).
///
/// `record` is the stored dispatch record's jobs, or `None` when
/// there is no record for this id. A missing record raises
/// `UndoError` before any job is touched: `state_of` and `cancel`
/// are never called. Every job in the record is read fresh from
/// the queue, so the undo acts on the job's current state, not
/// the state at posting time. An open job is cancelled through
/// `cancel` with argv `["cancel", <job id>, "--reason=dispatch
/// undo <id>"]`; a zero exit code lands it in `cancelled`, while
/// a nonzero code re-reads the job and classifies its actual
/// state instead of failing the run, so a claim landing between
/// the read and the cancel is reported honestly. A claimed job
/// is work in progress and is left untouched; a done, blocked,
/// failed-final, or already cancelled job is history and is left
/// untouched; a job id no longer in the queue is reported as
/// missing. Nothing else is touched, and a second undo cancels
/// nothing new: the first run's cancelled jobs come back as
/// untouched with status cancelled.
///
/// The returned `undone_at` is the caller's `now`, the value
/// Python stores on the record beside the report.
///
/// Rust adaptations, stated not hidden: Python reads the record
/// from `intel.store`, the states from `jobs.job_get`, cancels
/// through `jobs.main`, and stores the report back on the record
/// with `put_dispatch`; this wrapper takes the record, the state
/// lookup, and the cancel call as arguments, and returns the
/// report with `undone_at`, so store and queue access stay with
/// the caller. Python formats the id with `!r`; this message
/// uses plain single quotes, which matches for ordinary ids.
pub fn undo_dispatch(
    id: &str,
    record: Option<&[DispatchRecordJob]>,
    state_of: impl Fn(&str) -> Option<(String, String)>,
    cancel: impl Fn(&[String]) -> i32,
    now: i64,
) -> Result<(UndoReport, i64), UndoError> {
    let jobs = match record {
        None => {
            return Err(UndoError(format!(
                "dispatch undo failed: no dispatch record '{id}' (nothing touched)"
            )))
        }
        Some(jobs) => jobs,
    };
    let mut report = UndoReport {
        id: id.to_string(),
        cancelled: vec![],
        untouched_claimed: vec![],
        untouched_other: vec![],
        missing: vec![],
    };
    let reason = format!("dispatch undo {id}");
    for entry in jobs {
        match state_of(&entry.id) {
            None => undo_classify(
                &mut report,
                entry.key.clone(),
                entry.id.clone(),
                entry.title.clone(),
                None,
            ),
            Some((status, _claim)) if status == "open" => {
                let argv = vec![
                    "cancel".to_string(),
                    entry.id.clone(),
                    format!("--reason={reason}"),
                ];
                if cancel(&argv) == 0 {
                    report.cancelled.push(UndoJob {
                        key: entry.key.clone(),
                        id: entry.id.clone(),
                        title: entry.title.clone(),
                    });
                } else {
                    let fresh = state_of(&entry.id);
                    undo_classify(
                        &mut report,
                        entry.key.clone(),
                        entry.id.clone(),
                        entry.title.clone(),
                        fresh,
                    );
                }
            }
            Some((status, claim)) => undo_classify(
                &mut report,
                entry.key.clone(),
                entry.id.clone(),
                entry.title.clone(),
                Some((status, claim)),
            ),
        }
    }
    Ok((report, now))
}

/// Parse one `jobs.main` post result into the posted job id (DSP-008).
///
/// This is the pure half of Python's `_jobs_main_post`: Python captures
/// only stdout (jobs.py warnings stay on stderr for the operator), and
/// a post is a failed post when the exit code is nonzero, or when a
/// zero exit code carries no `JOB <id>` line. Scanning from the last
/// line back, the first `JOB ` line with a non-empty id wins, so an
/// empty `JOB ` line is skipped, not returned.
///
/// Rust adaptation, stated not hidden: Python calls `jobs.main`
/// itself and captures its stdout; this function takes the exit code
/// and the captured stdout as arguments, so the queue call stays with
/// the caller. The full `post_plan` poster (order, argv, record,
/// spend ledger, announcement) is still to come; this parser is its
/// first piece, not a post by itself.
pub fn parse_posted_job_id(code: i32, stdout: &str) -> Option<String> {
    if code != 0 {
        return None;
    }
    for line in stdout.lines().rev() {
        if let Some(rest) = line.strip_prefix("JOB ") {
            let id = rest.trim();
            if !id.is_empty() {
                return Some(id.to_string());
            }
        }
    }
    None
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

    #[test]
    fn announcement_counts_posted_jobs() {
        let jobs = vec!["j1".to_string(), "j2".to_string(), "j3".to_string()];
        assert_eq!(
            format_dispatch_announcement("d1", &jobs).as_deref(),
            Some("DISPATCH:d1 -> 3 jobs")
        );
    }

    #[test]
    fn announcement_single_job_keeps_plural() {
        let jobs = vec!["j1".to_string()];
        assert_eq!(
            format_dispatch_announcement("d1", &jobs).as_deref(),
            Some("DISPATCH:d1 -> 1 jobs")
        );
    }

    #[test]
    fn announcement_blank_or_spaced_id_is_none() {
        let jobs = vec!["j1".to_string()];
        assert_eq!(format_dispatch_announcement("", &jobs), None);
        assert_eq!(format_dispatch_announcement("   ", &jobs), None);
        assert_eq!(format_dispatch_announcement("d 1", &jobs), None);
    }

    #[test]
    fn announcement_empty_jobs_is_none() {
        let jobs: Vec<String> = vec![];
        assert_eq!(format_dispatch_announcement("d1", &jobs), None);
    }

    fn show_job(
        key: &str,
        id: &str,
        files: Vec<&str>,
        deps: Vec<&str>,
        status: &str,
        claim: &str,
    ) -> DispatchShowJob {
        DispatchShowJob {
            key: key.into(),
            id: id.into(),
            title: format!("Do {key}"),
            files: files.iter().map(|s| s.to_string()).collect(),
            deps: deps.iter().map(|s| s.to_string()).collect(),
            status: status.into(),
            claim: claim.into(),
        }
    }

    #[test]
    fn show_render_golden_lines() {
        let report = DispatchShowReport {
            id: "dsp-show-1".into(),
            summary: "Build the snapshot in order.".into(),
            jobs: vec![
                show_job("base", "j-base", vec!["intel/ingest.py"], vec![], "open", ""),
                show_job(
                    "api",
                    "j-api",
                    vec!["intel/ingest.py"],
                    vec!["j-base"],
                    "claimed",
                    "tester",
                ),
            ],
            counts: vec![("open".to_string(), 1), ("claimed".to_string(), 1)],
        };
        let text = render_dispatch_show(&report);
        assert!(text.starts_with("dispatch dsp-show-1:\n"), "got: {text}");
        assert!(
            text.contains("  summary: Build the snapshot in order.\n"),
            "got: {text}"
        );
        assert!(
            text.contains(
                "  base -> j-base: Do base (files: intel/ingest.py; deps: none) now: open"
            ),
            "got: {text}"
        );
        assert!(
            text.contains(
                "  api -> j-api: Do api (files: intel/ingest.py; deps: base) now: claimed by tester"
            ),
            "got: {text}"
        );
        assert!(text.ends_with("  counts: 1 open, 1 claimed"), "got: {text}");
    }

    #[test]
    fn show_render_empty_report_has_no_summary_line() {
        let report = DispatchShowReport {
            id: "d-empty".into(),
            summary: String::new(),
            jobs: vec![],
            counts: vec![],
        };
        assert_eq!(
            render_dispatch_show(&report),
            "dispatch d-empty:\n  counts: 0 jobs"
        );
    }

    #[test]
    fn show_render_claimed_without_nick_and_outside_dep() {
        let report = DispatchShowReport {
            id: "d-odd".into(),
            summary: String::new(),
            jobs: vec![show_job(
                "solo",
                "j-solo",
                vec![],
                vec!["j-outside"],
                "claimed",
                "",
            )],
            counts: vec![
                ("weird".to_string(), 1),
                ("done".to_string(), 1),
                ("open".to_string(), 1),
            ],
        };
        let text = render_dispatch_show(&report);
        assert!(
            text.contains(
                "  solo -> j-solo: Do solo (files: none; deps: j-outside) now: claimed"
            ),
            "got: {text}"
        );
        // Fixed statuses first in fixed order, then other statuses alphabetically.
        assert!(
            text.ends_with("  counts: 1 open, 1 done, 1 weird"),
            "got: {text}"
        );
    }

    #[test]
    fn show_render_missing_job_says_so() {
        let report = DispatchShowReport {
            id: "d-miss".into(),
            summary: String::new(),
            jobs: vec![show_job("gone", "j-gone", vec![], vec![], "missing", "")],
            counts: vec![("missing".to_string(), 1)],
        };
        let text = render_dispatch_show(&report);
        assert!(text.contains("now: missing"), "got: {text}");
        assert!(text.ends_with("  counts: 1 missing"), "got: {text}");
    }

    #[test]
    fn show_builder_classifies_fresh_states_and_counts() {
        let record = vec![
            DispatchRecordJob { key: "base".into(), id: "j-base".into(), title: "Do base".into(), files: vec!["intel/ingest.py".into()], deps: vec![] },
            DispatchRecordJob { key: "api".into(), id: "j-api".into(), title: "Do api".into(), files: vec![], deps: vec!["j-base".into()] },
            DispatchRecordJob { key: "gone".into(), id: "j-gone".into(), title: "Do gone".into(), files: vec![], deps: vec![] },
            DispatchRecordJob { key: "done-one".into(), id: "j-done".into(), title: "Do done".into(), files: vec![], deps: vec![] },
        ];
        let report = build_dispatch_show_report("dsp-show-2", "Build it.", &record, |id| match id {
            "j-base" => Some(("open".to_string(), String::new())),
            "j-api" => Some(("claimed".to_string(), "tester".to_string())),
            "j-done" => Some(("done".to_string(), "stale-nick".to_string())),
            _ => None,
        });
        assert_eq!(report.id, "dsp-show-2");
        assert_eq!(report.summary, "Build it.");
        assert_eq!(report.jobs[0].status, "open");
        assert_eq!(report.jobs[0].claim, "");
        assert_eq!(report.jobs[1].status, "claimed");
        assert_eq!(report.jobs[1].claim, "tester");
        assert_eq!(report.jobs[2].status, "missing");
        assert_eq!(report.jobs[2].claim, "");
        // A non-claimed job never carries a claim, even when the lookup names one.
        assert_eq!(report.jobs[3].status, "done");
        assert_eq!(report.jobs[3].claim, "");
        assert_eq!(
            report.counts,
            vec![
                ("open".to_string(), 1),
                ("claimed".to_string(), 1),
                ("missing".to_string(), 1),
                ("done".to_string(), 1),
            ]
        );
        // The built report renders through the existing renderer unchanged.
        let text = render_dispatch_show(&report);
        assert!(
            text.contains("  api -> j-api: Do api (files: none; deps: base) now: claimed by tester"),
            "got: {text}"
        );
        assert!(text.ends_with("  counts: 1 open, 1 claimed, 1 done, 1 missing"), "got: {text}");
    }

    #[test]
    fn show_missing_record_errors_before_any_read() {
        let reads = std::cell::Cell::new(0);
        let err = show_dispatch("dsp-gone", "", None, |_id| {
            reads.set(reads.get() + 1);
            None
        })
        .expect_err("missing record must fail");
        assert_eq!(
            err.0,
            "dispatch show failed: no dispatch record 'dsp-gone' (nothing touched)"
        );
        // Python raises before any job is read; the lookup stays untouched.
        assert_eq!(reads.get(), 0);
    }

    #[test]
    fn show_present_record_builds_report() {
        let record = vec![DispatchRecordJob {
            key: "base".into(),
            id: "j-base".into(),
            title: "Do base".into(),
            files: vec![],
            deps: vec![],
        }];
        let report = show_dispatch("dsp-show-3", "Build it.", Some(&record), |id| match id {
            "j-base" => Some(("claimed".to_string(), "tester".to_string())),
            _ => None,
        })
        .expect("present record must show");
        assert_eq!(report.id, "dsp-show-3");
        assert_eq!(report.jobs[0].status, "claimed");
        assert_eq!(report.jobs[0].claim, "tester");
        assert_eq!(report.counts, vec![("claimed".to_string(), 1)]);
        let text = render_dispatch_show(&report);
        assert!(text.contains("now: claimed by tester"), "got: {text}");
        assert!(text.ends_with("  counts: 1 claimed"), "got: {text}");
    }

    #[test]
    fn undo_missing_record_errors_before_any_touch() {
        let reads = std::cell::Cell::new(0);
        let cancels = std::cell::Cell::new(0);
        let err = undo_dispatch(
            "dsp-gone",
            None,
            |_id| {
                reads.set(reads.get() + 1);
                None
            },
            |_argv| {
                cancels.set(cancels.get() + 1);
                0
            },
            0,
        )
        .expect_err("missing record must fail");
        assert_eq!(
            err.0,
            "dispatch undo failed: no dispatch record 'dsp-gone' (nothing touched)"
        );
        // Python raises before any job is touched: no reads, no cancels.
        assert_eq!(reads.get(), 0);
        assert_eq!(cancels.get(), 0);
    }

    #[test]
    fn undo_cancels_open_leaves_rest() {
        let record = vec![
            DispatchRecordJob {
                key: "base".into(),
                id: "j-base".into(),
                title: "Do base".into(),
                files: vec![],
                deps: vec![],
            },
            DispatchRecordJob {
                key: "api".into(),
                id: "j-api".into(),
                title: "Do api".into(),
                files: vec![],
                deps: vec![],
            },
            DispatchRecordJob {
                key: "done".into(),
                id: "j-done".into(),
                title: "Did it".into(),
                files: vec![],
                deps: vec![],
            },
            DispatchRecordJob {
                key: "gone".into(),
                id: "j-gone".into(),
                title: "Was here".into(),
                files: vec![],
                deps: vec![],
            },
        ];
        let seen_argv = std::cell::RefCell::new(Vec::new());
        let (report, undone_at) = undo_dispatch(
            "dsp-undo-1",
            Some(&record),
            |id| match id {
                "j-base" => Some(("open".to_string(), String::new())),
                "j-api" => Some(("claimed".to_string(), "tester".to_string())),
                "j-done" => Some(("done".to_string(), String::new())),
                _ => None,
            },
            |argv| {
                seen_argv.borrow_mut().push(argv.to_vec());
                0
            },
            1700000000,
        )
        .expect("present record must undo");
        assert_eq!(undone_at, 1700000000);
        assert_eq!(report.id, "dsp-undo-1");
        assert_eq!(report.cancelled.len(), 1);
        assert_eq!(report.cancelled[0].id, "j-base");
        assert_eq!(report.untouched_claimed.len(), 1);
        assert_eq!(report.untouched_claimed[0].claim, "tester");
        assert_eq!(report.untouched_other.len(), 1);
        assert_eq!(report.untouched_other[0].status, "done");
        assert_eq!(report.missing.len(), 1);
        assert_eq!(report.missing[0].id, "j-gone");
        let argv_seen = seen_argv.borrow();
        assert_eq!(argv_seen.len(), 1);
        assert_eq!(
            argv_seen[0],
            vec![
                "cancel".to_string(),
                "j-base".to_string(),
                "--reason=dispatch undo dsp-undo-1".to_string()
            ]
        );
    }

    #[test]
    fn undo_refused_cancel_re_reads_and_classifies() {
        let record = vec![DispatchRecordJob {
            key: "base".into(),
            id: "j-base".into(),
            title: "Do base".into(),
            files: vec![],
            deps: vec![],
        }];
        let reads = std::cell::Cell::new(0);
        let (report, _) = undo_dispatch(
            "dsp-undo-2",
            Some(&record),
            |_id| {
                reads.set(reads.get() + 1);
                if reads.get() == 1 {
                    Some(("open".to_string(), String::new()))
                } else {
                    Some(("claimed".to_string(), "racer".to_string()))
                }
            },
            |_argv| 1,
            0,
        )
        .expect("refused cancel must still report");
        // One read to find it open, one re-read after the refusal.
        assert_eq!(reads.get(), 2);
        assert!(report.cancelled.is_empty());
        assert_eq!(report.untouched_claimed.len(), 1);
        assert_eq!(report.untouched_claimed[0].claim, "racer");
    }

    #[test]
    fn posted_job_id_zero_code_with_job_line() {
        assert_eq!(
            parse_posted_job_id(0, "some note\nJOB j-9\n"),
            Some("j-9".to_string())
        );
    }

    #[test]
    fn posted_job_id_last_job_line_wins() {
        assert_eq!(
            parse_posted_job_id(0, "JOB j-1\nJOB j-2\n"),
            Some("j-2".to_string())
        );
    }

    #[test]
    fn posted_job_id_empty_job_line_skipped() {
        assert_eq!(
            parse_posted_job_id(0, "JOB j-1\nJOB   \n"),
            Some("j-1".to_string())
        );
    }

    #[test]
    fn posted_job_id_nonzero_code_fails_even_with_job_line() {
        assert_eq!(parse_posted_job_id(1, "JOB j-9\n"), None);
    }

    #[test]
    fn posted_job_id_zero_code_without_job_line_fails() {
        assert_eq!(parse_posted_job_id(0, "posted, no id line\n"), None);
    }

    // Scripted Spark callable for plan_from_spark tests, mirroring
    // Python's _ScriptedComplete: scripted answers in order (the
    // last repeats), counting calls; a Transport answer raises.
    struct ScriptedComplete {
        answers: Vec<Result<SparkAnswer, (String, String)>>,
        calls: usize,
    }

    impl ScriptedComplete {
        fn call(&mut self, _goal: &str) -> Result<SparkAnswer, SparkTransport> {
            self.calls += 1;
            let index = (self.calls - 1).min(self.answers.len() - 1);
            match &self.answers[index] {
                Ok(SparkAnswer::Malformed) => Ok(SparkAnswer::Malformed),
                Ok(SparkAnswer::Plan(p)) => Ok(SparkAnswer::Plan(p.clone())),
                Err((kind, detail)) => Err(SparkTransport {
                    kind: kind.clone(),
                    detail: detail.clone(),
                }),
            }
        }
    }

    fn valid_spark_plan() -> Plan {
        Plan {
            goal: "Do the thing".into(),
            summary: "Do the one job.".into(),
            jobs: vec![PlanJob {
                key: "do-it".into(),
                title: "Do it".into(),
                files: vec!["intel/ingest.py".into()],
                deps: vec![],
                max_attempts: 3,
                spec: "Goal, context, files, steps, out of scope.".into(),
                accept: vec!["file-exists: intel/ingest.py".into()],
                req: vec![],
            }],
        }
    }

    #[test]
    fn spark_malformed_twice_falls_back_with_raw_goal() {
        let goal = "Wire the snapshot panel\nsecond line of the goal";
        let mut complete = ScriptedComplete {
            answers: vec![Ok(SparkAnswer::Malformed), Ok(SparkAnswer::Malformed)],
            calls: 0,
        };
        let result = plan_from_spark(goal, &mut |g| complete.call(g)).unwrap();
        assert_eq!(complete.calls, 2);
        assert!(result.fallback);
        assert_eq!(result.order, vec![FALLBACK_JOB_KEY.to_string()]);
        assert!(result.clamps.is_empty());
        let warning = result.warning.as_deref().unwrap_or("");
        assert!(warning.contains("FALLBACK"), "got: {warning}");
        assert_eq!(result.plan.jobs.len(), 1);
        let job = &result.plan.jobs[0];
        assert_eq!(job.key, FALLBACK_JOB_KEY);
        assert!(result.plan.summary.contains("FALLBACK"));
        assert!(job.title.contains("FALLBACK"));
        assert!(job.spec.contains("FALLBACK"));
        assert!(job.spec.contains(goal), "got: {}", job.spec);
    }

    #[test]
    fn spark_malformed_then_valid_succeeds_without_fallback() {
        let mut complete = ScriptedComplete {
            answers: vec![
                Ok(SparkAnswer::Malformed),
                Ok(SparkAnswer::Plan(valid_spark_plan())),
            ],
            calls: 0,
        };
        let result = plan_from_spark("Do the thing", &mut |g| complete.call(g)).unwrap();
        assert_eq!(complete.calls, 2);
        assert!(!result.fallback);
        assert!(result.warning.is_none());
        assert_eq!(result.order, vec!["do-it".to_string()]);
        assert_eq!(result.plan.jobs[0].title, "Do it");
    }

    #[test]
    fn spark_valid_first_answer_calls_once() {
        let mut complete = ScriptedComplete {
            answers: vec![Ok(SparkAnswer::Plan(valid_spark_plan()))],
            calls: 0,
        };
        let result = plan_from_spark("Do the thing", &mut |g| complete.call(g)).unwrap();
        assert_eq!(complete.calls, 1);
        assert!(!result.fallback);
    }

    #[test]
    fn spark_structured_invalid_plan_propagates_without_retry() {
        // Two jobs sharing a file with no dep order: the overlap
        // guard refuses on the first attempt, no retry, no fallback.
        let mut bad = valid_spark_plan();
        bad.jobs.push(PlanJob {
            key: "also".into(),
            title: "Also".into(),
            files: vec!["intel/ingest.py".into()],
            deps: vec![],
            max_attempts: 3,
            spec: "Goal, context, files, steps, out of scope.".into(),
            accept: vec![],
            req: vec![],
        });
        let mut complete = ScriptedComplete {
            answers: vec![Ok(SparkAnswer::Plan(bad))],
            calls: 0,
        };
        assert!(plan_from_spark("Do the thing", &mut |g| complete.call(g)).is_err());
        assert_eq!(complete.calls, 1);
    }

    #[test]
    fn spark_dependency_cycle_propagates_without_fallback() {
        let mut cyclic = valid_spark_plan();
        cyclic.jobs = vec![
            PlanJob {
                key: "a".into(),
                title: "Do a".into(),
                files: vec!["intel/ingest.py".into()],
                deps: vec!["b".into()],
                max_attempts: 3,
                spec: "Spec a.".into(),
                accept: vec!["file-exists: intel/ingest.py".into()],
                req: vec![],
            },
            PlanJob {
                key: "b".into(),
                title: "Do b".into(),
                files: vec!["intel.py".into()],
                deps: vec!["a".into()],
                max_attempts: 3,
                spec: "Spec b.".into(),
                accept: vec!["file-exists: intel.py".into()],
                req: vec![],
            },
        ];
        let mut complete = ScriptedComplete {
            answers: vec![Ok(SparkAnswer::Plan(cyclic))],
            calls: 0,
        };
        assert!(plan_from_spark("Do the thing", &mut |g| complete.call(g)).is_err());
        assert_eq!(complete.calls, 1);
    }

    #[test]
    fn spark_transport_error_falls_back_with_endpoint_down_warning() {
        let mut complete = ScriptedComplete {
            answers: vec![Err(("RuntimeError".to_string(), "spark down".to_string()))],
            calls: 0,
        };
        let result = plan_from_spark("Do the thing", &mut |g| complete.call(g)).unwrap();
        assert_eq!(complete.calls, 1);
        assert!(result.fallback);
        assert_eq!(result.order, vec!["fallback-job".to_string()]);
        assert!(result.plan.summary.contains("FALLBACK"));
        assert!(
            result.plan.jobs[0].spec.contains("Do the thing"),
            "got: {}",
            result.plan.jobs[0].spec
        );
        let warning = result.warning.as_deref().unwrap_or("");
        assert!(warning.contains("endpoint is down"), "got: {warning}");
    }

    #[test]
    fn spark_empty_goal_raises_before_any_call() {
        let mut complete = ScriptedComplete {
            answers: vec![Ok(SparkAnswer::Plan(valid_spark_plan()))],
            calls: 0,
        };
        assert!(plan_from_spark("   ", &mut |g| complete.call(g)).is_err());
        assert_eq!(complete.calls, 0);
    }

    #[test]
    fn malformed_json_classifier_accepts_parseable_docs() {
        // Each parses under Python's json.loads, so none is malformed.
        let valid = [
            "{}",
            "[]",
            "{\"a\": 1}",
            "[1, 2.5, -3e+4]",
            "\"text\"",
            "123",
            "-0.5",
            "true",
            "false",
            "null",
            "NaN",
            "Infinity",
            "-Infinity",
            "[NaN, Infinity]",
            "{\"a\": [{\"b\": null}]}",
            "  {\"a\": 1}  ",
            "\"a\\nb\"",
            "\"\\u0041\"",
            "0.5e-2",
        ];
        for text in valid {
            assert!(!is_malformed_json(text), "should parse: {text}");
        }
    }

    #[test]
    fn malformed_json_classifier_rejects_unparseable_docs() {
        // Each fails under Python's json.loads, so each is malformed.
        let invalid = [
            "",
            "   ",
            "{",
            "}",
            "[1,]",
            "{\"a\":}",
            "{\"a\": 1,}",
            "'single'",
            "01",
            "+1",
            ".5",
            "1.",
            "1e",
            "1e+",
            "tru",
            "nul",
            "nan",
            "\"unterminated",
            "\"bad\\x\"",
            "\"bad\\u12\"",
            "{\"a\" 1}",
            "[1 2]",
            "{\"a\": 1} extra",
            "{a: 1}",
            "[1, 2",
            "\"a\" \"b\"",
            "-",
            "-x",
            "Infinityy",
            "{\"a\": 1,, \"b\": 2}",
        ];
        for text in invalid {
            assert!(is_malformed_json(text), "should fail: {text}");
        }
    }
}
