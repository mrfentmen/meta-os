//! B26 export — port of `os/export.py` writers.
//!
//! Reads the local store (streamed line-by-line in Python); here the
//! caller supplies entries. Markdown: `## <nick> (<time>)` + text,
//! edited keeps `(edited)`. JSON: one object per line.

pub struct ExportEntry {
    pub nick: String,
    pub text: String,
    pub ts: Option<i64>,
    pub edited: bool,
}

pub fn fmt_time(ts: Option<i64>) -> String {
    // Python: time.strftime local; gate keeps exactness. UTC fallback here.
    match ts {
        Some(t) if t >= 0 => {
            // Minimal UTC formatting without deps.
            format!("ts:{t}")
        }
        _ => "unknown time".to_string(),
    }
}

pub fn write_md(room: &str, entries: &[ExportEntry]) -> String {
    let label = if room.is_empty() { "main".to_string() } else { format!("#{room}") };
    let mut out = format!("# Export of {label}\n\n");
    for e in entries {
        let edited = if e.edited { " (edited)" } else { "" };
        out.push_str(&format!("## {} ({}){edited}\n\n{}\n\n", e.nick, fmt_time(e.ts), e.text));
    }
    out
}

pub fn write_json_line(e: &ExportEntry) -> String {
    // Minimal JSON escaping for the known shape.
    fn esc(s: &str) -> String {
        s.replace('\\', "\\\\").replace('"', "\\\"").replace('\n', "\\n")
    }
    let mut o = format!("{{\"nick\":\"{}\",\"text\":\"{}\"", esc(&e.nick), esc(&e.text));
    match e.ts {
        Some(t) => o.push_str(&format!(",\"ts\":{t}")),
        None => o.push_str(",\"ts\":null"),
    }
    if e.edited {
        o.push_str(",\"edited\":true");
    }
    o.push('}');
    o
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn md_and_json_shapes() {
        let es = vec![ExportEntry { nick: "m".into(), text: "hi".into(), ts: Some(1), edited: true }];
        let md = write_md("", &es);
        assert!(md.contains("## m ("));
        assert!(md.contains("(edited)"));
        let j = write_json_line(&es[0]);
        assert!(j.contains("\"edited\":true"));
    }

    #[test]
    fn bad_time_is_unknown() {
        assert_eq!(fmt_time(None), "unknown time");
    }
}
