// Baseline source for the Musica harness: the always-reject fixture.
// It predicts "reject" for every keeper check, zero keepers for every
// session, "not a clone" for every variation pair, a rights violation
// for every catalogue, out-of-tolerance for every normalisation, and
// an empty catalogue. It exists so the harness can show, honestly,
// what a do-nothing source scores against the same ground truth:
// it passes exactly the one scenario whose expected outcome is
// negative (MUS-KEEP-02, the recorded reject) and fails the other
// nine. A real run must beat 1/10 to claim it replays the records.
// No network, no model calls, no inspection of the session files:
// the scenario argument is accepted only to satisfy the source
// contract (an async function assess(scenario, root)).

export async function assessBaseline(scenario) {
  switch (scenario.kind) {
    case "keeper-measure":
      return { detail: "Baseline predicts reject for every take.", pass: scenario.expected_verdict === "reject" };
    case "variation":
      // Baseline predicts "not a clone" for every pair, so it passes
      // only a scenario with no clone pair in it; MUS-VAR-01 has one.
      return { detail: "Baseline predicts not-a-clone for every pair.", pass: scenario.pairs.every((p) => p.expected_clone === false) };
    default:
      return { detail: "Baseline predicts no keepers, no catalogue, no pass.", pass: false };
  }
}
