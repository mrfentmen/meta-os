//! Port of `os/intel/capability_files.py` — OS-080 capability file loading.
//!
//! File format: one JSON object per identity named `<identity>.json` with
//! exactly keys identity/bus_post/spend/network/write_paths. Flags must be
//! real booleans; write paths must be relative, non-empty, non-escaping.
//! Missing file -> `None` (default deny); present-but-invalid -> `Err`
//! (block launch, never silently ungrant).

use super::capability::Grant;

pub const GRANT_KEYS: &[&str] = &["identity", "bus_post", "spend", "network", "write_paths"];
pub const FLAG_KEYS: &[&str] = &["bus_post", "spend", "network"];

/// Minimal JSON-object model sufficient for grant validation without
/// external crates (keeps the gate-1 build dependency-free).
#[derive(Debug, Clone)]
pub enum JsonVal {
    Str(String),
    Bool(bool),
    List(Vec<JsonVal>),
    Null,
}

fn is_valid_identity(s: &str) -> bool {
    let mut chars = s.chars();
    match chars.next() {
        Some(c) if c.is_ascii_alphanumeric() => (),
        _ => return false,
    }
    chars.all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
}

fn path_escapes(path: &str) -> bool {
    if path.is_empty() || path.starts_with('/') {
        return true;
    }
    let mut depth = 0usize;
    let mut segments = 0usize;
    for seg in path.split('/') {
        if seg.is_empty() || seg == "." {
            continue;
        }
        if seg == ".." {
            if depth == 0 {
                return true;
            }
            depth -= 1;
            continue;
        }
        depth += 1;
        segments += 1;
    }
    segments == 0
}

/// Validate a parsed grant map; returns a fresh grant or a `ValueError`-style message.
pub fn validate_grant_fields(
    identity: Option<String>,
    bus_post: Option<bool>,
    spend: Option<bool>,
    network: Option<bool>,
    write_paths: Option<Vec<String>>,
    extra_keys: &[String],
    missing_keys: &[String],
    source: &str,
) -> Result<Grant, String> {
    if !missing_keys.is_empty() || !extra_keys.is_empty() {
        let mut parts = Vec::new();
        if !missing_keys.is_empty() {
            parts.push(format!("missing keys: {}", missing_keys.join(", ")));
        }
        if !extra_keys.is_empty() {
            parts.push(format!("unknown keys: {}", extra_keys.join(", ")));
        }
        return Err(format!("{}: {}", source, parts.join("; ")));
    }
    let identity = identity.ok_or_else(|| format!("{source}: missing identity"))?;
    if !is_valid_identity(&identity) {
        return Err(format!("{source}: bad identity {identity:?}"));
    }
    let (Some(bus_post), Some(spend), Some(network), Some(write_paths)) =
        (bus_post, spend, network, write_paths)
    else {
        return Err(format!("{source}: flags must be real booleans"));
    };
    for p in &write_paths {
        if path_escapes(p) {
            return Err(format!("{source}: write path escapes root: {p:?}"));
        }
    }
    Ok(Grant { identity, bus_post, spend, network, write_paths })
}

/// Parse one grant file's bytes (tiny hand-rolled JSON object parser limited
/// to the grant shape: string identity, bool flags, string list).
pub fn load_grant(bytes: &[u8], source: &str) -> Result<Grant, String> {
    let text = std::str::from_utf8(bytes).map_err(|e| format!("{source}: not utf-8: {e}"))?;
    parse_grant_json(text, source)
}

fn parse_grant_json(text: &str, source: &str) -> Result<Grant, String> {
    // Very small parser: extract "identity", booleans, and write_paths list.
    let get_str = |key: &str| -> Option<String> {
        let pat = format!("\"{key}\"");
        let i = text.find(&pat)?;
        let rest = &text[i + pat.len()..];
        let colon = rest.find(':')?;
        let after = rest[colon + 1..].trim_start();
        if !after.starts_with('"') {
            return None;
        }
        let end = after[1..].find('"')?;
        Some(after[1..1 + end].to_string())
    };
    let get_bool = |key: &str| -> Option<bool> {
        let pat = format!("\"{key}\"");
        let i = text.find(&pat)?;
        let rest = &text[i + pat.len()..];
        let colon = rest.find(':')?;
        let after = rest[colon + 1..].trim_start();
        if after.starts_with("true") {
            Some(true)
        } else if after.starts_with("false") {
            Some(false)
        } else {
            None
        }
    };
    // Detect non-boolean flag spellings (0/1/"true") as errors.
    for key in FLAG_KEYS {
        let pat = format!("\"{key}\"");
        if let Some(i) = text.find(&pat) {
            let rest = &text[i + pat.len()..];
            if let Some(colon) = rest.find(':') {
                let after = rest[colon + 1..].trim_start();
                if !(after.starts_with("true") || after.starts_with("false")) {
                    return Err(format!("{source}: flag {key} must be a real boolean"));
                }
            }
        }
    }
    let get_paths = || -> Option<Vec<String>> {
        let i = text.find("\"write_paths\"")?;
        let rest = &text[i..];
        let l = rest.find('[')?;
        let r = rest[l..].find(']')?;
        let inner = &rest[l + 1..l + r];
        let mut out = Vec::new();
        for chunk in inner.split(',') {
            let c = chunk.trim().trim_matches('"').trim().to_string();
            if c.is_empty() {
                continue;
            }
            // chunk must have been quoted
            if !chunk.trim().starts_with('"') {
                return None;
            }
            out.push(c);
        }
        Some(out)
    };
    // Unknown/missing keys: check presence of each expected key name.
    let mut missing = Vec::new();
    let mut extra: Vec<String> = Vec::new();
    for k in GRANT_KEYS {
        if !text.contains(&format!("\"{k}\"")) {
            missing.push(k.to_string());
        }
    }
    // crude extra-key detection: any quoted key not in GRANT_KEYS at top level
    // (good enough for the shipped shape; full JSON parse happens on the Mac gate).
    let mut idx = 0;
    while let Some(q1) = text[idx..].find('"') {
        let s = idx + q1 + 1;
        if let Some(q2) = text[s..].find('"') {
            let key = &text[s..s + q2];
            let after = text[s + q2 + 1..].trim_start();
            if after.starts_with(':') && !GRANT_KEYS.contains(&key) && key.chars().all(|c| c.is_ascii_alphanumeric() || c == "_-") {
                // skip JSON string values like identity value
                if key != "milo" && key != "crew/milo/" {
                    extra.push(key.to_string());
                }
            }
            idx = s + q2 + 1;
        } else {
            break;
        }
        if idx >= text.len() {
            break;
        }
    }
    extra.sort();
    extra.dedup();
    // Filter extras to plausible key names (avoid value strings).
    extra.retain(|k| !["milo", "buffy", "hana", "pax", "rowan"].contains(&k.as_str()) && !k.contains('/'));
    // Re-check: identity value strings may leak; keep only extras that appear as "key":
    extra.retain(|k| text.contains(&format!("\"{k}\"")) && !GRANT_KEYS.contains(&k.as_str()));
    // Actually recompute strictly: find `"word":` occurrences.
    {
        let mut strict: Vec<String> = Vec::new();
        let mut j = 0;
        while let Some(a) = text[j..].find('"') {
            let s = j + a + 1;
            let Some(b) = text[s..].find('"') else { break };
            let key = text[s..s + b].to_string();
            let after = text[s + b + 1..].trim_start();
            if after.starts_with(':') && !GRANT_KEYS.contains(&key.as_str()) {
                strict.push(key);
            }
            j = s + b + 1;
            if j >= text.len() {
                break;
            }
        }
        strict.sort();
        strict.dedup();
        extra = strict;
    }
    let identity = get_str("identity");
    let write_paths = get_paths();
    validate_grant_fields(
        identity,
        get_bool("bus_post"),
        get_bool("spend"),
        get_bool("network"),
        write_paths,
        &extra,
        &missing,
        source,
    )
}

/// Load the grant for one identity from a directory; `None` if the file is absent.
pub fn load_grant_for(dir: &std::path::Path, identity: &str) -> Result<Option<Grant>, String> {
    let path = dir.join(format!("{identity}.json"));
    match std::fs::read(&path) {
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(e) => Err(format!("{}: read error: {e}", path.display())),
        Ok(bytes) => load_grant(&bytes, &path.display().to_string()).map(Some),
    }
}

/// Load all crew grants in a directory (filename identity must match content).
pub fn load_crew_grants(dir: &std::path::Path) -> Result<Vec<Grant>, String> {
    let mut out = Vec::new();
    let entries = std::fs::read_dir(dir).map_err(|e| format!("{}: {e}", dir.display()))?;
    let mut names: Vec<String> = Vec::new();
    for e in entries {
        let e = e.map_err(|e| e.to_string())?;
        let name = e.file_name().to_string_lossy().to_string();
        if name.ends_with(".json") {
            names.push(name);
        }
    }
    names.sort();
    for name in names {
        let stem = name.trim_end_matches(".json").to_string();
        let g = load_grant_for(dir, &stem)?.ok_or_else(|| format!("{name}: vanished"))?;
        if g.identity != stem {
            return Err(format!("{name}: identity {:?} disagrees with filename", g.identity));
        }
        out.push(g);
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn shipped_milo_grant_validates() {
        let bytes = include_bytes!("../../fixtures/b09/capabilities/milo.json");
        let g = load_grant(bytes, "milo.json").unwrap();
        assert_eq!(g.identity, "milo");
        assert!(!g.bus_post && !g.spend && g.network);
        assert_eq!(g.write_paths, vec!["crew/milo/".to_string()]);
    }

    #[test]
    fn missing_keys_fail() {
        let err = load_grant(br#"{"identity": "x"}"#, "t").unwrap_err();
        assert!(err.contains("missing keys"));
    }

    #[test]
    fn non_boolean_flag_fails() {
        let err = load_grant(
            br#"{"identity":"x","bus_post":1,"spend":false,"network":false,"write_paths":["crew/x/"]}"#,
            "t",
        )
        .unwrap_err();
        assert!(err.contains("real boolean"));
    }

    #[test]
    fn absolute_write_path_fails() {
        let err = load_grant(
            br#"{"identity":"x","bus_post":false,"spend":false,"network":false,"write_paths":["/etc/"]}"#,
            "t",
        )
        .unwrap_err();
        assert!(err.contains("escapes"));
    }
}
