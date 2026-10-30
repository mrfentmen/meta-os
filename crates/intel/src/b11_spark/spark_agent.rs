//! Port of `os/intel/spark_agent.py` — resident Spark agent surface.
//!
//! [`SparkAgent`] polls Spark-complete jobs and generates; without
//! configuration [`unconfigured_generate`] errors (never fakes).
//! [`parse_spark_spec`] validates the dispatcher envelope.

#[derive(Debug, Clone, PartialEq)]
pub struct SparkSpec {
    pub kind: String,
    pub v: u32,
    pub lane_feature: String,
    pub system: String,
    pub prompt: String,
    pub max_tokens: u32,
    pub job_ns: String,
    pub result_key_pattern: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct AgentError(pub String);

/// Called when generation is not configured: always errors.
pub fn unconfigured_generate() -> Result<String, AgentError> {
    Err(AgentError("spark agent not configured".to_string()))
}

pub fn parse_spark_spec(
    kind: &str,
    v: u32,
    lane_feature: &str,
    system: &str,
    prompt: &str,
    max_tokens: u32,
    job_ns: &str,
) -> Result<SparkSpec, AgentError> {
    if kind != "spark-complete" {
        return Err(AgentError(format!("bad spec kind: {kind}")));
    }
    if v != 1 {
        return Err(AgentError(format!("bad spec v: {v}")));
    }
    if prompt.is_empty() {
        return Err(AgentError("empty prompt".to_string()));
    }
    Ok(SparkSpec {
        kind: kind.to_string(),
        v,
        lane_feature: lane_feature.to_string(),
        system: system.to_string(),
        prompt: prompt.to_string(),
        max_tokens,
        job_ns: job_ns.to_string(),
        result_key_pattern: "{job_ns}:{jid}:result".to_string(),
    })
}

pub fn result_key_for(job_ns: &str, jid: &str) -> String {
    format!("{job_ns}:{jid}:result")
}

pub fn result_body_for(text: &str, tokens_in: Option<u64>, tokens_out: Option<u64>) -> String {
    match (tokens_in, tokens_out) {
        (Some(ti), Some(to)) => format!("{{\"text\":{text:?},\"tokens_in\":{ti},\"tokens_out\":{to}}}"),
        _ => text.to_string(),
    }
}

/// Resident agent handle (poll/generate wiring lives on the Mac gate).
#[derive(Debug)]
pub struct SparkAgent {
    pub capability: String,
    pub room: String,
}

impl SparkAgent {
    pub fn new(capability: &str, room: &str) -> Self {
        Self { capability: capability.to_string(), room: room.to_string() }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn unconfigured_never_fakes() {
        assert!(unconfigured_generate().is_err());
    }
    #[test]
    fn spec_validates_kind_and_version() {
        assert!(parse_spark_spec("nope", 1, "l", "s", "p", 8, "n").is_err());
        assert!(parse_spark_spec("spark-complete", 2, "l", "s", "p", 8, "n").is_err());
        assert!(parse_spark_spec("spark-complete", 1, "l", "s", "p", 8, "n").is_ok());
    }
}
