//! T059 [B31] port of `os/tests/test_pomodoro.py` (same name roots).
//!
//! Pomodoro pure core: compound-duration parsing (`send.py`
//! `parse_pomodoro_duration`: `25m`, `1h30m`, `90s`, `2h`, `1d`,
//! `2h 15m`; garbage rejected) and remaining-time formatting
//! (`45`→`"45s"`, `1500`→`"25m"`, `5430`→`"1h 30m 30s"`, `0`→`"0s"`:
//! nonzero components joined, `"0s"` when all zero).
//! The 8 bus/CLI cases need the excluded `relay_common` store +
//! `send`/`poll` CLIs — recorded blocked, never dropped.

pub const CASES: &[&str] = &[
    "parse compound durations",
    "parse rejects garbage",
    "send pomodoro posts and schedules",
    "send pomodoro garbage duration",
    "send pomodoro needs label",
    "send pomodoro exclusive",
    "timecapsule fires done",
    "poll renders active timers",
    "poll prunes expired timers",
    "poll timer room scoped",
    "fmt remaining",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[
    "send pomodoro posts and schedules (needs relay_common store + send CLI)",
    "send pomodoro garbage duration (needs relay_common store + send CLI)",
    "send pomodoro needs label (needs send CLI arg parsing)",
    "send pomodoro exclusive (needs relay_common store + send CLI)",
    "timecapsule fires done (needs relay_common store + timecapsule)",
    "poll renders active timers (needs relay_common store + poll CLI)",
    "poll prunes expired timers (needs relay_common store + poll CLI)",
    "poll timer room scoped (needs relay_common store + poll CLI)",
];

const UNIT_SECS: &[(&str, u64)] = &[("s", 1), ("m", 60), ("h", 3600), ("d", 86400)];

/// `send.parse_pomodoro_duration`: `'25m'`, `'1h30m'`, `'2h 15m'` →
/// seconds. Rejects garbage (unknown units, zero total, trailing junk).
pub fn parse_pomodoro_duration(spec: &str) -> Result<u64, String> {
    let s = spec.trim();
    let bytes = s.as_bytes();
    let mut total: u64 = 0;
    let mut pos = 0;
    let mut any = false;
    while pos < bytes.len() {
        while pos < bytes.len() && bytes[pos].is_ascii_whitespace() {
            pos += 1;
        }
        if pos >= bytes.len() {
            break;
        }
        let start = pos;
        while pos < bytes.len() && bytes[pos].is_ascii_digit() {
            pos += 1;
        }
        if start == pos {
            return Err(format!("not a pomodoro duration (try 25m, 1h30m, 90s): {spec:?}"));
        }
        let num: u64 = s[start..pos].parse().map_err(|_| format!("not a pomodoro duration: {spec:?}"))?;
        while pos < bytes.len() && bytes[pos].is_ascii_whitespace() {
            pos += 1;
        }
        if pos >= bytes.len() {
            return Err(format!("not a pomodoro duration (try 25m, 1h30m, 90s): {spec:?}"));
        }
        let u = bytes[pos].to_ascii_lowercase() as char;
        let secs = UNIT_SECS.iter().find(|(k, _)| *k == u.to_string().as_str()).map(|(_, v)| *v);
        match secs {
            Some(m) => {
                total += num * m;
                pos += 1;
                any = true;
            }
            None => return Err(format!("not a pomodoro duration (try 25m, 1h30m, 90s): {spec:?}")),
        }
    }
    if !any || total == 0 {
        return Err(format!("not a pomodoro duration (try 25m, 1h30m, 90s): {spec:?}"));
    }
    // Trailing junk check: the loop consumes only valid segments;
    // any non-space leftover means a failed parse above. Re-verify by
    // ensuring the whole string was valid segments.
    Ok(total)
}

/// Remaining-time formatting per the pinned vectors.
pub fn fmt_remaining(secs: u64) -> String {
    if secs == 0 {
        return "0s".to_string();
    }
    let (h, m, s) = (secs / 3600, (secs % 3600) / 60, secs % 60);
    let mut parts = vec![];
    if h > 0 {
        parts.push(format!("{h}h"));
    }
    if m > 0 {
        parts.push(format!("{m}m"));
    }
    if s > 0 {
        parts.push(format!("{s}s"));
    }
    parts.join(" ")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_compound_durations() {
        assert_eq!(parse_pomodoro_duration("25m"), Ok(1500));
        assert_eq!(parse_pomodoro_duration("1h30m"), Ok(5400));
        assert_eq!(parse_pomodoro_duration("90s"), Ok(90));
        assert_eq!(parse_pomodoro_duration("2h"), Ok(7200));
        assert_eq!(parse_pomodoro_duration("1d"), Ok(86400));
        assert_eq!(parse_pomodoro_duration("2h 15m"), Ok(8100));
    }

    #[test]
    fn test_parse_rejects_garbage() {
        for bad in ["", "abc", "10x", "1h 2x", "0m", "m", "-5m", "1.5h"] {
            assert!(parse_pomodoro_duration(bad).is_err(), "{bad:?}");
        }
    }

    #[test]
    fn test_fmt_remaining() {
        assert_eq!(fmt_remaining(45), "45s");
        assert_eq!(fmt_remaining(1500), "25m");
        assert_eq!(fmt_remaining(5430), "1h 30m 30s");
        assert_eq!(fmt_remaining(0), "0s");
    }
}
