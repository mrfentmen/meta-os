// CB2-367: one parsed relay message, validated as data.
//
// relay.mjs validates {nick, text} on the POST path, before a line is
// formatted. This checks the other end: a message a reader already has in
// hand (GET /rooms/<room>/messages returns the stored lines; a consumer
// parses one into {nick, body, ts}). Same caps, same rule as the relay --
// one line, no control characters -- so a consumer cannot accept a record
// the writer would have refused.
//
// Returns a list of named errors; [] when the message is valid. The text is
// never echoed in an error, so a bad message cannot leak into a log line.

export const MAX_NICK_CHARS = 40;
export const MAX_BODY_CHARS = 2000;

function isSingleLine(value, maxChars) {
  return (
    typeof value === "string" &&
    value.length >= 1 &&
    value.length <= maxChars &&
    !/[\u0000-\u001f\u007f]/.test(value)
  );
}

export function validateMessageRecord(record) {
  if (!record || typeof record !== "object" || Array.isArray(record)) {
    return ["message: must be an object"];
  }
  const errors = [];
  if (!("nick" in record)) {
    errors.push("nick: missing");
  } else if (!isSingleLine(record.nick, MAX_NICK_CHARS)) {
    errors.push(`nick: must be a single line of 1-${MAX_NICK_CHARS} chars`);
  }
  if (!("body" in record)) {
    errors.push("body: missing");
  } else if (!isSingleLine(record.body, MAX_BODY_CHARS)) {
    errors.push(`body: must be a single line of 1-${MAX_BODY_CHARS} chars`);
  }
  if (!("ts" in record)) {
    errors.push("ts: missing");
  } else if (!Number.isInteger(record.ts) || record.ts < 0) {
    errors.push("ts: must be a non-negative integer of epoch seconds");
  }
  for (const key of Object.keys(record)) {
    if (key !== "nick" && key !== "body" && key !== "ts") {
      errors.push(`unexpected field: ${key}`);
    }
  }
  return errors;
}
