//! OS-083 workspace/artifact store (minimal), first light
//! (`os/mos/artifact_store.py`).
//!
//! A git-backed versioned shared filesystem where dispatched jobs
//! deposit work products and reference them by path in the job
//! record, instead of pasting work products through chat. Layout:
//!
//! ```text
//! <root>/jobs/<job_id>/<artifact name>
//! <root>/jobs/<job_id>/manifest.json
//! ```
//!
//! Every deposit is one git commit: the artifact file plus the job
//! manifest. Version numbers count from 1 per artifact name. A
//! redeposit of byte-identical content is a no-op returning the
//! current version with no new commit.
//!
//! The one deliberate Rust divergence: [`ArtifactStoreError`] is
//! the single error type (the Python original lets a raw
//! `OSError` escape when the latest-bytes file is missing from
//! disk); callers match on the message, which keeps the refusal
//! texts identical.

use serde_json::{Map, Value};
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};
use std::time::Duration;

use crate::git::{self, GitError};

pub const STORE_ROOT_DEFAULT: &str = "/var/lib/metaos/artifacts";
pub const MANIFEST_NAME: &str = "manifest.json";

/// Refused deposit, bad name, missing artifact, or git failure.
/// Mirrors `artifact_store.ArtifactStoreError`.
#[derive(Debug, Clone)]
pub struct ArtifactStoreError(pub String);

impl std::fmt::Display for ArtifactStoreError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl std::error::Error for ArtifactStoreError {}

impl From<GitError> for ArtifactStoreError {
    fn from(e: GitError) -> Self {
        ArtifactStoreError(e.0)
    }
}

fn git(root: &Path, args: &[&str]) -> Result<String, ArtifactStoreError> {
    if !git::have_git() {
        return Err(ArtifactStoreError(
            "git is not available on this machine".to_string(),
        ));
    }
    Ok(git::run(
        &root.to_string_lossy(),
        args,
        Duration::from_secs(60),
    )?)
}

fn validate_job_id(job_id: &str) -> Result<&str, ArtifactStoreError> {
    if job_id.is_empty() {
        return Err(ArtifactStoreError(
            "job id must be a non-empty string".to_string(),
        ));
    }
    if job_id.contains('/')
        || job_id.contains('\\')
        || job_id.contains(char::from(0))
        || job_id == "."
        || job_id == ".."
    {
        return Err(ArtifactStoreError(
            "job id must be a single path segment".to_string(),
        ));
    }
    if !job_id
        .chars()
        .all(|c| c.is_alphanumeric() || c == '.' || c == '_' || c == '-')
    {
        return Err(ArtifactStoreError(
            "job id holds characters outside [A-Za-z0-9._-]".to_string(),
        ));
    }
    Ok(job_id)
}

fn validate_name(name: &str) -> Result<&str, ArtifactStoreError> {
    if name.is_empty() {
        return Err(ArtifactStoreError(
            "artifact name must be a non-empty string".to_string(),
        ));
    }
    if name.starts_with('/') || name.contains(char::from(0)) || name.contains('\\') {
        return Err(ArtifactStoreError(
            "artifact name must be a relative POSIX path".to_string(),
        ));
    }
    if name
        .split('/')
        .any(|part| part.is_empty() || part == "." || part == "..")
    {
        return Err(ArtifactStoreError(
            "artifact name must not contain empty, . or .. segments".to_string(),
        ));
    }
    Ok(name)
}

fn job_dir(root: &Path, job_id: &str) -> Result<PathBuf, ArtifactStoreError> {
    validate_job_id(job_id)?;
    Ok(root.join("jobs").join(job_id))
}

fn manifest_path(root: &Path, job_id: &str) -> Result<PathBuf, ArtifactStoreError> {
    Ok(job_dir(root, job_id)?.join(MANIFEST_NAME))
}

fn read_manifest(root: &Path, job_id: &str) -> Result<Map<String, Value>, ArtifactStoreError> {
    let path = manifest_path(root, job_id)?;
    if !path.exists() {
        let mut manifest = Map::new();
        manifest.insert("job_id".to_string(), Value::String(job_id.to_string()));
        manifest.insert("artifacts".to_string(), Value::Object(Map::new()));
        return Ok(manifest);
    }
    let text = std::fs::read_to_string(&path)
        .map_err(|e| ArtifactStoreError(format!("manifest unreadable: {e}")))?;
    let data: Value = serde_json::from_str(&text)
        .map_err(|e| ArtifactStoreError(format!("manifest unreadable: {e}")))?;
    let obj = data.as_object().ok_or_else(|| {
        ArtifactStoreError("manifest has an unexpected shape".to_string())
    })?;
    if !matches!(obj.get("artifacts"), Some(Value::Object(_))) {
        return Err(ArtifactStoreError(
            "manifest has an unexpected shape".to_string(),
        ));
    }
    Ok(obj.clone())
}

fn write_manifest(
    root: &Path,
    job_id: &str,
    manifest: &Map<String, Value>,
) -> Result<(), ArtifactStoreError> {
    let path = manifest_path(root, job_id)?;
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| ArtifactStoreError(format!("manifest unreadable: {e}")))?;
    }
    let text = serde_json::to_string_pretty(&Value::Object(manifest.clone()))
        .map_err(|e| ArtifactStoreError(format!("manifest unreadable: {e}")))?;
    let tmp = path.with_extension("json.tmp");
    std::fs::write(&tmp, text + "\n")
        .map_err(|e| ArtifactStoreError(format!("manifest unreadable: {e}")))?;
    std::fs::rename(&tmp, &path)
        .map_err(|e| ArtifactStoreError(format!("manifest unreadable: {e}")))?;
    Ok(())
}

fn ensure_repo(root: &Path) -> Result<(), ArtifactStoreError> {
    std::fs::create_dir_all(root)
        .map_err(|e| ArtifactStoreError(format!("manifest unreadable: {e}")))?;
    if !root.join(".git").is_dir() {
        git(root, &["init", "-q", "-b", "main"])?;
    }
    Ok(())
}

fn relpath(job_id: &str, name: &str) -> String {
    format!("jobs/{job_id}/{name}")
}

/// One manifest record for a deposited artifact.
#[derive(Debug, Clone)]
pub struct DepositRecord {
    pub name: String,
    pub path: String,
    pub reference: String,
    pub version: u64,
    pub sha256: String,
    pub size: usize,
    pub author: String,
    pub new_commit: bool,
    pub deposited_at: u64,
}

impl DepositRecord {
    fn to_json(&self) -> Value {
        let mut map = Map::new();
        map.insert("name".to_string(), Value::String(self.name.clone()));
        map.insert("path".to_string(), Value::String(self.path.clone()));
        map.insert(
            "reference".to_string(),
            Value::String(self.reference.clone()),
        );
        map.insert(
            "version".to_string(),
            Value::Number(self.version.into()),
        );
        map.insert(
            "sha256".to_string(),
            Value::String(self.sha256.clone()),
        );
        map.insert("size".to_string(), Value::Number((self.size as u64).into()));
        map.insert(
            "author".to_string(),
            Value::String(self.author.clone()),
        );
        map.insert(
            "deposited_at".to_string(),
            Value::Number(self.deposited_at.into()),
        );
        Value::Object(map)
    }
}

/// Deposit bytes as one version. Returns the manifest record.
/// A byte-identical redeposit returns the current record with
/// `new_commit` false; every other deposit commits and returns
/// `new_commit` true.
pub fn deposit(
    root: &Path,
    job_id: &str,
    name: &str,
    data: &[u8],
    author: &str,
    now: u64,
) -> Result<DepositRecord, ArtifactStoreError> {
    validate_job_id(job_id)?;
    validate_name(name)?;
    ensure_repo(root)?;
    let dir = job_dir(root, job_id)?;
    std::fs::create_dir_all(&dir)
        .map_err(|e| ArtifactStoreError(format!("manifest unreadable: {e}")))?;
    let mut manifest = read_manifest(root, job_id)?;
    manifest.insert("job_id".to_string(), Value::String(job_id.to_string()));
    let digest = hex_sha256(data);
    // No-op check first (borrow ends before any mutation below).
    if let Some(current_version) = manifest
        .get("artifacts")
        .and_then(|v| v.as_object())
        .and_then(|o| o.get(name))
        .and_then(|v| v.as_object())
        .filter(|o| o.get("sha256").and_then(|v| v.as_str()) == Some(digest.as_str()))
        .and_then(|o| o.get("version"))
        .and_then(|v| v.as_u64())
    {
        let current = manifest["artifacts"][name]
            .as_object()
            .cloned()
            .unwrap_or_default();
        return Ok(record_from(&current, name, current_version, false));
    }
    let version = manifest
        .get("artifacts")
        .and_then(|v| v.as_object())
        .and_then(|o| o.get(name))
        .and_then(|v| v.as_object())
        .and_then(|o| o.get("version"))
        .and_then(|v| v.as_u64())
        .unwrap_or(0)
        + 1;
    let target = dir.join(name);
    if let Some(parent) = target.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| ArtifactStoreError(format!("manifest unreadable: {e}")))?;
    }
    let tmp = target.with_extension("tmp");
    std::fs::write(&tmp, data)
        .map_err(|e| ArtifactStoreError(format!("manifest unreadable: {e}")))?;
    std::fs::rename(&tmp, &target)
        .map_err(|e| ArtifactStoreError(format!("manifest unreadable: {e}")))?;
    let author = if author.is_empty() {
        "unknown".to_string()
    } else {
        author.to_string()
    };
    let record = DepositRecord {
        name: name.to_string(),
        path: relpath(job_id, name).replace(std::path::MAIN_SEPARATOR, "/"),
        reference: format!("artifact:{job_id}/{name}@v{version}"),
        version,
        sha256: digest,
        size: data.len(),
        author: author.clone(),
        new_commit: true,
        deposited_at: now,
    };
    manifest.insert("job_id".to_string(), Value::String(job_id.to_string()));
    manifest
        .get_mut("artifacts")
        .and_then(|v| v.as_object_mut())
        .ok_or_else(|| {
            ArtifactStoreError("manifest has an unexpected shape".to_string())
        })?
        .insert(name.to_string(), record.to_json());
    write_manifest(root, job_id, &manifest)?;
    // Commit the artifact file plus the job manifest, with the
    // local-only store identity (config inside the repo, never
    // global).
    git(
        root,
        &[
            "add",
            "--",
            &relpath(job_id, name),
            &format!("jobs/{job_id}/{MANIFEST_NAME}"),
        ],
    )?;
    git(
        root,
        &[
            "-c",
            "user.name=metaos-artifact-store",
            "-c",
            "user.email=artifact-store@metaos.local",
            "commit",
            "-q",
            "-m",
            &format!("job {job_id}: deposit {name} v{version} by {author}"),
        ],
    )?;
    Ok(record)
}

fn record_from(obj: &Map<String, Value>, name: &str, version: u64, new_commit: bool) -> DepositRecord {
    let str_field = |k: &str| {
        obj.get(k)
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string()
    };
    DepositRecord {
        name: name.to_string(),
        path: str_field("path"),
        reference: str_field("reference"),
        version,
        sha256: str_field("sha256"),
        size: obj
            .get("size")
            .and_then(|v| v.as_u64())
            .unwrap_or(0) as usize,
        author: str_field("author"),
        new_commit,
        deposited_at: obj
            .get("deposited_at")
            .and_then(|v| v.as_u64())
            .unwrap_or(0),
    }
}

fn hex_sha256(data: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(data);
    hasher
        .finalize()
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect()
}

/// Manifest records for one job, sorted by artifact name.
pub fn list_artifacts(
    root: &Path,
    job_id: &str,
) -> Result<Vec<DepositRecord>, ArtifactStoreError> {
    validate_job_id(job_id)?;
    let manifest = read_manifest(root, job_id)?;
    let artifacts = manifest
        .get("artifacts")
        .and_then(|v| v.as_object())
        .ok_or_else(|| {
            ArtifactStoreError("manifest has an unexpected shape".to_string())
        })?;
    let mut names: Vec<&String> = artifacts.keys().collect();
    names.sort();
    Ok(names
        .into_iter()
        .map(|name| {
            let obj = artifacts[name].as_object().cloned().unwrap_or_default();
            let version = obj
                .get("version")
                .and_then(|v| v.as_u64())
                .unwrap_or(0);
            record_from(&obj, name, version, false)
        })
        .collect())
}

fn version_commits(
    root: &Path,
    job_id: &str,
    name: &str,
) -> Result<Vec<String>, ArtifactStoreError> {
    let out = git(root, &["log", "--format=%H", "--", &relpath(job_id, name)])?;
    Ok(out.lines().map(|l| l.to_string()).filter(|l| !l.is_empty()).collect())
}

/// Artifact bytes: latest version, or one numbered version.
/// A numbered version maps to its git commit, so a version read
/// never depends on the current file on disk.
pub fn read(
    root: &Path,
    job_id: &str,
    name: &str,
    version: Option<u64>,
) -> Result<Vec<u8>, ArtifactStoreError> {
    validate_job_id(job_id)?;
    validate_name(name)?;
    let manifest = read_manifest(root, job_id)?;
    let artifacts = manifest
        .get("artifacts")
        .and_then(|v| v.as_object())
        .ok_or_else(|| {
            ArtifactStoreError("manifest has an unexpected shape".to_string())
        })?;
    if !artifacts.contains_key(name) {
        return Err(ArtifactStoreError(format!(
            "no artifact {name:?} for job {job_id:?}"
        )));
    }
    match version {
        None => std::fs::read(job_dir(root, job_id)?.join(name))
            .map_err(|e| ArtifactStoreError(format!("artifact unreadable: {e}"))),
        Some(v) => {
            if v < 1 {
                return Err(ArtifactStoreError(
                    "version must be a positive integer".to_string(),
                ));
            }
            let commits = version_commits(root, job_id, name)?;
            if v as usize > commits.len() {
                return Err(ArtifactStoreError(format!(
                    "artifact {name:?} for job {job_id:?} has {} versions, no v{v}",
                    commits.len()
                )));
            }
            let commit = &commits[commits.len() - v as usize];
            if !git::have_git() {
                return Err(ArtifactStoreError(
                    "git is not available on this machine".to_string(),
                ));
            }
            git::run_bytes(
                &root.to_string_lossy(),
                &["show", &format!("{commit}:{}", relpath(job_id, name))],
                None,
                Duration::from_secs(60),
            )
            .map_err(ArtifactStoreError::from)
            .and_then(|bytes| {
                // git show exits 0 with the bytes on success; an
                // empty result with a nonzero exit is already an
                // error above.
                Ok(bytes)
            })
        }
    }
}

/// Version records, oldest first, from the artifact git log.
pub fn history(
    root: &Path,
    job_id: &str,
    name: &str,
) -> Result<Vec<(u64, String)>, ArtifactStoreError> {
    validate_job_id(job_id)?;
    validate_name(name)?;
    let commits = version_commits(root, job_id, name)?;
    Ok(commits
        .iter()
        .rev()
        .enumerate()
        .map(|(i, c)| (i as u64 + 1, c.clone()))
        .collect())
}

/// Return a copy of a job record carrying its artifact paths.
/// The input record is never mutated. Mirrors
/// `artifact_store.attach`.
pub fn attach(
    root: &Path,
    job_id: &str,
    record: &Value,
) -> Result<Value, ArtifactStoreError> {
    validate_job_id(job_id)?;
    let obj = record.as_object().ok_or_else(|| {
        ArtifactStoreError("job record must be a dict".to_string())
    })?;
    let mut out = obj.clone();
    let mut existing: Vec<Value> = match obj.get("artifacts") {
        Some(Value::Array(items)) => items.clone(),
        _ => Vec::new(),
    };
    for item in list_artifacts(root, job_id)? {
        let mut entry = Map::new();
        entry.insert("path".to_string(), Value::String(item.path));
        entry.insert("reference".to_string(), Value::String(item.reference));
        entry.insert(
            "version".to_string(),
            Value::Number(item.version.into()),
        );
        entry.insert("sha256".to_string(), Value::String(item.sha256));
        existing.push(Value::Object(entry));
    }
    out.insert("artifacts".to_string(), Value::Array(existing));
    Ok(Value::Object(out))
}

/// Minimal CLI: deposit|list|read|show. Errors exit 2.
/// Mirrors `artifact_store.main` argument shapes exactly.
pub fn cli(argv: &[String]) -> (i32, Vec<u8>, String) {
    let fail = |e: String| {
        (
            2,
            Vec::new(),
            format!("ARTIFACT_STORE_ERROR: {e}\n"),
        )
    };
    if argv.is_empty() {
        return (
            2,
            Vec::new(),
            "usage: artifact_store deposit|list|read|show ROOT JOB [ARGS]\n".to_string(),
        );
    }
    let now = system_now();
    match argv[0].as_str() {
        "deposit" if argv.len() >= 5 => {
            let mut author = "";
            if argv[5..].contains(&"--author".to_string()) {
                let i = argv.iter().position(|a| a == "--author").unwrap();
                if i + 1 < argv.len() {
                    author = &argv[i + 1];
                }
            }
            let data = match std::fs::read(&argv[4]) {
                Ok(d) => d,
                Err(e) => return fail(e.to_string()),
            };
            match deposit(Path::new(&argv[1]), &argv[2], &argv[3], &data, author, now) {
                Ok(record) => {
                    let mut line = serde_json::to_string(&record.to_json())
                        .unwrap_or_else(|_| "{}".to_string());
                    line.push('\n');
                    (0, line.into_bytes(), String::new())
                }
                Err(e) => fail(e.to_string()),
            }
        }
        "list" if argv.len() == 3 => match list_artifacts(Path::new(&argv[1]), &argv[2]) {
            Ok(items) => {
                let mut out = Vec::new();
                for item in &items {
                    let mut line = serde_json::to_string(&item.to_json())
                        .unwrap_or_else(|_| "{}".to_string());
                    line.push('\n');
                    out.extend_from_slice(line.as_bytes());
                }
                (0, out, String::new())
            }
            Err(e) => fail(e.to_string()),
        },
        "read" if argv.len() >= 4 => {
            let mut version = None;
            if argv[4..].contains(&"--version".to_string()) {
                let i = argv.iter().position(|a| a == "--version").unwrap();
                match argv.get(i + 1).and_then(|v| v.parse::<u64>().ok()) {
                    Some(v) => version = Some(v),
                    None => {
                        return (
                            2,
                            Vec::new(),
                            "ARTIFACT_STORE_ERROR: invalid --version\n".to_string(),
                        )
                    }
                }
            }
            match read(Path::new(&argv[1]), &argv[2], &argv[3], version) {
                Ok(bytes) => (0, bytes, String::new()),
                Err(e) => fail(e.to_string()),
            }
        }
        "show" if argv.len() == 4 => match history(Path::new(&argv[1]), &argv[2], &argv[3]) {
            Ok(entries) => {
                let mut out = String::new();
                for (version, commit) in &entries {
                    out.push_str(&format!("v{version} {commit}\n"));
                }
                (0, out.into_bytes(), String::new())
            }
            Err(e) => fail(e.to_string()),
        },
        _ => (
            2,
            Vec::new(),
            "usage: artifact_store deposit|list|read|show ROOT JOB [ARGS]\n".to_string(),
        ),
    }
}

fn system_now() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}
