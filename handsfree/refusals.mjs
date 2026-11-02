// Hands-Free C4 — the refusal catalogue (R11-245).
//
// Some things this system will not do by voice, at any confidence, no matter how the order is
// phrased: move money, send on the boss's behalf, or delete. The catalogue is data so a test can
// hold the whole list at once, and the matcher is deliberately blunt — a refusal that needs a
// clever parse is a refusal that will one day miss.
//
// This module decides only "is this utterance in the forbidden set". It never performs the
// allowed action; that is the caller's job and its own approval gate.
export const REFUSALS = [
  { id: "money", pattern: /\b(pay|payment|transfer|wire|invoice|refund|charge|buy|purchase)\b/i, says: "I do not move money by voice." },
  { id: "send", pattern: /\b(send|email|post|publish|tweet|message|reply)\b/i, says: "I do not send anything on your behalf by voice." },
  { id: "delete", pattern: /\b(delete|erase|wipe|remove|drop|unlink|rm)\b/i, says: "I do not delete anything by voice." },
];

export function classifyUtterance(text) {
  const t = String(text == null ? "" : text);
  const hit = REFUSALS.find((r) => r.pattern.test(t));
  if (!hit) return { refused: false, id: null, says: null };
  return { refused: true, id: hit.id, says: hit.says };
}

export function catalogueIds() {
  return REFUSALS.map((r) => r.id);
}
