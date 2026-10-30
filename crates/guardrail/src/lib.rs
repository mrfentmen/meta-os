//! Crate `guardrail` — Meta OS Rust rebuild (B03).
//!
//! Batch B03 — Guardrail + Spark transport. Owner: Rowan.
//! Sources: `server/queue/spark_gen.py`, `server/queue/spark_guardrail.py`.
//! Port behavior, do not redesign.
//!
//! Scope, honestly: the guardrail counts the DIRECT transport
//! (SPARK_API_KEY path). The DEV helper transport is counted by the
//! helper's own guardrail instead — never both.

use serde::{Deserialize, Serialize};

pub const TEST_BUDGET_USD: f64 = 75.0;
pub const RATE_IN_PER_M: f64 = 1.25;
pub const RATE_OUT_PER_M: f64 = 4.25;
pub const SPARK_ENDPOINT: &str = "https://api.meta.ai/v1/chat/completions";
pub const SPARK_MODEL: &str = "muse-spark-1.3";

#[derive(Debug, Clone)]
pub struct GuardrailStop(pub String);
impl std::fmt::Display for GuardrailStop {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result { write!(f, "{}", self.0) }
}
impl std::error::Error for GuardrailStop {}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UsageLog {
    pub ts: String,
    pub kind: String,
    pub model: String,
    pub input_tokens: u64,
    pub output_tokens: u64,
    pub latency_ms: u64,
    pub est_cost_usd: f64,
    pub cum_est_cost_usd: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GuardrailState {
    #[serde(default)]
    pub calls: u64,
    #[serde(default)]
    pub est_cost_usd: f64,
    #[serde(default)]
    pub log: Vec<UsageLog>,
}

impl Default for GuardrailState {
    fn default() -> Self {
        Self { calls: 0, est_cost_usd: 0.0, log: vec![] }
    }
}

pub fn load_state(path: &str) -> GuardrailState {
    std::fs::read_to_string(path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default()
}

pub fn save_state(path: &str, state: &GuardrailState) {
    if let Ok(s) = serde_json::to_string_pretty(state) {
        let _ = std::fs::write(path, s);
    }
}

pub fn check(state: &GuardrailState) -> Result<(), GuardrailStop> {
    if state.est_cost_usd >= TEST_BUDGET_USD {
        return Err(GuardrailStop(format!(
            "GUARDRAIL STOP: estimated test spend ${:.4} has reached the ${:.2} test budget. No call sent.",
            state.est_cost_usd, TEST_BUDGET_USD
        )));
    }
    Ok(())
}

pub fn estimate(input_tokens: u64, output_tokens: u64) -> f64 {
    input_tokens as f64 / 1e6 * RATE_IN_PER_M + output_tokens as f64 / 1e6 * RATE_OUT_PER_M
}

pub fn record(state_path: &str, kind: &str, model: &str, input_tokens: u64, output_tokens: u64, latency_ms: u64) -> f64 {
    let mut state = load_state(state_path);
    let est = estimate(input_tokens, output_tokens);
    state.calls += 1;
    state.est_cost_usd = ((state.est_cost_usd + est) * 1e6).round() / 1e6;
    state.log.push(UsageLog {
        ts: "2026-10-30T00:00:00Z".to_string(),
        kind: kind.to_string(),
        model: model.to_string(),
        input_tokens,
        output_tokens,
        latency_ms,
        est_cost_usd: (est * 1e6).round() / 1e6,
        cum_est_cost_usd: state.est_cost_usd,
    });
    save_state(state_path, &state);
    est
}

pub fn status_of(state: &GuardrailState) -> serde_json::Value {
    serde_json::json!({
        "calls": state.calls,
        "est_cost_usd": state.est_cost_usd,
        "test_budget_usd": TEST_BUDGET_USD,
        "remaining_usd": (TEST_BUDGET_USD - state.est_cost_usd),
    })
}

/// `unwrap_model_text` from spark_gen.py: tolerate a ``` fence and prose
/// around the object; parse failure still raises downstream.
pub fn unwrap_model_text(content: &str) -> String {
    let mut t = content.trim().to_string();
    if t.starts_with("```") {
        let mut lines: Vec<&str> = t.split('\n').collect();
        lines.remove(0);
        t = lines.join("\n").trim().to_string();
        if t.ends_with("```") {
            t = t[..t.len() - 3].trim().to_string();
        }
    }
    if let (Some(s), Some(e)) = (t.find('{'), t.rfind('}')) {
        if e > s {
            t = t[s..=e].to_string();
        }
    }
    t
}

/// `buildSparkPrompt` shape from server/model.mjs, fed by product profile.
pub fn build_prompt(product: &str, display_name: &str, department: &str, categories: &[&str], limitations: &str, timestamp: &str, correction: Option<&str>) -> String {
    let cats = categories.join(", ");
    let mut lines = vec![
        format!("You are the visual assessment model for {display_name} ({department})."),
        "Look at the attached image and return JSON ONLY, no prose, no markdown fences, matching this shape exactly:".to_string(),
        "{".to_string(),
        format!("  \"product\": \"{product}\","),
        format!("  \"timestamp\": \"{timestamp}\","),
        "  \"observations\": [{\"category\": \"<one of the categories below>\", \"description\": \"<what is visible>\", \"evidence\": \"<where in the frame>\", \"confidence\": <0..1 or null>}],".to_string(),
        "  \"assessment\": {\"category\": \"<one of the categories below>\", \"summary\": \"<one or two sentences>\", \"uncertainty\": [\"<anything unclear>\"], \"requires_human_review\": <true|false>},".to_string(),
        format!("  \"processing\": {{\"model\": \"{SPARK_MODEL}\", \"latency_ms\": null}}"),
        "}".to_string(),
        format!("Categories (assessment.category and every observation category must be one of these): {cats}."),
        format!("Limits: {limitations}"),
        "Describe only what is visible in the image. This is supplementary awareness only: never dispatch, never claim certainty beyond what is visible. When unsure, use indeterminate and set requires_human_review to true.".to_string(),
    ];
    if let Some(c) = correction {
        lines.push(format!("CORRECTION: a previous reply for this same frame failed these contract checks: {c}"));
        lines.push("Return corrected JSON only, matching the shape above exactly. Do not repeat the failed checks.".to_string());
    }
    lines.join("\n")
}

pub fn via_helper() -> bool {
    std::env::var("TRIO_SPARK_VIA_HELPER").map(|v| v == "1").unwrap_or(false)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_estimate_math() {
        let est = estimate(1_000_000, 1_000_000);
        assert!((est - (1.25 + 4.25)).abs() < 1e-9);
    }

    #[test]
    fn test_record_counts_and_cumulates() {
        let dir = std::env::temp_dir().join(format!("guardrail-{}", std::process::id()));
        let _ = std::fs::create_dir_all(&dir);
        let p = dir.join("g.json").to_string_lossy().to_string();
        let _ = std::fs::remove_file(&p);
        record(&p, "assess:ignis", "muse-spark-1.3", 1000, 1000, 42);
        let st = load_state(&p);
        assert_eq!(st.calls, 1);
        assert!(st.est_cost_usd > 0.0 && st.est_cost_usd < 0.01);
    }

    #[test]
    fn test_stop_at_budget() {
        let st = GuardrailState { calls: 999, est_cost_usd: TEST_BUDGET_USD, log: vec![] };
        assert!(check(&st).is_err());
    }

    #[test]
    fn test_check_passes_under_budget() {
        assert!(check(&GuardrailState::default()).is_ok());
    }

    #[test]
    fn test_unwrap_fence() {
        let s = unwrap_model_text("```json\n{\"a\":1}\n```");
        assert_eq!(s, "{\"a\":1}");
    }
}
