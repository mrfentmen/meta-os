//! The boot config: `key=value` lines, read strictly.
//!
//! A boot config decides what the machine loads. Three rules, each one a
//! decision written down rather than left to a default:
//!
//! 1. **A kernel path is required.** A config with no `kernel=` cannot boot,
//!    so it is refused at parse instead of at power-on.
//! 2. **An unknown key is refused, with the key named.** A typo like `kernal=`
//!    would otherwise be ignored and the machine would boot the previous
//!    kernel while the config looked edited.
//! 3. **A duplicate key keeps the LAST value.** Later lines override earlier
//!    ones, the way every boot loader reads its config; the test pins it so a
//!    future change has to be deliberate.
//!
//! Format: one `key=value` per line, `#` starts a comment, blank lines are
//! skipped, and `value` is trimmed but never unquoted — what is written is
//! what is passed on.

/// Keys this parser accepts. Anything else is refused.
pub const KNOWN_KEYS: &[&str] = &["kernel", "initrd", "cmdline", "timeout"];

/// Timeout used when the config states none, in seconds.
pub const DEFAULT_TIMEOUT_SECS: u64 = 3;

/// A parsed boot config.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BootConfig {
    pub kernel: String,
    pub initrd: Option<String>,
    pub cmdline: String,
    pub timeout_secs: u64,
}

/// A config that must not be used, with the reason named.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ConfigError(pub String);

impl BootConfig {
    /// Parse config text. See the module docs for the three rules.
    pub fn parse(text: &str) -> Result<BootConfig, ConfigError> {
        let mut kernel: Option<String> = None;
        let mut initrd: Option<String> = None;
        let mut cmdline = String::new();
        let mut timeout_secs = DEFAULT_TIMEOUT_SECS;

        for (index, raw) in text.lines().enumerate() {
            let line = match raw.split_once('#') {
                Some((before, _)) => before.trim(),
                None => raw.trim(),
            };
            if line.is_empty() {
                continue;
            }
            let (key, value) = line.split_once('=').ok_or_else(|| {
                ConfigError(format!("boot config: line {} has no '=': {raw:?}", index + 1))
            })?;
            let key = key.trim();
            let value = value.trim();
            if !KNOWN_KEYS.contains(&key) {
                return Err(ConfigError(format!(
                    "boot config: unknown key {key:?} on line {} (known: {})",
                    index + 1,
                    KNOWN_KEYS.join(", "),
                )));
            }
            match key {
                "kernel" => kernel = Some(value.to_string()),
                "initrd" => {
                    initrd = if value.is_empty() { None } else { Some(value.to_string()) }
                }
                "cmdline" => cmdline = value.to_string(),
                "timeout" => {
                    timeout_secs = value.parse().map_err(|_| {
                        ConfigError(format!(
                            "boot config: timeout must be a whole number of seconds, got {value:?}"
                        ))
                    })?
                }
                _ => unreachable!("known keys are matched above"),
            }
        }

        let kernel = kernel.ok_or_else(|| ConfigError("boot config: kernel path is required".to_string()))?;
        if kernel.is_empty() {
            return Err(ConfigError("boot config: kernel path is required".to_string()));
        }
        Ok(BootConfig { kernel, initrd, cmdline, timeout_secs })
    }
}
