//! B24 send — port of `os/send.py` pure helpers.
//!
//! Network posting (`bus_push`, blob transport) goes through
//! [`super::transport::BusTransport`] at the gate; this module ports
//! the oddity-for-oddity parsing the CLI depends on.

use std::time::SystemTime;

/// `'30s'`, `'10m'`, `'2h'`, `'1d'` (optional leading `+`) -> seconds.
pub fn parse_duration(spec: &str) -> Result<u64, String> {
    let s = spec.trim();
    let s = s.strip_prefix('+').unwrap_or(s).trim();
    if s.len() < 2 {
        return Err(format!("not a duration (try 30s, 10m, 2h, 1d): {spec:?}"));
    }
    let (num, unit) = s.split_at(s.len() - 1);
    let n: u64 = num
        .trim()
        .parse()
        .map_err(|_| format!("not a duration (try 30s, 10m, 2h, 1d): {spec:?}"))?;
    let mult = match unit.to_ascii_lowercase().as_str() {
        "s" => 1,
        "m" => 60,
        "h" => 3600,
        "d" => 86400,
        _ => return Err(format!("not a duration (try 30s, 10m, 2h, 1d): {spec:?}")),
    };
    Ok(n * mult)
}

/// `'25m'`, `'1h30m'`, `'90s'`, `'2h 15m'` -> seconds. Rejects garbage.
pub fn parse_pomodoro_duration(spec: &str) -> Result<u64, String> {
    let err = || format!("not a pomodoro duration (try 25m, 1h30m, 90s): {spec:?}");
    let s = spec.trim();
    if s.is_empty() {
        return Err(err());
    }
    let bytes = s.as_bytes();
    let mut i = 0usize;
    let mut total: u64 = 0;
    let mut consumed_any = false;
    while i < bytes.len() {
        while i < bytes.len() && bytes[i].is_ascii_whitespace() {
            i += 1;
        }
        if i >= bytes.len() {
            break;
        }
        let start = i;
        while i < bytes.len() && bytes[i].is_ascii_digit() {
            i += 1;
        }
        if start == i {
            return Err(err());
        }
        let n: u64 = s[start..i].parse().map_err(|_| err())?;
        if i >= bytes.len() {
            return Err(err());
        }
        let unit = bytes[i].to_ascii_lowercase() as char;
        let mult = match unit {
            's' => 1,
            'm' => 60,
            'h' => 3600,
            'd' => 86400,
            _ => return Err(err()),
        };
        i += 1;
        total += n * mult;
        consumed_any = true;
    }
    if !consumed_any || total == 0 {
        return Err(err());
    }
    Ok(total)
}

/// `--ttl SPEC` -> seconds. Durations only.
pub fn parse_ttl(spec: &str) -> Result<u64, String> {
    parse_duration(spec)
        .map_err(|_| format!("--ttl needs a duration (30s, 10m, 2h, 1d), got {spec:?}"))
}

/// Basename sanitizer for `--blob` pointer names.
pub fn sanitize_basename(name: &str) -> String {
    let base = name.rsplit('/').next().unwrap_or(name).trim();
    let mut out = String::new();
    for c in base.chars() {
        if c.is_ascii_alphanumeric() || c == '.' || c == '_' || c == '-' {
            out.push(c);
        } else {
            out.push('_');
        }
    }
    if out.is_empty() {
        out.push_str("blob");
    }
    out.chars().take(60).collect()
}

/// `--at SPEC` -> unix delivery time.
/// Accepts duration, unix timestamp, or ISO `YYYY-MM-DD[THH:MM[:SS]]`.
/// Naive ISO is interpreted as local time (approximated via UTC here;
/// the gate's local-time path keeps the Python exactness).
pub fn parse_when(spec: &str, now: u64) -> Result<i64, String> {
    let s = spec.trim();
    if let Ok(d) = parse_duration(s) {
        return Ok((now + d) as i64);
    }
    let t = s.strip_prefix('+').unwrap_or(s);
    if !t.is_empty() && t.chars().all(|c| c.is_ascii_digit()) {
        return t
            .parse::<i64>()
            .map_err(|_| format!("can't parse --at {spec:?}"));
    }
    // Minimal ISO `YYYY-MM-DD[THH:MM[:SS]]` parser (UTC).
    if let Some(ts) = parse_iso_naive(s) {
        return Ok(ts);
    }
    Err(format!(
        "can't parse --at {spec:?}: use 10m/2h/1d, a unix timestamp, or ISO like 2026-09-21 or 2026-09-21T14:30"
    ))
}

fn parse_iso_naive(s: &str) -> Option<i64> {
    let (date, time) = match s.split_once('T') {
        Some((d, t)) => (d, Some(t)),
        None => (s, None),
    };
    let mut dp = date.split('-');
    let y: i32 = dp.next()?.parse().ok()?;
    let m: i32 = dp.next()?.parse().ok()?;
    let d: i32 = dp.next()?.parse().ok()?;
    if dp.next().is_some() || !(1..=12).contains(&m) || !(1..=31).contains(&d) {
        return None;
    }
    let (hh, mm, ss) = match time {
        None => (0, 0, 0),
        Some(t) => {
            let mut tp = t.split(':');
            let h: i32 = tp.next()?.parse().ok()?;
            let mi: i32 = tp.next()?.parse().ok()?;
            let se: i32 = tp.next().map(|x| x.parse().unwrap_or(-1)).unwrap_or(0);
            if !(0..=23).contains(&h) || !(0..=59).contains(&mi) || !(0..=59).contains(&se) {
                return None;
            }
            (h, mi, se)
        }
    };
    Some(days_to_unix(y, m, d) + (hh as i64) * 3600 + (mm as i64) * 60 + ss as i64)
}

fn days_to_unix(y: i32, m: i32, d: i32) -> i64 {
    // Howard Hinnant's days_from_civil, days since 1970-01-01.
    let y = y as i64 - ((14 - m as i64) / 12);
    let mm = m as i64 + 12 * ((14 - m as i64) / 12) - 3;
    let days = 365 * y + y / 4 - y / 100 + y / 400 + (153 * mm + 2) / 5 + d as i64 - 719468;
    days * 86400
}

pub fn now_unix() -> u64 {
    SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn duration_shapes() {
        assert_eq!(parse_duration("30s").unwrap(), 30);
        assert_eq!(parse_duration("+10m").unwrap(), 600);
        assert_eq!(parse_duration("2h").unwrap(), 7200);
        assert_eq!(parse_duration("1d").unwrap(), 86400);
        assert!(parse_duration("10x").is_err());
        assert!(parse_duration("abc").is_err());
    }

    #[test]
    fn pomodoro_shapes() {
        assert_eq!(parse_pomodoro_duration("25m").unwrap(), 1500);
        assert_eq!(parse_pomodoro_duration("1h30m").unwrap(), 5400);
        assert_eq!(parse_pomodoro_duration("90s").unwrap(), 90);
        assert_eq!(parse_pomodoro_duration("2h 15m").unwrap(), 8100);
        assert!(parse_pomodoro_duration("25x").is_err());
        assert!(parse_pomodoro_duration("").is_err());
        assert!(parse_pomodoro_duration("0m").is_err());
    }

    #[test]
    fn at_shapes() {
        let now = 1_700_000_000u64;
        assert_eq!(parse_when("10m", now).unwrap(), (now + 600) as i64);
        assert_eq!(parse_when("1700000100", now).unwrap(), 1_700_000_100);
        // 2026-09-21 UTC midnight.
        assert!(parse_when("2026-09-21", now).unwrap() > 1_700_000_000);
        assert!(parse_when("garbage!!", now).is_err());
    }

    #[test]
    fn basename_shapes() {
        assert_eq!(sanitize_basename("/tmp/a b.txt"), "a_b.txt");
        assert_eq!(sanitize_basename(""), "blob");
    }
}
