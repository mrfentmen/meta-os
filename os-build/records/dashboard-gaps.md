# `dashboard` — Python behaviours the Rust port does not carry (B149)

Deliverable only: these are **not ported** by this pass. Each item
names the Python source that still holds the live behaviour. The
crate's own header (`crates/dashboard/src/lib.rs:1-56`) already calls
the viewer fold-excluded; this list makes that concrete and countable.

The Rust port is the backend **contract** (rules, shapes, refusal
messages), not the web viewer. The viewer and anything that drives a
browser, a Node process, Redis, or missing submission assets stays
out by design.

| # | Behaviour not carried | Python source (lines) | Why it is out |
|---|---|---|---|
| G1 | The dashboard viewer itself: HTML, CSS, DOM wiring, panels, buttons | `os/tests/test_dashboard_palette.py`, `test_dashboard_error_states.py`, `test_dashboard_demo_mode.py`, `test_dashboard_deep_links.py` all read `bus.html` / `index.html` | Viewer is fold-excluded; the crate is not a web target |
| G2 | Crew-board card/detail HTML rendering | `os/tests/test_crewboard_alert_ribbon.py`, `test_crewboard_attempts.py`, `test_crewboard_files_deps.py`, `test_crewboard_os084_artifacts.py` (HTML halves) | Reads the fold-excluded `crew-board.html` through a Node driver |
| G3 | Bus/index byte-identity check (the two viewer files must match) | `os/tests/test_dashboard_help.py:113-117` | Needs both viewer files |
| G4 | Help panel title, four-panel coverage, data-source names, refresh/read-only/demo text, no-new-hex rule | `os/tests/test_dashboard_help.py:119-168` | Viewer text and DOM |
| G5 | Intel focus shortcut: `i` toggles focus in demo mode, inert while typing/modified, CSS hides log and widens panels | `os/tests/test_dashboard_intel_focus.py:150-195` | Needs the viewer's JavaScript and CSS |
| G6 | Read-only token posture in the UI: four panels busy, write buttons disabled with explanation | `os/tests/test_dashboard_readonly_token.py:222-272` | Viewer DOM |
| G7 | Screenshot pack and its assertions | `os/tests/test_dashboard_screenshots.py` | Submission assets are absent from this tree |
| G8 | Palette rendering (classes and computed colours in the page) | `os/tests/test_dashboard_palette.py` | Only the contrast math is ported (`contract.rs:91-122`) |
| G9 | Performance cap enforcement ("newest 200" in the feed) | `os/tests/test_dashboard_performance.py` | The cap is a viewer fetch rule; the contract has no fetch |
| G10 | OS-084 JSON-string-field parsing from a Redis hash | `os/tests/test_crewboard_os084_artifacts.py` | Needs the live hash/Redis shape |
| G11 | Live `attach()` cross-check against a real artifact deposit | `os/tests/test_crewboard_os084_artifacts.py` | Needs `mos/artifact_store` I/O |
| G12 | Keyless-verify cross-check against `admin.py` | `os/tests/test_crewboard_signing.py` | B26's contract and an admin script, not this crate |
| G13 | Panel-vs-CLI consistency for three real brief ids | `os/tests/test_intel_brief_dashboard_consistency.py:156-215` | Runs the CLI and reads the viewer |
| G14 | Alert lifecycle Node driver and the resolved-collapse HTML | `os/tests/test_dashboard_alert_lifecycle.py` | The transition rules are ported; the driver and HTML are not |
| G15 | Actually rolling back a deployment | `os/tests/test_dashboard_rollback_int031.py:30-73` | The runbook text is pinned; no deploy is performed |
| G16 | Smoke checklist execution (ten browser checks) | `os/tests/test_dashboard_smoke_checklist.py` | The checklist text is pinned; the checks are run by a person/browser |
| G17 | Cross-browser runs | `os/tests/test_dashboard_cross_browser.py:22-37` | Only the recorded log is carried as a fixture |

## What the port does carry, for contrast

Rules and shapes: brief payload/staleness, palette contrast math,
verdict mapping, section order/titles/open map, alerts feed order,
deep-link parsing, demo mode, today counters, error-row copy, posting
gates, rollback pins, crew-board ribbon/badge/files/deps/artifact
rules, keyless signing entry shapes, and alert lifecycle transitions.
See `dashboard.md` for the file:line map.
