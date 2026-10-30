//! T041 [B31] port of `os/tests/test_os094_job_artifacts.py` (same name roots).
//!
//! Job artifact refs: the pure `parse_artifact_ref` contract
//! (`os/jobs.py`, regex + name rules + v>=1) is ported for real and pinned.
//! The 9 record/store/CLI cases need the jobs record + `mos.artifact_store`
//! ports — absent on main (os-jobs crate and os-workspace crate are still
//! B00 skeletons; Milo's B16/B19 unmerged) — recorded blocked, never dropped.

pub const CASES: &[&str] = &[
    "post stores show and lists artifacts",
    "post without artifacts has empty list",
    "post malformed ref rejected before any state",
    "parse artifact ref shape",
    "attach appends and dedupes in order",
    "attach duplicate is a noop",
    "attach malformed leaves hash unchanged",
    "attach missing job errors",
    "second worker reads everything from the record",
    "attach after signing keeps signature valid",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[
    "post stores show and lists artifacts (needs jobs record port, absent on main)",
    "post without artifacts has empty list (needs jobs record port, absent on main)",
    "post malformed ref rejected before any state (needs jobs record port, absent on main)",
    "attach appends and dedupes in order (needs jobs + artifact store ports, absent on main)",
    "attach duplicate is a noop (needs jobs + artifact store ports, absent on main)",
    "attach malformed leaves hash unchanged (needs jobs + artifact store ports, absent on main)",
    "attach missing job errors (needs jobs record port, absent on main)",
    "second worker reads everything from the record (needs jobs + artifact store ports, absent on main)",
    "attach after signing keeps signature valid (needs jobs + artifact store ports, absent on main)",
];

/// `jobs.parse_artifact_ref`: (job id, name, version) for a well-formed
/// OS-083 reference, else `None`. Regex `^artifact:([A-Za-z0-9._-]+)/(.+)@v(\d+)$`
/// + name rules (relative POSIX, no empty/./.. segments, no backslash/NUL)
/// + version >= 1.
pub fn parse_artifact_ref(reference: Option<&str>) -> Option<(String, String, u64)> {
    let r = reference?;
    let rest = r.strip_prefix("artifact:")?;
    let (head, ver) = rest.rsplit_once("@v")?;
    if ver.is_empty() || !ver.bytes().all(|b| b.is_ascii_digit()) {
        return None;
    }
    let version: u64 = ver.parse().ok()?;
    if version < 1 {
        return None;
    }
    let (job_id, name) = head.split_once('/')?;
    if job_id.is_empty() || !job_id.bytes().all(|b| b.is_ascii_alphanumeric() || b".-_".contains(&b)) {
        return None;
    }
    if name.is_empty() || name.starts_with('/') || name.contains('\\') || name.contains('\0') {
        return None;
    }
    if name.split('/').any(|p| p.is_empty() || p == "." || p == "..") {
        return None;
    }
    Some((job_id.to_string(), name.to_string(), version))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_artifact_ref_shape() {
        assert_eq!(
            parse_artifact_ref(Some("artifact:1/build/app.bin@v2")),
            Some(("1".into(), "build/app.bin".into(), 2))
        );
        assert_eq!(parse_artifact_ref(Some("artifact:1/a.md@v0")), None);
        assert_eq!(parse_artifact_ref(Some("artifact:1/a\\b.md@v1")), None);
        assert_eq!(parse_artifact_ref(None), None);
    }
}
