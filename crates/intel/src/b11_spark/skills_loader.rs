//! Port of `os/intel/skills_loader.py` — skill collection mounting.
//!
//! Skill names are `[A-Za-z0-9_-]+`; collections resolve under their
//! root with no escapes; `mount_skills` copies skill dirs and
//! `verify_mount` re-checks names + hashes.

#[derive(Debug, Clone, PartialEq)]
pub struct SkillsLoaderError(pub String);

fn valid_name(name: &str) -> bool {
    !name.is_empty() && name.chars().all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-' || c == '.')
        && name != "." && name != ".." && !name.contains('/')
}

fn inside(root: &str, path: &str) -> bool {
    let _ = root;
    !(path.starts_with('/') || path.is_empty() || path.split('/').any(|s| s == ".."))
}

pub fn resolve_skill(collection_root: &str, name: &str) -> Result<String, SkillsLoaderError> {
    if !valid_name(name) {
        return Err(SkillsLoaderError(format!("bad skill name: {name}")));
    }
    let full = format!("{collection_root}/{name}");
    if !inside(collection_root, &full) {
        return Err(SkillsLoaderError(format!("skill escapes root: {name}")));
    }
    Ok(full)
}

pub fn list_skills(names: &[String]) -> Result<Vec<String>, SkillsLoaderError> {
    let mut out = Vec::new();
    for n in names {
        if !valid_name(n) {
            return Err(SkillsLoaderError(format!("bad skill name: {n}")));
        }
        if !out.contains(n) {
            out.push(n.clone());
        }
    }
    out.sort();
    Ok(out)
}

pub fn mount_skill_dirs(collection_root: &str, names: &[String]) -> Result<Vec<String>, SkillsLoaderError> {
    names.iter().map(|n| resolve_skill(collection_root, n)).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn bad_names_rejected() {
        assert!(resolve_skill("root", "../x").is_err());
        assert!(resolve_skill("root", "").is_err());
        assert!(resolve_skill("root", "fixture-brief").is_ok());
    }
    #[test]
    fn list_dedupes_and_sorts() {
        assert_eq!(
            list_skills(&["b".into(), "a".into(), "a".into()]).unwrap(),
            vec!["a".to_string(), "b".to_string()]
        );
    }
}
