//! Local/cloud compute tiering router (decision core).
//!
//! Every task lands on exactly one tier: LOCAL (cheap, on-device) or
//! CLOUD (frontier model, metered). The router scores task kind +
//! policy caps and files a ledger record per routing. Execution stays
//! with the caller: this module never runs models or spends money, so
//! a "cloud" verdict with no backend configured is reported as
//! NO_BACKEND, never silently run as local.
//!
//! Tiers are explicit and auditable; there is no silent fallback from
//! cloud to local (that would hide cost/behavior changes).

/// Where a task may run.
#[derive(Debug, Clone, PartialEq)]
pub enum Tier {
    Local,
    Cloud,
}

/// What the task needs. Scores stay small and legible on purpose:
///
/// kind weight + estimated tokens decide the tier; policy caps veto.
#[derive(Debug, Clone)]
pub struct Task {
    /// 0 = trivial (format, lint), 1 = standard, 2 = deep reasoning.
    pub kind_weight: u8,
    pub est_tokens: u64,
}

/// Policy caps set by the operator.
#[derive(Debug, Clone)]
pub struct Caps {
    /// Cloud allowed at all.
    pub cloud_enabled: bool,
    /// Tasks at/above this weight must use cloud (if enabled).
    pub cloud_from_weight: u8,
    /// Token estimates at/above this go cloud (if enabled).
    pub cloud_from_tokens: u64,
    /// Backend actually configured (key present, reachable).
    pub backend_ready: bool,
}

impl Default for Caps {
    fn default() -> Self {
        Caps { cloud_enabled: true, cloud_from_weight: 2, cloud_from_tokens: 20_000, backend_ready: false }
    }
}

/// The routing outcome.
#[derive(Debug, PartialEq)]
pub enum Route {
    /// Run locally now.
    Local { reason: String },
    /// Send to cloud now.
    Cloud { reason: String },
    /// Cloud was correct but no backend is configured. Caller must
    /// surface this, never downgrade silently.
    NoBackend { reason: String },
}

/// Route one task. Pure logic.
pub fn route(task: &Task, caps: &Caps) -> Route {
    let want_cloud = task.kind_weight >= caps.cloud_from_weight || task.est_tokens >= caps.cloud_from_tokens;
    if !want_cloud {
        return Route::Local { reason: format!("weight {} < {} and {} tokens < {}", task.kind_weight, caps.cloud_from_weight, task.est_tokens, caps.cloud_from_tokens) };
    }
    if !caps.cloud_enabled {
        return Route::Local { reason: "cloud disabled by operator; task queued local with notice".into() };
    }
    if !caps.backend_ready {
        return Route::NoBackend { reason: "cloud tier selected but no backend configured".into() };
    }
    Route::Cloud { reason: format!("weight {} / {} est. tokens", task.kind_weight, task.est_tokens) }
}

/// One ledger line for the routing decision.
#[derive(Debug)]
pub struct RouteRecord {
    pub at_secs: u64,
    pub kind_weight: u8,
    pub est_tokens: u64,
    pub outcome: &'static str,
}

pub fn record(at_secs: u64, task: &Task, route: &Route) -> RouteRecord {
    let outcome = match route {
        Route::Local { .. } => "local",
        Route::Cloud { .. } => "cloud",
        Route::NoBackend { .. } => "no-backend",
    };
    RouteRecord { at_secs, kind_weight: task.kind_weight, est_tokens: task.est_tokens, outcome }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ready() -> Caps {
        Caps { cloud_enabled: true, cloud_from_weight: 2, cloud_from_tokens: 20_000, backend_ready: true }
    }

    #[test]
    fn trivial_tasks_stay_local() {
        let t = Task { kind_weight: 0, est_tokens: 500 };
        assert!(matches!(route(&t, &ready()), Route::Local { .. }));
    }

    #[test]
    fn heavy_tasks_go_cloud_when_backend_ready() {
        let t = Task { kind_weight: 2, est_tokens: 500 };
        assert!(matches!(route(&t, &ready()), Route::Cloud { .. }));
        let big = Task { kind_weight: 1, est_tokens: 50_000 };
        assert!(matches!(route(&big, &ready()), Route::Cloud { .. }));
    }

    #[test]
    fn missing_backend_is_reported_not_downgraded() {
        let mut c = ready();
        c.backend_ready = false;
        let t = Task { kind_weight: 2, est_tokens: 500 };
        let r = route(&t, &c);
        assert!(matches!(r, Route::NoBackend { .. }));
    }

    #[test]
    fn disabled_cloud_stays_local_with_notice() {
        let mut c = ready();
        c.cloud_enabled = false;
        let t = Task { kind_weight: 2, est_tokens: 500 };
        assert!(matches!(route(&t, &c), Route::Local { .. }));
    }
}
