//! Port of `os/intel/abrun.py` — measured A/B run + image-defect
//! attribution (OS-106).
//!
//! The comparison records the same fixed job suite under two
//! image versions and attributes each observed stall, as a pure
//! function of the stall and the image it ran under, checked in
//! this order: missing skill (named skill absent from the image's
//! skills layer, with the journal naming it), bad instruction
//! (named instruction present in the image's instructions),
//! thin brief (stall wants context and the brief is thin/absent),
//! worker failure (a named worker cause), else unattributed.
//! Malformed versions, runs, and stalls are skipped silently;
//! inputs are never mutated; a missing run reads "missing".

use super::value::Value;

/// `_text`: a non-empty string value, or None.
fn text(value: &Value) -> Option<&str> {
    value.as_text()
}

/// `_string_list`: the string items of a list, ignoring the rest.
fn string_list(value: &Value) -> Vec<String> {
    match value.as_list() {
        Some(items) => items
            .iter()
            .filter_map(|item| item.as_str().map(|s| s.to_string()))
            .collect(),
        None => Vec::new(),
    }
}

/// `_image_layers`: skills, instructions, brief (default "absent").
fn image_layers(image: &Value) -> (Vec<String>, Vec<String>, String) {
    if !image.is_dict() {
        return (Vec::new(), Vec::new(), "absent".to_string());
    }
    let skills = string_list(&image.get("skills"));
    let instructions = string_list(&image.get("instructions"));
    let brief = match image.get("brief").as_str() {
        Some(b @ ("full" | "thin" | "absent")) => b.to_string(),
        _ => "absent".to_string(),
    };
    (skills, instructions, brief)
}

/// `_journal_evidence`: journal lines naming the needle, or the
/// needle itself when no line names it.
fn journal_evidence(stall: &Value, needle: &str) -> Vec<Value> {
    let journal = string_list(&stall.get("journal"));
    let hits: Vec<Value> = journal
        .iter()
        .filter(|line| line.contains(needle))
        .map(|line| Value::s(line))
        .collect();
    if !hits.is_empty() {
        return hits;
    }
    vec![Value::s(needle)]
}

/// `attribute_stall(stall, image)` — (kind, detail, evidence).
/// Kind is "image-defect" (detail "missing-skill",
/// "bad-instruction", or "thin-brief"), "worker-failure" (detail
/// the worker cause), or "unattributed" (detail None).
pub fn attribute_stall(stall: &Value, image: &Value) -> (String, Option<String>, Vec<Value>) {
    if !stall.is_dict() {
        return ("unattributed".to_string(), None, Vec::new());
    }
    let (skills, instructions, brief) = image_layers(image);
    if let Some(skill) = text(&stall.get("missing_skill")) {
        if !skills.iter().any(|s| s == skill) {
            return (
                "image-defect".to_string(),
                Some("missing-skill".to_string()),
                journal_evidence(stall, skill),
            );
        }
    }
    if let Some(instruction) = text(&stall.get("bad_instruction")) {
        if instructions.iter().any(|s| s == instruction) {
            return (
                "image-defect".to_string(),
                Some("bad-instruction".to_string()),
                journal_evidence(stall, instruction),
            );
        }
    }
    if stall.get("thin_brief").as_bool() == Some(true) && (brief == "thin" || brief == "absent") {
        let journal = string_list(&stall.get("journal"));
        let evidence = if !journal.is_empty() {
            journal.iter().map(|l| Value::s(l)).collect()
        } else {
            vec![Value::s("worker stalled for context")]
        };
        return (
            "image-defect".to_string(),
            Some("thin-brief".to_string()),
            evidence,
        );
    }
    if let Some(cause) = text(&stall.get("worker_cause")) {
        let journal = string_list(&stall.get("journal"));
        let evidence = if !journal.is_empty() {
            journal.iter().map(|l| Value::s(l)).collect()
        } else {
            vec![Value::s(cause)]
        };
        return (
            "worker-failure".to_string(),
            Some(cause.to_string()),
            evidence,
        );
    }
    let journal = string_list(&stall.get("journal"));
    let evidence = if !journal.is_empty() {
        journal.iter().map(|l| Value::s(l)).collect()
    } else if let Some(reason) = text(&stall.get("reason")) {
        vec![Value::s(reason)]
    } else {
        Vec::new()
    };
    ("unattributed".to_string(), None, evidence)
}

/// `_clean_run`: a run record in canonical shape, or None.
fn clean_run(run: &Value) -> Option<Value> {
    if !run.is_dict() {
        return None;
    }
    let outcome = match run.get("outcome").as_str() {
        Some(o @ ("pass" | "fail")) => o.to_string(),
        _ => "missing".to_string(),
    };
    let seconds = match run.get("seconds") {
        Value::Int(i) => Value::Int(i),
        Value::Float(f) => Value::Float(f),
        _ => Value::Null,
    };
    let stalls = match run.get("stalls").as_list() {
        Some(items) => items
            .iter()
            .filter(|s| s.is_dict())
            .cloned()
            .collect::<Vec<Value>>(),
        None => Vec::new(),
    };
    Some(Value::obj(vec![
        ("outcome", Value::s(&outcome)),
        ("seconds", seconds),
        ("stalls", Value::List(stalls)),
    ]))
}

/// Seconds total with Python's int/float promotion: int while
/// every summed value is an int, float once any float joins.
#[derive(Default)]
struct SecondsTotal {
    ints: i64,
    floats: f64,
    any_float: bool,
}

impl SecondsTotal {
    fn add(&mut self, value: &Value) {
        match value {
            Value::Int(i) => {
                self.ints += i;
                self.floats += *i as f64;
            }
            Value::Float(f) => {
                self.any_float = true;
                self.floats += f;
            }
            _ => {}
        }
    }
    fn value(&self) -> Value {
        if self.any_float {
            Value::Float(self.floats)
        } else {
            Value::Int(self.ints)
        }
    }
}

/// `run_comparison(job_ids, runs_by_version, images_by_version)`.
pub fn run_comparison(job_ids: &Value, runs_by_version: &Value, images_by_version: &Value) -> Value {
    let jobs: Vec<String> = match job_ids.as_list() {
        Some(items) => items
            .iter()
            .filter_map(|j| j.as_str().map(|s| s.to_string()))
            .collect(),
        None => Vec::new(),
    };
    let versions: Vec<String> = match runs_by_version.as_map() {
        Some(pairs) => pairs.iter().map(|(k, _)| k.clone()).collect(),
        None => Vec::new(),
    };
    let images = if images_by_version.is_dict() {
        images_by_version.clone()
    } else {
        Value::obj(vec![])
    };
    let mut totals: Vec<(String, Value)> = Vec::new();
    let mut seconds_totals: Vec<SecondsTotal> = Vec::new();
    for version in &versions {
        totals.push((
            version.clone(),
            Value::obj(vec![
                ("jobs", Value::Int(0)),
                ("passed", Value::Int(0)),
                ("failed", Value::Int(0)),
                ("seconds", Value::Int(0)),
                ("stalls", Value::Int(0)),
            ]),
        ));
        seconds_totals.push(SecondsTotal::default());
    }
    let mut table = Vec::new();
    let mut defects = Vec::new();
    let mut measurements = Vec::new();
    for job in &jobs {
        let mut row_versions: Vec<(String, Value)> = Vec::new();
        for (vi, version) in versions.iter().enumerate() {
            let runs = runs_by_version.get(version);
            let raw = if runs.is_dict() {
                runs.get(job)
            } else {
                Value::Null
            };
            let run = clean_run(&raw).unwrap_or_else(|| {
                Value::obj(vec![
                    ("outcome", Value::s("missing")),
                    ("seconds", Value::Null),
                    ("stalls", Value::List(Vec::new())),
                ])
            });
            let image = images.get(version);
            let stalls = run.get("stalls");
            let stall_items: Vec<Value> = stalls.as_list().cloned().unwrap_or_default();
            let mut kinds: Vec<Value> = Vec::new();
            for stall in &stall_items {
                let (kind, detail, evidence) = attribute_stall(stall, &image);
                if kind == "image-defect" {
                    defects.push(Value::obj(vec![
                        ("job", Value::s(job)),
                        ("version", Value::s(version)),
                        ("kind", Value::s(detail.as_deref().unwrap_or(""))),
                        ("evidence", Value::List(evidence)),
                    ]));
                    kinds.push(Value::s(detail.as_deref().unwrap_or("")));
                }
            }
            let outcome = run.get("outcome");
            let seconds = run.get("seconds");
            row_versions.push((
                version.clone(),
                Value::obj(vec![
                    ("outcome", outcome.clone()),
                    ("seconds", seconds.clone()),
                    ("stalls", Value::Int(stall_items.len() as i64)),
                    ("defect_kinds", Value::List(kinds.clone())),
                ]),
            ));
            let total = &mut totals[vi].1;
            fn bump(total: &mut Value, key: &str) {
                let cur = total.get(key).as_int().unwrap_or(0);
                total.set(key, Value::Int(cur + 1));
            }
            bump(total, "jobs");
            match outcome.as_str() {
                Some("pass") => bump(total, "passed"),
                Some("fail") => bump(total, "failed"),
                _ => {}
            }
            if !seconds.is_null() {
                seconds_totals[vi].add(&seconds);
                total.set("seconds", seconds_totals[vi].value());
            }
            let stall_count = total.get("stalls").as_int().unwrap_or(0);
            total.set("stalls", Value::Int(stall_count + stall_items.len() as i64));
            measurements.push(Value::obj(vec![
                ("job", Value::s(job)),
                ("version", Value::s(version)),
                ("seconds", seconds),
                ("outcome", outcome),
                ("stalls", Value::Int(stall_items.len() as i64)),
                ("defect_kinds", Value::List(kinds)),
            ]));
        }
        table.push(Value::obj(vec![
            ("job", Value::s(job)),
            ("versions", Value::Map(row_versions)),
        ]));
    }
    Value::obj(vec![
        ("jobs", Value::List(jobs.iter().map(|j| Value::s(j)).collect())),
        (
            "versions",
            Value::List(versions.iter().map(|v| Value::s(v)).collect()),
        ),
        ("table", Value::List(table)),
        ("totals", Value::Map(totals)),
        ("defects", Value::List(defects)),
        ("measurements", Value::List(measurements)),
    ])
}

/// `measurement_records(comparison)` — the watchdog-style lines.
pub fn measurement_records(comparison: &Value) -> Vec<String> {
    if !comparison.is_dict() {
        return Vec::new();
    }
    let records = comparison.get("measurements");
    let items = match records.as_list() {
        Some(items) => items,
        None => return Vec::new(),
    };
    let mut lines = Vec::new();
    for record in items {
        if !record.is_dict() {
            continue;
        }
        let kinds = record.get("defect_kinds");
        let joined = match kinds.as_list() {
            Some(list) if !list.is_empty() => list
                .iter()
                .map(|k| k.py_str())
                .collect::<Vec<String>>()
                .join(","),
            _ => "none".to_string(),
        };
        lines.push(format!(
            "job {} under {}: {} in {} seconds, {} stalls, defects {}",
            record.get("job").py_str(),
            record.get("version").py_str(),
            record.get("outcome").py_str(),
            record.get("seconds").py_str(),
            record.get("stalls").py_str(),
            joined
        ));
    }
    lines
}

/// `revision_note(defects)` — a proposed change per defect,
/// deduped. A proposal only; nothing auto-applies.
pub fn revision_note(defects: &Value) -> Value {
    if !defects.is_list() {
        return Value::obj(vec![
            ("next_version_changes", Value::List(Vec::new())),
            ("note", Value::s("no defects given")),
        ]);
    }
    let items = defects.as_list().cloned().unwrap_or_default();
    let mut seen: Vec<(Option<String>, Option<String>)> = Vec::new();
    let mut changes: Vec<Value> = Vec::new();
    for defect in &items {
        if !defect.is_dict() {
            continue;
        }
        let kind = defect.get("kind").as_str().map(|s| s.to_string());
        let evidence = defect.get("evidence");
        let subject = match evidence.as_list() {
            Some(list) if !list.is_empty() => list[0].as_str().map(|s| s.to_string()),
            _ => None,
        };
        let key = (kind.clone(), subject.clone());
        if seen.contains(&key) {
            continue;
        }
        seen.push(key);
        match (kind.as_deref(), &subject) {
            (Some("missing-skill"), Some(subject)) => {
                changes.push(Value::s(&format!(
                    "add skill {} to the skills layer (evidence: {})",
                    subject, subject
                )));
            }
            (Some("bad-instruction"), Some(subject)) => {
                changes.push(Value::s(&format!(
                    "remove or replace instruction {} (evidence: {})",
                    subject, subject
                )));
            }
            (Some("thin-brief"), _) => {
                changes.push(Value::s(&format!(
                    "thicken the environment brief layer for job {} (evidence: {})",
                    defect.get("job").py_str(),
                    subject.as_deref().unwrap_or("stall for context")
                )));
            }
            _ => continue,
        }
    }
    Value::obj(vec![
        ("next_version_changes", Value::List(changes)),
        ("note", Value::s("proposal only; nothing auto-applies")),
    ])
}
