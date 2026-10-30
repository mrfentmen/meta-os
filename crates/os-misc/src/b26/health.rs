//! B26 health — port of `os/health.py` text shaping.
//!
//! Posts `<nick>: HEALTH cpu=..% mem=..% disk=..% up=.. load=..`
//! through the normal send path. Stats are dependency-free.

/// `uptime_str` port: 3d4h12m shape (`{d}d{h}h{m}m`, omits zero units).
pub fn uptime_str(total_secs: u64) -> String {
    let d = total_secs / 86400;
    let h = (total_secs % 86400) / 3600;
    let m = (total_secs % 3600) / 60;
    let mut s = format!("{m}m");
    if h != 0 || d != 0 {
        s = format!("{h}h{s}");
    }
    if d != 0 {
        s = format!("{d}d{s}");
    }
    s
}

/// HEALTH line body.
pub fn health_text(cpu: f64, mem: f64, disk: f64, up: &str, load: f64) -> String {
    format!("HEALTH cpu={cpu:.0}% mem={mem:.0}% disk={disk:.0}% up={up} load={load:.2}")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn uptime_shapes() {
        assert_eq!(uptime_str(5 * 60), "5m");
        assert_eq!(uptime_str(3 * 3600 + 12 * 60), "3h12m");
        // 3d4h12m.
        assert_eq!(uptime_str(3 * 86400 + 4 * 3600 + 12 * 60), "3d4h12m");
    }

    #[test]
    fn line_shape() {
        let t = health_text(12.4, 45.6, 70.1, "3d4h12m", 0.42);
        assert!(t.starts_with("HEALTH cpu=12%"));
        assert!(t.contains("load=0.42"));
    }
}
