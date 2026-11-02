/**
 * registry_validate.mjs — shape checks for agents/registry.json (CB2-356).
 *
 * The real registry carries `owner` where older task text says `badge`;
 * `owner` is required here and `badge` is checked when present, so both
 * shapes are honest. A `["true"]` command is reported as a draft, never
 * as runnable.
 */

const PLACEHOLDER_COMMANDS = [["true"], ["/bin/true"]];

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function commandIsPlaceholder(command) {
  if (!Array.isArray(command) || command.length === 0) return false;
  return PLACEHOLDER_COMMANDS.some(
    (placeholder) =>
      placeholder.length === command.length &&
      placeholder.every((part, i) => part === command[i]),
  );
}

export function validateRegistry(doc) {
  const errors = [];
  const drafts = [];
  if (!doc || typeof doc !== "object" || !Array.isArray(doc.agents)) {
    return { ok: false, errors: [{ index: -1, field: "agents", message: "agents must be an array" }], drafts: [] };
  }

  const seen = new Map();
  doc.agents.forEach((entry, index) => {
    if (!entry || typeof entry !== "object") {
      errors.push({ index, field: "entry", message: "agent entry must be an object" });
      return;
    }
    if (!isNonEmptyString(entry.name)) {
      errors.push({ index, field: "name", message: "name must be a non-empty string" });
    } else {
      const key = entry.name.trim();
      if (seen.has(key)) {
        errors.push({
          index,
          field: "name",
          message: `duplicate agent name ${JSON.stringify(key)} (first at index ${seen.get(key)})`,
        });
      } else {
        seen.set(key, index);
      }
    }
    if (!Array.isArray(entry.command) || entry.command.length === 0) {
      errors.push({ index, field: "command", message: "command must be a non-empty array" });
    } else if (!entry.command.every(isNonEmptyString)) {
      errors.push({ index, field: "command", message: "every command part must be a non-empty string" });
    } else if (commandIsPlaceholder(entry.command)) {
      drafts.push({ index, name: entry.name, reason: "placeholder command" });
    }
    if (!isNonEmptyString(entry.owner)) {
      errors.push({ index, field: "owner", message: "owner must be a non-empty string" });
    }
    if (entry.badge !== undefined && !isNonEmptyString(entry.badge)) {
      errors.push({ index, field: "badge", message: "badge, when present, must be a non-empty string" });
    }
    if (entry.draft === true && !drafts.some((d) => d.index === index)) {
      drafts.push({ index, name: entry.name, reason: entry.draftReason || "marked draft" });
    }
  });

  return { ok: errors.length === 0, errors, drafts };
}
