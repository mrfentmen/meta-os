"use strict";
/* Meta OS shell notifications (notify.js).
 * Standalone drop-in for shell.html — NO edits to shell.html itself.
 * Usage (manual, once): add <script src="notify.js"></script> before </body> in shell.html.
 * What it does:
 *  - injects a topbar bell with an unread badge (into #topbar .icons, fallback #topbar)
 *  - polls http://127.0.0.1:18935/messages?room=general every 10s
 *  - dropdown lists new messages; click marks read in localStorage
 *  - keeps a poll/message log (in-memory + localStorage + console)
 */
(function () {
  var ROOM = "general";
  var API = "http://127.0.0.1:18935/messages?room=" + encodeURIComponent(ROOM);
  var POLL_MS = 10000;
  var LAST_READ_KEY = "metaos-notify-last-read-general";
  var LOG_KEY = "metaos-notify-log";
  var MAX_LOG = 100;

  var state = { messages: [], unread: 0, lastRead: 0, log: [] };

  function loadLastRead() {
    try {
      var v = window.localStorage.getItem(LAST_READ_KEY);
      var n = parseInt(v, 10);
      return isNaN(n) ? 0 : n;
    } catch (e) { return 0; }
  }

  function saveLastRead(id) {
    try { window.localStorage.setItem(LAST_READ_KEY, String(id)); } catch (e) {}
  }

  function loadLog() {
    try {
      var raw = window.localStorage.getItem(LOG_KEY);
      if (!raw) return [];
      var d = JSON.parse(raw);
      return Array.isArray(d) ? d : [];
    } catch (e) { return []; }
  }

  function saveLog() {
    try { window.localStorage.setItem(LOG_KEY, JSON.stringify(state.log.slice(-MAX_LOG))); } catch (e) {}
  }

  function addLog(entry) {
    entry.ts = new Date().toISOString();
    entry.room = ROOM;
    state.log.push(entry);
    if (state.log.length > MAX_LOG) state.log = state.log.slice(-MAX_LOG);
    saveLog();
    try {
      if (entry.kind === "poll") console.log("[notify] poll " + ROOM + ": " + entry.total + " msgs, " + entry.unread + " unread");
      else if (entry.kind === "read") console.log("[notify] marked read up to #" + entry.upto);
      else console.log("[notify]", entry);
    } catch (e) {}
  }

  function maxId(msgs) {
    var m = 0, i;
    for (i = 0; i < msgs.length; i++) if (msgs[i] && msgs[i].id > m) m = msgs[i].id;
    return m;
  }

  function esc(s) { return String(s == null ? "" : s); }

  // ---- UI ----
  var bell = null, badge = null, drop = null, listEl = null;

  function injectStyles() {
    if (document.getElementById("notify-style")) return;
    var st = document.createElement("style");
    st.id = "notify-style";
    st.textContent = [
      "#notify-bell{position:relative;cursor:pointer;border:1px solid transparent;background:transparent;color:inherit;font-size:14px;padding:0 6px;border-radius:8px;line-height:1}",
      "#notify-bell:hover{border-color:var(--accent,#4f7ec2)}",
      "#notify-badge{position:absolute;top:-6px;right:-2px;min-width:15px;height:15px;padding:0 3px;border-radius:8px;background:#d00;color:#fff;font-size:10px;line-height:15px;text-align:center;display:none}",
      "#notify-drop{position:fixed;top:30px;right:8px;width:320px;max-height:50vh;overflow-y:auto;background:var(--bar,#111);color:var(--fg,#eee);border:1px solid #555;border-radius:10px;z-index:200;display:none;box-shadow:0 8px 32px rgba(0,0,0,.5)}",
      "#notify-drop.open{display:block}",
      "#notify-drop .hd{display:flex;gap:8px;align-items:center;padding:8px 10px;border-bottom:1px solid #555;font-weight:bold}",
      "#notify-drop .hd button{margin-left:auto;font-size:11px;padding:2px 8px;cursor:pointer}",
      "#notify-drop .item{padding:8px 10px;border-bottom:1px solid #333;cursor:pointer;font-size:12px}",
      "#notify-drop .item:hover{background:rgba(127,127,127,.25)}",
      "#notify-drop .item b{color:var(--accent,#4f7ec2)}",
      "#notify-drop .item .meta{opacity:.6;font-size:11px;margin-left:6px}",
      "#notify-drop .empty{padding:12px;text-align:center;opacity:.7;font-size:12px}"
    ].join("\n");
    document.head.appendChild(st);
  }

  function buildUI() {
    injectStyles();
    var bar = document.getElementById("topbar");
    if (!bar) return false;
    if (document.getElementById("notify-bell")) return true;
    bell = document.createElement("button");
    bell.id = "notify-bell";
    bell.title = "Board notifications (#general)";
    bell.setAttribute("aria-label", "Board notifications");
    bell.textContent = "\uD83D\uDD14"; // bell emoji
    badge = document.createElement("span");
    badge.id = "notify-badge";
    badge.textContent = "";
    bell.appendChild(badge);

    var icons = bar.querySelector(".icons");
    if (icons) icons.insertBefore(bell, icons.firstChild);
    else {
      var clock = document.getElementById("clock");
      if (clock && clock.parentNode === bar) bar.insertBefore(bell, clock);
      else bar.appendChild(bell);
    }

    drop = document.createElement("div");
    drop.id = "notify-drop";
    drop.setAttribute("role", "menu");
    drop.setAttribute("aria-label", "Board notifications");
    document.body.appendChild(drop);

    bell.addEventListener("click", function (e) {
      e.stopPropagation();
      var open = drop.classList.toggle("open");
      // Clicking bell to close the dropdown counts as "seen" -> mark read.
      if (!open) markRead();
    });
    // Click anywhere inside dropdown marks read in localStorage.
    drop.addEventListener("click", function (e) {
      var t = e.target;
      if (t && t.dataset && t.dataset.act === "open-board") return; // let link work, still mark read below
      markRead();
    });
    document.addEventListener("pointerdown", function (e) {
      if (drop && drop.classList.contains("open") && !drop.contains(e.target) && e.target !== bell && !bell.contains(e.target)) {
        drop.classList.remove("open");
      }
    });
    return true;
  }

  function render() {
    if (!badge || !drop) return;
    if (state.unread > 0) {
      badge.style.display = "block";
      badge.textContent = state.unread > 99 ? "99+" : String(state.unread);
      bell.setAttribute("aria-label", "Board notifications (" + state.unread + " unread)");
    } else {
      badge.style.display = "none";
      badge.textContent = "";
      bell.setAttribute("aria-label", "Board notifications");
    }
    var html = '<div class="hd"><span>Board #general</span>' +
      '<button data-act="open-board" title="Open board.html">Board</button>' +
      '<button data-act="mark-read" title="Mark all read">Mark read</button></div>';
    var fresh = state.messages.filter(function (m) { return m.id > state.lastRead; });
    var show = fresh.length ? fresh : state.messages.slice(-10);
    if (!show.length) {
      html += '<div class="empty">No messages yet.</div>';
    }
    // Render newest-first via DOM (escaped with textContent-safe builder).
    drop.innerHTML = html;
    var boardBtn = drop.querySelector('[data-act="open-board"]');
    if (boardBtn) boardBtn.addEventListener("click", function (ev) {
      ev.stopPropagation();
      markRead();
      try { window.open("board.html", "_blank"); } catch (e) { window.location.href = "board.html"; }
    });
    var markBtn = drop.querySelector('[data-act="mark-read"]');
    if (markBtn) markBtn.addEventListener("click", function (ev) { ev.stopPropagation(); markRead(); });
    listEl = document.createElement("div");
    drop.appendChild(listEl);
    if (!show.length) return;
    var ordered = show.slice().sort(function (a, b) { return b.id - a.id; });
    ordered.forEach(function (m) {
      var d = document.createElement("div");
      d.className = "item";
      d.title = "Click to mark read";
      var b = document.createElement("b");
      b.textContent = esc(m.author || "anon");
      d.appendChild(b);
      var meta = document.createElement("span");
      meta.className = "meta";
      var when = "";
      try { when = m.ts ? new Date(m.ts * 1000).toLocaleTimeString() : ""; } catch (e) {}
      meta.textContent = " #" + m.id + (when ? " " + when : "");
      d.appendChild(meta);
      d.appendChild(document.createElement("br"));
      var txt = document.createElement("span");
      txt.textContent = esc(m.text || "");
      d.appendChild(txt);
      listEl.appendChild(d);
    });
  }

  function markRead() {
    var upto = maxId(state.messages);
    if (upto < state.lastRead) upto = state.lastRead;
    state.lastRead = upto;
    saveLastRead(upto);
    state.unread = 0;
    addLog({ kind: "read", upto: upto });
    render();
  }

  function poll() {
    fetch(API).then(function (r) {
      if (!r.ok) throw new Error("http " + r.status);
      return r.json();
    }).then(function (d) {
      var msgs = (d && d.messages) || [];
      state.messages = msgs;
      var m = maxId(msgs);
      var unread = msgs.filter(function (x) { return x.id > state.lastRead; }).length;
      state.unread = unread;
      addLog({ kind: "poll", total: msgs.length, unread: unread, maxId: m });
      render();
    }).catch(function (err) {
      addLog({ kind: "error", error: String((err && err.message) || err) });
    });
  }

  function init() {
    state.lastRead = loadLastRead();
    state.log = loadLog();
    if (!buildUI()) {
      // topbar not ready yet; retry shortly (still no shell.html edits needed)
      setTimeout(init, 500);
      return;
    }
    render();
    poll();
    setInterval(poll, POLL_MS);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();

  // Exposed for debugging/tests.
  try {
    window.MetaOSNotify = {
      poll: poll, markRead: markRead, render: render,
      get state() { return state; },
      get unread() { return state.unread; },
      get log() { return state.log; },
      ROOM: ROOM, API: API, POLL_MS: POLL_MS
    };
  } catch (e) {}
})();
