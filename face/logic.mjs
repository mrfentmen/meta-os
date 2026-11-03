// Face pure logic — no DOM, no localStorage, no rendering.
//
// face.js is a browser script: it owns the DOM. Everything in this module is the
// part that does not need a browser, so a Node test can pin the rules the desktop
// actually follows. face.js imports these and renders the results.
//
// The rule for adding here: if it touches document, window, localStorage or the
// clock, it stays in face.js. If it is a pure transform of values, it lives here.

/* ---------------------------------------------------------------- calculator */

export function initialCalc() {
  return { cur: "0", prev: null, op: null, fresh: true };
}

// The face calculator is sequential, not algebraic: it applies the pending
// operator as soon as the next one is pressed, so 2 + 3 * 4 is 20, not 14.
export function calc(a, b, op) {
  const x = parseFloat(a);
  const y = parseFloat(b);
  if (op === "+") return String(x + y);
  if (op === "-") return String(x - y);
  if (op === "*") return String(x * y);
  if (op === "/") return y === 0 ? "Error" : String(x / y);
  return String(y);
}

// One key press, one new state. Pure: the caller keeps the state it passes in.
// Keys are the grid labels plus "Backspace" and "Escape".
export function calcKey(state, key) {
  const next = { ...state };
  if (/[0-9.]/.test(key)) {
    if (next.fresh || next.cur === "0" || next.cur === "Error") {
      next.cur = key === "." ? "0." : key;
      next.fresh = false;
    } else if (key !== "." || !next.cur.includes(".")) {
      next.cur += key;
    }
  } else if ("+-*/".includes(key)) {
    if (next.prev !== null && next.op && !next.fresh) next.cur = calc(next.prev, next.cur, next.op);
    next.prev = next.cur;
    next.op = key;
    next.fresh = true;
  } else if (key === "=" || key === "Enter") {
    if (next.prev !== null && next.op) {
      next.cur = calc(next.prev, next.cur, next.op);
      next.prev = null;
      next.op = null;
      next.fresh = true;
    }
  } else if (key === "C" || key === "Escape") {
    return initialCalc();
  } else if (key === "Backspace") {
    next.cur = next.cur.length > 1 ? next.cur.slice(0, -1) : "0";
  }
  return next;
}

/* ------------------------------------------------------------------ calendar */

export const DOW = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

export function daysInMonth(year, month) {
  return new Date(year, month + 1, 0).getDate();
}

// The leading blanks before day 1, and the day numbers, for a month grid.
export function monthCells(year, month) {
  const leading = new Date(year, month, 1).getDay();
  const days = [];
  for (let d = 1; d <= daysInMonth(year, month); d++) days.push(d);
  return { leading, days };
}

// Shift a {year, month} view by whole months, rolling the year at both ends.
export function shiftMonth(view, delta) {
  const d = new Date(view.year, view.month + delta, 1);
  return { year: d.getFullYear(), month: d.getMonth() };
}

// The event key the calendar stores under. Unpadded, as the face always wrote it.
export function dayKey(date) {
  return date.getFullYear() + "-" + (date.getMonth() + 1) + "-" + date.getDate();
}

/* ------------------------------------------------------------------ terminal */

export const TERMINAL_HELP = "commands: status help uptime mem ps";

const TERMINAL_ANSWERS = {
  help: [TERMINAL_HELP],
  status: ["STATUS tasks 7 heap_total 512K milestone K6"],
  mem: ["mem frames_free 118784 heap_total 512K"],
  ps: [
    "ps id 1 state running (kernel)",
    "ps id 4 state sleeping (sleeper)",
    "ps id 7 state running (console)",
    "ps id 8 state held (readkey - spawn held until its boot proof)",
  ],
  uptime: ["uptime 141s ticks 14100"],
};

// What the shell answers for one input line. Extra whitespace is trimmed, an
// empty line answers nothing at all, and an unknown word says so and reprints
// the command list rather than guessing.
export function terminalAnswer(raw) {
  const cmd = typeof raw === "string" ? raw.trim().toLowerCase() : "";
  if (cmd === "") return { lines: [], clear: false };
  if (cmd === "clear") return { lines: [], clear: true };
  const lines = TERMINAL_ANSWERS[cmd];
  if (!lines) return { lines: ["unknown command", TERMINAL_HELP], clear: false };
  return { lines: lines.slice(), clear: false };
}

/* --------------------------------------------------------------------- notes */

// A note is {id, title, text}. The face allows an empty body — a new note starts
// empty — so nothing here refuses one; only a missing id is refused.
export function newNote(notes, id, title = "Untitled", text = "") {
  if (!Number.isInteger(id)) throw new TypeError("note: id must be an integer");
  return [{ id, title, text }, ...notes];
}

export function updateNote(notes, id, patch) {
  return notes.map((n) => (n.id === id ? { ...n, ...patch, id: n.id } : n));
}

export function deleteNote(notes, id) {
  return notes.filter((n) => n.id !== id);
}

export function findNote(notes, id) {
  return notes.find((n) => n.id === id) || null;
}

/* ------------------------------------------------------------------ settings */

export const SETTING_KEYS = ["mode", "bar", "speed", "paused", "variant", "bg"];
export const MODES = ["dark", "light"];
export const BAR_COLOURS = ["auto", "black", "white", "blue"];

// One write path for settings. An unknown key is refused by name instead of
// being silently dropped, and a value outside its set is refused the same way.
export function setSetting(settings, key, value) {
  if (!SETTING_KEYS.includes(key)) {
    throw new Error("settings: unknown key " + JSON.stringify(key));
  }
  if (key === "mode" && !MODES.includes(value)) {
    throw new Error("settings: mode must be one of " + MODES.join(", "));
  }
  if (key === "bar" && !BAR_COLOURS.includes(value)) {
    throw new Error("settings: bar must be one of " + BAR_COLOURS.join(", "));
  }
  if (key === "speed") {
    if (!Number.isFinite(value) || value <= 0) throw new Error("settings: speed must be a positive number");
    return { ...settings, speed: value };
  }
  if (key === "paused") return { ...settings, paused: value === true };
  return { ...settings, [key]: value };
}

/* --------------------------------------------------------- files and trash */

// The file store is a flat list of {id, name, folder, trashed, content}. The
// folder is a path like "Home/logs"; there is no tree to walk, so this is a
// filter and a path guard, which is exactly what the window needs.
export function filesIn(fs, trashed = false) {
  return fs.filter((f) => f.trashed === trashed);
}

// Resolve a relative path inside a root, refusing anything that escapes it.
// This is the guard the Files window needs before it puts a folder in a header.
export function resolvePath(root, rel) {
  if (typeof rel !== "string" || rel.length === 0) throw new Error("path: a relative path is required");
  if (rel.startsWith("/") || /^[a-zA-Z]:/.test(rel)) throw new Error("path: absolute paths are refused: " + rel);
  const parts = [];
  for (const part of rel.split("/")) {
    if (part === "" || part === ".") continue;
    if (part === "..") {
      if (parts.length === 0) throw new Error("path: escapes the root: " + rel);
      parts.pop();
      continue;
    }
    parts.push(part);
  }
  return [root.replace(/\/+$/, ""), ...parts].join("/");
}

export function withinRoot(root, rel) {
  try {
    return resolvePath(root, rel).startsWith(root.replace(/\/+$/, "") + "/");
  } catch {
    return false;
  }
}

export function moveToTrash(fs, id) {
  const item = fs.find((f) => f.id === id);
  if (!item) throw new Error("trash: no file with id " + id);
  return fs.map((f) => (f.id === id ? { ...f, trashed: true } : f));
}

// Restore keeps the folder the file was deleted from, so it lands back where it
// was rather than at the root.
export function restoreFromTrash(fs, id) {
  const item = fs.find((f) => f.id === id);
  if (!item) throw new Error("trash: no file with id " + id);
  return fs.map((f) => (f.id === id ? { ...f, trashed: false } : f));
}

export function emptyTrash(fs) {
  return fs.filter((f) => !f.trashed);
}

/* ------------------------------------------------------------ window state */

// Windows are an ordered list, oldest first; the last one is focused. The face
// keeps the elements, this keeps the order, so focus and close have one rule.
export function initialWindowState() {
  return { order: [], z: 20 };
}

export function openWindow(state, id) {
  if (state.order.includes(id)) return { state, focused: id, opened: false };
  return { state: { order: [...state.order, id], z: state.z + 1 }, focused: id, opened: true };
}

export function focusWindow(state, id) {
  if (!state.order.includes(id)) throw new Error("window: not open: " + id);
  return { order: [...state.order.filter((x) => x !== id), id], z: state.z + 1 };
}

export function closeWindow(state, id) {
  return { order: state.order.filter((x) => x !== id), z: state.z };
}

export function focusedWindow(state) {
  return state.order.length ? state.order[state.order.length - 1] : null;
}

// Opening an already-open window focuses it and opens nothing new.
export function openOrFocus(state, id) {
  return state.order.includes(id) ? focusWindow(state, id) : openWindow(state, id).state;
}
