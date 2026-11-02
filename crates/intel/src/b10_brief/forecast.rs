//! Port of `os/intel/forecast.py` — end-of-day budget forecasting.
//!
//! Projects spend from usable numbers only (bools/NaN/negatives are not
//! numbers); confidence degrades with missing inputs; preemption trips
//! when projected spend crosses the cap.

pub fn usable_number(v: f64) -> Option<f64> {
    if v.is_finite() && v >= 0.0 {
        Some(v)
    } else {
        None
    }
}

pub fn project_end_of_day(spent: f64, rate_per_hour: f64, hours_left: f64) -> Option<f64> {
    Some(usable_number(spent)? + usable_number(rate_per_hour)? * usable_number(hours_left)?)
}

pub fn confidence_for(missing_inputs: usize) -> &'static str {
    match missing_inputs {
        0 => "high",
        1 => "medium",
        _ => "low",
    }
}

pub fn forecast_entry(label: String, projected: f64, cap: f64) -> String {
    format!("{label}: projected {projected:.2} vs cap {cap:.2}")
}

pub fn preempt_decision(projected: f64, cap: f64) -> bool {
    projected > cap
}

/// One lane's raw forecast input, mirroring the dict `forecast_lines`
/// reads in Python (`os/intel/forecast.py`): lane, spent, cap,
/// elapsed_hours, and day_hours (Python defaults it to 24).
pub struct ForecastInput {
    pub lane: String,
    pub spent: f64,
    pub cap: f64,
    pub elapsed_hours: f64,
    pub day_hours: f64,
}

/// Python `_format_hours`: an integral float prints as an integer.
fn format_hours(value: f64) -> String {
    if value.fract() == 0.0 && value.is_finite() {
        format!("{value:.0}")
    } else {
        format!("{value}")
    }
}

/// Python `str(float)` for a spent/cap figure: an integral float keeps
/// its `.0` (50.0, not 50). Rust's Display would drop it.
fn format_amount(value: f64) -> String {
    if value.fract() == 0.0 && value.is_finite() {
        format!("{value:.0}.0")
    } else {
        format!("{value}")
    }
}

/// Plain brief lines for a list of forecast entries, ported from
/// Python `forecast_lines`.
///
/// Each usable entry yields one line: lane, spent, cap, projected
/// end-of-day spend rounded DOWN to a whole number (a forecast is an
/// estimate; rounding up would overstate it), the basis sentence, the
/// confidence word from elapsed hours alone (low under 4, medium from
/// 4 to under 12, high at 12 or more), and "breach expected before end
/// of day" when the projection passes the cap, else "within cap".
/// Unusable entries are skipped, never guessed; an empty input yields
/// no lines. Lines are not bullets, so the BRF-007 trim keeps them.
///
/// NOTE: this deliberately does NOT reuse the sketch `project_end_of_day`
/// / `confidence_for` above — those carry different, parity-pinned
/// semantics (spent + rate * hours; confidence from a missing-input
/// count). Unifying them would break `b10_parity.rs`. The formulas
/// here are Python's own: projected = spent * day_hours / elapsed_hours,
/// or spent itself once elapsed reaches the full day.
pub fn forecast_lines(entries: &[ForecastInput]) -> Vec<String> {
    let mut lines = Vec::new();
    for entry in entries {
        if entry.lane.is_empty() {
            continue;
        }
        if !entry.cap.is_finite() || entry.cap <= 0.0 {
            continue;
        }
        if !entry.spent.is_finite() || entry.spent < 0.0 {
            continue;
        }
        if !entry.elapsed_hours.is_finite() || entry.elapsed_hours <= 0.0 {
            continue;
        }
        if !entry.day_hours.is_finite() || entry.day_hours <= 0.0 {
            continue;
        }
        let projected = if entry.elapsed_hours >= entry.day_hours {
            entry.spent
        } else {
            entry.spent * entry.day_hours / entry.elapsed_hours
        };
        if !projected.is_finite() {
            continue;
        }
        let projected_int = projected as i64;
        let confidence = if entry.elapsed_hours < 4.0 {
            "low"
        } else if entry.elapsed_hours < 12.0 {
            "medium"
        } else {
            "high"
        };
        let basis = format!(
            "based on {} hours of ledger in a {}-hour day",
            format_hours(entry.elapsed_hours),
            format_hours(entry.day_hours)
        );
        let verdict = if projected > entry.cap {
            "breach expected before end of day"
        } else {
            "within cap"
        };
        lines.push(format!(
            "Budget forecast for lane {}: {} spent of {} cap, projected {} by end of day, {} ({} confidence) - {}.",
            entry.lane,
            format_amount(entry.spent),
            format_amount(entry.cap),
            projected_int,
            basis,
            confidence,
            verdict
        ));
    }
    lines
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn nan_is_unusable() {
        assert_eq!(usable_number(f64::NAN), None);
        assert_eq!(usable_number(-1.0), None);
        assert_eq!(usable_number(2.0), Some(2.0));
    }
    #[test]
    fn projection_math() {
        assert_eq!(project_end_of_day(10.0, 5.0, 2.0), Some(20.0));
    }
    #[test]
    fn preempt_trips_over_cap() {
        assert!(preempt_decision(80.0, 75.0));
        assert!(!preempt_decision(70.0, 75.0));
    }
    #[test]
    fn forecast_lines_breach_medium_confidence() {
        let entries = [ForecastInput {
            lane: "vigiles".to_string(),
            spent: 50.0,
            cap: 100.0,
            elapsed_hours: 6.0,
            day_hours: 24.0,
        }];
        assert_eq!(
            forecast_lines(&entries),
            vec!["Budget forecast for lane vigiles: 50.0 spent of 100.0 cap, projected 200 by end of day, based on 6 hours of ledger in a 24-hour day (medium confidence) - breach expected before end of day.".to_string()]
        );
    }
    #[test]
    fn forecast_lines_within_cap_high_confidence() {
        let entries = [ForecastInput {
            lane: "ignis".to_string(),
            spent: 10.0,
            cap: 100.0,
            elapsed_hours: 12.0,
            day_hours: 24.0,
        }];
        assert_eq!(
            forecast_lines(&entries),
            vec!["Budget forecast for lane ignis: 10.0 spent of 100.0 cap, projected 20 by end of day, based on 12 hours of ledger in a 24-hour day (high confidence) - within cap.".to_string()]
        );
    }
    #[test]
    fn forecast_lines_truncates_projection_down() {
        // 10 * 10 / 3 = 33.33... -> 33, never rounded up to 34.
        let entries = [ForecastInput {
            lane: "medicus".to_string(),
            spent: 10.0,
            cap: 1000.0,
            elapsed_hours: 3.0,
            day_hours: 10.0,
        }];
        assert_eq!(
            forecast_lines(&entries),
            vec!["Budget forecast for lane medicus: 10.0 spent of 1000.0 cap, projected 33 by end of day, based on 3 hours of ledger in a 10-hour day (low confidence) - within cap.".to_string()]
        );
    }
    #[test]
    fn forecast_lines_full_day_projects_spent_itself() {
        let entries = [ForecastInput {
            lane: "vigiles".to_string(),
            spent: 30.0,
            cap: 100.0,
            elapsed_hours: 24.0,
            day_hours: 24.0,
        }];
        assert_eq!(
            forecast_lines(&entries),
            vec!["Budget forecast for lane vigiles: 30.0 spent of 100.0 cap, projected 30 by end of day, based on 24 hours of ledger in a 24-hour day (high confidence) - within cap.".to_string()]
        );
    }
    #[test]
    fn forecast_lines_skips_unusable_entries() {
        let entries = [
            ForecastInput { lane: "".to_string(), spent: 10.0, cap: 100.0, elapsed_hours: 6.0, day_hours: 24.0 },
            ForecastInput { lane: "a".to_string(), spent: 10.0, cap: 0.0, elapsed_hours: 6.0, day_hours: 24.0 },
            ForecastInput { lane: "b".to_string(), spent: -5.0, cap: 100.0, elapsed_hours: 6.0, day_hours: 24.0 },
            ForecastInput { lane: "c".to_string(), spent: 10.0, cap: 100.0, elapsed_hours: 0.0, day_hours: 24.0 },
            ForecastInput { lane: "d".to_string(), spent: 10.0, cap: 100.0, elapsed_hours: 6.0, day_hours: 0.0 },
        ];
        assert!(forecast_lines(&entries).is_empty());
        assert!(forecast_lines(&[]).is_empty());
    }
}
