//! Port of `os/intel/sam_check.py` — STR-003 check: validate
//! the SAM eval set in intel/evals/sam/.
//!
//! All must pass (exit 0): pairs.json parses with the pinned
//! set id and exactly the labels {build-ok, build-broken};
//! every pair has one good and one bad half, distinct files,
//! no file reused; every listed file exists and is a real PNG
//! of non-trivial size; every bad half's alert_ids equal
//! exactly the 5 alert ids in the DSH-037 dev-pack payload;
//! firing files are sha256-identical to the DSH-030 submission
//! shots; quiet files carry the sam_render name convention.
//! The fixture data itself is B12c — this is the check code.

use super::sha256::sha256_hex;
use super::value::{parse_json, Value};
use std::path::{Path, PathBuf};

pub const PNG_MAGIC: [u8; 8] = [0x89, b'P', b'N', b'G', b'\r', b'\n', 0x1a, b'\n'];
pub const SET_ID: &str = "sam-eval-alerts-panel-v1";

fn fail(msg: String) -> (i32, Vec<String>) {
    (1, vec![format!("FAIL: {}", msg)])
}

/// Recursive alert-id collection, the source's `alert_ids`:
/// a dict with both "id" and "kind" contributes its id, then
/// every value recurses; lists recurse per item.
fn alert_ids(node: &Value, out: &mut Vec<String>) {
    match node {
        Value::Map(pairs) => {
            let has_id = pairs.iter().any(|(k, _)| k == "id");
            let has_kind = pairs.iter().any(|(k, _)| k == "kind");
            if has_id && has_kind {
                out.push(node.get("id").py_str());
            }
            for (_, value) in pairs {
                alert_ids(value, out);
            }
        }
        Value::List(items) => {
            for value in items {
                alert_ids(value, out);
            }
        }
        _ => {}
    }
}

fn read_json(path: &Path) -> Option<Value> {
    let text = std::fs::read_to_string(path).ok()?;
    parse_json(&text)
}

fn digest(path: &Path) -> Option<String> {
    let bytes = std::fs::read(path).ok()?;
    Some(sha256_hex(&bytes))
}

/// The script's main() over a repo root: (exit code, lines).
/// The source derives REPO from its own file location; here
/// the root rides in, and SAM_DIR = <repo>/intel/evals/sam.
pub fn execute(repo: &Path) -> (i32, Vec<String>) {
    let sam_dir: PathBuf = repo.join("intel").join("evals").join("sam");
    let manifest = match read_json(&sam_dir.join("pairs.json")) {
        Some(m) => m,
        None => {
            return (
                1,
                vec!["error: pairs.json missing or unparseable".to_string()],
            )
        }
    };
    if manifest.get("set").as_str() != Some(SET_ID) {
        return fail(format!(
            "unexpected set id: {}",
            manifest.get("set").py_repr()
        ));
    }
    let mut labels: Vec<String> = manifest
        .get("labels")
        .as_list()
        .map(|items| items.iter().map(|v| v.py_str()).collect())
        .unwrap_or_default();
    labels.sort();
    labels.dedup();
    if labels != vec!["build-broken".to_string(), "build-ok".to_string()] {
        return fail(format!(
            "labels must be exactly build-ok/build-broken: {{{}}}",
            labels
                .iter()
                .map(|l| format!("'{}'", l))
                .collect::<Vec<_>>()
                .join(", ")
        ));
    }
    let pack = match read_json(&repo.join("intel").join("devpack").join("alerts.json")) {
        Some(p) => p,
        None => {
            return (
                1,
                vec!["error: devpack alerts.json missing or unparseable".to_string()],
            )
        }
    };
    let mut pack_ids: Vec<String> = Vec::new();
    alert_ids(&pack, &mut pack_ids);
    pack_ids.sort();
    if pack_ids.len() != 5 {
        return fail(format!(
            "dev-pack alerts payload no longer has 5 alerts: {}",
            Value::List(pack_ids.iter().map(|s| Value::s(s)).collect()).py_repr()
        ));
    }
    let pairs = match manifest.get("pairs").as_list() {
        Some(p) => p.clone(),
        None => return (1, vec!["KeyError: 'pairs'".to_string()]),
    };
    let mut seen_files: Vec<String> = Vec::new();
    for pair in &pairs {
        let good = pair.get("good");
        let bad = pair.get("bad");
        if good.get("label").as_str() != Some("build-ok")
            || bad.get("label").as_str() != Some("build-broken")
        {
            return fail(format!("pair {} has wrong labels", pair.get("id").py_str()));
        }
        for half in [&good, &bad] {
            let file = half.get("file").py_str();
            if seen_files.contains(&file) {
                return fail(format!("file reused across pairs: {}", file));
            }
            seen_files.push(file.clone());
            let path = sam_dir.join(&file);
            if !path.is_file() {
                return fail(format!("missing file: {}", file));
            }
            let head = std::fs::read(&path)
                .map(|bytes| {
                    let mut h = [0u8; 8];
                    let n = bytes.len().min(8);
                    h[..n].copy_from_slice(&bytes[..n]);
                    h
                })
                .unwrap_or([0u8; 8]);
            if head != PNG_MAGIC {
                return fail(format!("not a PNG: {}", file));
            }
            let size = std::fs::metadata(&path).map(|m| m.len()).unwrap_or(0);
            if size < 1000 {
                return fail(format!("suspiciously small PNG: {}", file));
            }
        }
        let mut bad_ids: Vec<String> = bad
            .get("alert_ids")
            .as_list()
            .map(|items| items.iter().map(|v| v.py_str()).collect())
            .unwrap_or_default();
        bad_ids.sort();
        if bad_ids != pack_ids {
            return fail(format!(
                "pair {} bad alert_ids != dev-pack payload: {}",
                pair.get("id").py_str(),
                bad.get("alert_ids").py_repr()
            ));
        }
        // Firing halves must match the pinned DSH-030 shots.
        let bad_file = bad.get("file").py_str();
        let orig = repo
            .join("hackathon")
            .join("relay-intelligence")
            .join("submission-assets")
            .join(&bad_file);
        if !orig.is_file() {
            return fail(format!(
                "submission original missing: {}",
                orig.display()
            ));
        }
        let sam_digest = digest(&sam_dir.join(&bad_file));
        let orig_digest = digest(&orig);
        if sam_digest.is_none() || sam_digest != orig_digest {
            return fail(format!(
                "firing shot drifted from submission original: {}",
                bad_file
            ));
        }
        let good_file = good.get("file").py_str();
        if !good_file.starts_with("alerts-quiet-") {
            return fail(format!(
                "good half is not a sam_render.py output: {}",
                good_file
            ));
        }
    }
    (
        0,
        vec![format!(
            "SAM eval set OK: {} pairs, {} files, bad halves match the 5-alert dev-pack payload",
            pairs.len(),
            seen_files.len()
        )],
    )
}
