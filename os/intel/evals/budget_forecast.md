# OS-091: budget preemption + forecasting — eval

## What was built

- `intel/forecast.py`: end-of-day projection from the ledger
  rate (spent * 24 / elapsed hours), confidence from elapsed
  hours alone (low < 4h, medium 4–12h, high >= 12h), plain
  brief lines carrying the basis sentence verbatim, and the
  pause/resume decision (pause only low-priority running jobs
  in a warning-band lane; resume only paused jobs whose lane
  dropped below warning).
- `intel/drills/budget_forecast.py`: 5/5 phases PASS — forecast
  80/100 at 8h projects 240 with a breach flag, low-priority
  job pauses with progress kept, high-priority job untouched,
  paused job resumes cleanly on a freed budget, one plain
  forecast brief line.
- `tests/test_intel_budget_forecast.py`: 18 tests pinning the
  math, the confidence rule, the brief lines, the decision
  table (including the OS-085 warning band as the pause
  trigger), and the drill as a subprocess.
- README section: "Budget forecasting + preemption (OS-091)".

## Design notes

- The projection is one division, stated openly; the
  confidence word is deliberately coarse (three bands from
  elapsed hours only) so no reader mistakes a forecast for
  a measurement.
- Projected spend is rounded down for display: a forecast is
  an estimate, and rounding up would overstate it.
- Pause is decided in the warning band, not at cap: at cap
  the OS-085 gate already holds new claims, and pausing
  running work at cap is a separate call this module does
  not make.
- OS-091 is tagged [B] (Phase B, post-hackathon) in the
  lane file; this build lands the judgment module and its
  fixtures early, in the same renderer-only pattern as the
  OS-075/OS-092 brief sections. It does not claim the
  Phase B track itself (no 7-day soak, no live daily brief).

## NOT proven here

- A forecast against a live spend ledger (no ledger exists
  in Redis; OS-085 names the same gap for its gate).
- A forecast line inside a daily brief actually run by the
  brief pipeline (the line renderer is proven; no daily
  brief run fills a forecast section yet).
- A real worker paused or resumed by a preempt decision
  (no worker pause path exists for a decision to drive).
- Any tuning of the confidence bands against real lane
  histories (the bands are starting defaults, not tuned
  values).
