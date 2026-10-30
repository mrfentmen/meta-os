//! Crate `stack` — Meta Trio demo stack wiring (B06).
//!
//! Port of `run-stack.sh` (the spec): the same four services, in the
//! same order, with the same ports and env contract. Behavior, not
//! redesign — including the script's quirks, which are noted below.
//!
//! Quirks ported from the script:
//! - Empty/unset `RELAY_PORT`, `QUEUE_PORT`, `PORT` fall back to their
//!   defaults (`${VAR:-default}` semantics).
//! - `TRIO_UPSTASH_HOST` is **not** set by the script even though the
//!   batch contract names it: like `TRIO_JOB_NS`, it is inherited from
//!   the environment when already exported (the queue service reads it).
//! - `wait_http` polls up to 50 times, 200 ms apart, with a ~2 s per-try
//!   timeout (`curl -sf -m 2`).

use std::collections::HashMap;
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream, ToSocketAddrs};
use std::time::Duration;

// ---------------------------------------------------------------------------
// Defaults (mirror `${VAR:-default}` in run-stack.sh)
// ---------------------------------------------------------------------------

/// Default Meta Nuntius relay port (`RELAY_PORT`).
pub const DEFAULT_RELAY_PORT: u16 = 8787;
/// Default OS queue service port (`QUEUE_PORT`).
pub const DEFAULT_QUEUE_PORT: u16 = 8935;
/// Default Trio app server port (`PORT`).
pub const DEFAULT_APP_PORT: u16 = 8080;
/// `wait_http` poll attempts (`for i in $(seq 1 50)`).
pub const WAIT_ATTEMPTS: u32 = 50;
/// Delay between `wait_http` polls (the script's `sleep 0.2`).
pub const WAIT_DELAY_MS: u64 = 200;
/// Per-try timeout (the script's `curl -m 2`).
pub const WAIT_TRY_TIMEOUT_SECS: u64 = 2;

/// Parse a port env value with `${VAR:-default}` semantics: missing or
/// empty means the default. A non-numeric value also falls back to the
/// default here; the script would instead fail later when the service
/// tries to listen, so this is fail-safe hardening, not a redesign.
#[must_use]
pub fn parse_port(raw: Option<&str>, default: u16) -> u16 {
    match raw {
        None => default,
        Some(s) if s.trim().is_empty() => default,
        Some(s) => s.trim().parse::<u16>().unwrap_or(default),
    }
}

// ---------------------------------------------------------------------------
// Generation transport (SPARK_API_KEY branch)
// ---------------------------------------------------------------------------

/// Which generation transport the stack uses.
///
/// Mirrors the `SPARK_API_KEY` branch at the top of `run-stack.sh`:
/// production direct when the key is present, otherwise the DEV helper
/// transport (`TRIO_SPARK_VIA_HELPER=1`) with a loud warning.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GenerationTransport {
    /// `SPARK_API_KEY` is set: production direct transport.
    ProductionDirect,
    /// No key: DEV helper transport (`TRIO_SPARK_VIA_HELPER=1`).
    DevHelper,
}

impl GenerationTransport {
    /// Resolve from the presence of a non-empty `SPARK_API_KEY`.
    #[must_use]
    pub fn resolve(spark_api_key: Option<&str>) -> Self {
        match spark_api_key {
            Some(key) if !key.trim().is_empty() => GenerationTransport::ProductionDirect,
            _ => GenerationTransport::DevHelper,
        }
    }

    /// The `TRIO_SPARK_VIA_HELPER` export the script performs (or
    /// explicitly unsets) for this transport.
    #[must_use]
    pub fn helper_env(&self) -> Option<(&'static str, &'static str)> {
        match self {
            GenerationTransport::ProductionDirect => None,
            GenerationTransport::DevHelper => Some(("TRIO_SPARK_VIA_HELPER", "1")),
        }
    }

    #[must_use]
    pub fn describe(&self) -> &'static str {
        match self {
            GenerationTransport::ProductionDirect => {
                "Generation transport: production direct (SPARK_API_KEY present)."
            }
            GenerationTransport::DevHelper => {
                "WARNING: SPARK_API_KEY is not set — using the DEV helper transport \
                 (TRIO_SPARK_VIA_HELPER=1). Sandbox/development only; the \
                 production run sets SPARK_API_KEY in the environment."
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Stack configuration
// ---------------------------------------------------------------------------

/// The four stack services in boot order.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ServiceKind {
    Relay,
    QueueService,
    ResidentAgent,
    AppServer,
}

impl ServiceKind {
    #[must_use]
    pub fn name(self) -> &'static str {
        match self {
            ServiceKind::Relay => "relay",
            ServiceKind::QueueService => "queue-service",
            ServiceKind::ResidentAgent => "resident-agent",
            ServiceKind::AppServer => "app-server",
        }
    }
}

/// Resolved stack configuration: ports, base URLs, transport, and
/// environment passthroughs.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StackConfig {
    pub relay_port: u16,
    pub queue_port: u16,
    pub app_port: u16,
    pub transport: GenerationTransport,
    /// Inherited when exported before the script runs (proofs use a
    /// scratch namespace; default is `"trio"`).
    pub trio_job_ns: Option<String>,
    /// Inherited when exported; the script never sets it itself.
    pub trio_upstash_host: Option<String>,
}

impl StackConfig {
    /// Build from explicit values (tests and embedders).
    #[must_use]
    pub fn new(
        relay_port: u16,
        queue_port: u16,
        app_port: u16,
        transport: GenerationTransport,
    ) -> Self {
        Self {
            relay_port,
            queue_port,
            app_port,
            transport,
            trio_job_ns: None,
            trio_upstash_host: None,
        }
    }

    /// Read from the process environment, exactly the names the script
    /// reads: `RELAY_PORT`, `QUEUE_PORT`, `PORT`, `SPARK_API_KEY`,
    /// plus the `TRIO_JOB_NS` / `TRIO_UPSTASH_HOST` passthroughs.
    #[must_use]
    pub fn from_env() -> Self {
        Self::from_map(&env_map())
    }

    /// Build from a variable map (used by `from_env` and tests).
    #[must_use]
    pub fn from_map(vars: &HashMap<String, String>) -> Self {
        let get = |key: &str| vars.get(key).map(String::as_str);
        let nonempty = |key: &str| {
            get(key)
                .filter(|v| !v.trim().is_empty())
                .map(str::to_string)
        };
        Self {
            relay_port: parse_port(get("RELAY_PORT"), DEFAULT_RELAY_PORT),
            queue_port: parse_port(get("QUEUE_PORT"), DEFAULT_QUEUE_PORT),
            app_port: parse_port(get("PORT"), DEFAULT_APP_PORT),
            transport: GenerationTransport::resolve(get("SPARK_API_KEY")),
            trio_job_ns: nonempty("TRIO_JOB_NS"),
            trio_upstash_host: nonempty("TRIO_UPSTASH_HOST"),
        }
    }

    #[must_use]
    pub fn relay_base(&self) -> String {
        format!("http://127.0.0.1:{}", self.relay_port)
    }

    #[must_use]
    pub fn queue_base(&self) -> String {
        format!("http://127.0.0.1:{}", self.queue_port)
    }

    #[must_use]
    pub fn app_base(&self) -> String {
        format!("http://127.0.0.1:{}", self.app_port)
    }

    /// The four services in boot order.
    #[must_use]
    pub fn services(&self) -> Vec<Service> {
        vec![
            Service {
                kind: ServiceKind::Relay,
                workdir: None,
                program: "node".to_string(),
                args: vec!["relay/relay.mjs".to_string()],
                env: vec![(
                    "RELAY_PORT".to_string(),
                    self.relay_port.to_string(),
                )],
                readiness: Readiness::HttpHealth(format!("{}/health", self.relay_base())),
                label: "Meta Nuntius relay".to_string(),
            },
            Service {
                kind: ServiceKind::QueueService,
                workdir: Some("server/queue".to_string()),
                program: "python3".to_string(),
                args: vec![
                    "queue_service.py".to_string(),
                    "--port".to_string(),
                    self.queue_port.to_string(),
                ],
                env: vec![],
                readiness: Readiness::HttpHealth(format!("{}/health", self.queue_base())),
                label: "queue service".to_string(),
            },
            Service {
                kind: ServiceKind::ResidentAgent,
                workdir: Some("server/queue".to_string()),
                program: "python3".to_string(),
                args: vec!["trio_agent.py".to_string()],
                env: vec![(
                    "TRIO_RELAY_URL".to_string(),
                    self.relay_base(),
                )],
                // The script sleeps 1 s then `kill -0`s the agent pid.
                readiness: Readiness::ProcessAlive { settle_secs: 1 },
                label: format!("resident agent (TRIO_RELAY_URL={})", self.relay_base()),
            },
            Service {
                kind: ServiceKind::AppServer,
                workdir: None,
                program: "node".to_string(),
                args: vec!["server/server.mjs".to_string()],
                env: vec![
                    ("PORT".to_string(), self.app_port.to_string()),
                    ("TRIO_QUEUE_ENABLED".to_string(), "1".to_string()),
                    ("TRIO_QUEUE_URL".to_string(), self.queue_base()),
                ],
                readiness: Readiness::HttpHealth(format!("{}/api/health", self.app_base())),
                label: "Trio app server".to_string(),
            },
        ]
    }

    /// The end-of-boot summary the script prints.
    #[must_use]
    pub fn summary_lines(&self) -> Vec<String> {
        vec![
            "Meta Trio stack is up:".to_string(),
            format!("  Meta Nuntius viewer   {}/", self.relay_base()),
            format!("  Queue service         {}/health", self.queue_base()),
            format!(
                "  Resident agent        running (NOTIFY -> {}/rooms/main)",
                self.relay_base()
            ),
            format!(
                "  Web console + API     {}/  (POST {}/api/assess)",
                self.app_base(),
                self.app_base()
            ),
            String::new(),
            "Ctrl-C stops the whole stack.".to_string(),
        ]
    }
}

/// How the script waits for a freshly started service.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Readiness {
    /// `wait_http <url> <label>`: poll the health endpoint.
    HttpHealth(String),
    /// `sleep 1; kill -0 <pid>`: the agent has no health endpoint.
    ProcessAlive { settle_secs: u64 },
}

/// One wired service: what to spawn, where, and how to wait for it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Service {
    pub kind: ServiceKind,
    /// Subdirectory to start in (`(cd dir && ...)` in the script).
    pub workdir: Option<String>,
    pub program: String,
    pub args: Vec<String>,
    pub env: Vec<(String, String)>,
    pub readiness: Readiness,
    /// Human label used in `up: <label>` / `FAILED to come up` lines.
    pub label: String,
}

impl Service {
    /// Full command line (`program` + `args`).
    #[must_use]
    pub fn command_line(&self) -> Vec<String> {
        let mut cmd = vec![self.program.clone()];
        cmd.extend(self.args.clone());
        cmd
    }

    /// Look up one of the service's explicit env entries.
    #[must_use]
    pub fn env_value(&self, key: &str) -> Option<&str> {
        self.env
            .iter()
            .find(|(k, _)| k == key)
            .map(|(_, v)| v.as_str())
    }
}

fn env_map() -> HashMap<String, String> {
    std::env::vars().collect()
}

// ---------------------------------------------------------------------------
// wait_http
// ---------------------------------------------------------------------------

/// Poll `url` until it answers HTTP 200 or attempts run out.
///
/// Direct port of the script's `wait_http`: up to `attempts` tries,
/// `delay` between tries, ~2 s per-try timeout. Returns `Ok(())` once
/// the endpoint answers (`up: <label>`), else `Err` with the script's
/// `FAILED to come up: <label> (<url>)` text.
pub fn wait_http(url: &str, label: &str) -> Result<(), String> {
    wait_http_with(
        url,
        label,
        WAIT_ATTEMPTS,
        Duration::from_millis(WAIT_DELAY_MS),
    )
}

/// [`wait_http`] with injectable retry budget (tests use small budgets).
pub fn wait_http_with(
    url: &str,
    label: &str,
    attempts: u32,
    delay: Duration,
) -> Result<(), String> {
    for _ in 0..attempts.max(1) {
        if http_get_ok(url) {
            return Ok(());
        }
        std::thread::sleep(delay);
    }
    Err(format!("FAILED to come up: {label} ({url})"))
}

/// Minimal blocking HTTP GET over std TCP: true when the server answers
/// with a 2xx status. Only `http://` URLs are supported (the whole stack
/// is loopback plain HTTP).
fn http_get_ok(url: &str) -> bool {
    let Some((host_port, path)) = split_http_url(url) else {
        return false;
    };
    let timeout = Duration::from_secs(WAIT_TRY_TIMEOUT_SECS);
    let addrs: Vec<SocketAddr> = match host_port.to_socket_addrs() {
        Ok(addrs) => addrs.collect(),
        Err(_) => return false,
    };
    let mut stream = None;
    for addr in addrs {
        if let Ok(s) = TcpStream::connect_timeout(&addr, timeout) {
            stream = Some(s);
            break;
        }
    };
    let mut stream = match stream {
        Some(s) => s,
        None => return false,
    };
    if stream
        .set_read_timeout(Some(timeout))
        .and_then(|()| stream.set_write_timeout(Some(timeout)))
        .is_err()
    {
        return false;
    }
    let request = format!("GET {path} HTTP/1.0\r\nHost: {host_port}\r\nConnection: close\r\n\r\n");
    if stream.write_all(request.as_bytes()).is_err() {
        return false;
    }
    let mut response = Vec::with_capacity(128);
    if stream.read_to_end(&mut response).is_err() {
        return false;
    }
    let head = String::from_utf8_lossy(&response);
    let status = head.lines().next().unwrap_or("");
    let code: u16 = status
        .split_whitespace()
        .nth(1)
        .and_then(|c| c.parse().ok())
        .unwrap_or(0);
    (200..300).contains(&code)
}

fn split_http_url(url: &str) -> Option<(String, String)> {
    let rest = url.strip_prefix("http://")?;
    let (host_port, path) = match rest.split_once('/') {
        Some((h, p)) => (h, format!("/{p}")),
        None => (rest, "/".to_string()),
    };
    if host_port.is_empty() {
        return None;
    }
    Some((host_port.to_string(), path))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::net::TcpListener;
    use std::thread;

    fn vars(pairs: &[(&str, &str)]) -> HashMap<String, String> {
        pairs
            .iter()
            .map(|(k, v)| ((*k).to_string(), (*v).to_string()))
            .collect()
    }

    #[test]
    fn default_ports_match_the_script() {
        let config = StackConfig::from_map(&vars(&[]));
        assert_eq!(config.relay_port, 8787);
        assert_eq!(config.queue_port, 8935);
        assert_eq!(config.app_port, 8080);
        assert_eq!(config.relay_base(), "http://127.0.0.1:8787");
        assert_eq!(config.queue_base(), "http://127.0.0.1:8935");
        assert_eq!(config.app_base(), "http://127.0.0.1:8080");
    }

    #[test]
    fn env_overrides_ports() {
        let config = StackConfig::from_map(&vars(&[
            ("RELAY_PORT", "9999"),
            ("QUEUE_PORT", "9998"),
            ("PORT", "9997"),
        ]));
        assert_eq!(config.relay_port, 9999);
        assert_eq!(config.queue_port, 9998);
        assert_eq!(config.app_port, 9997);
    }

    #[test]
    fn empty_env_falls_back_to_defaults() {
        // Mirrors `${VAR:-default}`: empty means unset.
        let config = StackConfig::from_map(&vars(&[
            ("RELAY_PORT", ""),
            ("QUEUE_PORT", ""),
            ("PORT", ""),
        ]));
        assert_eq!(config.relay_port, DEFAULT_RELAY_PORT);
        assert_eq!(config.queue_port, DEFAULT_QUEUE_PORT);
        assert_eq!(config.app_port, DEFAULT_APP_PORT);
    }

    #[test]
    fn generation_transport_production_vs_dev() {
        let prod = StackConfig::from_map(&vars(&[("SPARK_API_KEY", "sk-live")]));
        assert_eq!(prod.transport, GenerationTransport::ProductionDirect);
        assert_eq!(prod.transport.helper_env(), None);
        assert!(prod.transport.describe().contains("production direct"));

        let dev = StackConfig::from_map(&vars(&[]));
        assert_eq!(dev.transport, GenerationTransport::DevHelper);
        assert_eq!(
            dev.transport.helper_env(),
            Some(("TRIO_SPARK_VIA_HELPER", "1"))
        );

        // Empty key counts as unset, like `[ -n "${SPARK_API_KEY:-}" ]`.
        let empty = StackConfig::from_map(&vars(&[("SPARK_API_KEY", "")]));
        assert_eq!(empty.transport, GenerationTransport::DevHelper);
    }

    #[test]
    fn service_order_and_commands() {
        let config = StackConfig::from_map(&vars(&[]));
        let services = config.services();
        assert_eq!(
            services.iter().map(|s| s.kind).collect::<Vec<_>>(),
            vec![
                ServiceKind::Relay,
                ServiceKind::QueueService,
                ServiceKind::ResidentAgent,
                ServiceKind::AppServer,
            ]
        );
        assert_eq!(
            services[0].command_line(),
            vec!["node", "relay/relay.mjs"]
        );
        assert_eq!(
            services[1].command_line(),
            vec!["python3", "queue_service.py", "--port", "8935"]
        );
        assert_eq!(services[2].command_line(), vec!["python3", "trio_agent.py"]);
        assert_eq!(
            services[3].command_line(),
            vec!["node", "server/server.mjs"]
        );
    }

    #[test]
    fn relay_wiring_env_and_health() {
        let config = StackConfig::from_map(&vars(&[]));
        let relay = &config.services()[0];
        assert_eq!(relay.workdir, None);
        assert_eq!(relay.env_value("RELAY_PORT"), Some("8787"));
        assert_eq!(
            relay.readiness,
            Readiness::HttpHealth("http://127.0.0.1:8787/health".to_string())
        );
    }

    #[test]
    fn queue_command_and_health() {
        let config = StackConfig::from_map(&vars(&[("QUEUE_PORT", "8935")]));
        let queue = &config.services()[1];
        assert_eq!(queue.workdir.as_deref(), Some("server/queue"));
        assert!(queue.args.windows(2).any(|w| w == ["--port", "8935"]));
        assert_eq!(
            queue.readiness,
            Readiness::HttpHealth("http://127.0.0.1:8935/health".to_string())
        );
    }

    #[test]
    fn agent_relay_url_and_alive_check() {
        let config = StackConfig::from_map(&vars(&[]));
        let agent = &config.services()[2];
        assert_eq!(agent.workdir.as_deref(), Some("server/queue"));
        assert_eq!(
            agent.env_value("TRIO_RELAY_URL"),
            Some("http://127.0.0.1:8787")
        );
        // The agent has no health endpoint: sleep 1 then `kill -0`.
        assert_eq!(agent.readiness, Readiness::ProcessAlive { settle_secs: 1 });
    }

    #[test]
    fn app_queue_wiring_and_health() {
        let config = StackConfig::from_map(&vars(&[]));
        let app = &config.services()[3];
        assert_eq!(app.env_value("PORT"), Some("8080"));
        assert_eq!(app.env_value("TRIO_QUEUE_ENABLED"), Some("1"));
        assert_eq!(
            app.env_value("TRIO_QUEUE_URL"),
            Some("http://127.0.0.1:8935")
        );
        assert_eq!(
            app.readiness,
            Readiness::HttpHealth("http://127.0.0.1:8080/api/health".to_string())
        );
    }

    #[test]
    fn job_ns_and_upstash_host_are_passthrough() {
        // `TRIO_JOB_NS` is inherited when exported; `TRIO_UPSTASH_HOST`
        // is likewise never set by the script itself (named in the batch
        // contract only) — both ride along from the environment.
        let config = StackConfig::from_map(&vars(&[
            ("TRIO_JOB_NS", "scratch-7"),
            ("TRIO_UPSTASH_HOST", "upstash.example"),
        ]));
        assert_eq!(config.trio_job_ns.as_deref(), Some("scratch-7"));
        assert_eq!(
            config.trio_upstash_host.as_deref(),
            Some("upstash.example")
        );
        let unset = StackConfig::from_map(&vars(&[]));
        assert_eq!(unset.trio_job_ns, None);
        assert_eq!(unset.trio_upstash_host, None);
    }

    #[test]
    fn summary_lists_all_endpoints() {
        let config = StackConfig::from_map(&vars(&[]));
        let summary = config.summary_lines().join("\n");
        assert!(summary.contains("http://127.0.0.1:8787/"));
        assert!(summary.contains("http://127.0.0.1:8935/health"));
        assert!(summary.contains("NOTIFY -> http://127.0.0.1:8787/rooms/main"));
        assert!(summary.contains("POST http://127.0.0.1:8080/api/assess"));
    }

    #[test]
    fn wait_budget_constants_match_script() {
        assert_eq!(WAIT_ATTEMPTS, 50);
        assert_eq!(WAIT_DELAY_MS, 200);
        assert_eq!(WAIT_TRY_TIMEOUT_SECS, 2);
    }

    fn spawn_ok_server() -> (String, thread::JoinHandle<()>) {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        let handle = thread::spawn(move || {
            let (mut stream, _) = listener.accept().unwrap();
            let mut buf = [0u8; 512];
            let _ = stream.read(&mut buf);
            let _ = stream.write_all(
                b"HTTP/1.0 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok",
            );
        });
        (format!("http://127.0.0.1:{port}/health"), handle)
    }

    #[test]
    fn wait_http_succeeds_against_local_listener() {
        let (url, handle) = spawn_ok_server();
        let result = wait_http_with(&url, "test service", 10, Duration::from_millis(10));
        assert!(result.is_ok());
        handle.join().unwrap();
    }

    #[test]
    fn wait_http_fails_after_attempts() {
        // Closed port on loopback: refused fast, so a small budget suffices.
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        drop(listener);
        let url = format!("http://127.0.0.1:{port}/health");
        let result = wait_http_with(&url, "test service", 3, Duration::from_millis(5));
        let err = result.unwrap_err();
        assert!(err.contains("FAILED to come up: test service"));
        assert!(err.contains(&url));
    }
}
