//! B31 `acceptance` — port of `os/mos/acceptance.py`.
//!
//! `accept` field: one check per line (`file-exists`, `tests-pass`,
//! `command-ok`, `contains: path :: substring`). Unparseable = failed
//! check, never skipped.

#[derive(Debug, Clone, PartialEq)]
pub struct Check {
    pub kind: String,
    pub arg: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct CheckResult {
    pub check: String,
    pub ok: bool,
    pub detail: String,
}

/// Parse accept text into checks. Raises (Err) on bad lines.
pub fn parse_accept(text: &str) -> Result<Vec<Check>, String> {
    let mut out = vec![];
    for (lineno, raw) in text.lines().enumerate() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let Some((kind, arg)) = line.split_once(':') else {
            return Err(format!("line {}: no ':' separator: {line:?}", lineno + 1));
        };
        let kind = kind.trim().to_lowercase();
        let arg = arg.trim().to_string();
        if !["file-exists", "tests-pass", "command-ok", "contains"].contains(&kind.as_str()) {
            return Err(format!("line {}: unknown check {kind:?}", lineno + 1));
        }
        if arg.is_empty() {
            return Err(format!("line {}: empty argument", lineno + 1));
        }
        if kind == "contains" && !arg.contains("::") {
            return Err(format!("line {}: contains needs 'path :: substring'", lineno + 1));
        }
        out.push(Check { kind, arg });
    }
    Ok(out)
}

/// `tests/test_x.py` -> `tests.test_x`; passthrough otherwise.
pub fn mod_name(target: &str) -> String {
    let mut t = target.trim().to_string();
    if let Some(s) = t.strip_suffix(".py") {
        t = s.to_string();
    }
    t.replace('/', ".").replace('\\', ".")
}

/// Empty accept text -> (true, note). Parse error -> (false, parse result).
pub fn verify_shape(accept_text: &str) -> (bool, Vec<CheckResult>) {
    if accept_text.trim().is_empty() {
        return (
            true,
            vec![CheckResult {
                check: "(no acceptance criteria)".to_string(),
                ok: true,
                detail: "nothing to verify".to_string(),
            }],
        );
    }
    match parse_accept(accept_text) {
        Ok(checks) if checks.is_empty() => (
            true,
            vec![CheckResult {
                check: "(no acceptance criteria)".to_string(),
                ok: true,
                detail: "nothing to verify".to_string(),
            }],
        ),
        Ok(_) => (false, vec![]), // live run happens at the gate
        Err(e) => (
            false,
            vec![CheckResult {
                check: "(parse)".to_string(),
                ok: false,
                detail: e,
            }],
        ),
    }
}

pub fn format_report(results: &[CheckResult]) -> String {
    results
        .iter()
        .map(|r| format!("[{}] {} -- {}", if r.ok { "PASS" } else { "FAIL" }, r.check, r.detail))
        .collect::<Vec<_>>()
        .join("\n")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_shapes() {
        let cs = parse_accept("file-exists: a.py\n# c\ntests-pass: tests/test_x.py").unwrap();
        assert_eq!(cs.len(), 2);
        assert!(parse_accept("no-colon").is_err());
        assert!(parse_accept("bogus: x").is_err());
        assert!(parse_accept("contains: onlypath").is_err());
        assert_eq!(mod_name("tests/test_x.py"), "tests.test_x");
    }

    #[test]
    fn empty_and_bad() {
        assert!(verify_shape("").0);
        assert!(!verify_shape("bogus: x").0);
    }
}
