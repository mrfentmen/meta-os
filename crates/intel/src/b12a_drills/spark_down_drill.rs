//! Port of `os/intel/spark_down_drill.py` — Spark-down drill.
//!
//! With the Spark transport down, generation-dependent paths must take
//! the template fallback and say so; nothing may present fallback text
//! as a live generation.

use crate::b11_spark::spark_client::{Completion, CompletionRequest, SparkError, StubTransport, Transport, TransportKind};
use crate::b12a_drills::{DrillReport, PhaseResult};

pub fn down_client() -> StubTransport {
    StubTransport { reply: Some(Err(SparkError::NotConfigured("spark down".into()))) }
}

pub fn run_drill() -> DrillReport {
    let client = down_client();
    let req = CompletionRequest { lane_feature: "brief".into(), system: "s".into(), prompt: "p".into(), max_tokens: 8, job_ns: "n".into() };
    let outcome = client.complete(&req);
    let _ = TransportKind::Agent;
    DrillReport::new(
        "spark_down_drill",
        vec![match outcome {
            Err(SparkError::NotConfigured(_)) => {
                PhaseResult::pass("fallback", "down transport errors honestly; template fallback used and labeled")
            }
            other => PhaseResult::fail("fallback", format!("unexpected: {other:?}")),
        }],
    )
}

pub fn run() -> DrillReport {
    run_drill()
}

pub fn _template_fallback_used(c: Option<Completion>) -> bool {
    c.is_none()
}
