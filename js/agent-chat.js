/* The in-app agent chat — one box, every application.
 *
 * Usage, one line before </body>:
 *   <script src="/js/agent-chat.js" data-app="officina" data-label="Officina"></script>
 *
 * data-app          persona id the server knows (server/agent-chat.mjs, APP_IDS)
 * data-label        what the panel calls this app (default: the app id)
 * data-accent       color of the launcher and the agent's rule (default #7fb8ff)
 * data-placeholder  the input's placeholder
 * data-context      a fixed paragraph about what the page is showing, or leave
 *                   it out and define window.metaAgentContext() -> string, which
 *                   is read fresh for every question (the trio pages do this
 *                   with their watch list)
 * data-api          backend base (default: this origin, or 127.0.0.1:18934 when
 *                   the page is served from the 18900 face or from file://)
 *
 * The box asks POST <api>/api/agent/ask { app, question, context, bot, thread }.
 * It does not compose an answer, and it does not retry a failed one: every
 * refusal is printed with the port and the server's own message, so a demo
 * shows what actually happened. window.MetaAgentChat exposes ask/open/close for
 * probes.
 *
 * Two things come from the roster (server/bot-roster.mjs):
 *   - a row of bot chips under the header, one per bot of this app. Picking one
 *     asks that bot; typing @Name in the box does the same thing for one
 *     message. With nothing picked and no mention the app's lead bot answers.
 *   - a thread id kept in localStorage, so reopening the panel (or the app)
 *     re-reads the same room instead of starting from nothing.
 */
(function () {
  "use strict";

  var script = document.currentScript;
  var APP = (script && script.dataset.app) || "general";
  var LABEL = (script && script.dataset.label) || APP;
  var ACCENT = (script && script.dataset.accent) || "#7fb8ff";
  var PLACEHOLDER =
    (script && script.dataset.placeholder) || "Ask the " + LABEL + " agent about this screen";
  var STATIC_CONTEXT = (script && script.dataset.context) || "";
  var MAX_QUESTION = 2000;
  var MAX_CONTEXT = 4000;
  var THREAD_KEY = "meta-agent-thread:" + APP;
  var THREAD_ID = /^[a-z0-9][a-z0-9_-]{0,63}$/;

  function threadId() {
    var saved = "";
    try {
      saved = window.localStorage.getItem(THREAD_KEY) || "";
    } catch (e) {
      saved = "";
    }
    if (THREAD_ID.test(saved)) return saved;
    var fresh = (APP + "-" + Math.random().toString(36).slice(2, 8)).toLowerCase();
    try {
      window.localStorage.setItem(THREAD_KEY, fresh);
    } catch (e) {
      /* private mode: this visit keeps the thread in memory only */
    }
    return fresh;
  }

  var THREAD = threadId();
  var BOTS = [];
  var BOT = null;

  // The face pages (18900) and a file:// open are different origins from the
  // API, and the chat is the one call that must still land: 18934 is the
  // server that answers /api/agent/ask in the image.
  function apiBase() {
    var explicit = script && script.dataset.api;
    if (explicit) return explicit.replace(/\/+$/, "");
    if (typeof location !== "object" || !location.origin || location.protocol === "file:") {
      return "http://127.0.0.1:18934";
    }
    if (location.port === "18900") return "http://127.0.0.1:18934";
    return location.origin;
  }
  var API = apiBase();
  var PORT = API.replace(/^https?:\/\//, "").replace(/\/.*$/, "");

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function contextFor() {
    var dyn = "";
    if (typeof window.metaAgentContext === "function") {
      try {
        dyn = String(window.metaAgentContext() || "");
      } catch (e) {
        dyn = "";
      }
    }
    var text = [STATIC_CONTEXT, dyn].filter(Boolean).join("\n");
    return text.slice(0, MAX_CONTEXT);
  }

  // The panel borrows the page's own typeface and takes only an accent, so it
  // reads as part of that app instead of a widget pasted on top of twelve
  // different designs.
  var css = document.createElement("style");
  css.textContent = [
    "#meta-agent-chat{position:fixed;left:18px;bottom:18px;z-index:880;font-family:inherit;font-size:13px;color:#e9f1ff;--mac-accent:" + ACCENT + "}",
    "#meta-agent-chat *{box-sizing:border-box}",
    "#meta-agent-chat-launch{display:flex;align-items:center;gap:8px;height:38px;padding:0 14px;border:1px solid rgba(140,170,220,.4);border-radius:19px;background:rgba(10,16,28,.92);color:inherit;cursor:pointer;font:inherit;letter-spacing:.02em}",
    "#meta-agent-chat-launch:hover{border-color:var(--mac-accent)}",
    "#meta-agent-chat-launch .dot{width:7px;height:7px;border-radius:50%;background:var(--mac-accent)}",
    "#meta-agent-chat[data-state=down] #meta-agent-chat-launch .dot{background:#ffb14a}",
    "#meta-agent-chat-panel{position:absolute;left:0;bottom:48px;display:none;flex-direction:column;width:352px;max-height:min(64vh,470px);border:1px solid rgba(140,170,220,.32);border-radius:12px;background:#0b1220;box-shadow:0 20px 55px rgba(0,0,0,.6);overflow:hidden}",
    '#meta-agent-chat[data-open="1"] #meta-agent-chat-panel{display:flex}',
    "#meta-agent-chat-head{display:flex;align-items:baseline;gap:8px;padding:10px 12px;border-bottom:1px solid rgba(140,170,220,.18)}",
    "#meta-agent-chat-head b{font-weight:650;font-size:12.5px;letter-spacing:.02em}",
    "#meta-agent-chat-head .state{margin-left:auto;font:10.5px ui-monospace,SFMono-Regular,Menlo,monospace;color:#8ea3c2;text-align:right}",
    "#meta-agent-chat-head .state.bad{color:#ff9a8f}",
    "#meta-agent-chat-log{flex:1;min-height:130px;overflow-y:auto;padding:10px 12px;display:flex;flex-direction:column;gap:8px}",
    "#meta-agent-chat-log p{margin:0;overflow-wrap:anywhere;line-height:1.5;font-size:12.5px}",
    "#meta-agent-chat-log .user{align-self:flex-end;max-width:92%;padding:4px 9px;border:1px solid rgba(140,170,220,.24);border-radius:9px;background:rgba(40,60,90,.4);font:11.5px ui-monospace,SFMono-Regular,Menlo,monospace}",
    "#meta-agent-chat-log .agent{border-left:2px solid var(--mac-accent);padding-left:9px}",
    "#meta-agent-chat-log .note{color:#8b9cb8;font:11px ui-monospace,SFMono-Regular,Menlo,monospace}",
    "#meta-agent-chat-log .bad{color:#ff9a8f;border-left:2px solid #ff6b5e;padding-left:9px}",
    "#meta-agent-chat-log .who{display:block;margin-bottom:2px;font:10px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--mac-accent);letter-spacing:.05em;text-transform:uppercase}",
    "#meta-agent-chat-bots{display:flex;flex-wrap:wrap;gap:5px;padding:8px 10px;border-bottom:1px solid rgba(140,170,220,.14)}",
    "#meta-agent-chat-bots button{height:24px;padding:0 9px;border:1px solid rgba(140,170,220,.28);border-radius:12px;background:transparent;color:#a9bcd8;font:11px ui-monospace,SFMono-Regular,Menlo,monospace;cursor:pointer}",
    "#meta-agent-chat-bots button[aria-pressed=true]{border-color:var(--mac-accent);background:rgba(40,70,120,.4);color:#e9f1ff}",
    "#meta-agent-chat form{display:flex;gap:6px;padding:9px 10px 10px;border-top:1px solid rgba(140,170,220,.18)}",
    "#meta-agent-chat input{flex:1;min-width:0;height:34px;padding:0 9px;border:1px solid rgba(140,170,220,.3);border-radius:7px;background:#080f1a;color:inherit;font:12px ui-monospace,SFMono-Regular,Menlo,monospace}",
    "#meta-agent-chat button[type=submit]{height:34px;padding:0 13px;border:1px solid var(--mac-accent);border-radius:7px;background:rgba(30,60,100,.45);color:inherit;cursor:pointer;font:inherit}",
    "#meta-agent-chat button[type=submit]:disabled{opacity:.5;cursor:default}",
    "#meta-agent-chat :focus-visible{outline:2px solid var(--mac-accent);outline-offset:2px}",
    "@media (max-width:560px){#meta-agent-chat{left:10px;bottom:10px}#meta-agent-chat-panel{width:min(92vw,352px)}}"
  ].join("\n");
  document.head.appendChild(css);

  var root = document.createElement("div");
  root.id = "meta-agent-chat";
  root.setAttribute("data-app", APP);
  root.innerHTML =
    '<button id="meta-agent-chat-launch" type="button" aria-expanded="false" aria-controls="meta-agent-chat-panel">' +
      '<span class="dot" aria-hidden="true"></span><span>' + esc(LABEL) + " agent" + "</span>" +
    "</button>" +
    '<div id="meta-agent-chat-panel" role="dialog" aria-label="' + esc(LABEL) + ' agent chat">' +
      '<div id="meta-agent-chat-head"><b>' + esc(LABEL) + '</b><span class="state">reading the server…</span></div>' +
      '<div id="meta-agent-chat-bots" role="group" aria-label="Which agent answers"></div>' +
      '<div id="meta-agent-chat-log" role="log" aria-live="polite" aria-label="Agent transcript"></div>' +
      '<form autocomplete="off"><input type="text" name="question" maxlength="' + MAX_QUESTION + '" placeholder="' + esc(PLACEHOLDER) + '" aria-label="' + esc(PLACEHOLDER) + '"><button type="submit">Send</button></form>' +
    "</div>";
  document.body.appendChild(root);

  var toggle = root.querySelector("#meta-agent-chat-launch");
  var panel = root.querySelector("#meta-agent-chat-panel");
  var log = root.querySelector("#meta-agent-chat-log");
  var stateEl = root.querySelector("#meta-agent-chat-head .state");
  var botsEl = root.querySelector("#meta-agent-chat-bots");
  var form = root.querySelector("form");
  var input = form.querySelector("input");
  var sendBtn = form.querySelector("button");

  // The first line is an instruction, not a fake message: it says what this
  // agent can see and that it cannot act.
  var intro = document.createElement("p");
  intro.className = "note";
  intro.textContent =
    "Agent for " + LABEL + ". It reads what this page shows and answers from it; it cannot open apps or change anything.";
  log.appendChild(intro);

  function setState(text, bad) {
    stateEl.textContent = text;
    stateEl.className = bad ? "state bad" : "state";
    root.dataset.state = bad ? "down" : "up";
  }

  function addTurn(kind, text, who) {
    var p = document.createElement("p");
    p.className = kind;
    if (who) {
      var label = document.createElement("span");
      label.className = "who";
      label.textContent = who;
      p.appendChild(label);
    }
    p.appendChild(document.createTextNode(text));
    log.appendChild(p);
    log.scrollTop = log.scrollHeight;
    return p;
  }

  // "Who answered, and how did that get decided" in the operator's words,
  // never in the server's field names.
  function why(pickedBy) {
    var map = {
      chosen: "the agent you picked",
      mention: "you named it",
      routing: "routed by the desk",
      lead: "this desk's lead",
      "everyone-to-lead": "@everyone, answered by the lead",
      "unknown-mention": "that name is not in this room, so the lead answered",
      "unknown-bot": "that agent is not in this room, so the lead answered",
    };
    return map[pickedBy] || "answered";
  }

  // One chip per bot of this app. No bots (an older server) leaves the row
  // empty rather than offering a name the server would not know, and the box
  // still answers with the app's own agent.
  function renderBots() {
    botsEl.innerHTML = "";
    if (!BOTS.length) {
      botsEl.style.display = "none";
      return;
    }
    botsEl.style.display = "";
    BOTS.forEach(function (bot) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = bot.name;
      b.title = bot.title;
      b.setAttribute("aria-pressed", String(BOT && BOT.id === bot.id));
      b.addEventListener("click", function () {
        BOT = bot;
        renderBots();
        input.focus();
      });
      botsEl.appendChild(b);
    });
  }

  function loadRoster() {
    return fetch(API + "/api/agent/roster", { cache: "no-store" })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (body) {
        var all = (body && body.bots) || [];
        // The room is the whole desk: this page's own bot first (it answers by
        // default), then every other desk's bot, reachable by name.
        var mine = all.filter(function (b) { return b.app === APP; });
        var rest = all.filter(function (b) { return b.app !== APP; });
        BOTS = mine.concat(rest);
        if (!BOT || !BOTS.some(function (b) { return b.id === BOT.id; })) {
          BOT = BOTS[0] || null;
        }
        renderBots();
        return BOTS;
      })
      .catch(function () {
        // The roster is a convenience; an older or unreachable server must not
        // stop the box from answering. The chips stay hidden and the ask call
        // lets the server pick the bot.
        BOTS = [];
        renderBots();
        return [];
      });
  }

  // Reopening the panel reads the room back. A thread the server does not have
  // yet answers with no turns, which is the empty state, not an error.
  function loadThread() {
    return fetch(API + "/api/agent/thread?id=" + encodeURIComponent(THREAD), { cache: "no-store" })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (body) {
        var turns = (body && body.turns) || [];
        if (!turns.length) return turns;
        log.innerHTML = "";
        turns.forEach(function (turn) {
          if (turn.role === "operator") addTurn("user", turn.text);
          else if (turn.role === "error") addTurn("bad", turn.text);
          else addTurn("agent", turn.text, turn.bot);
        });
        return turns;
      })
      .catch(function () {
        return [];
      });
  }

  function health() {
    return fetch(API + "/api/health", { cache: "no-store" })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (body) {
        var model = (body && body.model) || {};
        if (model.configured && model.live_enabled) setState("model live", false);
        else if (!model.configured) setState("no key on " + PORT, true);
        else setState("calls held", true);
        return stateEl.textContent;
      })
      .catch(function (err) {
        setState("server unreachable on " + PORT, true);
        return "server unreachable on " + PORT + " (" + err.message + ")";
      });
  }

  // One question, one call. Resolves { ok, reply } or { ok:false, reason } so a
  // probe can read the outcome without scraping the DOM.
  function ask(question) {
    var text = String(question == null ? "" : question).trim();
    if (!text) return Promise.resolve({ ok: false, reason: "empty question" });
    if (text.length > MAX_QUESTION) text = text.slice(0, MAX_QUESTION);
    addTurn("user", text);
    sendBtn.disabled = true;
    var pending = addTurn("note", "asking " + PORT + " …");
    var controller = typeof AbortController === "function" ? new AbortController() : null;
    var timer = controller ? setTimeout(function () { controller.abort(); }, 60000) : null;

    return fetch(API + "/api/agent/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ app: APP, question: text, context: contextFor(), bot: BOT ? BOT.id : null, thread: THREAD }),
      signal: controller ? controller.signal : undefined,
    })
      .then(function (res) {
        return res.json().catch(function () { return {}; }).then(function (body) {
          return { res: res, body: body };
        });
      })
      .then(function (out) {
        if (timer) clearTimeout(timer);
        pending.remove();
        sendBtn.disabled = false;
        if (!out.res.ok) {
          var reason = (out.body && out.body.error) || "Agent request failed with HTTP " + out.res.status + ".";
          addTurn("bad", reason);
          setState("refused on " + PORT, true);
          return { ok: false, reason: reason };
        }
        var reply = out.body && out.body.reply;
        if (typeof reply !== "string" || !reply.trim()) {
          var empty = "The agent returned no reply text from " + API + "/api/agent/ask.";
          addTurn("bad", empty);
          return { ok: false, reason: empty };
        }
        var answered = out.body && out.body.bot;
        addTurn("agent", reply, answered ? answered.name : null);
        // A routed answer says so, once, under the reply. The operator picked
        // nothing, and the transcript should not pretend otherwise.
        var picked = out.body && out.body.picked_by;
        if (answered && picked && picked !== "chosen" && picked !== "mention" && picked !== "lead") {
          addTurn("note", answered.name + " — " + why(picked));
        }
        if (answered) {
          var match = BOTS.filter(function (b) { return b.id === answered.id; })[0];
          if (match) {
            BOT = match;
            renderBots();
          }
        }
        var spend = out.body && out.body.spend;
        setState(
          "model live · " + (answered ? answered.name + " · " : "") +
            (out.body.latency_ms ? out.body.latency_ms + " ms" : "answered") +
            (spend && typeof spend.remaining_usd === "number" ? " · $" + spend.remaining_usd.toFixed(2) + " left" : ""),
          false
        );
        return { ok: true, reply: reply, body: out.body };
      })
      .catch(function (err) {
        if (timer) clearTimeout(timer);
        pending.remove();
        sendBtn.disabled = false;
        var reason =
          err && err.name === "AbortError"
            ? "The agent did not answer within 60 s on " + PORT + "."
            : "Agent unreachable on " + PORT + ": " + (err && err.message ? err.message : String(err)) + ". Is the site server running?";
        addTurn("bad", reason);
        setState("server unreachable on " + PORT, true);
        return { ok: false, reason: reason };
      });
  }

  function open() {
    root.dataset.open = "1";
    toggle.setAttribute("aria-expanded", "true");
    input.focus();
    health();
    // Both reads are best-effort: an unreachable roster or thread leaves the
    // box usable instead of blank.
    loadRoster().then(loadThread);
  }
  function close() {
    delete root.dataset.open;
    toggle.setAttribute("aria-expanded", "false");
  }

  toggle.addEventListener("click", function () {
    if (root.dataset.open) close(); else open();
  });
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" && root.dataset.open) close();
  });
  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var q = input.value;
    input.value = "";
    ask(q);
    input.focus();
  });

  // A closed box still reads health once, so the launcher's dot can say the
  // backend is down before anyone clicks it.
  health();

  window.MetaAgentChat = {
    app: APP,
    thread: function () { return THREAD; },
    bots: function () { return BOTS.slice(); },
    bot: function () { return BOT ? BOT.id : null; },
    loadRoster: loadRoster,
    loadThread: loadThread,
    api: API,
    ask: ask,
    open: open,
    close: close,
    health: health,
    log: log,
    input: input,
    root: root,
  };
})();
