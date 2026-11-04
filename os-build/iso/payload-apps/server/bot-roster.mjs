// The bot roster: the agents in Meta OS, as contacts rather than "the agent".
//
// The chat box used to have exactly one voice per app. This module gives each
// app a named bot with its own title, its own standing instructions and
// optionally its own model, and answers the question the room asks every
// messaging product has to answer: when someone types into a room with more
// than one agent in it, who answers?
//
// The rule, copied in behaviour from the way OpenMausBot rooms work (we wrote
// this file ourselves; nothing here is their code):
//
//   1. An explicit @mention wins: @Watch answers, and only @Watch.
//   2. @everyone is read as "the room's lead answers" — we say so instead of
//      spending four model calls to have every bot chime in.
//   3. No mention: the room's lead answers, unless the message clearly belongs
//      to another member, in which case that member answers and the reply says
//      it was routed by the desk rather than chosen by a person.
//
// Routing is a keyword score, not a model call: it costs nothing, it is the
// same answer twice, and it never blocks a reply. A model-based picker (what
// they call the decision model) is a later option, not this file.
//
// Operators can override any bot by writing roster.json into the state
// directory (see stateDir below): the shipped table is the default, the file
// is the exception, and an unreadable or malformed exception is ignored rather
// than allowed to take the roster down.

import fs from "node:fs";
import os from "node:os";
import path from "node:path";

// Bots are addressed in the box as @Name, so names are one word, no spaces.
export const SHIPPED_BOTS = [
  {
    id: "watch",
    name: "Watch",
    title: "Camera desk · Vigiles",
    app: "vigiles",
    glyph: "WA",
    accent: "#6ea8ff",
    tags: ["camera", "cameras", "footage", "frame", "frames", "patrol", "perimeter", "watch", "video"],
    voice: "Answer like a desk sergeant: short, flat, and only about what the board actually shows. Never name a person.",
  },
  {
    id: "ember",
    name: "Ember",
    title: "Fire desk · Ignis",
    app: "ignis",
    glyph: "EM",
    accent: "#ff8a5c",
    tags: ["fire", "smoke", "flame", "flames", "burn", "burning", "heat", "wildfire", "alarm"],
    voice: "Answer about visible fire and smoke only. Never state a cause, never call a flag an incident.",
  },
  {
    id: "halo",
    name: "Halo",
    title: "EMS desk · Medicus",
    app: "medicus",
    glyph: "HA",
    accent: "#7fe0c0",
    tags: ["medic", "medical", "casualty", "casualties", "patient", "patients", "triage", "ems", "ambulance", "scene"],
    voice: "Answer about the scene and what a frame records. Never diagnose, never sort patients — the board sorts frames.",
  },
  {
    id: "sentry",
    name: "Sentry",
    title: "Security review · Aegis",
    app: "aegis",
    glyph: "SE",
    accent: "#c48bff",
    tags: ["sweep", "sweeps", "finding", "findings", "secret", "secrets", "audit", "review", "manifest", "leak"],
    voice: "Answer with the finding's file and reason. Never invent a finding and never upgrade an unproven one to confirmed.",
  },
  {
    id: "wire",
    name: "Wire",
    title: "Services · Nervus",
    app: "nervus",
    glyph: "WI",
    accent: "#ffd166",
    tags: ["port", "ports", "service", "services", "backend", "socket", "server", "health", "tray", "daemon"],
    voice: "Answer about ports on 127.0.0.1 and which backend answered. If a port did not answer, say so first.",
  },
  {
    id: "ledger",
    name: "Ledger",
    title: "Records and spend · Custos",
    app: "custos",
    glyph: "LE",
    accent: "#9ae6b4",
    tags: ["spend", "cost", "costs", "receipt", "receipts", "budget", "queue", "jobs", "agent", "agents", "estimate"],
    voice: "Answer from the records and say when a number is an estimate. Never present an estimate as a bill.",
  },
  {
    id: "forge",
    name: "Forge",
    title: "Engineering · Officina",
    app: "officina",
    glyph: "FO",
    accent: "#ffb347",
    tags: ["blueprint", "dimension", "dimensions", "build", "tolerance", "design", "drawing", "part", "spec"],
    voice: "Answer with the figure and where it comes from. Say when a figure is a record rather than live telemetry.",
  },
  {
    id: "beaker",
    name: "Beaker",
    title: "Molecule lab · Science",
    app: "science",
    glyph: "BE",
    accent: "#64d2ff",
    tags: ["molecule", "molecules", "atom", "atoms", "bond", "bonds", "formula", "cid", "caffeine", "structure"],
    voice: "Answer about the molecule the page has loaded. Say when the file does not carry the property being asked for.",
  },
  {
    id: "reed",
    name: "Reed",
    title: "Sessions · Musica",
    app: "musica",
    glyph: "RE",
    accent: "#f78fb3",
    tags: ["track", "tracks", "take", "takes", "session", "sessions", "play", "audio", "music", "volume"],
    voice: "Answer from what the session records say. Never claim to have heard the take.",
  },
  {
    id: "desk",
    name: "Desk",
    title: "Boards and rooms · Messages",
    app: "messages",
    glyph: "DE",
    accent: "#8fa4c4",
    tags: ["room", "rooms", "board", "boards", "post", "notify", "dispatch", "message", "messages", "thread"],
    voice: "Answer about which room carries which thread. You do not send messages and you do not speak as anyone else.",
  },
  {
    id: "gauge",
    name: "Gauge",
    title: "Machine facts · Monitor",
    app: "monitor",
    glyph: "GA",
    accent: "#a3e635",
    tags: ["cpu", "memory", "disk", "uptime", "load", "ram", "temperature", "machine", "facts"],
    voice: "Answer from the last reading and say when that reading is stale.",
  },
  {
    id: "meta",
    name: "Meta",
    title: "Meta OS · general desk",
    app: "general",
    glyph: "ME",
    accent: "#7fb8ff",
    tags: ["os", "desktop", "app", "apps", "launch", "window", "system", "meta", "wallpaper"],
    voice: "Answer about the applications that ship on this machine, and say plainly when the question needs an app that is not open.",
  },
];

export const BOT_IDS = SHIPPED_BOTS.map((b) => b.id);

// Models a bot may be pointed at. A roster.json entry outside this list is a
// typo or a stale name, so it falls back to the server default with a note
// instead of sending the request to a model that does not exist.
export const BOT_MODELS = ["muse-spark-1.3-contributor", "muse-spark-1.3"];

// $METAOS_AGENTS_STATE, else $METAOS_STATE/agents, else ~/.local/state/metaos/
// agents — the same precedence server/bus.mjs uses, so one knob moves every
// state directory on a machine.
export function stateDir(env = process.env) {
  if (env.METAOS_AGENTS_STATE && env.METAOS_AGENTS_STATE.trim()) {
    return path.resolve(env.METAOS_AGENTS_STATE.trim());
  }
  const base = env.METAOS_STATE
    ? env.METAOS_STATE
    : path.join(os.homedir(), ".local", "state", "metaos");
  return path.join(path.resolve(base), "agents");
}

function validBot(bot) {
  return (
    bot &&
    typeof bot.id === "string" &&
    /^[a-z0-9-]{1,24}$/.test(bot.id) &&
    typeof bot.name === "string" &&
    bot.name.length <= 24 &&
    typeof bot.title === "string" &&
    typeof bot.app === "string" &&
    typeof bot.voice === "string"
  );
}

// The roster the server actually runs with. Overrides are matched by id and
// limited to the fields an operator should change; id, name, app and tags stay
// the shipped ones so routing and addresses cannot be rewritten by a file.
export function buildRoster(overrides = {}) {
  const patch = overrides && typeof overrides === "object" && !Array.isArray(overrides.bots)
    ? overrides.bots || {}
    : {};
  const notes = [];
  const bots = SHIPPED_BOTS.map((shipped) => {
    const bot = { ...shipped, model: null };
    const override = patch[shipped.id];
    if (!override || typeof override !== "object") return bot;
    if (typeof override.title === "string" && override.title.length <= 80) bot.title = override.title;
    if (typeof override.voice === "string" && override.voice.length <= 600) bot.voice = override.voice;
    if (typeof override.model === "string" && override.model.trim()) {
      const model = override.model.trim();
      if (BOT_MODELS.includes(model)) bot.model = model;
      else notes.push(`${shipped.id}: model "${model}" is not in BOT_MODELS, using the server default`);
    }
    return bot;
  });
  return { bots, notes };
}

export function loadRoster(dir = stateDir(), env = process.env) {
  const file = path.join(dir, "roster.json");
  try {
    const raw = fs.readFileSync(file, "utf8");
    const parsed = JSON.parse(raw);
    return buildRoster(parsed);
  } catch (err) {
    if (err && err.code === "ENOENT") return buildRoster({});
    // A broken roster file must not take the desk down: run the shipped table
    // and say why in the notes, which the roster endpoint returns.
    const { bots, notes } = buildRoster({});
    return { bots, notes: notes.concat(`roster.json could not be read (${err.message}); using the shipped roster`) };
  }
}

export function botsForApp(roster, app) {
  const list = (roster.bots || []).filter((b) => b.app === app);
  if (list.length) return list;
  return (roster.bots || []).filter((b) => b.id === "meta");
}

export function resolveBot(roster, id) {
  if (typeof id !== "string" || !id.trim()) return null;
  const wanted = id.trim().toLowerCase();
  return (roster.bots || []).find((b) => b.id === wanted) || null;
}

// @Name, @name, @everyone, and a bare @ in an email address has to survive.
export function parseMention(text) {
  const source = typeof text === "string" ? text : "";
  const out = { all: false, names: [], ids: [] };
  const m = source.match(/(^|[\s(])@([A-Za-z][A-Za-z0-9_-]{0,23})\b/g) || [];
  for (const hit of m) {
    const name = hit.trim().replace(/^\(?@/, "").toLowerCase();
    if (name === "everyone" || name === "all" || name === "here") {
      out.all = true;
      continue;
    }
    if (!out.names.includes(name)) out.names.push(name);
  }
  out.ids = out.names;
  return out;
}

function score(bot, text) {
  const haystack = String(text || "").toLowerCase();
  if (!haystack) return 0;
  let points = 0;
  for (const tag of bot.tags || []) {
    // Word-ish match so "fi" does not fire on every word.
    const re = new RegExp(`(^|[^a-z0-9])${tag.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}([^a-z0-9]|$)`);
    if (re.test(haystack)) points += 1;
  }
  if (new RegExp(`(^|[^a-z0-9])${bot.id}([^a-z0-9]|$)`).test(haystack)) points += 1;
  return points;
}

// Who answers this message, and why. `picked_by` is what the UI prints under
// the reply, so "the person asked for it" and "the desk guessed" never look
// the same.
export function pickResponder({ bots, lead, text }) {
  const members = Array.isArray(bots) && bots.length ? bots : [];
  if (!members.length) return { bot: null, picked_by: "none", score: 0 };

  const leadBot = members.find((b) => b.id === (lead || "").toLowerCase()) || members[0];
  const mention = parseMention(text);

  if (mention.all) return { bot: leadBot, picked_by: "everyone-to-lead", score: 0 };

  if (mention.ids.length) {
    const wanted = members.filter((b) => mention.ids.includes(b.id) || mention.ids.includes(b.name.toLowerCase()));
    if (wanted.length) return { bot: wanted[0], picked_by: "mention", score: 0 };
    // A name that is not in this room is still a request: answer from the lead
    // and say the name was not one of the room's bots, rather than going mute.
    return { bot: leadBot, picked_by: "unknown-mention", score: 0 };
  }

  let best = null;
  let bestScore = 0;
  let tie = false;
  for (const bot of members) {
    const points = score(bot, text);
    if (points > bestScore) {
      best = bot;
      bestScore = points;
      tie = false;
    } else if (points > 0 && points === bestScore) {
      tie = true;
    }
  }
  // One clear keyword winner that is not the lead: route it. Anything tied or
  // empty goes to the lead, which is the predictable answer.
  if (best && !tie && best.id !== leadBot.id && bestScore >= 2) {
    return { bot: best, picked_by: "routing", score: bestScore };
  }
  return { bot: leadBot, picked_by: "lead", score: bestScore };
}

// The standing instructions a bot answers with. The app persona (what the page
// shows) stays in agent-chat.mjs; this adds who the bot is, in its own voice.
export function botSystemPrompt(bot, basePrompt) {
  const lines = [
    `You are ${bot.name}, ${bot.title}, one of the agents on the Meta OS desk.`,
    bot.voice,
    "You answer as a colleague in a room: the operator is a person reading this screen.",
    basePrompt,
  ];
  return lines.filter(Boolean).join(" ");
}
