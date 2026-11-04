// Duty agent console — one behaviour, three skins.
//
// The original single console gave every operator the same capabilities. When
// it was split into Vigiles, Ignis and Medicus, the agent console existed only
// on Medicus, so two divisions had no way to ask about the board they were
// watching. This module is that console: the request, the transcript, the
// refusal and the health line are identical on all three pages, and each page
// owns the CSS that makes it look like its own division.
//
// The reply is whatever the server's /api/agent/ask returns. Nothing here
// composes an answer, and a failure is printed with the endpoint name.

import { backendBase, el, MAX_WATCHED } from "./core.js";

const TURN_CLASS = {
  user: "turn user",
  agent: "turn agent",
  note: "turn note",
  bad: "turn bad",
};

// One paragraph of plain text per watched camera, with the recorded result.
// It is the context the model is allowed to use; it is not a claim about the
// world beyond this board.
export function boardContext(store) {
  const watched = [...store.watch].map((id) => store.byId.get(id)).filter(Boolean);
  if (watched.length === 0) {
    return "The board is empty. " + store.cameras.length + " cameras are available to watch.";
  }
  const lines = watched.map((cam) => {
    const r = store.results.get(cam.id);
    const state = !r
      ? "not assessed"
      : r.status === "failed"
        ? "assessment failed: " + r.reason
        : (r.flagged ? "flagged: " : "clear: ") + r.category + (r.summary ? ". " + r.summary : "");
    return "- " + cam.name + " (" + cam.area + "): " + state;
  });
  return "Watched cameras, " + watched.length + " of " + MAX_WATCHED + ":\n" + lines.join("\n");
}

export function createAgent({
  store,
  division,
  mount,
  title = "Duty agent",
  intro,
  placeholder = "Ask the duty agent about this board",
}) {
  const log = el("div", { class: "agent-log", role: "log", "aria-live": "polite" });
  const state = el("span", { class: "state", text: "reading the server…" });
  const input = el("input", {
    class: "agent-q",
    type: "text",
    placeholder,
    autocomplete: "off",
    "aria-label": placeholder,
  });
  const send = el("button", { class: "agent-send", type: "submit", text: "Send" });
  const form = el("form", { class: "agent-form" }, [input, send]);
  const head = el("header", { class: "agent-head" }, [el("h2", { text: title }), state]);
  // The mount is the page's own .agent element: its grid rows style the head,
  // transcript and composer without a wrapper in between.
  mount.replaceChildren(head, log, form);
  const root = mount;

  function addTurn(kind, text) {
    if (log.querySelector(".turn.note.only")) log.replaceChildren();
    const node = el("p", { class: TURN_CLASS[kind] || TURN_CLASS.note, text });
    log.append(node);
    log.scrollTop = log.scrollHeight;
    return node;
  }

  async function refreshHealth() {
    try {
      const res = await fetch(backendBase() + "/api/health", { cache: "no-store" });
      const body = await res.json();
      const model = body && body.model ? body.model : {};
      if (model.configured && model.live_enabled) {
        state.textContent = "model live";
        state.className = "state";
      } else if (!model.configured) {
        state.textContent = "no key configured";
        state.className = "state bad";
      } else {
        state.textContent = "calls held";
        state.className = "state bad";
      }
    } catch {
      state.textContent = "server unreachable";
      state.className = "state bad";
    }
    return state.textContent;
  }

  async function ask(question) {
    const text = String(question || "").trim();
    if (!text) return { ok: false, reason: "empty question" };
    addTurn("user", text);
    const pending = addTurn("note", "asking the model through " + backendBase() + " …");
    try {
      const res = await fetch(backendBase() + "/api/agent/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text, division: division.product, context: boardContext(store) }),
      });
      const body = await res.json().catch(() => ({}));
      pending.remove();
      if (!res.ok) {
        const reason = body.error || "Agent request failed with HTTP " + res.status + ".";
        addTurn("bad", reason);
        return { ok: false, reason };
      }
      if (typeof body.reply !== "string" || !body.reply.trim()) {
        const reason = "The agent returned no reply text from " + backendBase() + "/api/agent/ask.";
        addTurn("bad", reason);
        return { ok: false, reason };
      }
      addTurn("agent", body.reply);
      return { ok: true, reply: body.reply };
    } catch (err) {
      pending.remove();
      const reason =
        "Agent unreachable: " + (err && err.message ? err.message : String(err)) + ". The server is on " + backendBase() + ".";
      addTurn("bad", reason);
      return { ok: false, reason };
    }
  }

  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const question = input.value;
    input.value = "";
    ask(question);
  });

  const note = addTurn(
    "note",
    intro ||
      "Duty agent for " +
        division.name +
        ". It reads the board you are watching and the results on it; it cannot dispatch anyone."
  );
  note.classList.add("only");

  return { root, ask, addTurn, refreshHealth, log, input };
}
