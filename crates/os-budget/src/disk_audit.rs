//! OS-128 disk-state audit, first light (`os/mos/disk_audit.py`).
//!
//! The recovery law says state lives on disk, never in a session:
//! whatever recovery needs must be readable from the store by a
//! process that has never met the agent that wrote it. This
//! module is the cold reader. Given job records plus the two
//! on-disk stores it walks every job and reconstructs its complete
//! state from disk alone, with no bus, no Redis, and no live
//! session. The audit passes only when the leak list is empty. A
//! leak names its layer (spec, baton, claim, artifacts, memory,
//! memory-journal, record) so the fix task lands in the owning
//! lane. A corrupt memory journal is a loud failure, never a
//! skipped memory.

use serde_json::{Map, Value};
use std::path::Path;

use crate::stores;

const ARTIFACT_PREFIX: &str = "artifact:";

/// Unreadable audit input: not a job record, not JSON, not a list.
#[derive(Debug, Clone)]
pub struct DiskAuditError(pub String);

impl std::fmt::Display for DiskAuditError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl std::error::Error for DiskAuditError {}

fn text(value: &Value) -> Option<String> {
    match value {
        Value::String(s) => {
            let t = s.trim();
            if t.is_empty() {
                None
            } else {
                Some(t.to_string())
            }
        }
        _ => None,
    }
}

fn str_list(value: &Value) -> Vec<String> {
    match value {
        Value::Array(items) => items
            .iter()
            .filter_map(|i| match i {
                Value::String(s) if !s.is_empty() => Some(s.clone()),
                _ => None,
            })
            .collect(),
        Value::String(s) if !s.is_empty() => vec![s.clone()],
        _ => Vec::new(),
    }
}

fn goal(record: &Map<String, Value>) -> Option<String> {
    if let Some(g) = record.get("goal").and_then(text) {
        return Some(g);
    }
    if let Value::String(spec) = record.get("spec").unwrap_or(&Value::Null) {
        for line in spec.lines() {
            let stripped = line.trim();
            if stripped.to_lowercase().starts_with("goal:") {
                if let Some(g) = text(&Value::String(stripped["goal:".len()..].to_string())) {
                    return Some(g);
                }
                return None;
            }
        }
    }
    None
}

fn progress_notes(record: &Map<String, Value>) -> Vec<String> {
    let notes = str_list(record.get("progress_notes").unwrap_or(&Value::Null));
    if !notes.is_empty() {
        return notes;
    }
    match text(record.get("note").unwrap_or(&Value::Null)) {
        Some(n) => vec![n],
        None => Vec::new(),
    }
}

fn remaining_files(record: &Map<String, Value>) -> Vec<String> {
    let files = str_list(record.get("files").unwrap_or(&Value::Null));
    let completed: std::collections::HashSet<String> = str_list(
        record.get("completed_files").unwrap_or(&Value::Null),
    )
    .into_iter()
    .collect();
    files.into_iter().filter(|p| !completed.contains(p)).collect()
}

fn parse_artifact_ref(reference: &str) -> Option<(String, String, u64)> {
    let rest = reference.strip_prefix(ARTIFACT_PREFIX)?;
    let slash = rest.find('/')?;
    let (job_id, after) = rest.split_at(slash);
    let name_ver = &after[1..];
    let at = name_ver.rfind("@v")?;
    let (name, ver) = name_ver.split_at(at);
    if job_id.is_empty() || name.is_empty() {
        return None;
    }
    let version: u64 = ver[2..].parse().ok()?;
    if version < 1 {
        return None;
    }
    Some((job_id.to_string(), name.to_string(), version))
}

/// One leak: which job (if any), which layer, and the detail.
#[derive(Debug, Clone)]
pub struct Leak {
    pub job: Option<String>,
    pub layer: String,
    pub detail: String,
}

impl Leak {
    fn to_json(&self) -> Value {
        serde_json::json!({
            "job": self.job.clone().map(Value::String).unwrap_or(Value::Null),
            "layer": self.layer,
            "detail": self.detail,
        })
    }
}

/// One reconstructed job.
#[derive(Debug, Clone)]
pub struct AuditedJob {
    pub id: String,
    pub status: Option<String>,
    pub title: Option<String>,
    pub spec: Option<String>,
    pub goal: Option<String>,
    pub progress_notes: Vec<String>,
    pub remaining_files: Vec<String>,
    pub accept: Value,
    pub artifacts: Vec<String>,
    pub decisions: Vec<String>,
}

impl AuditedJob {
    fn to_json(&self) -> Value {
        serde_json::json!({
            "id": self.id,
            "status": self.status.clone().map(Value::String).unwrap_or(Value::Null),
            "title": self.title.clone().map(Value::String).unwrap_or(Value::Null),
            "spec": self.spec.clone().map(Value::String).unwrap_or(Value::Null),
            "goal": self.goal.clone().map(Value::String).unwrap_or(Value::Null),
            "progress_notes": self.progress_notes,
            "remaining_files": self.remaining_files,
            "accept": self.accept,
            "artifacts": self.artifacts,
            "decisions": self.decisions,
        })
    }
}

pub struct AuditResult {
    pub jobs: Vec<AuditedJob>,
    pub decisions: Vec<String>,
    pub leaks: Vec<Leak>,
    pub passed: bool,
}

/// Audit job records against the on-disk stores.
pub fn audit(
    memory_root: &Path,
    artifact_root: &Path,
    job_records: &Value,
) -> Result<AuditResult, DiskAuditError> {
    let records = job_records.as_array().ok_or_else(|| {
        DiskAuditError("job records must be a list".to_string())
    })?;
    let mut leaks: Vec<Leak> = Vec::new();
    let mut shared: Map<String, Value> = Map::new();
    if memory_root.is_dir() {
        match stores::list_shared_keys(memory_root) {
            Ok(keys) => shared = keys,
            Err(e) => leaks.push(Leak {
                job: None,
                layer: "memory-journal".to_string(),
                detail: format!("shared journal unreadable: {e}"),
            }),
        }
    }
    let mut journal_leaked = std::collections::HashSet::new();
    let mut agent_cache: Map<String, Value> = Map::new();
    let mut jobs_out = Vec::new();
    for record in records {
        let obj = match record.as_object() {
            Some(o) => o,
            None => {
                leaks.push(Leak {
                    job: None,
                    layer: "record".to_string(),
                    detail: "job record is not an object".to_string(),
                });
                continue;
            }
        };
        let job_id = text(obj.get("id").unwrap_or(&Value::Null))
            .or_else(|| text(obj.get("job_id").unwrap_or(&Value::Null)));
        let job_id = match job_id {
            Some(id) => id,
            None => {
                leaks.push(Leak {
                    job: None,
                    layer: "record".to_string(),
                    detail: "job record carries no id".to_string(),
                });
                continue;
            }
        };
        let spec = text(obj.get("spec").unwrap_or(&Value::Null));
        let title = text(obj.get("title").unwrap_or(&Value::Null));
        if title.is_none() || spec.is_none() {
            leaks.push(Leak {
                job: Some(job_id.clone()),
                layer: "spec".to_string(),
                detail: "cold reader cannot tell what this job is".to_string(),
            });
        }
        let status = text(obj.get("status").unwrap_or(&Value::Null));
        let job_goal = goal(obj);
        if status.as_deref() == Some("claimed") && job_goal.is_none() {
            leaks.push(Leak {
                job: Some(job_id.clone()),
                layer: "baton".to_string(),
                detail: "claimed job has no goal for the next worker".to_string(),
            });
        }
        let claimer = text(obj.get("claim").unwrap_or(&Value::Null));
        if status.as_deref() == Some("claimed") && claimer.is_none() {
            leaks.push(Leak {
                job: Some(job_id.clone()),
                layer: "claim".to_string(),
                detail: "claimed job names no holder or lease".to_string(),
            });
        }
        let mut verified = Vec::new();
        for reference in str_list(obj.get("artifacts").unwrap_or(&Value::Null)) {
            let (ref_job, name, version) = match parse_artifact_ref(&reference) {
                Some(p) => p,
                None => {
                    leaks.push(Leak {
                        job: Some(job_id.clone()),
                        layer: "artifacts".to_string(),
                        detail: format!("unparseable artifact reference: {reference}"),
                    });
                    continue;
                }
            };
            let entries = match stores::list_artifact_entries(artifact_root, &ref_job) {
                Ok(e) => e,
                Err(e) => {
                    leaks.push(Leak {
                        job: Some(job_id.clone()),
                        layer: "artifacts".to_string(),
                        detail: format!("store unreadable for {reference}: {e}"),
                    });
                    continue;
                }
            };
            let entry = match entries.get(&name) {
                Some(e) => e,
                None => {
                    leaks.push(Leak {
                        job: Some(job_id.clone()),
                        layer: "artifacts".to_string(),
                        detail: format!("no manifest entry for {reference}"),
                    });
                    continue;
                }
            };
            let manifest_version = entry.get("version").and_then(|v| v.as_u64()).unwrap_or(0);
            if manifest_version != version {
                leaks.push(Leak {
                    job: Some(job_id.clone()),
                    layer: "artifacts".to_string(),
                    detail: format!(
                        "manifest holds v{manifest_version}, record references {reference}"
                    ),
                });
                continue;
            }
            // Versioned read through git, exactly like
            // artifact_store.read(root, job, name, version).
            if stores::read_artifact_version(artifact_root, &ref_job, &name, version).is_none() {
                leaks.push(Leak {
                    job: Some(job_id.clone()),
                    layer: "artifacts".to_string(),
                    detail: format!("artifact bytes unreadable for {reference}"),
                });
                continue;
            }
            verified.push(reference);
        }
        let mut decisions_ok = Vec::new();
        for key in str_list(obj.get("decisions").unwrap_or(&Value::Null)) {
            let mut found = shared.contains_key(&key);
            if !found {
                if let Some(ref claimer_name) = claimer {
                    if !agent_cache.contains_key(claimer_name) {
                        if memory_root.is_dir() {
                            match stores::list_agent_keys(memory_root, claimer_name) {
                                Ok(keys) => {
                                    agent_cache.insert(
                                        claimer_name.clone(),
                                        Value::Object(keys),
                                    );
                                }
                                Err(e) => {
                                    if journal_leaked.insert(claimer_name.clone()) {
                                        leaks.push(Leak {
                                            job: None,
                                            layer: "memory-journal".to_string(),
                                            detail: format!(
                                                "journal for {claimer_name} unreadable: {e}"
                                            ),
                                        });
                                    }
                                    agent_cache.insert(
                                        claimer_name.clone(),
                                        Value::Object(Map::new()),
                                    );
                                }
                            }
                        } else {
                            agent_cache
                                .insert(claimer_name.clone(), Value::Object(Map::new()));
                        }
                    }
                    if let Some(Value::Object(keys)) = agent_cache.get(claimer_name) {
                        found = keys.contains_key(&key);
                    }
                }
            }
            if found {
                decisions_ok.push(key);
            } else {
                leaks.push(Leak {
                    job: Some(job_id.clone()),
                    layer: "memory".to_string(),
                    detail: format!("decision {key} in no journal the reader can see"),
                });
            }
        }
        jobs_out.push(AuditedJob {
            id: job_id,
            status,
            title,
            spec,
            goal: job_goal,
            progress_notes: progress_notes(obj),
            remaining_files: remaining_files(obj),
            accept: obj.get("accept").cloned().unwrap_or(Value::Null),
            artifacts: verified,
            decisions: decisions_ok,
        });
    }
    let mut decisions: Vec<String> = shared.keys().cloned().collect();
    decisions.sort();
    let passed = leaks.is_empty();
    Ok(AuditResult {
        jobs: jobs_out,
        decisions,
        leaks,
        passed,
    })
}

/// CLI: audit a jobs JSON file against two store roots.
/// Exit 0 when the leak list is empty, 1 when leaks are found, 2
/// when the input itself cannot be read.
pub fn cli(argv: &[String]) -> (i32, String, String) {
    let mut jobs_path: Option<&str> = None;
    let mut memory_root: Option<&str> = None;
    let mut artifact_root: Option<&str> = None;
    let mut it = argv.iter().peekable();
    while let Some(arg) = it.next() {
        match arg.as_str() {
            "--jobs" => jobs_path = it.next().map(|s| s.as_str()),
            "--memory-root" => memory_root = it.next().map(|s| s.as_str()),
            "--artifact-root" => artifact_root = it.next().map(|s| s.as_str()),
            _ => {}
        }
    }
    let (jobs_path, memory_root, artifact_root) =
        match (jobs_path, memory_root, artifact_root) {
            (Some(j), Some(m), Some(a)) => (j, m, a),
            _ => {
                return (
                    2,
                    String::new(),
                    "RELAY_ERROR: --jobs, --memory-root, and --artifact-root are required\n".to_string(),
                )
            }
        };
    let text = match std::fs::read_to_string(jobs_path) {
        Ok(t) => t,
        Err(e) => {
            return (
                2,
                String::new(),
                format!("RELAY_ERROR: cannot read jobs file: {e}\n"),
            )
        }
    };
    let job_records: Value = match serde_json::from_str(&text) {
        Ok(v) => v,
        Err(e) => {
            return (
                2,
                String::new(),
                format!("RELAY_ERROR: cannot read jobs file: {e}\n"),
            )
        }
    };
    let result = match audit(Path::new(memory_root), Path::new(artifact_root), &job_records) {
        Ok(r) => r,
        Err(e) => {
            return (2, String::new(), format!("RELAY_ERROR: {e}\n"));
        }
    };
    let mut out = String::new();
    for job in &result.jobs {
        out.push_str(&format!(
            "{} {} goal={} progress={} remaining={} artifacts={}\n",
            job.id,
            job.status.as_deref().unwrap_or("unknown"),
            job.goal.as_deref().unwrap_or("-"),
            job.progress_notes.len(),
            job.remaining_files.len(),
            job.artifacts.len(),
        ));
    }
    out.push_str(&format!("decisions visible: {}\n", result.decisions.len()));
    if result.passed {
        out.push_str("PASS: no leaks, every job reconstructable from disk\n");
        return (0, out, String::new());
    }
    for leak in &result.leaks {
        out.push_str(&format!(
            "LEAK {} {}: {}\n",
            leak.job.as_deref().unwrap_or("-"),
            leak.layer,
            leak.detail
        ));
    }
    out.push_str(&format!("FAIL: {} leak(s)\n", result.leaks.len()));
    (1, out, String::new())
}

pub fn result_to_json(result: &AuditResult) -> Value {
    serde_json::json!({
        "jobs": result.jobs.iter().map(|j| j.to_json()).collect::<Vec<_>>(),
        "decisions": result.decisions,
        "leaks": result.leaks.iter().map(|l| l.to_json()).collect::<Vec<_>>(),
        "passed": result.passed,
    })
}
