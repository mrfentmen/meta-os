//! Minimal on-disk store readers for the disk audit.
//!
//! `disk_audit` needs two read paths: the OS-078 shared/agent
//! journals (`mos/memory.py` shape) and the OS-083 artifact
//! manifests (`mos/artifact_store.py` shape). Their canonical
//! homes are `os-memory` (B17) and `os-workspace` (B19); this
//! module carries the smallest read-only projections the audit
//! needs, so the budget crate stays self-contained on its branch
//! (path dependencies across batch branches resolve to skeletons
//! until integration). Behavior matches the owners exactly:
//! corrupt journals raise loudly, missing roots read as empty,
//! versioned artifact reads go through git.

use serde_json::{Map, Value};
use std::path::Path;

/// A journal read error: corrupt line or unreadable file.
#[derive(Debug, Clone)]
pub struct StoreError(pub String);

impl std::fmt::Display for StoreError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl std::error::Error for StoreError {}

fn journal_entries(journal_path: &Path) -> Result<Vec<Map<String, Value>>, StoreError> {
    let text = std::fs::read_to_string(journal_path)
        .map_err(|e| StoreError(format!("journal unreadable: {e}")))?;
    let mut entries = Vec::new();
    for (i, line) in text.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let value: Value = serde_json::from_str(line)
            .map_err(|_| StoreError(format!("journal line {} does not parse", i + 1)))?;
        let obj = value.as_object().ok_or_else(|| {
            StoreError(format!("journal line {} has an unexpected shape", i + 1))
        })?;
        let ok = obj.get("key").and_then(|v| v.as_str()).is_some()
            && obj.get("version").and_then(|v| v.as_i64()).is_some()
            && obj.get("text").and_then(|v| v.as_str()).is_some()
            && obj.get("author").and_then(|v| v.as_str()).is_some()
            && obj.get("ts").and_then(|v| v.as_i64()).is_some();
        if !ok {
            return Err(StoreError(format!(
                "journal line {} has an unexpected shape",
                i + 1
            )));
        }
        entries.push(obj.clone());
    }
    Ok(entries)
}

/// Latest shared entries, keyed by key. Missing root reads as
/// empty; a corrupt journal raises.
pub fn list_shared_keys(memory_root: &Path) -> Result<Map<String, Value>, StoreError> {
    if !memory_root.is_dir() {
        return Ok(Map::new());
    }
    let journal = memory_root.join("shared/journal.jsonl");
    if !journal.exists() {
        return Ok(Map::new());
    }
    let mut latest = Map::new();
    for entry in journal_entries(&journal)? {
        if let Some(key) = entry.get("key").and_then(|v| v.as_str()) {
            latest.insert(key.to_string(), Value::Object(entry));
        }
    }
    Ok(latest)
}

/// Latest own entries for one agent, keyed by key. Mirrors
/// `mos/memory.py list_keys` error rules: a bad nick or a corrupt
/// journal raises; a missing root reads as empty.
pub fn list_agent_keys(memory_root: &Path, agent: &str) -> Result<Map<String, Value>, StoreError> {
    if !memory_root.is_dir() {
        return Ok(Map::new());
    }
    if agent.is_empty()
        || agent.contains('/')
        || agent.contains('\\')
        || agent.contains(char::from(0))
        || agent == "."
        || agent == ".."
        || !agent
            .chars()
            .all(|c| c.is_alphanumeric() || c == '.' || c == '_' || c == '-')
    {
        return Err(StoreError(format!("bad agent nick: {agent:?}")));
    }
    let journal = memory_root.join("agents").join(agent).join("journal.jsonl");
    if !journal.exists() {
        return Ok(Map::new());
    }
    let mut latest = Map::new();
    for entry in journal_entries(&journal)? {
        if let Some(key) = entry.get("key").and_then(|v| v.as_str()) {
            latest.insert(key.to_string(), Value::Object(entry));
        }
    }
    Ok(latest)
}

/// Manifest records for one job, keyed by artifact name.
/// Missing manifest reads as empty.
pub fn list_artifact_entries(
    artifact_root: &Path,
    job_id: &str,
) -> Result<Map<String, Value>, StoreError> {
    let path = artifact_root
        .join("jobs")
        .join(job_id)
        .join("manifest.json");
    if !path.exists() {
        return Ok(Map::new());
    }
    let text = std::fs::read_to_string(&path)
        .map_err(|e| StoreError(format!("manifest unreadable: {e}")))?;
    let data: Value = serde_json::from_str(&text)
        .map_err(|e| StoreError(format!("manifest unreadable: {e}")))?;
    match data.get("artifacts").and_then(|v| v.as_object()) {
        Some(artifacts) => Ok(artifacts.clone()),
        None => Err(StoreError("manifest has an unexpected shape".to_string())),
    }
}

/// Number of git commits touching one artifact path (its version
/// count). Errors (no repo, no git) read as zero versions here;
/// the audit files them as leaks from the manifest mismatch.
pub fn artifact_version_count(artifact_root: &Path, job_id: &str, name: &str) -> usize {
    let out = std::process::Command::new("git")
        .arg("-c")
        .arg("safe.directory=*")
        .arg("-C")
        .arg(artifact_root)
        .arg("log")
        .arg("--format=%H")
        .arg("--")
        .arg(format!("jobs/{job_id}/{name}"))
        .output();
    match out {
        Ok(o) if o.status.success() => String::from_utf8_lossy(&o.stdout)
            .lines()
            .filter(|l| !l.is_empty())
            .count(),
        _ => 0,
    }
}

/// Bytes of one artifact version via `git show`. `None` on any
/// git failure (the audit files it as a leak).
pub fn read_artifact_version(
    artifact_root: &Path,
    job_id: &str,
    name: &str,
    version: u64,
) -> Option<Vec<u8>> {
    let log = std::process::Command::new("git")
        .arg("-c")
        .arg("safe.directory=*")
        .arg("-C")
        .arg(artifact_root)
        .arg("log")
        .arg("--format=%H")
        .arg("--")
        .arg(format!("jobs/{job_id}/{name}"))
        .output()
        .ok()?;
    if !log.status.success() {
        return None;
    }
    let commits: Vec<String> = String::from_utf8_lossy(&log.stdout)
        .lines()
        .filter(|l| !l.is_empty())
        .map(|s| s.to_string())
        .collect();
    if version < 1 || version as usize > commits.len() {
        return None;
    }
    let commit = &commits[commits.len() - version as usize];
    let show = std::process::Command::new("git")
        .arg("-c")
        .arg("safe.directory=*")
        .arg("-C")
        .arg(artifact_root)
        .arg("show")
        .arg(format!("{commit}:jobs/{job_id}/{name}"))
        .output()
        .ok()?;
    if !show.status.success() {
        return None;
    }
    Some(show.stdout)
}

/// Latest artifact bytes from disk. `None` when unreadable.
pub fn read_artifact_latest(artifact_root: &Path, job_id: &str, name: &str) -> Option<Vec<u8>> {
    std::fs::read(artifact_root.join("jobs").join(job_id).join(name)).ok()
}
