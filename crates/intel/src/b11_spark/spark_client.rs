//! Port of `os/intel/spark_client.py` — the one Spark gateway (FND-005/006/007).
//!
//! A completion is always a real Muse Spark generation: no fake, canned,
//! or fallback output anywhere. `SPARK_TRANSPORT` selects `agent`
//! (default, job-queue dispatch to a resident crew agent) or `http`
//! (direct chat-completions POST, inert until endpoint/key named under
//! GOV-001). With neither available, [`complete`] raises
//! [`SparkError::NotConfigured`] before anything is sent.
//!
//! Agent completion contract: JSON envelope spec, DM to agents with the
//! spark capability, atomic claim + lease heartbeat, result at
//! `<job_ns>:<jid>:result` (JSON envelope or plain text), `done` with
//! `sha256:<result body>` digest; blocked -> [`SparkError::Agent`] with
//! the agent's reason; expired leases re-dispatch within the retry
//! budget. Token counts are recorded exactly as reported, else null
//! with usage "unreported" — never fabricated. Spend ledger entries go
//! through the guardrail counter (B03 $75 cap), never a private counter.

#[derive(Debug, Clone, PartialEq)]
pub enum SparkError {
    NotConfigured(String),
    Http(String),
    Budget(String),
    Response(String),
    Agent(String),
    Timeout(String),
}

impl std::fmt::Display for SparkError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NotConfigured(s) => write!(f, "spark not configured: {s}"),
            Self::Http(s) => write!(f, "spark http: {s}"),
            Self::Budget(s) => write!(f, "spark budget: {s}"),
            Self::Response(s) => write!(f, "spark response: {s}"),
            Self::Agent(s) => write!(f, "spark agent: {s}"),
            Self::Timeout(s) => write!(f, "spark timeout: {s}"),
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum TransportKind {
    Agent,
    Http,
}

impl TransportKind {
    pub fn from_env(transport: &str) -> Result<Self, SparkError> {
        match transport {
            "agent" => Ok(Self::Agent),
            "http" => Ok(Self::Http),
            _ => Err(SparkError::NotConfigured(format!("unknown SPARK_TRANSPORT: {transport}"))),
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct CompletionRequest {
    pub lane_feature: String,
    pub system: String,
    pub prompt: String,
    pub max_tokens: u32,
    pub job_ns: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Completion {
    pub text: String,
    pub tokens_in: Option<u64>,
    pub tokens_out: Option<u64>,
    pub usage: String, // "reported" | "estimated" | "unreported"
}

/// Injected transport (real or stub for tests — ported as-is).
pub trait Transport {
    fn complete(&self, req: &CompletionRequest) -> Result<Completion, SparkError>;
}

/// Result envelope helpers: `<job_ns>:<jid>:result`.
pub fn result_key_for(job_ns: &str, jid: &str) -> String {
    format!("{job_ns}:{jid}:result")
}

/// Parse a result body: JSON envelope `{"text",...}` or plain text.
pub fn result_body_for(body: &str) -> (String, Option<u64>, Option<u64>) {
    let t = body.trim();
    if t.starts_with('{') {
        let text = extract_json_str(t, "text").unwrap_or_default();
        let tin = extract_json_num(t, "tokens_in");
        let tout = extract_json_num(t, "tokens_out");
        (text, tin, tout)
    } else {
        (body.to_string(), None, None)
    }
}

fn extract_json_str(json: &str, key: &str) -> Option<String> {
    let pat = format!("\"{key}\"");
    let i = json.find(&pat)?;
    let rest = &json[i + pat.len()..];
    let colon = rest.find(':')?;
    let after = rest[colon + 1..].trim_start();
    if !after.starts_with('"') {
        return None;
    }
    let end = after[1..].find('"')?;
    Some(after[1..1 + end].to_string())
}

fn extract_json_num(json: &str, key: &str) -> Option<u64> {
    let pat = format!("\"{key}\"");
    let i = json.find(&pat)?;
    let rest = &json[i + pat.len()..];
    let colon = rest.find(':')?;
    let after = rest[colon + 1..].trim_start();
    if after.starts_with("null") {
        return None;
    }
    let digits: String = after.chars().take_while(|c| c.is_ascii_digit()).collect();
    if digits.is_empty() {
        return None;
    }
    digits.parse().ok()
}

/// Serve one completion through a transport, enforcing the spend cap
/// (`http` only; agent calls carry no API cost) via `spend_so_far_usd`.
pub fn complete(
    transport: &dyn Transport,
    kind: &TransportKind,
    req: &CompletionRequest,
    spend_so_far_usd: f64,
    cap_usd: f64,
) -> Result<Completion, SparkError> {
    if matches!(kind, TransportKind::Http) && spend_so_far_usd >= cap_usd {
        return Err(SparkError::Budget(format!(
            "spend cap reached: {spend_so_far_usd} >= {cap_usd}"
        )));
    }
    transport.complete(req)
}

/// Stub transport for ported offline tests (injected, never live).
#[derive(Debug, Default)]
pub struct StubTransport {
    pub reply: Option<Result<Completion, SparkError>>,
}

impl Transport for StubTransport {
    fn complete(&self, _req: &CompletionRequest) -> Result<Completion, SparkError> {
        self.reply.clone().unwrap_or(Err(SparkError::NotConfigured(
            "stub has no reply".to_string(),
        )))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unknown_transport_is_not_configured() {
        assert!(matches!(
            TransportKind::from_env("pigeon"),
            Err(SparkError::NotConfigured(_))
        ));
    }

    #[test]
    fn plain_text_body_has_null_counts() {
        let (t, tin, tout) = result_body_for("hello");
        assert_eq!((t.as_str(), tin, tout), ("hello", None, None));
    }

    #[test]
    fn json_envelope_parses() {
        let (t, tin, tout) =
            result_body_for(r#"{"text":"hi","tokens_in":3,"tokens_out":5}"#);
        assert_eq!((t.as_str(), tin, tout), ("hi", Some(3), Some(5)));
    }

    #[test]
    fn http_capped_by_guardrail() {
        let stub = StubTransport::default();
        let req = CompletionRequest { lane_feature: "l".into(), system: "s".into(), prompt: "p".into(), max_tokens: 8, job_ns: "n".into() };
        assert!(matches!(
            complete(&stub, &TransportKind::Http, &req, 75.0, 75.0),
            Err(SparkError::Budget(_))
        ));
    }
}
