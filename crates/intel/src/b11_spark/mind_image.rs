//! Port of `os/intel/mind_image.py` — mind-image bundle handling.
//!
//! Bundle layers: manifest/brief/constitution/grants/memory/skills.
//! Layer 4 `grants.json` names an identity + actions list (NOT the
//! OS-080 file grant — see `b09_core::capability_files`). Loads reject
//! unknown fields and path escapes; `resolve_bundle` pins files that
//! exist inside the bundle root.

use std::collections::HashMap;

#[derive(Debug, Clone, PartialEq)]
pub struct BundleError(pub String);

#[derive(Debug, Clone, PartialEq)]
pub struct Bundle {
    pub manifest: HashMap<String, String>,
    pub brief: String,
    pub constitution: String,
    pub grants: Vec<BundleGrant>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct BundleGrant {
    pub identity: String,
    pub actions: Vec<String>,
}

fn fail(msg: impl Into<String>) -> BundleError {
    BundleError(msg.into())
}

pub fn parse_bundle(
    manifest: HashMap<String, String>,
    brief: &str,
    constitution: &str,
    grants: Vec<(String, Vec<String>)>,
    unknown: &[String],
) -> Result<Bundle, BundleError> {
    if !unknown.is_empty() {
        return Err(fail(format!("unknown fields: {}", unknown.join(", "))));
    }
    if !manifest.contains_key("name") {
        return Err(fail("bundle manifest needs name"));
    }
    Ok(Bundle {
        manifest,
        brief: brief.to_string(),
        constitution: constitution.to_string(),
        grants: grants.into_iter().map(|(identity, actions)| BundleGrant { identity, actions }).collect(),
    })
}

fn inside(root: &str, path: &str) -> bool {
    if path.starts_with('/') || path.is_empty() {
        return false;
    }
    let mut depth = 0;
    for seg in path.split('/') {
        if seg.is_empty() || seg == "." {
            continue;
        }
        if seg == ".." {
            if depth == 0 {
                return false;
            }
            depth -= 1;
        } else {
            depth += 1;
        }
    }
    let _ = root;
    depth > 0
}

/// Resolve bundle-relative paths against the root; escapes/missing fail.
pub fn resolve_bundle(root: &str, paths: &[String], existing: &[String]) -> Result<Vec<String>, BundleError> {
    let mut out = Vec::new();
    for p in paths {
        if !inside(root, p) {
            return Err(fail(format!("bundle path escapes: {p}")));
        }
        let full = format!("{root}/{p}");
        if !existing.contains(&full) {
            return Err(fail(format!("bundle file missing: {p}")));
        }
        out.push(full);
    }
    Ok(out)
}

pub fn validate_bundle(b: &Bundle) -> Result<(), BundleError> {
    if b.brief.trim().is_empty() {
        return Err(fail("bundle brief is empty"));
    }
    for g in &b.grants {
        if g.identity.is_empty() {
            return Err(fail("bundle grant needs identity"));
        }
    }
    Ok(())
}

pub fn bundle_summary(b: &Bundle) -> String {
    format!(
        "bundle {}: {} grants, brief {} chars",
        b.manifest.get("name").map(String::as_str).unwrap_or("?"),
        b.grants.len(),
        b.brief.len()
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn rejects_unknown_fields() {
        assert!(parse_bundle(HashMap::new(), "b", "c", vec![], &["zzz".into()]).is_err());
    }
    #[test]
    fn escapes_rejected() {
        assert!(resolve_bundle("root", &["../x".into()], &[]).is_err());
    }
}
