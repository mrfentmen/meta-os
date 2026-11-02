// Meta Aegis — D6, the alarm split (R11-238).
//
// Two outputs, one rule: a small finding gets a quiet note, a big one gets the full alarm. Size
// is severity first and count second, and the reason is written down so a quiet note can never
// be mistaken for "we decided nothing was wrong".
export const QUIET = "quiet";
export const ALARM = "alarm";

export const BIG = new Set(["medium", "high", "critical"]);

export function classify(findings) {
  const list = Array.isArray(findings) ? findings : [];
  const counts = { info: 0, low: 0, medium: 0, high: 0, critical: 0 };
  for (const f of list) if (counts[f.severity] != null) counts[f.severity] += 1;
  const big = [...BIG].reduce((n, s) => n + counts[s], 0);
  if (big > 0) {
    return {
      mode: ALARM,
      reason: big + " finding(s) at medium or above",
      counts,
      headline: "Aegis alarm: " + big + " finding(s) need a decision.",
    };
  }
  // Many small findings are not one big finding; the note says how many so the reader can judge.
  return {
    mode: QUIET,
    reason: list.length + " finding(s), all low or informational",
    counts,
    headline: list.length
      ? "Aegis note: " + list.length + " low finding(s), no decision needed."
      : "Aegis note: nothing found.",
  };
}

export function render(classification) {
  if (classification.mode === ALARM) {
    const lines = [classification.headline];
    for (const s of ["critical", "high", "medium"]) {
      if (classification.counts[s]) lines.push("  " + s + ": " + classification.counts[s]);
    }
    return lines.join("\n");
  }
  return classification.headline;
}
