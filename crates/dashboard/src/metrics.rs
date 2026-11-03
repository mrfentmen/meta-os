//! Machine metrics for the dashboard: four cards, one reading each.
//!
//! The viewer was fold-excluded from the cleaned tree, so this is the
//! backend data the four cards render from — not HTML. Two rules shape it:
//!
//! 1. **A missing reading is stated, never zeroed.** An empty snapshot is a
//!    real state (the source did not answer yet), and a card that shows `0%`
//!    for "no reading" is a lie a human cannot tell from a quiet machine.
//! 2. **A wrong type is refused where it is parsed, with the field named.** A
//!    metric that silently became `0.0` would look exactly like a healthy
//!    machine.
//!
//! Arithmetic only: no clock, no I/O, no dependency beyond `core`.

/// The one sentence a card shows when its source reported nothing.
pub const EMPTY_READING: &str = "no reading reported";

/// One metric value with the unit its source reported.
#[derive(Debug, Clone, PartialEq)]
pub struct Metric {
    pub value: f64,
    pub unit: &'static str,
}

/// The four cards' inputs. `None` means "this source did not answer", which
/// is different from a reported zero.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct MetricsSnapshot {
    pub cpu_pct: Option<Metric>,
    pub memory: Option<Metric>,
    pub storage: Option<Metric>,
    pub network: Option<Metric>,
}

impl MetricsSnapshot {
    /// True when no source answered at all: the documented empty state.
    pub fn is_empty(&self) -> bool {
        self.cpu_pct.is_none()
            && self.memory.is_none()
            && self.storage.is_none()
            && self.network.is_none()
    }
}

/// One rendered card's data.
#[derive(Debug, Clone, PartialEq)]
pub struct MetricCard {
    pub title: &'static str,
    /// The big number, or [`EMPTY_READING`] when the source did not answer.
    pub value: String,
    /// The line under the number: its unit, or why it is empty.
    pub detail: String,
    /// True when the card is showing the empty state rather than a reading.
    pub empty: bool,
}

/// Parse one reading. Blank means "not reported" and is an error, not zero;
/// a non-numeric or negative value is refused with the field named.
pub fn parse_metric(field: &str, raw: &str, unit: &'static str) -> Result<Metric, String> {
    let text = raw.trim();
    if text.is_empty() {
        return Err(format!("{field}: {EMPTY_READING}"));
    }
    let value: f64 = text
        .parse()
        .map_err(|_| format!("{field}: not a number: {raw:?}"))?;
    if !value.is_finite() {
        return Err(format!("{field}: must be a finite number, got {raw:?}"));
    }
    if value < 0.0 {
        return Err(format!("{field}: must not be negative, got {raw:?}"));
    }
    Ok(Metric { value, unit })
}

/// Build the snapshot from four raw readings, as a source supplies them.
/// Every field is parsed even after one fails, so a caller sees every bad
/// field at once instead of fixing them one restart at a time.
pub fn parse_snapshot(
    cpu: &str,
    memory: &str,
    storage: &str,
    network: &str,
) -> Result<MetricsSnapshot, Vec<String>> {
    let mut errors = Vec::new();
    let mut take = |field: &str, raw: &str, unit: &'static str| match parse_metric(field, raw, unit) {
        Ok(m) => Some(m),
        Err(e) => {
            errors.push(e);
            None
        }
    };
    let snapshot = MetricsSnapshot {
        cpu_pct: take("cpu", cpu, "%"),
        memory: take("memory", memory, "MiB"),
        storage: take("storage", storage, "GiB"),
        network: take("network", network, "Mbit/s"),
    };
    if errors.is_empty() {
        Ok(snapshot)
    } else {
        Err(errors)
    }
}

fn card(title: &'static str, metric: &Option<Metric>, empty_detail: &str) -> MetricCard {
    match metric {
        None => MetricCard {
            title,
            value: EMPTY_READING.to_string(),
            detail: empty_detail.to_string(),
            empty: true,
        },
        Some(m) => MetricCard {
            title,
            value: format!("{:.1}", m.value),
            detail: m.unit.to_string(),
            empty: false,
        },
    }
}

/// CPU as a percentage of one core's capacity.
pub fn cpu_card(snapshot: &MetricsSnapshot) -> MetricCard {
    card("CPU", &snapshot.cpu_pct, "this source did not answer")
}

/// Memory in use, in MiB.
pub fn memory_card(snapshot: &MetricsSnapshot) -> MetricCard {
    card("Memory", &snapshot.memory, "this source did not answer")
}

/// Storage in use, in GiB.
pub fn storage_card(snapshot: &MetricsSnapshot) -> MetricCard {
    card("Storage", &snapshot.storage, "this source did not answer")
}

/// Network throughput, in Mbit/s.
pub fn network_card(snapshot: &MetricsSnapshot) -> MetricCard {
    card("Network", &snapshot.network, "this source did not answer")
}

/// The four cards, always in the same order, so the dashboard layout never
/// shuffles when one source goes quiet.
pub fn cards(snapshot: &MetricsSnapshot) -> Vec<MetricCard> {
    vec![
        cpu_card(snapshot),
        memory_card(snapshot),
        storage_card(snapshot),
        network_card(snapshot),
    ]
}
