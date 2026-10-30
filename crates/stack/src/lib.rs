//! `stack` — Rust port of the Meta Trio demo-stack wiring (batch B06, owner Rowan).
//!
//! Ports the pure, decidable behavior of one shell source, without
//! redesigning it:
//!   * `run-stack.sh` — service start order, ports, env contract,
//!     health-check shape, transport decision, summary lines.
//!
//! This crate computes the stack plan; it does not spawn processes.
//! A runner executes the plan in order, waits for each readiness
//! gate, and on exit / interrupt / terminate kills every started
//! PID, ignoring errors — mirroring the script's `trap cleanup EXIT
//! INT TERM` and its final `wait`. The Python/Node originals stay
//! untouched as the live fallback until this port is PORTED.
//!
//! Faithful oddities (the script's, kept, not fixed):
//!   * Ports are strings, never validated: `RELAY_PORT=abc` yields
//!     base `http://127.0.0.1:abc`, exactly as the script's
//!     interpolation would. Only empty/missing falls back to the
//!     default, matching `${VAR:-default}`.
//!   * `TRIO_JOB_NS` is never set by the script — it is inherited by
//!     the queue service and the agent when exported beforehand, so
//!     the plan carries it through verbatim (including an empty
//!     exported value). The documented default `"trio"` lives in the
//!     queue service / agent, not in this script.
//!   * `TRIO_UPSTASH_HOST` is part of the queue service's own env
//!     contract, not of this script: the script neither sets nor
//!     mentions it, so the plan does not invent it. Ambient
//!     environment passes through to every service.
//!   * The resident agent has no HTTP health endpoint: readiness is
//!     a 1-second settle followed by an alive check (`kill -0`),
//!     and a dead agent fails the stack (`FAILED: resident agent
//!     exited`, exit 1) — unlike the other three services, which
//!     poll an HTTP health URL.
//!   * The app server always starts with the queue path on:
//!     `TRIO_QUEUE_ENABLED=1` is hardcoded in the script, not
//!     toggled by the stack's own environment.

/// Health-poll attempts per service (`wait_http`: `seq 1 50`).
pub const WAIT_HTTP_MAX_ATTEMPTS: u32 = 50;
/// Health-poll interval in milliseconds (`wait_http`: `sleep 0.2`).
pub const WAIT_HTTP_INTERVAL_MS: u64 = 200;
/// Per-attempt HTTP timeout in seconds (`curl -m 2`).
pub const WAIT_HTTP_TIMEOUT_SECS: u64 = 2;
/// Resident-agent settle before the alive check (`sleep 1`).
pub const AGENT_SETTLE_SECS: u64 = 1;

/// Generation transport, decided exactly as the script decides it:
/// a non-empty `SPARK_API_KEY` means production direct; anything
/// else (missing or empty) means the DEV helper transport, which
/// the script announces loudly as a warning.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Transport {
    /// `SPARK_API_KEY` present: `TRIO_SPARK_VIA_HELPER` unset.
    ProductionDirect,
    /// `SPARK_API_KEY` absent/empty: `TRIO_SPARK_VIA_HELPER=1`.
    DevHelper,
}

impl Transport {
    /// True when the stack must print the DEV-helper warning.
    pub fn dev_helper_warning(self) -> bool {
        self == Transport::DevHelper
    }
}

/// Readiness gate for one service, mirroring the script's checks.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Readiness {
    /// `wait_http`: poll the URL until an HTTP success (`curl -sf`),
    /// or fail after [`WAIT_HTTP_MAX_ATTEMPTS`] attempts.
    HttpHealth {
        url: String,
        max_attempts: u32,
        interval_ms: u64,
        timeout_secs: u64,
    },
    /// Settle [`AGENT_SETTLE_SECS`]s, then require the process to
    /// still be alive (`kill -0`); a dead agent fails the stack.
    ProcessAlive,
}

/// One service in the stack plan, in script start order.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Service {
    /// Display name, as the script echoes it.
    pub name: &'static str,
    /// Command argv, exactly as the script invokes it.
    pub argv: Vec<String>,
    /// Working directory relative to the stack root (the directory
    /// containing `run-stack.sh`); `"."` is the stack root itself.
    pub cwd: &'static str,
    /// Environment the script itself sets for this service, plus
    /// `TRIO_JOB_NS` when inherited. Ambient env passes through.
    pub env: Vec<(String, String)>,
    /// How the script waits for this service to be up.
    pub readiness: Readiness,
}

/// Resolved stack configuration: ports, transport, job namespace.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StackConfig {
    pub relay_port: String,
    pub queue_port: String,
    pub app_port: String,
    pub transport: Transport,
    /// `TRIO_JOB_NS` as inherited, if exported (verbatim, even empty).
    pub job_ns: Option<String>,
}

fn resolve_port(value: Option<&str>, default: &str) -> String {
    match value {
        Some(v) if !v.is_empty() => v.to_string(),
        _ => default.to_string(),
    }
}

fn resolve_transport(spark_api_key: Option<&str>) -> Transport {
    match spark_api_key {
        Some(k) if !k.is_empty() => Transport::ProductionDirect,
        _ => Transport::DevHelper,
    }
}

impl StackConfig {
    /// Build from an explicit env snapshot (key, value) pairs —
    /// the pure, testable form. Missing keys behave as unset.
    pub fn from_entries(entries: &[(&str, &str)]) -> StackConfig {
        let get = |key: &str| entries.iter().find(|(k, _)| *k == key).map(|(_, v)| *v);
        StackConfig {
            relay_port: resolve_port(get("RELAY_PORT"), "8787"),
            queue_port: resolve_port(get("QUEUE_PORT"), "8935"),
            app_port: resolve_port(get("PORT"), "8080"),
            transport: resolve_transport(get("SPARK_API_KEY")),
            job_ns: get("TRIO_JOB_NS").map(str::to_string),
        }
    }

    /// Build from the live process environment.
    pub fn from_env() -> StackConfig {
        let get = |key: &str| std::env::var(key).ok();
        StackConfig {
            relay_port: resolve_port(get("RELAY_PORT").as_deref(), "8787"),
            queue_port: resolve_port(get("QUEUE_PORT").as_deref(), "8935"),
            app_port: resolve_port(get("PORT").as_deref(), "8080"),
            transport: resolve_transport(get("SPARK_API_KEY").as_deref()),
            job_ns: get("TRIO_JOB_NS"),
        }
    }

    pub fn relay_base(&self) -> String {
        format!("http://127.0.0.1:{}", self.relay_port)
    }

    pub fn queue_base(&self) -> String {
        format!("http://127.0.0.1:{}", self.queue_port)
    }

    pub fn app_base(&self) -> String {
        format!("http://127.0.0.1:{}", self.app_port)
    }
}

fn http_health(url: String) -> Readiness {
    Readiness::HttpHealth {
        url,
        max_attempts: WAIT_HTTP_MAX_ATTEMPTS,
        interval_ms: WAIT_HTTP_INTERVAL_MS,
        timeout_secs: WAIT_HTTP_TIMEOUT_SECS,
    }
}

/// The four services in script start order, with the exact argv,
/// cwd, env, and readiness gate the script uses for each.
pub fn plan(config: &StackConfig) -> Vec<Service> {
    let relay_base = config.relay_base();
    let queue_base = config.queue_base();
    let app_base = config.app_base();
    // TRIO_JOB_NS is inherited, not set: it rides along only when
    // exported beforehand, for the queue service and the agent.
    let job_ns_env: Vec<(String, String)> = config
        .job_ns
        .as_ref()
        .map(|ns| vec![("TRIO_JOB_NS".to_string(), ns.clone())])
        .unwrap_or_default();
    vec![
        Service {
            name: "Meta Nuntius relay",
            argv: vec!["node".to_string(), "relay/relay.mjs".to_string()],
            cwd: ".",
            env: vec![("RELAY_PORT".to_string(), config.relay_port.clone())],
            readiness: http_health(format!("{}/health", relay_base)),
        },
        Service {
            name: "queue service",
            argv: vec![
                "python3".to_string(),
                "queue_service.py".to_string(),
                "--port".to_string(),
                config.queue_port.clone(),
            ],
            cwd: "server/queue",
            env: job_ns_env.clone(),
            readiness: http_health(format!("{}/health", queue_base)),
        },
        Service {
            name: "resident agent",
            argv: vec!["python3".to_string(), "trio_agent.py".to_string()],
            cwd: "server/queue",
            env: {
                let mut env = vec![("TRIO_RELAY_URL".to_string(), relay_base.clone())];
                env.extend(job_ns_env);
                env
            },
            readiness: Readiness::ProcessAlive,
        },
        Service {
            name: "Trio app server",
            argv: vec!["node".to_string(), "server/server.mjs".to_string()],
            cwd: ".",
            env: vec![
                ("PORT".to_string(), config.app_port.clone()),
                ("TRIO_QUEUE_ENABLED".to_string(), "1".to_string()),
                ("TRIO_QUEUE_URL".to_string(), queue_base),
            ],
            readiness: http_health(format!("{}/api/health", app_base)),
        },
    ]
}

/// The four address lines the script echoes once the stack is up,
/// verbatim apart from the substituted bases.
pub fn summary_lines(config: &StackConfig) -> Vec<String> {
    let relay_base = config.relay_base();
    let queue_base = config.queue_base();
    let app_base = config.app_base();
    vec![
        format!("  Meta Nuntius viewer   {}/", relay_base),
        format!("  Queue service         {}/health", queue_base),
        format!(
            "  Resident agent        running (NOTIFY -> {}/rooms/main)",
            relay_base
        ),
        format!(
            "  Web console + API     {}/  (POST {}/api/assess)",
            app_base, app_base
        ),
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    fn defaults() -> StackConfig {
        StackConfig::from_entries(&[])
    }

    #[test]
    fn default_ports_and_bases() {
        let c = defaults();
        assert_eq!(c.relay_port, "8787");
        assert_eq!(c.queue_port, "8935");
        assert_eq!(c.app_port, "8080");
        assert_eq!(c.relay_base(), "http://127.0.0.1:8787");
        assert_eq!(c.queue_base(), "http://127.0.0.1:8935");
        assert_eq!(c.app_base(), "http://127.0.0.1:8080");
    }

    #[test]
    fn port_overrides_are_honored() {
        let c = StackConfig::from_entries(&[
            ("RELAY_PORT", "9000"),
            ("QUEUE_PORT", "9001"),
            ("PORT", "9002"),
        ]);
        assert_eq!(c.relay_base(), "http://127.0.0.1:9000");
        assert_eq!(c.queue_base(), "http://127.0.0.1:9001");
        assert_eq!(c.app_base(), "http://127.0.0.1:9002");
    }

    #[test]
    fn empty_port_values_fall_back_to_defaults() {
        // ${VAR:-default}: empty counts as unset.
        let c = StackConfig::from_entries(&[("RELAY_PORT", ""), ("QUEUE_PORT", ""), ("PORT", "")]);
        assert_eq!(c.relay_port, "8787");
        assert_eq!(c.queue_port, "8935");
        assert_eq!(c.app_port, "8080");
    }

    #[test]
    fn non_numeric_port_passes_through_verbatim() {
        // Bash interpolates without validating; the port keeps the
        // oddity instead of failing the stack.
        let c = StackConfig::from_entries(&[("RELAY_PORT", "abc")]);
        assert_eq!(c.relay_base(), "http://127.0.0.1:abc");
    }

    #[test]
    fn transport_production_when_key_present() {
        let c = StackConfig::from_entries(&[("SPARK_API_KEY", "sk-live")]);
        assert_eq!(c.transport, Transport::ProductionDirect);
        assert!(!c.transport.dev_helper_warning());
    }

    #[test]
    fn transport_dev_helper_when_key_missing_or_empty() {
        assert_eq!(defaults().transport, Transport::DevHelper);
        assert!(defaults().transport.dev_helper_warning());
        let c = StackConfig::from_entries(&[("SPARK_API_KEY", "")]);
        assert_eq!(c.transport, Transport::DevHelper);
        assert!(c.transport.dev_helper_warning());
    }

    #[test]
    fn job_ns_absent_by_default_and_inherited_verbatim() {
        assert_eq!(defaults().job_ns, None);
        let c = StackConfig::from_entries(&[("TRIO_JOB_NS", "scratch-7")]);
        assert_eq!(c.job_ns.as_deref(), Some("scratch-7"));
        // An exported empty value is still inherited (verbatim).
        let c = StackConfig::from_entries(&[("TRIO_JOB_NS", "")]);
        assert_eq!(c.job_ns.as_deref(), Some(""));
    }

    #[test]
    fn plan_order_is_script_order() {
        let names: Vec<&str> = plan(&defaults()).iter().map(|s| s.name).collect();
        assert_eq!(
            names,
            vec![
                "Meta Nuntius relay",
                "queue service",
                "resident agent",
                "Trio app server",
            ]
        );
    }

    #[test]
    fn relay_service_matches_script() {
        let s = &plan(&defaults())[0];
        assert_eq!(s.argv, vec!["node", "relay/relay.mjs"]);
        assert_eq!(s.cwd, ".");
        assert_eq!(s.env, vec![("RELAY_PORT".to_string(), "8787".to_string())]);
        assert_eq!(
            s.readiness,
            Readiness::HttpHealth {
                url: "http://127.0.0.1:8787/health".to_string(),
                max_attempts: 50,
                interval_ms: 200,
                timeout_secs: 2,
            }
        );
    }

    #[test]
    fn queue_service_matches_script() {
        let s = &plan(&defaults())[1];
        assert_eq!(
            s.argv,
            vec!["python3", "queue_service.py", "--port", "8935"]
        );
        assert_eq!(s.cwd, "server/queue");
        assert!(s.env.is_empty(), "no TRIO_JOB_NS when not exported");
        assert_eq!(
            s.readiness,
            Readiness::HttpHealth {
                url: "http://127.0.0.1:8935/health".to_string(),
                max_attempts: 50,
                interval_ms: 200,
                timeout_secs: 2,
            }
        );
        // With TRIO_JOB_NS exported, the queue service inherits it.
        let c = StackConfig::from_entries(&[("TRIO_JOB_NS", "scratch-7")]);
        assert_eq!(
            plan(&c)[1].env,
            vec![("TRIO_JOB_NS".to_string(), "scratch-7".to_string())]
        );
    }

    #[test]
    fn agent_service_matches_script() {
        let s = &plan(&defaults())[2];
        assert_eq!(s.argv, vec!["python3", "trio_agent.py"]);
        assert_eq!(s.cwd, "server/queue");
        assert_eq!(
            s.env,
            vec![(
                "TRIO_RELAY_URL".to_string(),
                "http://127.0.0.1:8787".to_string()
            )]
        );
        // No HTTP health gate: settle + alive check, unlike the rest.
        assert_eq!(s.readiness, Readiness::ProcessAlive);
        assert_eq!(AGENT_SETTLE_SECS, 1);
        // With TRIO_JOB_NS exported, the agent inherits it too.
        let c = StackConfig::from_entries(&[("TRIO_JOB_NS", "scratch-7")]);
        assert_eq!(
            plan(&c)[2].env,
            vec![
                (
                    "TRIO_RELAY_URL".to_string(),
                    "http://127.0.0.1:8787".to_string()
                ),
                ("TRIO_JOB_NS".to_string(), "scratch-7".to_string()),
            ]
        );
    }

    #[test]
    fn app_service_matches_script_queue_path_always_on() {
        let s = &plan(&defaults())[3];
        assert_eq!(s.argv, vec!["node", "server/server.mjs"]);
        assert_eq!(s.cwd, ".");
        assert_eq!(
            s.env,
            vec![
                ("PORT".to_string(), "8080".to_string()),
                ("TRIO_QUEUE_ENABLED".to_string(), "1".to_string()),
                (
                    "TRIO_QUEUE_URL".to_string(),
                    "http://127.0.0.1:8935".to_string()
                ),
            ]
        );
        assert_eq!(
            s.readiness,
            Readiness::HttpHealth {
                url: "http://127.0.0.1:8080/api/health".to_string(),
                max_attempts: 50,
                interval_ms: 200,
                timeout_secs: 2,
            }
        );
    }

    #[test]
    fn summary_lines_match_script_echo() {
        assert_eq!(
            summary_lines(&defaults()),
            vec![
                "  Meta Nuntius viewer   http://127.0.0.1:8787/".to_string(),
                "  Queue service         http://127.0.0.1:8935/health".to_string(),
                "  Resident agent        running (NOTIFY -> http://127.0.0.1:8787/rooms/main)".to_string(),
                "  Web console + API     http://127.0.0.1:8080/  (POST http://127.0.0.1:8080/api/assess)".to_string(),
            ]
        );
        // Custom ports flow into every line.
        let c = StackConfig::from_entries(&[
            ("RELAY_PORT", "9000"),
            ("QUEUE_PORT", "9001"),
            ("PORT", "9002"),
        ]);
        let lines = summary_lines(&c);
        assert!(lines[0].contains("http://127.0.0.1:9000/"));
        assert!(lines[1].contains("http://127.0.0.1:9001/health"));
        assert!(lines[2].contains("http://127.0.0.1:9000/rooms/main"));
        assert!(lines[3].contains("http://127.0.0.1:9002/"));
        assert!(lines[3].contains("http://127.0.0.1:9002/api/assess"));
    }
}
