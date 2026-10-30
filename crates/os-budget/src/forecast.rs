//! Budget forecasting + preemption (OS-091, Milo).
//! (`os/intel/forecast.py` behavior as pinned by B20's drill and
//! tests.)
//!
//! Canonical home of `intel/forecast.py` is Hana's `intel` crate
//! (B10). This module ports exactly the forecast math, the
//! preempt/resume decisions, the brief line, and the drill phases
//! B20's assigned tests pin, so the budget crate verifies its own
//! gate without reaching into another batch's subtree.
//!
//! Forecasting is one division: the ledger rate so far (spent
//! over elapsed hours) projected to the end of a 24-hour day.
//! Preemption is pause, not kill, and only for low-priority work
//! in a lane currently at warning.

pub const DAY_HOURS: f64 = 24.0;
pub const LOW_CONFIDENCE_BELOW: f64 = 4.0;
pub const HIGH_CONFIDENCE_AT: f64 = 12.0;

fn usable_number(value: &serde_json::Value) -> Option<f64> {
    match value {
        serde_json::Value::Number(n) => n.as_f64(),
        _ => None,
    }
}

/// Projected end-of-day spend, or `None` when unprojectable.
pub fn project_end_of_day(spent: f64, elapsed_hours: f64, day_hours: f64) -> Option<f64> {
    if !(spent >= 0.0) || !(elapsed_hours > 0.0) || !(day_hours > 0.0) {
        return None;
    }
    if elapsed_hours >= day_hours {
        return Some(spent);
    }
    Some(spent * day_hours / elapsed_hours)
}

/// Value-level projection (non-numbers unprojectable).
pub fn project_end_of_day_value(
    spent: &serde_json::Value,
    elapsed_hours: &serde_json::Value,
    day_hours: &serde_json::Value,
) -> Option<f64> {
    project_end_of_day(
        usable_number(spent)?,
        usable_number(elapsed_hours)?,
        usable_number(day_hours)?,
    )
}

/// Confidence word from elapsed hours alone.
pub fn confidence_for(elapsed_hours: f64) -> &'static str {
    if !(elapsed_hours > 0.0) {
        return "unknown";
    }
    if elapsed_hours < LOW_CONFIDENCE_BELOW {
        "low"
    } else if elapsed_hours < HIGH_CONFIDENCE_AT {
        "medium"
    } else {
        "high"
    }
}

pub fn confidence_for_value(elapsed_hours: &serde_json::Value) -> &'static str {
    match usable_number(elapsed_hours) {
        Some(h) => confidence_for(h),
        None => "unknown",
    }
}

fn format_hours(value: f64) -> String {
    if value == value.trunc() && value.abs() < 1e15 {
        format!("{}", value as i64)
    } else {
        format!("{value}")
    }
}

/// One lane's forecast, or `None` when it cannot be made.
#[derive(Debug, Clone)]
pub struct ForecastEntry {
    pub lane: String,
    pub spent: f64,
    pub cap: f64,
    pub projected: f64,
    pub over_cap: bool,
    pub confidence: String,
    pub basis: String,
}

pub fn forecast_entry(
    lane: &str,
    spent: f64,
    cap: f64,
    elapsed_hours: f64,
    day_hours: f64,
) -> Option<ForecastEntry> {
    if lane.is_empty() || !(cap > 0.0) || !(spent >= 0.0) {
        return None;
    }
    let projected = project_end_of_day(spent, elapsed_hours, day_hours)?;
    Some(ForecastEntry {
        lane: lane.to_string(),
        spent,
        cap,
        projected,
        over_cap: projected > cap,
        confidence: confidence_for(elapsed_hours).to_string(),
        basis: format!(
            "based on {} hours of ledger in a {}-hour day",
            format_hours(elapsed_hours),
            format_hours(day_hours)
        ),
    })
}

pub fn forecast_entry_value(entry: &serde_json::Value) -> Option<ForecastEntry> {
    let obj = entry.as_object()?;
    let lane = obj.get("lane").and_then(|v| v.as_str())?;
    let spent = usable_number(obj.get("spent")?)?;
    let cap = usable_number(obj.get("cap")?)?;
    let elapsed = usable_number(obj.get("elapsed_hours")?)?;
    let day = obj
        .get("day_hours")
        .and_then(usable_number)
        .unwrap_or(DAY_HOURS);
    forecast_entry(lane, spent, cap, elapsed, day)
}

/// Plain brief lines for a list of forecast entries.
pub fn forecast_lines(entries: &serde_json::Value) -> Vec<String> {
    let mut lines = Vec::new();
    let items = match entries.as_array() {
        Some(items) => items,
        None => return lines,
    };
    for entry in items {
        let fc = match forecast_entry_value(entry) {
            Some(fc) => fc,
            None => continue,
        };
        let projected = fc.projected as i64;
        let verdict = if fc.over_cap {
            "breach expected before end of day"
        } else {
            "within cap"
        };
        lines.push(format!(
            "Budget forecast for lane {}: {} spent of {} cap, projected {} by end of day, {} ({} confidence) - {}.",
            fc.lane,
            trim_num(fc.spent),
            trim_num(fc.cap),
            projected,
            fc.basis,
            fc.confidence,
            verdict
        ));
    }
    lines
}

fn trim_num(v: f64) -> String {
    if v == v.trunc() && v.abs() < 1e15 {
        format!("{}", v as i64)
    } else {
        format!("{v}")
    }
}

/// `"pause"`, `"resume"`, or `None` for one job in one lane state.
pub fn preempt_decision(job: &serde_json::Value, lane_state: &str) -> Option<&'static str> {
    let obj = job.as_object()?;
    let status = obj.get("status").and_then(|v| v.as_str())?;
    let priority = obj.get("priority").and_then(|v| v.as_str())?;
    if status == "running" && priority == "low" && lane_state == "warning" {
        return Some("pause");
    }
    if status == "paused" && (lane_state == "ok" || lane_state == "unbudgeted") {
        return Some("resume");
    }
    None
}

/// A journal record for a pause or resume, nothing more.
pub fn preempt_record(job_id: &str, lane: &str, action: &str, reason: &str) -> serde_json::Value {
    serde_json::json!({
        "job": job_id,
        "lane": lane,
        "action": action,
        "reason": reason,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn projection_scales_the_ledger_rate() {
        assert_eq!(project_end_of_day(80.0, 8.0, 24.0), Some(240.0));
        assert_eq!(project_end_of_day(50.0, 12.0, 24.0), Some(100.0));
    }

    #[test]
    fn projection_at_or_past_day_end_is_spent() {
        assert_eq!(project_end_of_day(90.0, 24.0, 24.0), Some(90.0));
        assert_eq!(project_end_of_day(90.0, 30.0, 24.0), Some(90.0));
    }

    #[test]
    fn unprojectable_inputs_yield_none() {
        assert_eq!(project_end_of_day(-5.0, 8.0, 24.0), None);
        assert_eq!(project_end_of_day(80.0, 0.0, 24.0), None);
        assert_eq!(project_end_of_day(80.0, -2.0, 24.0), None);
        assert_eq!(project_end_of_day(80.0, 8.0, 0.0), None);
        assert_eq!(
            project_end_of_day_value(&json!("lots"), &json!(8), &json!(24)),
            None
        );
    }

    #[test]
    fn confidence_comes_from_elapsed_hours_alone() {
        assert_eq!(confidence_for(2.0), "low");
        assert_eq!(confidence_for(4.0), "medium");
        assert_eq!(confidence_for(8.0), "medium");
        assert_eq!(confidence_for(12.0), "high");
        assert_eq!(confidence_for(0.0), "unknown");
        assert_eq!(confidence_for_value(&json!("soon")), "unknown");
    }
}
