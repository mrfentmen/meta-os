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
}
