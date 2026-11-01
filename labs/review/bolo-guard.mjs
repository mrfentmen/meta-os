// labs/review/bolo-guard.mjs — the no-name rule, shared by the BOLO page
// and the node test suite. A record carrying a `name` field (any
// non-empty value) is REFUSED, never rendered: names must not reach a
// BOLO card even by accident.
export function guardNoName(incident) {
  if (incident && Object.hasOwn(incident, "name") && incident.name !== undefined && incident.name !== null && String(incident.name).trim() !== "") {
    throw new Error("refused: incident carries a name field — BOLO cards never show names");
  }
  return true;
}
