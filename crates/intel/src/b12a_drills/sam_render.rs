//! Port of `os/intel/sam_render.py` — STR-003: render the
//! all-quiet Alerts panel (known-good half of the SAM eval
//! pairs).
//!
//! Method (same as DSH-030/DSH-035): headless render of
//! bus.html in demo mode (?demo=1), feed the panel through the
//! __busTest.intelPanel harness — zero alerts plus a live beat
//! 30 s old — and screenshot the #panel-intel-alerts element at
//! desktop and phone viewports. The panel must read "All
//! quiet — watchdog alive" and the snapshot must report
//! alerts 0 and beat alive, or the render fails and writes
//! nothing. The known-bad half is NOT re-rendered here (the
//! pinned DSH-030 submission shots; see sam_check).
//!
//! Browser seam: the Python drives Playwright + the repo's
//! own Chromium build. Rust std has no browser engine, so the
//! driving rides the [`PanelDriver`] trait — the assertion
//! sequence, harness calls, and results shape are the
//! source's own; the driver implementation (a headless
//! Chromium at the pinned build) is wired at gate 1.

use super::value::{to_json_pretty, Value};
use std::path::{Path, PathBuf};

pub const CHROME_PATH: &str = "~/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome";
pub const PANEL_SELECTOR: &str = "#panel-intel-alerts";

/// One screenshot target: (filename, viewport width, height).
pub const SHOTS: [(&str, i64, i64); 2] = [
    ("alerts-quiet-desktop.png", 1280, 900),
    ("alerts-quiet-phone.png", 390, 844),
];

/// The Playwright seat, one page at a time.
pub trait PanelDriver {
    /// Open the page at the viewport; collect page errors.
    fn open_page(&mut self, width: i64, height: i64, url: &str) -> Result<(), String>;
    /// `page.wait_for_timeout(ms)`.
    fn wait(&mut self, ms: i64);
    /// `window.__busTest.intelPanel.snapshot()`.
    fn panel_snapshot(&mut self) -> Result<Value, String>;
    /// The harness feed: setAlerts([], now) and
    /// setBeat({ts: now_seconds - 30}, now).
    fn feed_quiet_panel(&mut self, now_ms: i64) -> Result<(), String>;
    /// `#panel-intel-alerts` innerText.
    fn panel_text(&mut self) -> Result<String, String>;
    /// Screenshot the panel element to `path`; returns bytes written.
    fn screenshot_panel(&mut self, path: &Path) -> Result<u64, String>;
    /// Page errors collected since open.
    fn page_errors(&self) -> Vec<String>;
    /// `page.close()`.
    fn close_page(&mut self);
}

/// `render(outdir)` — the STR-003 render. Returns
/// (exit code, printed lines); on success the single line is
/// the source's `json.dumps(results, indent=1)`.
pub fn render(driver: &mut dyn PanelDriver, repo: &Path, outdir: &Path) -> (i32, Vec<String>) {
    match render_inner(driver, repo, outdir) {
        Ok(results) => (0, vec![to_json_pretty(&results, 1)]),
        Err(msg) => (1, vec![format!("AssertionError: {}", msg)]),
    }
}

fn render_inner(
    driver: &mut dyn PanelDriver,
    repo: &Path,
    outdir: &Path,
) -> Result<Value, String> {
    std::fs::create_dir_all(outdir).map_err(|e| e.to_string())?;
    let url = format!("file://{}/bus.html?demo=1", repo.display());
    let mut results: Vec<(String, Value)> = Vec::new();
    for (name, width, height) in SHOTS {
        driver.open_page(width, height, &url)?;
        driver.wait(800);
        let snap = driver.panel_snapshot()?;
        if snap.get("demoMode") != Value::Bool(true) {
            return Err(format!("demo mode not on: {}", snap.py_repr()));
        }
        let now_ms = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_millis() as i64)
            .unwrap_or(0);
        driver.feed_quiet_panel(now_ms)?;
        driver.wait(400);
        let snap = driver.panel_snapshot()?;
        if snap.get("alerts") != Value::Int(0) {
            return Err(format!("alerts not zero: {}", snap.py_repr()));
        }
        if snap.get("beat") != Value::Bool(true) {
            return Err(format!("beat missing: {}", snap.py_repr()));
        }
        let panel_text = driver.panel_text()?;
        if !panel_text.contains("All quiet") {
            return Err(format!("quiet text absent: {:?}", panel_text));
        }
        if !panel_text.contains("watchdog alive") {
            return Err(format!("beat not alive in render: {:?}", panel_text));
        }
        let errors = driver.page_errors();
        if !errors.is_empty() {
            return Err(format!("page errors: {:?}", errors));
        }
        let path: PathBuf = outdir.join(name);
        driver.screenshot_panel(&path)?;
        let size = std::fs::metadata(&path).map(|m| m.len()).unwrap_or(0);
        if size <= 1000 {
            return Err(format!("tiny screenshot: {}", path.display()));
        }
        let first_line = panel_text
            .trim()
            .lines()
            .next()
            .unwrap_or("")
            .to_string();
        results.push((
            name.to_string(),
            Value::obj(vec![
                (
                    "viewport",
                    Value::List(vec![Value::Int(width), Value::Int(height)]),
                ),
                ("panel_text", Value::s(&first_line)),
                ("bytes", Value::Int(size as i64)),
            ]),
        ));
        driver.close_page();
    }
    Ok(Value::Map(results))
}

/// The default outdir: <repo>/intel/evals/sam.
pub fn default_outdir(repo: &Path) -> PathBuf {
    repo.join("intel").join("evals").join("sam")
}
