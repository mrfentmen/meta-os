/* Meta chat box — one messaging surface for the product pages.
 *
 * Every page that ships this script gets the same room board the Messages app
 * opens: the same rooms, the same NOTIFY lines, the same server (board/board.mjs
 * on 18935). There is no second protocol and no account.
 *
 * Usage, one line before </body>:
 *   <script src="/js/site-chat.js" data-room="custos" data-label="Custos desk"></script>
 *
 * data-room  room key (default "general")
 * data-label who the page is, shown in the header (default "This desk")
 * data-api   board base URL (default http://127.0.0.1:18935)
 *
 * Failure is stated, never silent: a header line names the port that did not
 * answer, and the panel keeps the last message it managed to read.
 */
(function () {
  "use strict";

  var script = document.currentScript;
  // A page that carries several boards (#board-custos, #board-officina) picks
  // the room from the anchor, so clicking the Custos tile lands you in the same
  // room the Messages app shows for Custos, not in one shared "boards" room.
  function roomFromHash(fallback) {
    var m = /^#board-([a-z0-9-]{1,32})$/.exec(window.location.hash || "");
    return m ? m[1] : fallback;
  }
  var BASE_ROOM = (script && script.dataset.room) || "general";
  var ROOM = roomFromHash(BASE_ROOM);
  var LABEL = (script && script.dataset.label) || "This desk";
  var API = ((script && script.dataset.api) || "http://127.0.0.1:18935").replace(/\/+$/, "");
  var PORT = API.replace(/^https?:\/\//, "").replace(/\/.*$/, "");
  var POLL_MS = 5000;
  var NICK_KEY = "meta-chat-nick";
  var sent = 0;

  // One nick per browser, so the room reads like people, not "anon".
  function nick() {
    var n = "";
    try { n = window.localStorage.getItem(NICK_KEY) || ""; } catch (e) { /* private mode */ }
    if (!n) {
      n = "operator-" + Math.random().toString(36).slice(2, 6);
      try { window.localStorage.setItem(NICK_KEY, n); } catch (e) { /* this visit only */ }
    }
    return n;
  }

  var css = document.createElement("style");
  css.textContent = [
    "#meta-chat{position:fixed;right:18px;bottom:18px;z-index:900;font:13px/1.45 Manrope,system-ui,sans-serif;color:#e7eefb}",
    "#meta-chat *{box-sizing:border-box}",
    "#meta-chat-toggle{display:flex;align-items:center;gap:8px;height:38px;padding:0 14px;border:1px solid rgba(140,170,220,.35);border-radius:19px;background:rgba(15,22,36,.92);color:inherit;cursor:pointer;font:inherit}",
    "#meta-chat-toggle:hover{border-color:rgba(140,190,255,.7)}",
    "#meta-chat-toggle .dot{width:7px;height:7px;border-radius:50%;background:#6fe0a0}",
    "#meta-chat-toggle[data-state=down] .dot{background:#ffb14a}",
    "#meta-chat-panel{position:absolute;right:0;bottom:48px;display:none;flex-direction:column;width:330px;max-height:440px;border:1px solid rgba(140,170,220,.32);border-radius:12px;background:#0c1220;box-shadow:0 18px 50px rgba(0,0,0,.55);overflow:hidden}",
    '#meta-chat[data-open="1"] #meta-chat-panel{display:flex}',
    "#meta-chat-head{display:flex;align-items:baseline;gap:8px;padding:10px 12px;border-bottom:1px solid rgba(140,170,220,.18)}",
    "#meta-chat-head b{font-weight:650;font-size:12.5px}",
    "#meta-chat-head span{margin-left:auto;font:11px ui-monospace,monospace;color:#8fa4c4}",
    "#meta-chat-log{flex:1;min-height:120px;overflow-y:auto;padding:10px 12px;font:12px/1.5 ui-monospace,monospace}",
    "#meta-chat-log p{margin:0 0 6px;overflow-wrap:anywhere}",
    "#meta-chat-log .who{color:#8fc2ff}",
    "#meta-chat-log .note{color:#ffcf7a}",
    "#meta-chat-log .empty{color:#7d8ea8}",
    "#meta-chat-status{padding:0 12px 6px;font:11px ui-monospace,monospace;color:#8fa4c4;min-height:15px}",
    "#meta-chat-status.bad{color:#ff9a8f}",
    "#meta-chat form{display:flex;gap:6px;padding:8px 10px 10px;border-top:1px solid rgba(140,170,220,.18)}",
    "#meta-chat input[type=text]{flex:1;min-width:0;height:32px;padding:0 8px;border:1px solid rgba(140,170,220,.32);border-radius:6px;background:#0a111d;color:inherit;font:12px ui-monospace,monospace}",
    "#meta-chat button[type=submit]{height:32px;padding:0 12px;border:1px solid rgba(120,180,255,.45);border-radius:6px;background:rgba(40,90,160,.35);color:inherit;cursor:pointer;font:inherit}",
    "#meta-chat :focus-visible{outline:2px solid #7fb8ff;outline-offset:2px}",
    "@media (max-width:520px){#meta-chat{right:10px;bottom:10px}#meta-chat-panel{width:min(92vw,330px)}}"
  ].join("\n");
  document.head.appendChild(css);

  var root = document.createElement("div");
  root.id = "meta-chat";
  root.innerHTML =
    '<button id="meta-chat-toggle" type="button" aria-expanded="false" aria-controls="meta-chat-panel">' +
      '<span class="dot" aria-hidden="true"></span><span>Desk chat</span>' +
    '</button>' +
    '<div id="meta-chat-panel" role="dialog" aria-label="' + esc(LABEL) + ' chat">' +
      '<div id="meta-chat-head"><b>' + esc(LABEL) + '</b><span>#' + esc(ROOM) + '</span></div>' +
      '<div id="meta-chat-log" role="log" aria-live="polite" aria-label="Room messages"><p class="empty">Loading room…</p></div>' +
      '<div id="meta-chat-status" role="status"></div>' +
      '<form autocomplete="off"><input type="text" name="text" placeholder="Message ' + esc(LABEL) + '…" aria-label="Message the room"><button type="submit">Send</button></form>' +
    '</div>';
  document.body.appendChild(root);

  var toggle = root.querySelector("#meta-chat-toggle");
  var roomTag = root.querySelector("#meta-chat-head span");
  var log = root.querySelector("#meta-chat-log");
  var statusEl = root.querySelector("#meta-chat-status");
  var form = root.querySelector("form");
  var input = form.querySelector("input");
  var timer = null;

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function say(text, bad) {
    statusEl.textContent = text;
    statusEl.className = bad ? "bad" : "";
    toggle.dataset.state = bad ? "down" : "up";
  }

  function render(lines) {
    if (!lines.length) {
      log.innerHTML = '<p class="empty">No messages yet. Say something and it lands in the same room the Messages app shows.</p>';
      return;
    }
    var atBottom = log.scrollTop + log.clientHeight >= log.scrollHeight - 24;
    log.innerHTML = lines.slice(-60).map(function (line) {
      var note = /^board: NOTIFY:/.test(line);
      var cut = line.indexOf(": ");
      if (note) return '<p class="note">' + esc(line) + "</p>";
      if (cut <= 0) return "<p>" + esc(line) + "</p>";
      return '<p><span class="who">' + esc(line.slice(0, cut)) + "</span>" + esc(line.slice(cut)) + "</p>";
    }).join("");
    if (atBottom) log.scrollTop = log.scrollHeight;
  }

  function read() {
    var url = API + "/rooms/" + encodeURIComponent(ROOM) + "/messages";
    return fetch(url, { cache: "no-store" }).then(function (res) {
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    }).then(function (data) {
      var lines = (data && data.messages) || [];
      render(lines);
      say(lines.length + (lines.length === 1 ? " message" : " messages") + " · board on " + PORT, false);
    }).catch(function (err) {
      // The panel states the port it could not reach; it never blanks itself.
      say("Board unreachable on " + PORT + " (" + err.message + ") — is the Messages app running?", true);
    });
  }

  function poll() {
    clearTimeout(timer);
    read().then(function () { timer = setTimeout(poll, POLL_MS); });
  }

  // Anchor changes switch rooms without a reload (the boards nav is plain
  // links, so this is the common path on surfaces.html).
  function followHash() {
    var next = roomFromHash(BASE_ROOM);
    if (next === ROOM) return;
    ROOM = next;
    roomTag.textContent = "#" + ROOM;
    log.innerHTML = '<p class="empty">Loading room…</p>';
    poll();
  }
  window.addEventListener("hashchange", followHash);

  function open() {
    root.dataset.open = "1";
    toggle.setAttribute("aria-expanded", "true");
    input.focus();
    poll();
  }

  function close() {
    delete root.dataset.open;
    toggle.setAttribute("aria-expanded", "false");
    clearTimeout(timer);
  }

  toggle.addEventListener("click", function () {
    if (root.dataset.open) close(); else open();
  });

  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" && root.dataset.open) close();
  });

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var text = input.value.trim();
    if (!text) return;
    input.value = "";
    var body = JSON.stringify({ nick: nick(), text: text });
    fetch(API + "/rooms/" + encodeURIComponent(ROOM) + "/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body,
    }).then(function (res) {
      if (!res.ok) throw new Error("HTTP " + res.status);
      sent += 1;
      return read();
    }).catch(function (err) {
      input.value = text;
      say("Send failed on " + PORT + " (" + err.message + ") — text kept below.", true);
    });
  });

  // A closed panel keeps one cheap read so the button can show it is down.
  read();
})();
