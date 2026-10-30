//! Port of `os/intel/security_pass.py` — INT-011: security
//! pass scanner over the working tree.
//!
//! Scans a tree for committed secrets: provider token shapes,
//! private key headers, quoted credential assignments, and
//! secret filenames. Prints only file, line, and kind — never
//! a matched value. A shape-shaped hit is a fixture, not a
//! finding, only under the source's four stated rules, checked
//! in order (repeated-char value; dummy word in the value;
//! ascending sequential run of 6+; label word on the line
//! outside the match). Keyring lines are deliberately NOT
//! content-scanned (see the source docstring); the *.keyring
//! filename rule carries that control.
//!
//! The Python patterns are `re` patterns; the workspace is
//! std-only, so each pattern is a hand-rolled scanner with
//! the same leftmost-match, greedy-quantifier semantics for
//! these shapes.

use std::path::{Path, PathBuf};

pub const SKIP_DIRS: [&str; 3] = [".git", "__pycache__", "node_modules"];

pub const PATTERN_KINDS: [&str; 7] = [
    "github-token",
    "github-fine-grained-token",
    "api-key",
    "aws-access-key-id",
    "bearer-token",
    "private-key",
    "credential-assignment",
];

pub const DUMMY_WORDS: [&str; 8] = [
    "drill",
    "dummy",
    "fake",
    "example",
    "placeholder",
    "sample",
    "test",
    "secret",
];

/// Narrower than DUMMY_WORDS by design: secret/test never
/// label a value fake from the line around it.
pub const LINE_WORDS: [&str; 6] = [
    "drill",
    "dummy",
    "fake",
    "example",
    "placeholder",
    "sample",
];

fn is_alnum(c: char) -> bool {
    c.is_ascii_alphanumeric()
}

fn is_token_char(c: char) -> bool {
    c.is_ascii_alphanumeric() || c == '.' || c == '_' || c == '-'
}

/// Longest run of `pred` chars starting at byte index `from`
/// in the char vector; returns the end index.
fn run_end(chars: &[char], from: usize, pred: fn(char) -> bool) -> usize {
    let mut i = from;
    while i < chars.len() && pred(chars[i]) {
        i += 1;
    }
    i
}

fn slice(chars: &[char], from: usize, to: usize) -> String {
    chars[from..to].iter().collect()
}

fn find_sub_from(chars: &[char], needle: &[char], from: usize) -> Option<usize> {
    if needle.is_empty() || chars.len() < needle.len() {
        return None;
    }
    let mut i = from;
    while i + needle.len() <= chars.len() {
        if &chars[i..i + needle.len()] == needle {
            return Some(i);
        }
        i += 1;
    }
    None
}

fn find_sub(chars: &[char], needle: &str) -> Option<usize> {
    let n: Vec<char> = needle.chars().collect();
    find_sub_from(chars, &n, 0)
}

/// The pattern scanners: each returns the matched text of the
/// leftmost match on the line, like `re.search(...).group(0)`.
mod patterns {
    use super::*;

    /// (?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}
    pub fn github_token(chars: &[char]) -> Option<String> {
        for (i, _) in chars.iter().enumerate() {
            for prefix in ["ghp_", "gho_", "ghu_", "ghs_", "ghr_"] {
                let p: Vec<char> = prefix.chars().collect();
                if i + p.len() <= chars.len() && chars[i..i + p.len()] == p[..] {
                    let end = run_end(chars, i + p.len(), is_alnum);
                    if end - (i + p.len()) >= 20 {
                        return Some(slice(chars, i, end));
                    }
                }
            }
        }
        None
    }

    /// github_pat_[A-Za-z0-9_]{20,}
    pub fn github_fine_grained(chars: &[char]) -> Option<String> {
        let mut from = 0;
        while let Some(i) = find_sub_from(chars, &"github_pat_".chars().collect::<Vec<_>>(), from) {
            let start = i + "github_pat_".len();
            let end = run_end(chars, start, |c| is_alnum(c) || c == '_');
            if end - start >= 20 {
                return Some(slice(chars, i, end));
            }
            from = i + 1;
        }
        None
    }

    /// sk-[A-Za-z0-9]{20,}
    pub fn api_key(chars: &[char]) -> Option<String> {
        let mut from = 0;
        while let Some(i) = find_sub_from(chars, &"sk-".chars().collect::<Vec<_>>(), from) {
            let start = i + 3;
            let end = run_end(chars, start, is_alnum);
            if end - start >= 20 {
                return Some(slice(chars, i, end));
            }
            from = i + 1;
        }
        None
    }

    /// AKIA[0-9A-Z]{16} — exactly 16.
    pub fn aws_access_key_id(chars: &[char]) -> Option<String> {
        let mut from = 0;
        while let Some(i) = find_sub_from(chars, &"AKIA".chars().collect::<Vec<_>>(), from) {
            let start = i + 4;
            let mut end = start;
            while end < chars.len()
                && end - start < 16
                && (chars[end].is_ascii_digit() || chars[end].is_ascii_uppercase())
            {
                end += 1;
            }
            if end - start == 16 {
                return Some(slice(chars, i, end));
            }
            from = i + 1;
        }
        None
    }

    /// Bearer\s+[A-Za-z0-9._\-]{10,}
    pub fn bearer_token(chars: &[char]) -> Option<String> {
        let mut from = 0;
        while let Some(i) = find_sub_from(chars, &"Bearer".chars().collect::<Vec<_>>(), from) {
            let mut j = i + "Bearer".len();
            let ws_start = j;
            while j < chars.len() && chars[j].is_whitespace() {
                j += 1;
            }
            if j > ws_start {
                let end = run_end(chars, j, is_token_char);
                if end - j >= 10 {
                    return Some(slice(chars, i, end));
                }
            }
            from = i + 1;
        }
        None
    }

    /// -----BEGIN [A-Z ]*PRIVATE KEY-----
    pub fn private_key(chars: &[char]) -> Option<String> {
        let mut from = 0;
        let head: Vec<char> = "-----BEGIN ".chars().collect();
        while let Some(i) = find_sub_from(chars, &head, from) {
            let start = i + head.len();
            let mut j = start;
            while j < chars.len()
                && (chars[j].is_ascii_uppercase() || chars[j] == ' ')
            {
                j += 1;
            }
            // Backtrack the [A-Z ]* so "PRIVATE KEY-----" can match.
            let tail: Vec<char> = "PRIVATE KEY-----".chars().collect();
            let mut k = j;
            loop {
                if k + tail.len() <= chars.len() && chars[k..k + tail.len()] == tail[..] {
                    return Some(slice(chars, i, k + tail.len()));
                }
                if k == start {
                    break;
                }
                k -= 1;
            }
            from = i + 1;
        }
        None
    }

    /// (?i)(?:api[_-]?key|access[_-]?token|secret|password)
    /// \s*[:=]\s*["'][^"'\s]{8,}["']
    pub fn credential_assignment(chars: &[char]) -> Option<String> {
        let lowered: Vec<char> = chars
            .iter()
            .flat_map(|c| c.to_lowercase())
            .collect();
        // Case-insensitive matching runs on the lowered line;
        // lengths agree for the ASCII shapes at stake.
        let keywords: [&str; 6] = [
            "api_key", "api-key", "apikey", "access_token", "access-token",
            "accesstoken",
        ];
        let plain: [&str; 2] = ["secret", "password"];
        let total = lowered.len().min(chars.len());
        for i in 0..total {
            let mut kw_len: Option<usize> = None;
            for kw in keywords.iter().chain(plain.iter()) {
                let k: Vec<char> = kw.chars().collect();
                if i + k.len() <= total && lowered[i..i + k.len()] == k[..] {
                    kw_len = Some(k.len());
                    break;
                }
            }
            let kw_len = match kw_len {
                Some(n) => n,
                None => continue,
            };
            let mut j = i + kw_len;
            while j < total && chars[j].is_whitespace() {
                j += 1;
            }
            if j >= total || (chars[j] != ':' && chars[j] != '=') {
                continue;
            }
            j += 1;
            while j < total && chars[j].is_whitespace() {
                j += 1;
            }
            if j >= total || (chars[j] != '"' && chars[j] != '\'') {
                continue;
            }
            j += 1;
            let value_start = j;
            while j < total
                && chars[j] != '"'
                && chars[j] != '\''
                && !chars[j].is_whitespace()
            {
                j += 1;
            }
            if j - value_start < 8 {
                continue;
            }
            if j < total && (chars[j] == '"' || chars[j] == '\'') {
                return Some(slice(chars, i, j + 1));
            }
        }
        None
    }
}

/// One pattern hit, in PATTERNS order: (kind, match text).
fn search_line(line: &str) -> Vec<(&'static str, String)> {
    let chars: Vec<char> = line.chars().collect();
    let scanners: [(&'static str, fn(&[char]) -> Option<String>); 7] = [
        ("github-token", patterns::github_token),
        ("github-fine-grained-token", patterns::github_fine_grained),
        ("api-key", patterns::api_key),
        ("aws-access-key-id", patterns::aws_access_key_id),
        ("bearer-token", patterns::bearer_token),
        ("private-key", patterns::private_key),
        ("credential-assignment", patterns::credential_assignment),
    ];
    let mut out = Vec::new();
    for (kind, scan) in scanners {
        if let Some(m) = scan(&chars) {
            out.push((kind, m));
        }
    }
    out
}

/// `_value_of`: the credential part of a match, prefix
/// stripped (the _PREFIX_RE alternation, anchored, one pass).
fn value_of(match_text: &str) -> String {
    let chars: Vec<char> = match_text.chars().collect();
    for prefix in ["ghp_", "gho_", "ghu_", "ghs_", "ghr_", "github_pat_", "sk-", "AKIA"] {
        if match_text.starts_with(prefix) {
            return match_text[prefix.len()..].to_string();
        }
    }
    if match_text.starts_with("Bearer") {
        let mut j = "Bearer".len();
        while j < chars.len() && chars[j].is_whitespace() {
            j += 1;
        }
        if j > "Bearer".len() {
            return slice(&chars, j, chars.len());
        }
    }
    match_text.to_string()
}

/// `_has_sequential_run`: six ascending letters or digits.
fn has_sequential_run(value: &str) -> bool {
    let lowered = value.to_lowercase();
    for seq in ["abcdefghijklmnopqrstuvwxyz", "0123456789"] {
        let s: Vec<char> = seq.chars().collect();
        for start in 0..(s.len() - 5) {
            let window: String = s[start..start + 6].iter().collect();
            if lowered.contains(&window) {
                return true;
            }
        }
    }
    false
}

/// `_is_fixture(match_text, line)` — the four rules, in order.
fn is_fixture(match_text: &str, line: &str) -> bool {
    let value = value_of(match_text);
    let value_chars: Vec<char> = value.chars().collect();
    if value_chars.len() >= 8
        && !value_chars.is_empty()
        && value_chars.iter().all(|c| *c == value_chars[0])
    {
        return true;
    }
    let lowered_value = value.to_lowercase();
    if DUMMY_WORDS.iter().any(|w| lowered_value.contains(w)) {
        return true;
    }
    if has_sequential_run(&value) {
        return true;
    }
    // Label words count only outside the match itself.
    let rest = match line.find(match_text) {
        Some(idx) => {
            let mut r = String::with_capacity(line.len());
            r.push_str(&line[..idx]);
            r.push_str(&line[idx + match_text.len()..]);
            r
        }
        None => line.to_string(),
    };
    rest.to_lowercase()
        .split(|c: char| !c.is_ascii_alphanumeric())
        .any(|piece| LINE_WORDS.contains(&piece))
}

/// Basename rules for files that must never be committed
/// (the SECRET_FILENAME_RES shapes, `re.match` anchored at
/// the start of the basename).
fn is_secret_filename(name: &str) -> bool {
    if name == ".env" || name.starts_with(".env.") {
        return true; // ^\.env(\..*)?$
    }
    if name.ends_with(".env") {
        return true; // .*\.env$
    }
    if name.contains("job-secret") {
        return true;
    }
    if name.contains("admin_secret") {
        return true;
    }
    if name.ends_with(".keyring") || name.ends_with(".pem") || name.ends_with(".key") {
        return true;
    }
    false
}

fn is_binary(path: &Path) -> bool {
    match std::fs::read(path) {
        Ok(bytes) => bytes.iter().take(4096).any(|b| *b == 0),
        Err(_) => true,
    }
}

/// (relpath, lineno, kind); lineno 0 is a filename finding.
pub type Hit = (String, usize, String);

/// `scan_root(root)` -> (findings, fixtures, files_scanned).
pub fn scan_root(root: &Path) -> (Vec<Hit>, Vec<Hit>, usize) {
    let mut findings: Vec<Hit> = Vec::new();
    let mut fixtures: Vec<Hit> = Vec::new();
    let mut files_scanned = 0usize;
    let mut stack: Vec<PathBuf> = vec![root.to_path_buf()];
    // os.walk is top-down; a stack with reversed push order
    // keeps the same depth-first shape.
    let mut ordered: Vec<PathBuf> = Vec::new();
    while let Some(dir) = stack.pop() {
        ordered.push(dir.clone());
        let mut subdirs: Vec<PathBuf> = Vec::new();
        if let Ok(entries) = std::fs::read_dir(&dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.is_dir() {
                    let name = entry.file_name().to_string_lossy().to_string();
                    if !SKIP_DIRS.contains(&name.as_str()) {
                        subdirs.push(path);
                    }
                }
            }
        }
        for sub in subdirs.into_iter().rev() {
            stack.push(sub);
        }
    }
    for dir in ordered {
        let mut filenames: Vec<String> = Vec::new();
        if let Ok(entries) = std::fs::read_dir(&dir) {
            for entry in entries.flatten() {
                if entry.path().is_file() {
                    filenames.push(entry.file_name().to_string_lossy().to_string());
                }
            }
        }
        filenames.sort();
        for name in filenames {
            let path = dir.join(&name);
            let rel = path
                .strip_prefix(root)
                .map(|p| p.to_string_lossy().to_string())
                .unwrap_or_else(|_| path.to_string_lossy().to_string());
            if is_secret_filename(&name) {
                findings.push((rel.clone(), 0, "secret-filename".to_string()));
            }
            if is_binary(&path) {
                continue;
            }
            files_scanned += 1;
            let bytes = match std::fs::read(&path) {
                Ok(b) => b,
                Err(_) => continue,
            };
            let text = String::from_utf8_lossy(&bytes);
            for (lineno, line) in text.lines().enumerate() {
                for (kind, match_text) in search_line(line) {
                    if is_fixture(&match_text, line) {
                        fixtures.push((rel.clone(), lineno + 1, kind.to_string()));
                    } else {
                        findings.push((rel.clone(), lineno + 1, kind.to_string()));
                    }
                }
            }
        }
    }
    (findings, fixtures, files_scanned)
}

/// The script's main(): (exit code, printed lines).
pub fn execute(root: &Path) -> (i32, Vec<String>) {
    let (findings, fixtures, files_scanned) = scan_root(root);
    let mut lines: Vec<String> = Vec::new();
    for (rel, lineno, kind) in &findings {
        lines.push(format!("FINDING {}:{} {}", rel, lineno, kind));
    }
    for (rel, lineno, kind) in &fixtures {
        lines.push(format!("fixture {}:{} {}", rel, lineno, kind));
    }
    let mut kinds: Vec<(String, usize)> = Vec::new();
    for (_, _, kind) in &findings {
        if let Some(slot) = kinds.iter_mut().find(|(k, _)| k == kind) {
            slot.1 += 1;
        } else {
            kinds.push((kind.clone(), 1));
        }
    }
    kinds.sort();
    let summary = kinds
        .iter()
        .map(|(k, c)| format!("{}={}", k, c))
        .collect::<Vec<_>>()
        .join(", ");
    lines.push(format!(
        "scanned {} files, {} findings, {} fixtures{}",
        files_scanned,
        findings.len(),
        fixtures.len(),
        if summary.is_empty() {
            String::new()
        } else {
            format!(" ({})", summary)
        }
    ));
    (if findings.is_empty() { 0 } else { 1 }, lines)
}
