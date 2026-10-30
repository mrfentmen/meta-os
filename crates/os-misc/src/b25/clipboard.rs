//! B25 clipboard — port of `os/clipboard.py`.
//!
//! Preference order per spec: xclip, xsel, pbcopy/pbpaste, wl-*,
//! then Termux and PowerShell fallbacks. Failure is LOUD.

/// Ordered read commands (first binary on PATH wins).
pub const READ_TOOLS: &[&[&str]] = &[
    &["xclip", "-selection", "clipboard", "-out"],
    &["xsel", "--clipboard", "--output"],
    &["pbpaste"],
    &["wl-paste", "--no-newline"],
    &["termux-clipboard-get"],
    &["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
];

/// Ordered write commands.
pub const WRITE_TOOLS: &[&[&str]] = &[
    &["xclip", "-selection", "clipboard", "-in"],
    &["xsel", "--clipboard", "--input"],
    &["pbcopy"],
    &["wl-copy"],
    &["termux-clipboard-set"],
    &["powershell", "-NoProfile", "-Command", "$input | Set-Clipboard"],
];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClipboardError(pub String);

impl std::fmt::Display for ClipboardError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}
impl std::error::Error for ClipboardError {}

/// Message when no tool is installed (names the whole fallback list).
pub fn no_tool_msg(tools: &[&[&str]], op: &str) -> String {
    let names: Vec<&str> = tools.iter().map(|c| c[0]).collect();
    format!(
        "no clipboard tool found (looked for: {}) — install one, e.g. 'apt install xclip' (or wl-clipboard, xsel)",
        names.join(", ")
    )
    .replace("install one", &format!("install one for {op}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tool_order_matches_spec() {
        assert_eq!(READ_TOOLS[0][0], "xclip");
        assert_eq!(WRITE_TOOLS[2][0], "pbcopy");
        assert!(no_tool_msg(READ_TOOLS, "read").contains("xclip"));
    }
}
