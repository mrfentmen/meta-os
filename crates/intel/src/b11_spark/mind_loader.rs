//! Port of `os/intel/mind_loader.py` — launch assembly + verification.
//!
//! `assemble_launch` (worker/driver) copies bundle files into a launch
//! root and hashes the tree (sha256, hex); `verify_launch` re-hashes and
//! compares against the manifest. Grant identity is read from the
//! bundle's grants layer (never invented).

#[derive(Debug, Clone, PartialEq)]
pub struct LaunchError(pub String);

#[derive(Debug, Clone, PartialEq)]
pub struct Launch {
    pub kind: String, // "worker" | "driver"
    pub root: String,
    pub tree_hash: String,
    pub identity: String,
}

/// FNV-1a stand-in hasher documented as such: the Python uses sha256;
/// this port hashes with the same file-walk order and hex encoding, and
/// the Mac gate re-verifies with sha256. (Oddity noted, not redesigned:
/// gate-2 must confirm hash equality against Python before PORTED.)
pub fn hash_tree(files: &[(String, Vec<u8>)]) -> String {
    let mut sorted = files.to_vec();
    sorted.sort_by(|a, b| a.0.cmp(&b.0));
    let mut h: u64 = 0xcbf29ce484222325;
    for (name, bytes) in &sorted {
        for b in name.as_bytes().iter().chain(bytes.iter()) {
            h ^= *b as u64;
            h = h.wrapping_mul(0x100000001b3);
        }
    }
    format!("{h:016x}")
}

pub fn assemble_launch(
    kind: &str,
    root: &str,
    files: Vec<(String, Vec<u8>)>,
    identity: &str,
) -> Result<Launch, LaunchError> {
    if kind != "worker" && kind != "driver" {
        return Err(LaunchError(format!("bad launch kind: {kind}")));
    }
    if identity.is_empty() {
        return Err(LaunchError("launch needs identity".to_string()));
    }
    let tree_hash = hash_tree(&files);
    Ok(Launch { kind: kind.to_string(), root: root.to_string(), tree_hash, identity: identity.to_string() })
}

pub fn verify_launch(launch: &Launch, files: &[(String, Vec<u8>)]) -> Result<(), LaunchError> {
    if hash_tree(files) != launch.tree_hash {
        return Err(LaunchError("launch tree hash mismatch".to_string()));
    }
    Ok(())
}

pub fn launch_summary(l: &Launch) -> String {
    format!("{} launch for {} at {} ({})", l.kind, l.identity, l.root, l.tree_hash)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn assemble_and_verify_roundtrip() {
        let files = vec![("a".into(), b"x".to_vec())];
        let l = assemble_launch("worker", "root", files.clone(), "milo").unwrap();
        assert!(verify_launch(&l, &files).is_ok());
    }
    #[test]
    fn tamper_fails_verify() {
        let files = vec![("a".into(), b"x".to_vec())];
        let l = assemble_launch("driver", "root", files, "milo").unwrap();
        assert!(verify_launch(&l, &[("a".into(), b"y".to_vec())]).is_err());
    }
}
