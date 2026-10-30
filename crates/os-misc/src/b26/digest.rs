//! B26 digest — port of `os/digest.py` pure stats.

use std::collections::HashMap;

pub const PAGE: usize = 1000;
pub const TOP_N: usize = 5;

/// Count messages + top talkers over bus lines.
pub fn talker_stats(lines: &[String]) -> (usize, Vec<(String, usize)>) {
    let mut counts: HashMap<String, usize> = HashMap::new();
    for line in lines {
        if let Some((nick, _)) = line.split_once(": ") {
            if !nick.is_empty() {
                *counts.entry(nick.to_string()).or_insert(0) += 1;
            }
        }
    }
    let total = lines.len();
    let mut top: Vec<(String, usize)> = counts.into_iter().collect();
    top.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(&b.0)));
    top.truncate(TOP_N);
    (total, top)
}

pub fn validate_hours(hours: f64) -> Result<(), String> {
    if hours <= 0.0 {
        return Err("--hours must be positive".to_string());
    }
    Ok(())
}

pub fn fmt_hour(hour: Option<u32>) -> String {
    match hour {
        Some(h) => format!("{h:02}:00"),
        None => "n/a".to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn talkers_and_hours() {
        let lines = vec!["milo: a".to_string(), "milo: b".to_string(), "pax: c".to_string()];
        let (total, top) = talker_stats(&lines);
        assert_eq!(total, 3);
        assert_eq!(top[0], ("milo".to_string(), 2));
        assert!(validate_hours(24.0).is_ok());
        assert!(validate_hours(0.0).is_err());
        assert_eq!(fmt_hour(Some(9)), "09:00");
        assert_eq!(fmt_hour(None), "n/a");
    }
}
