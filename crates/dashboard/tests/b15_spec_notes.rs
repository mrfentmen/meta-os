//! B15 spec-note parity — the portable half of the dashboard spec tests.
//!
//! Each test below ports one Python case that reads only a carried
//! doc fixture (DASHBOARD_SPEC.md, DSH-035-CROSS-BROWSER-CHECK.md, or
//! DEMO.md — all byte-identical to os/), never the fold-excluded
//! viewer (bus.html / index.html), a Node driver, or a live browser.
//! The viewer/Node half of each split case stays exclusion-blocked
//! and is named in the header of b15_parity.rs, never faked green.
//!
//! Coverage by task:
//! - T238: brief_sections spec note (DSH-031); cross_browser, all 3
//!   log cases (DSH-035). alert_lifecycle, bus_index_identity, and
//!   the accessibility viewer cases stay blocked.
//! - T239: dsh038, all 5 spec cases (section 5.6); deep_links,
//!   demo_mode, dsp039 spec-note cases only. The Node-driver and
//!   viewer cases of those files stay blocked.
//! - T240: error_states, help, intel_focus (spec + demo notes),
//!   os043 (section 8.1), os084 (section 8.2) spec cases only.
//! - T241: performance cap note; readonly_token spec half (DSH-033).
//!   palette, screenshots (submission-assets missing from this
//!   tree), and the viewer halves stay blocked.
//! - T242: str005 spec half (STR-005 note); today_counters spec
//!   half (DSH-032). The viewer/Node halves and the whole
//!   intel_brief_dashboard_consistency file stay blocked.

fn spec() -> &'static str {
    include_str!("../fixtures/DASHBOARD_SPEC.md")
}

fn section<'a>(text: &'a str, start: &str, end: &str) -> &'a str {
    let after = text.split(start).nth(1).expect("section start missing");
    after.split(end).next().unwrap_or(after)
}

// ---- T238: test_dashboard_brief_sections.py, spec half ----

#[test]
fn test_dashboard_brief_sections_spec_notes_dsh031() {
    assert!(spec().contains("Implemented (DSH-031)"));
}

// ---- T238: test_dashboard_cross_browser.py, all 3 log cases ----

fn cross_browser_log() -> &'static str {
    include_str!("../fixtures/DSH-035-CROSS-BROWSER-CHECK.md")
}

#[test]
fn test_dashboard_cross_browser_log_records_all_four_runs_pass() {
    let text = cross_browser_log();
    for row in [
        "Chromium (Playwright, cached build) | 1280x900 | PASS",
        "Chromium (Playwright, cached build) | 390x844 (phone) | PASS",
        "WebKit (Playwright, Safari engine) | 1280x900 | PASS",
        "WebKit (Playwright, Safari engine) | 390x844 (phone) | PASS",
    ] {
        assert!(text.contains(row), "check log omits run: {row}");
    }
}

#[test]
fn test_dashboard_cross_browser_log_records_no_safari_only_bug_verdict() {
    let text = cross_browser_log();
    assert!(text.contains("No Safari-only bug found"));
    assert!(text.contains("nothing to file before demo freeze"));
}

#[test]
fn test_dashboard_cross_browser_log_states_ios_device_caveat_plainly() {
    assert!(cross_browser_log().contains("No physical iOS device"));
}

// ---- T239: test_dashboard_dsh038.py, all 5 spec cases ----

fn dsh038_section() -> String {
    section(spec(), "### 5.6 DSH-038 decision", "## 6. Alerts panel").to_string()
}

#[test]
fn test_dashboard_dsh038_spec_has_request_only_decision_section() {
    let s = dsh038_section();
    assert!(s.contains("request-only"));
    assert!(s.contains("the viewer never posts a dispatch plan"));
    assert!(s.contains("no live"));
    assert!(s.contains("no flip task"));
}

#[test]
fn test_dashboard_dsh038_spec_decision_gives_real_cli_flow() {
    let s = dsh038_section();
    for needle in [
        "--dry-run --plan plan.json",
        "--plan plan.json --approve",
        "--secret-file",
        "--show <id>",
        "--undo <id>",
    ] {
        assert!(s.contains(needle), "missing: {needle}");
    }
}

#[test]
fn test_dashboard_dsh038_spec_decision_names_why_not_deferred() {
    let s = dsh038_section();
    assert!(s.contains("chmod 600"));
    assert!(s.contains("secrets never reach"));
    assert!(s.contains("GOV-002"));
}

#[test]
fn test_dashboard_dsh038_spec_decision_reopens_only_on_dale_plus_server() {
    let s = dsh038_section();
    assert!(s.contains("only a Dale decision"));
    assert!(s.contains("server-side"));
}

#[test]
fn test_dashboard_dsh038_spec_no_longer_waits_on_viewer_posting_rule() {
    let s = spec();
    assert!(!s.contains(
        "Dispatch approve) ship disabled/read-only until Dale's posting rule"));
    assert!(s.contains("Dispatch approve is decided, not pending"));
    assert!(s.contains("Dispatch approve is request-only (DSH-038"));
}

// ---- T239: test_dashboard_deep_links.py, spec case ----

#[test]
fn test_dashboard_deep_links_spec_documents_deep_links() {
    let s = spec();
    assert!(s.contains("DSH-022"));
    assert!(s.contains("#intel/brief/"));
    assert!(s.contains("#intel/alert/"));
}

// ---- T239: test_dashboard_demo_mode.py, spec case ----

#[test]
fn test_dashboard_demo_mode_spec_documents_demo_mode() {
    let s = spec();
    assert!(s.contains("DSH-028"));
    assert!(s.contains("?demo=1"));
}

// ---- T239: test_dashboard_dsp039.py, spec case ----

#[test]
fn test_dashboard_dsp039_spec_lists_all_six_states_with_exact_labels() {
    let s = section(spec(), "### 5.4 Approval states", "### 5.5");
    for state in ["idle", "planning", "plan-ready", "posting", "posted", "rejected"] {
        assert!(s.contains(state), "missing state: {state}");
    }
    for label in ["`Plan`", "Planning…", "`Post N jobs`", "`Reject plan`"] {
        assert!(s.contains(label), "missing label: {label}");
    }
}

// ---- T240: test_dashboard_error_states.py, spec case ----

#[test]
fn test_dashboard_error_states_spec_documents_error_states() {
    let s = spec();
    assert!(s.contains("is paused. The log above is unaffected."));
    assert!(s.contains("Paste a token above to load"));
    assert!(s.contains("DSH-021"));
}

// ---- T240: test_dashboard_help.py, spec case ----

#[test]
fn test_dashboard_help_spec_documents_help_panel() {
    let s = spec();
    assert!(s.contains("DOC-017"));
    assert!(s.contains("Dashboard help"));
}

// ---- T240: test_dashboard_intel_focus.py, spec + demo-notes case ----

#[test]
fn test_dashboard_intel_focus_spec_and_demo_notes_document_shortcut() {
    let s = spec();
    assert!(s.contains("Implemented (DSH-034)"));
    assert!(s.contains("intel-focus-mode"));
    let demo = include_str!("../fixtures/DEMO.md");
    assert!(demo.contains("DSH-034"));
    assert!(demo.contains("Intel focus"));
    assert!(demo.contains("?demo=1"));
}

// ---- T240: test_dashboard_os043.py, spec case ----

#[test]
fn test_dashboard_os043_spec_documents_boot_checklist_contract() {
    let s = section(spec(), "### 8.1 Boot checklist (OS-043)", "## 9.");
    let lower = s.to_lowercase();
    for line in ["bus", "queue", "supervisor", "watchdog", "brief"] {
        assert!(lower.contains(line), "missing: {line}");
    }
    assert!(s.contains("muse-bus:intel:wd:bootstatus:"));
    assert!(s.contains("30s"));
}

// ---- T240: test_dashboard_os084.py, spec case ----

#[test]
fn test_dashboard_os084_spec_documents_refusal_banner_contract() {
    let s = section(spec(), "### 8.2 Capability refusal banner", "## 9.");
    assert!(s.contains("capability-refusal"));
    assert!(s.contains("OS-081"));
    assert!(s.contains("OS-080"));
    assert!(s.contains("OS-083"));
}

// ---- T241: test_dashboard_performance.py, spec case ----

#[test]
fn test_dashboard_performance_spec_documents_the_cap() {
    assert!(spec().contains("newest 200"));
}

// ---- T241: test_dashboard_readonly_token.py, spec half ----
// (The bus/index identity half stays exclusion-blocked: bus.html
// and index.html are fold-excluded.)

#[test]
fn test_dashboard_readonly_token_spec_notes_dsh033() {
    assert!(spec().contains("Implemented (DSH-033)"));
}

// ---- T242: test_dashboard_str005.py, spec half ----
// (The bus/index identity half stays exclusion-blocked.)

#[test]
fn test_dashboard_str005_spec_notes_str005() {
    assert!(spec().contains("Visual checks (STR-005"));
}

// ---- T242: test_dashboard_today_counters.py, spec half ----
// (The bus/index identity half stays exclusion-blocked.)

#[test]
fn test_dashboard_today_counters_spec_notes_dsh032() {
    assert!(spec().contains("Implemented (DSH-032)"));
}
