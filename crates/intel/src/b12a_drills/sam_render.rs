//! Port of `os/intel/sam_render.py` — SAM pairs renderer.
//!
//! Renders `sam/pairs.json` pairs into the `sam_pairs.md` shape:
//! one section per pair, verdict quoted verbatim.

pub fn render(pairs: &[(String, String, String)]) -> String {
    let mut out = String::from("# SAM pairs\n");
    for (name, prompt, verdict) in pairs {
        out.push_str(&format!("\n## {name}\n\nprompt: {prompt}\nverdict: {verdict}\n"));
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn renders_sections() {
        let md = render(&[("p1".into(), "q".into(), "pass".into())]);
        assert!(md.contains("## p1") && md.contains("verdict: pass"));
    }
}
