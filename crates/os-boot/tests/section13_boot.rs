//! CB2-301/302/324 — the boot config's three rules.
use os_boot::boot_config::{BootConfig, ConfigError, DEFAULT_TIMEOUT_SECS, KNOWN_KEYS};

#[test]
fn config_missing_kernel_path() {
    // No kernel line at all, and a kernel line with no value, are the same
    // refusal: the machine has nothing to boot.
    assert_eq!(
        BootConfig::parse("initrd=/boot/initrd.img\ncmdline=quiet\n").unwrap_err(),
        ConfigError("boot config: kernel path is required".to_string()),
    );
    assert_eq!(
        BootConfig::parse("kernel=\n").unwrap_err(),
        ConfigError("boot config: kernel path is required".to_string()),
    );
    assert_eq!(
        BootConfig::parse("").unwrap_err(),
        ConfigError("boot config: kernel path is required".to_string()),
        "an empty file is not a config",
    );

    // The canonical shape parses, so the refusals above are not a blanket.
    let config = BootConfig::parse("# comment\nkernel=/boot/vmlinuz\n").expect("kernel present");
    assert_eq!(config.kernel, "/boot/vmlinuz");
    assert_eq!(config.initrd, None);
    assert_eq!(config.cmdline, "");
    assert_eq!(config.timeout_secs, DEFAULT_TIMEOUT_SECS);
}

#[test]
fn config_unknown_key() {
    // A typo is refused with the key and the line named, so it cannot be
    // silently ignored while the config looks edited.
    let err = BootConfig::parse("kernel=/boot/vmlinuz\nkernal=/boot/old\n").unwrap_err();
    assert_eq!(
        err.0,
        "boot config: unknown key \"kernal\" on line 2 (known: kernel, initrd, cmdline, timeout)",
    );
    assert!(err.0.contains("kernel, initrd, cmdline, timeout"), "the known keys are listed");

    // A line with no '=' is a bad line, not an unknown key.
    let bad = BootConfig::parse("kernel=/boot/vmlinuz\nquiet\n").unwrap_err();
    assert_eq!(bad.0, "boot config: line 2 has no '=': \"quiet\"");

    // A non-numeric timeout is refused by name too.
    let timeout = BootConfig::parse("kernel=/boot/vmlinuz\ntimeout=soon\n").unwrap_err();
    assert_eq!(timeout.0, "boot config: timeout must be a whole number of seconds, got \"soon\"");

    assert_eq!(KNOWN_KEYS, &["kernel", "initrd", "cmdline", "timeout"]);
}

#[test]
fn config_duplicate_entry() {
    // Later lines win: the documented winner is the last value.
    let config = BootConfig::parse(
        "kernel=/boot/one\n\
         kernel=/boot/two\n\
         initrd=/boot/first.img\n\
         initrd=/boot/second.img\n\
         timeout=5\n\
         timeout=9\n",
    )
    .expect("duplicates are allowed and resolved");
    assert_eq!(config.kernel, "/boot/two", "the last kernel wins");
    assert_eq!(config.initrd, Some("/boot/second.img".to_string()), "the last initrd wins");
    assert_eq!(config.timeout_secs, 9, "the last timeout wins");

    // Comments are stripped before the value, never after.
    let commented = BootConfig::parse("kernel=/boot/vmlinuz # the kernel\ncmdline=quiet # keep it quiet\n")
        .expect("comments parse");
    assert_eq!(commented.kernel, "/boot/vmlinuz");
    assert_eq!(commented.cmdline, "quiet");

    // An empty initrd clears an earlier one: the last value is the answer,
    // including when the last value is "none".
    let cleared = BootConfig::parse("kernel=/boot/k\ninitrd=/boot/i\ninitrd=\n").expect("parses");
    assert_eq!(cleared.initrd, None);
}
