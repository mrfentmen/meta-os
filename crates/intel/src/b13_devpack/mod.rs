//! B13 — Examples & devpack (`b13_devpack` subtree, code half).
//!
//! Ports `os/intel/devpack.py` (DSH-037): pure shaping functions that
//! turn real producer output into dashboard panel payloads, plus the
//! checked-in pack loader. No network/Redis/bus/Spark: producers run in
//! the test, which rebuilds every payload from real code on fixtures
//! and asserts equality with the checked-in JSON (stale pack = fix the
//! producers or regenerate, never hand-edit a payload).
//!
//! Fixture/data files (22) carried byte-for-byte under
//! `crates/intel/fixtures/b13/` preserving `os/intel/` relative paths:
//! `devpack/` JSON pack + README, `examples/` mind-images + skills,
//! `notes/` source-map + reuse-audit. Its test (`test_intel_devpack.py`)
//! is assigned to B09 — cross-referenced, not duplicated.

use std::collections::HashMap;

pub const PACK_FILES: &[(&str, &str)] = &[
    ("brief", "brief.json"),
    ("plan_preview", "plan_preview.json"),
    ("alerts", "alerts.json"),
    ("crew_board", "crew_board.json"),
];

/// Deep-copy a JSON-ish value (mirrors the `_copy` round-trip).
pub fn deep_copy_json(value: &serde_json_like::Json) -> serde_json_like::Json {
    value.clone()
}

/// Minimal JSON value model (dependency-free).
pub mod serde_json_like {
    use std::collections::HashMap;
    #[derive(Debug, Clone, PartialEq)]
    pub enum Json {
        Null,
        Bool(bool),
        Int(i64),
        Str(String),
        List(Vec<Json>),
        Dict(HashMap<String, Json>),
    }
}

use serde_json_like::Json;

#[derive(Debug, Clone, PartialEq)]
pub struct DevpackError(pub String);

/// A brief record plus its read-time age (BRF-020). Record fields copied
/// verbatim; non-int timestamps raise (never a guessed age).
pub fn brief_entry(record: &HashMap<String, Json>, as_of: &Json) -> Result<HashMap<String, Json>, DevpackError> {
    let err = |s: &str| DevpackError(s.to_string());
    let generated_at = record.get("generated_at").ok_or_else(|| err("brief record needs an int generated_at"))?;
    let Json::Int(gen) = generated_at else {
        return Err(err("brief record needs an int generated_at"));
    };
    let Json::Int(as_of) = as_of else {
        return Err(err("as_of must be an int epoch timestamp"));
    };
    let mut entry = record.clone();
    entry.insert("as_of".to_string(), Json::Int(*as_of));
    entry.insert("age_seconds".to_string(), Json::Int(*as_of - *gen));
    Ok(entry)
}

#[derive(Debug, Clone, PartialEq)]
pub struct PreviewJob {
    pub key: String,
    pub title: String,
    pub files: Vec<String>,
    pub deps: Vec<String>,
    pub max_attempts: i64,
    pub accept: Vec<String>,
    pub req: Vec<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct PreviewPlan {
    pub summary: String,
    pub jobs: Vec<PreviewJob>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct PlanPreview {
    pub summary: String,
    pub jobs: Vec<PreviewJob>,
    pub posting_order: Vec<String>,
    pub jobs_count: usize,
    pub max_attempts_total: i64,
}

/// Validated plan reduced to the DSP-037 preview shape. Order must cover
/// exactly the plan's jobs (mirrors the poster's own check).
pub fn plan_preview(plan: &PreviewPlan, order: &[String]) -> Result<PlanPreview, DevpackError> {
    let mut keys: Vec<&String> = plan.jobs.iter().map(|j| &j.key).collect();
    let mut ord: Vec<&String> = order.iter().collect();
    keys.sort();
    ord.sort();
    if keys != ord {
        return Err(DevpackError("posting order must cover exactly the plan jobs".to_string()));
    }
    Ok(PlanPreview {
        summary: plan.summary.clone(),
        jobs: plan.jobs.clone(),
        posting_order: order.to_vec(),
        jobs_count: plan.jobs.len(),
        max_attempts_total: plan.jobs.iter().map(|j| j.max_attempts).sum(),
    })
}

#[derive(Debug, Clone, PartialEq)]
pub struct AlertRow {
    pub id: String,
    pub created_at: i64,
}

/// Newest first (DSH-013); ties break on id for stable runs.
pub fn alerts_feed(mut records: Vec<AlertRow>) -> Vec<AlertRow> {
    records.sort_by(|a, b| (b.created_at, &b.id).cmp(&(a.created_at, &a.id)));
    records
}

/// The three DSH-003 sources exactly as the viewer reads them.
#[derive(Debug, Clone, PartialEq)]
pub struct CrewBoard {
    pub presence: Vec<String>,
    pub caps: Vec<HashMap<String, String>>,
    pub jobs: Vec<HashMap<String, String>>,
}

pub fn crew_board(presence: Vec<String>, caps: Vec<HashMap<String, String>>, jobs: Vec<HashMap<String, String>>) -> CrewBoard {
    CrewBoard { presence, caps, jobs }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn brief_entry_ages() {
        let mut r = HashMap::new();
        r.insert("generated_at".into(), Json::Int(100));
        let e = brief_entry(&r, &Json::Int(160)).unwrap();
        assert_eq!(e["age_seconds"], Json::Int(60));
        assert!(brief_entry(&r, &Json::Str("x".into())).is_err());
    }
    #[test]
    fn preview_order_must_cover() {
        let p = PreviewPlan { summary: "s".into(), jobs: vec![PreviewJob { key: "a".into(), title: "A".into(), files: vec![], deps: vec![], max_attempts: 3, accept: vec![], req: vec![] }] };
        assert!(plan_preview(&p, &["a".into()]).is_ok());
        assert!(plan_preview(&p, &["b".into()]).is_err());
    }
    #[test]
    fn feed_newest_first_stable() {
        let rows = vec![AlertRow { id: "b".into(), created_at: 1 }, AlertRow { id: "a".into(), created_at: 2 }];
        let f = alerts_feed(rows);
        assert_eq!(f[0].id, "a");
    }
}
