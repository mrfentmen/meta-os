// Meta Aegis eval baseline (fixture, not a source).
// Always predicts no detection. That sets the bar a real run must beat:
// it passes every no-detection scenario and fails exactly the positive one
// (AEG-PARSE-01). Replay scenarios (ledger summary, sweep diff) are not
// detections, so the baseline does not pass them either — it predicts
// nothing, and a prediction of nothing is not a replay.

export function assessBaseline(scenario) {
  const detection = scenario.fired_expected !== undefined &&
    (scenario.kind === "kev-reproduction" || scenario.kind === "fp-drill" || scenario.kind === "parse-hit");
  return {
    actual: null,
    fired: detection ? false : null,
    pass: detection ? scenario.fired_expected === false : false,
  };
}
