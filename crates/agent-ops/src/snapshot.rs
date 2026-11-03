//! Workspace snapshots and instant rollbacks.
//!
//! Before a destructive operation the agent snapshots the workspace;
//! corruption rolls back instead of failing permanently. A snapshot is
//! a manifest (sha256 per file) plus a full copy of the tree, the
//! process environment, and dependency fingerprints (manifest hashes,
//! not installed modules).
//!
//! Boundary: live process memory is NOT snapshotted. Stores are local
//! scratch and must never be committed (they may contain env values).

use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

/// Files/dirs never snapshotted.
pub const DEFAULT_EXCLUDES: &[&str] = &["node_modules", ".git", "target"];

#[derive(Debug)]
pub enum SnapError {
    NotFound(String),
    NotDir(String),
    NoSnapshot(String),
    Corrupt(String),
    TargetMismatch { expected: String, got: String },
    Escape(String),
    Io(String),
}

impl std::fmt::Display for SnapError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{:?}", self)
    }
}

impl std::error::Error for SnapError {}

/// One snapshotted file.
#[derive(Debug, Clone)]
pub struct FileEntry {
    pub path: String, // '/'-separated, relative
    pub sha256: String,
    pub size: u64,
}

/// A snapshot manifest (kept in memory; serialized by the caller).
#[derive(Debug, Clone)]
pub struct Manifest {
    pub id: String,
    pub label: String,
    pub target: PathBuf,
    pub excludes: Vec<String>,
    pub env: BTreeMap<String, String>,
    pub deps: BTreeMap<String, String>,
    pub files: Vec<FileEntry>,
}

fn sha256_file(path: &Path) -> Result<String, SnapError> {
    let bytes = fs::read(path).map_err(|e| SnapError::Io(e.to_string()))?;
    let mut h = Sha256::new();
    h.update(&bytes);
    Ok(format!("{:x}", h.finalize()))
}

fn walk(root: &Path, rel: &Path, excludes: &[String], out: &mut Vec<PathBuf>) -> Result<(), SnapError> {
    let dir = if rel.as_os_str().is_empty() { root.to_path_buf() } else { root.join(rel) };
    let entries = fs::read_dir(&dir).map_err(|e| SnapError::Io(e.to_string()))?;
    let mut names: Vec<_> = entries.filter_map(|e| e.ok()).collect();
    names.sort_by_key(|e| e.file_name());
    for e in names {
        let name = e.file_name().to_string_lossy().into_owned();
        if excludes.iter().any(|x| x == &name) {
            continue;
        }
        let child_rel = if rel.as_os_str().is_empty() { PathBuf::from(&name) } else { rel.join(&name) };
        let ft = e.file_type().map_err(|e| SnapError::Io(e.to_string()))?;
        if ft.is_symlink() {
            continue;
        } else if ft.is_dir() {
            walk(root, &child_rel, excludes, out)?;
        } else if ft.is_file() {
            out.push(child_rel);
        }
    }
    Ok(())
}

fn rel_string(p: &Path) -> String {
    p.components().map(|c| c.as_os_str().to_string_lossy().into_owned()).collect::<Vec<_>>().join("/")
}

/// Dependency fingerprints: hashes of package manifests if present.
pub fn dep_fingerprints(root: &Path) -> BTreeMap<String, String> {
    let mut m = BTreeMap::new();
    for name in ["package.json", "package-lock.json", "Cargo.lock", "go.mod"] {
        let p = root.join(name);
        if p.is_file() {
            if let Ok(h) = sha256_file(&p) {
                m.insert(name.to_string(), h);
            }
        }
    }
    m
}

/// Take a snapshot of `target` into a new directory under `store`.
/// Returns the snapshot id.
pub fn snapshot(target: &Path, store: &Path, label: &str) -> Result<String, SnapError> {
    if !target.is_dir() {
        return Err(SnapError::NotDir(target.display().to_string()));
    }
    let canonical = fs::canonicalize(target).map_err(|e| SnapError::Io(e.to_string()))?;
    fs::create_dir_all(store).map_err(|e| SnapError::Io(e.to_string()))?;
    let id = format!("snap-{}-{}", std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0), std::process::id());
    let dest = store.join(&id);
    let tree = dest.join("tree");
    fs::create_dir_all(&tree).map_err(|e| SnapError::Io(e.to_string()))?;

    let excludes: Vec<String> = DEFAULT_EXCLUDES.iter().map(|s| s.to_string()).collect();
    let mut rels = Vec::new();
    walk(&canonical, Path::new(""), &excludes, &mut rels)?;

    let mut files = Vec::new();
    for rel in rels {
        let src = canonical.join(&rel);
        // Never snapshot the store into itself when nested.
        if src == *store || src.starts_with(store) {
            continue;
        }
        let dst = tree.join(&rel);
        if let Some(parent) = dst.parent() {
            fs::create_dir_all(parent).map_err(|e| SnapError::Io(e.to_string()))?;
        }
        fs::copy(&src, &dst).map_err(|e| SnapError::Io(e.to_string()))?;
        let meta = fs::metadata(&src).map_err(|e| SnapError::Io(e.to_string()))?;
        files.push(FileEntry { path: rel_string(&rel), sha256: sha256_file(&src)?, size: meta.len() });
    }

    let deps = dep_fingerprints(&canonical);
    let manifest = Manifest {
        id: id.clone(),
        label: label.to_string(),
        target: canonical,
        excludes,
        env: std::env::vars().collect(),
        deps,
        files,
    };
    let json = manifest_to_json(&manifest);
    fs::write(dest.join("manifest.json"), json).map_err(|e| SnapError::Io(e.to_string()))?;
    Ok(id)
}

fn esc(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}

fn manifest_to_json(m: &Manifest) -> String {
    let mut o = String::from("{\"version\":1");
    o.push_str(&format!(",\"id\":\"{}\"", esc(&m.id)));
    o.push_str(&format!(",\"label\":\"{}\"", esc(&m.label)));
    o.push_str(&format!(",\"target\":\"{}\"", esc(&m.target.display().to_string())));
    o.push_str(",\"excludes\":[");
    o.push_str(&m.excludes.iter().map(|e| format!("\"{}\"", esc(e))).collect::<Vec<_>>().join(","));
    o.push_str("],\"coverage\":\"files+env+dep-fingerprints (NOT live process memory)\"");
    o.push_str(",\"env\":{");
    o.push_str(&m.env.iter().map(|(k, v)| format!("\"{}\":\"{}\"", esc(k), esc(v))).collect::<Vec<_>>().join(","));
    o.push_str("},\"deps\":{");
    o.push_str(&m.deps.iter().map(|(k, v)| format!("\"{}\":\"{}\"", esc(k), esc(v))).collect::<Vec<_>>().join(","));
    o.push_str("},\"files\":[");
    o.push_str(&m.files.iter().map(|f| format!("{{\"path\":\"{}\",\"sha256\":\"{}\",\"size\":{}}}", esc(&f.path), f.sha256, f.size)).collect::<Vec<_>>().join(","));
    o.push_str("]}");
    o
}

/// One rollback action.
#[derive(Debug, PartialEq)]
pub enum Action {
    Restore(String),
    Delete(String),
}

/// Dry-run diff of `target` against snapshot `id`. Refuses a target that
/// is not the snapshot's original directory.
pub fn rollback_diff(store: &Path, id: &str, target: Option<&Path>) -> Result<(PathBuf, Vec<Action>), SnapError> {
    let dir = store.join(id);
    let text = fs::read_to_string(dir.join("manifest.json")).map_err(|_| SnapError::NoSnapshot(id.to_string()))?;
    let orig_target = parse_target(&text).ok_or_else(|| SnapError::Corrupt(format!("snapshot {} has no target", id)))?;
    let root = match target {
        Some(t) => fs::canonicalize(t).map_err(|e| SnapError::Io(e.to_string()))?,
        None => PathBuf::from(&orig_target),
    };
    if root.to_string_lossy() != orig_target {
        return Err(SnapError::TargetMismatch { expected: orig_target, got: root.display().to_string() });
    }
    let wanted = parse_files(&text);
    let excludes: Vec<String> = DEFAULT_EXCLUDES.iter().map(|s| s.to_string()).collect();
    let mut current = Vec::new();
    walk(&root, Path::new(""), &excludes, &mut current)?;
    let current_set: std::collections::HashSet<String> = current.iter().map(|p| rel_string(p)).collect();
    let wanted_map: std::collections::HashMap<&str, &str> = wanted.iter().map(|(p, h)| (p.as_str(), h.as_str())).collect();

    let mut actions = Vec::new();
    for rel in &current {
        let r = rel_string(rel);
        match wanted_map.get(r.as_str()) {
            None => actions.push(Action::Delete(r)),
            Some(want) => {
                let h = sha256_file(&root.join(rel))?;
                if &h != want {
                    actions.push(Action::Restore(r));
                }
            }
        }
    }
    for (p, _) in &wanted {
        if !current_set.contains(p) {
            actions.push(Action::Restore(p.clone()));
        }
    }
    Ok((root, actions))
}

fn parse_target(text: &str) -> Option<String> {
    let key = "\"target\":\"";
    let i = text.find(key)? + key.len();
    let rest = &text[i..];
    let end = rest.find('"')?;
    Some(rest[..end].to_string())
}

fn parse_files(text: &str) -> Vec<(String, String)> {
    // Minimal reader for our own manifest shape: {"path":"..","sha256":"..",...}.
    let mut out = Vec::new();
    let mut rest = text;
    while let Some(i) = rest.find("\"path\":\"") {
        rest = &rest[i + 8..];
        let end = match rest.find('"') {
            Some(e) => e,
            None => break,
        };
        let p = rest[..end].to_string();
        rest = &rest[end..];
        let h = match rest.find("\"sha256\":\"") {
            Some(j) => {
                let r = &rest[j + 10..];
                match r.find('"') {
                    Some(e) => r[..e].to_string(),
                    None => break,
                }
            }
            None => break,
        };
        out.push((p, h));
    }
    out
}

/// Apply a dry-run diff. The `tree` dir comes from the snapshot store.
pub fn rollback_apply(store: &Path, id: &str, target: &Path, actions: &[Action]) -> Result<(), SnapError> {
    let tree = store.join(id).join("tree");
    for a in actions {
        match a {
            Action::Delete(p) => {
                let dst = target.join(p);
                if contained_in(target, &dst) {
                    let _ = fs::remove_file(&dst);
                } else {
                    return Err(SnapError::Escape(dst.display().to_string()));
                }
            }
            Action::Restore(p) => {
                let dst = target.join(p);
                if !contained_in(target, &dst) {
                    return Err(SnapError::Escape(dst.display().to_string()));
                }
                if let Some(parent) = dst.parent() {
                    fs::create_dir_all(parent).map_err(|e| SnapError::Io(e.to_string()))?;
                }
                fs::copy(tree.join(p), &dst).map_err(|e| SnapError::Io(e.to_string()))?;
            }
        }
    }
    Ok(())
}

fn contained_in(root: &Path, p: &Path) -> bool {
    // Lexical containment: collapse . and .. without touching the fs,
    // then require the result to stay under root. Manifest paths are
    // untrusted input, so this runs on every restore/delete target.
    use std::path::Component::*;
    let mut stack: Vec<std::ffi::OsString> = Vec::new();
    let mut rooted = false;
    for c in p.components() {
        match c {
            Prefix(p) => {
                stack.push(p.as_os_str().to_owned());
            }
            RootDir => {
                rooted = true;
                stack.clear();
            }
            CurDir => {}
            ParentDir => {
                if stack.pop().is_none() {
                    return false;
                }
            }
            Normal(o) => stack.push(o.to_owned()),
        }
    }
    if !rooted {
        return false;
    }
    let mut norm = PathBuf::from("/");
    for s in &stack {
        norm.push(s);
    }
    // Compare against the canonical root the same way.
    let mut rstack: Vec<std::ffi::OsString> = Vec::new();
    for c in root.components() {
        match c {
            Prefix(p) => {
                rstack.push(p.as_os_str().to_owned());
            }
            RootDir => {
                rstack.clear();
            }
            CurDir => {}
            ParentDir => {
                rstack.pop();
            }
            Normal(o) => rstack.push(o.to_owned()),
        }
    }
    if stack.len() < rstack.len() {
        return false;
    }
    stack[..rstack.len()] == rstack[..]
}

#[cfg(test)]
mod tests {
    use super::*;

    fn seed(dir: &Path) {
        fs::create_dir_all(dir.join("sub")).unwrap();
        fs::write(dir.join("a.txt"), "alpha").unwrap();
        fs::write(dir.join("sub").join("b.txt"), "beta").unwrap();
    }

    fn tmp() -> PathBuf {
        let d = std::env::temp_dir().join(format!("snaprs-{}-{}", std::process::id(), rand_suffix()));
        fs::create_dir_all(&d).unwrap();
        d
    }

    fn rand_suffix() -> String {
        use std::time::{SystemTime, UNIX_EPOCH};
        format!("{}", SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos())
    }

    #[test]
    fn round_trip_restore() {
        let base = tmp();
        let work = base.join("work");
        let store = base.join("store");
        fs::create_dir_all(&work).unwrap();
        seed(&work);
        let id = snapshot(&work, &store, "test").unwrap();
        // Corrupt + add + delete.
        fs::write(work.join("a.txt"), "CORRUPT").unwrap();
        fs::write(work.join("new.txt"), "junk").unwrap();
        fs::remove_file(work.join("sub").join("b.txt")).unwrap();
        let (root, actions) = rollback_diff(&store, &id, None).unwrap();
        assert_eq!(actions.len(), 3);
        rollback_apply(&store, &id, &root, &actions).unwrap();
        assert_eq!(fs::read_to_string(work.join("a.txt")).unwrap(), "alpha");
        assert_eq!(fs::read_to_string(work.join("sub").join("b.txt")).unwrap(), "beta");
        assert!(!work.join("new.txt").exists());
        fs::remove_dir_all(&base).unwrap();
    }

    #[test]
    fn wrong_target_refused() {
        let base = tmp();
        let work = base.join("work");
        let elsewhere = base.join("else");
        fs::create_dir_all(&work).unwrap();
        fs::create_dir_all(&elsewhere).unwrap();
        seed(&work);
        let id = snapshot(&work, &store_path(&base), "t").unwrap();
        let r = rollback_diff(&store_path(&base), &id, Some(&elsewhere));
        assert!(matches!(r, Err(SnapError::TargetMismatch { .. })));
        fs::remove_dir_all(&base).unwrap();
    }

    fn store_path(base: &Path) -> PathBuf {
        base.join("store")
    }
}
