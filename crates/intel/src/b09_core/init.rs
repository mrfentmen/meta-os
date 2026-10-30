//! Port of `os/intel/__init__.py` — package marker + version.
//!
//! The Python package init carries no behavior; this module is the Rust
//! equivalent marker so `b09_core` has a stable root.

pub const PACKAGE: &str = "intel";
pub const SUBTREE: &str = "b09_core";

#[cfg(test)]
mod tests {
    #[test]
    fn package_marker() {
        assert_eq!(super::PACKAGE, "intel");
    }
}
