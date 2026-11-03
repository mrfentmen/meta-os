// Meta OS face — reference web desktop (PAX_OS_BUILDOUT A-section).
// Honesty scope: this page is the DESIGN REFERENCE + website demo.
// The terminal answers with the recorded K7 kernel session shapes;
// the dashboard mixes LIVE page values with the RECORD from the
// committed boot log. Nothing here claims to be the kernel itself.
"use strict";

import {
  calcKey, initialCalc, monthCells, shiftMonth, dayKey, DOW,
  terminalAnswer, newNote, updateNote, deleteNote, findNote,
  setSetting, filesIn, resolvePath, moveToTrash, restoreFromTrash, emptyTrash,
  initialWindowState, openOrFocus, focusWindow, closeWindow
} from "./logic.mjs";

var $ = function (s) { return document.querySelector(s); };
var windowsEl = $("#windows"), dockEl = $("#dock");
var openWins = {};   // appId -> element
var winState = initialWindowState();   // focus order + top z, from logic.mjs
var cascade = 0;
var sessionStart = Date.now();

/* ---------- settings (persisted) ---------- */
var settings = {
  mode: localStorage.getItem("metaos-face-mode") || "dark",
  bar: localStorage.getItem("metaos-face-bar") || "auto",
  speed: +(localStorage.getItem("metaos-face-speed") || 25),
  paused: localStorage.getItem("metaos-face-paused") === "1",
  variant: localStorage.getItem("metaos-face-variant") || "blue",
  bg: localStorage.getItem("metaos-face-bg") || "default"
};
var VARIANTS = { blue: "", deep: "saturate(1.35) brightness(.82)", ice: "brightness(1.3) saturate(.75)", midnight: "brightness(.5) saturate(1.1)", solid: "" };
var BGS = { default: "", navy: "#0a1633", black: "#000000", slate: "#23272f", sky: "#bcd6f5" };
function applySettings() {
  document.body.classList.toggle("light", settings.mode === "light");
  var bg, fg;
  if (settings.bar === "blue") { bg = "#0750bc"; fg = "#fff"; }
  else if (settings.bar === "white") { bg = "#ffffff"; fg = "#000"; }
  else if (settings.bar === "black") { bg = "#000000"; fg = "#fff"; }
  else if (settings.mode === "light") { bg = "#ffffff"; fg = "#000"; }
  else { bg = "#000000"; fg = "#fff"; }
  document.body.style.setProperty("--bar-bg", bg);
  document.body.style.setProperty("--bar-fg", fg);
  $("#tb-mode").textContent = settings.mode.toUpperCase();
  var cv = document.getElementById("logo-background");
  cv.style.filter = VARIANTS[settings.variant] || "";
  cv.style.display = settings.variant === "solid" ? "none" : "";
  document.body.style.background = BGS[settings.bg] || "";
  window.dispatchEvent(new CustomEvent("meta-trio-logo-speed", { detail: { speed: settings.speed } }));
  window.dispatchEvent(new CustomEvent("meta-trio-logo-paused", { detail: { paused: settings.paused } }));
  localStorage.setItem("metaos-face-mode", settings.mode);
  localStorage.setItem("metaos-face-bar", settings.bar);
  localStorage.setItem("metaos-face-speed", String(settings.speed));
  localStorage.setItem("metaos-face-paused", settings.paused ? "1" : "0");
  localStorage.setItem("metaos-face-variant", settings.variant);
  localStorage.setItem("metaos-face-bg", settings.bg);
}

/* ---------- clock ---------- */
setInterval(function () {
  var d = new Date();
  $("#tb-clock").textContent = d.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" }) +
    "  " + d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}, 1000);

/* ---------- login ---------- */
function tryLogin() {
  var pw = $("#pw");
  if (!pw.value) { $(".glass-card").classList.remove("shake"); void pw.offsetWidth; $(".glass-card").classList.add("shake"); pw.focus(); return; }
  $("#login").hidden = true;
  $("#desktop").hidden = false;
  applySettings();
  openApp("terminal"); openApp("dashboard");
}
$("#login-btn").addEventListener("click", tryLogin);
$("#pw").addEventListener("keydown", function (e) { if (e.key === "Enter") tryLogin(); });

/* ---------- window manager ---------- */
function openApp(id) {
  if (openWins[id]) {
    var w = openWins[id]; w.hidden = false; focusWin(w);
    markRunning(); return;
  }
  var def = APPS[id];
  var node = $("#win-template").content.firstElementChild.cloneNode(true);
  node.querySelector(".win-title").textContent = def.title;
  node.style.left = (90 + cascade * 36) + "px";
  node.style.top = (64 + cascade * 30) + "px";
  cascade = (cascade + 1) % 6;
  node.dataset.app = id;
  windowsEl.appendChild(node);
  def.build(node.querySelector(".win-body"));
  node.querySelector(".win-close").addEventListener("click", function () { node.remove(); delete openWins[id]; winState = closeWindow(winState, id); markRunning(); });
  node.querySelector(".win-min").addEventListener("click", function () { node.hidden = true; });
  dragify(node);
  node.addEventListener("mousedown", function () { focusWin(node); });
  openWins[id] = node; focusWin(node); markRunning();
}
function focusWin(w) {
  winState = openOrFocus(winState, w.dataset.app);
  w.style.zIndex = winState.z;
  document.querySelectorAll(".window").forEach(function (x) { x.classList.toggle("focused", x === w); });
}
function dragify(node) {
  var bar = node.querySelector(".win-bar"), sx, sy, ox, oy, on = false;
  bar.addEventListener("mousedown", function (e) {
    if (e.target.tagName === "BUTTON") return;
    on = true; sx = e.clientX; sy = e.clientY; ox = node.offsetLeft; oy = node.offsetTop;
  });
  window.addEventListener("mousemove", function (e) {
    if (!on) return;
    node.style.left = (ox + e.clientX - sx) + "px";
    node.style.top = Math.max(34, oy + e.clientY - sy) + "px";
  });
  window.addEventListener("mouseup", function () { on = false; });
}
function markRunning() {
  document.querySelectorAll(".dock-item").forEach(function (d) {
    d.classList.toggle("running", !!openWins[d.dataset.app]);
  });
  var dc = $("#dash-count"); if (dc) dc.textContent = Object.keys(openWins).length;
}

/* ---------- tiny filesystem (Files + Trash share it) ---------- */
function loadFS() {
  var fs = JSON.parse(localStorage.getItem("metaos-face-fs") || "null");
  if (!fs) {
    fs = [
      { id: 1, name: "README.txt", folder: "Home", trashed: false, content: "Meta OS 0.1 (K6)\n\nMeta OS boots on x86_64 in QEMU, drops to ring 3, runs three userspace programs, isolates a fault to one task, and gives you a shell that reports the machine's real state." },
      { id: 2, name: "K7-boot.txt", folder: "Home/logs", trashed: false, content: "META OS 0.1 (K6)\nMETA OS KERNEL - alive (K1)\nHELLO FROM USERSPACE\nsleeper: sleep/wake ok\ncrasher: task killed (isolated)\n(record excerpt — full log: os-build/logs/K7-boot.txt)" },
      { id: 3, name: "imperium-run.txt", folder: "Home/systems", trashed: false, content: "Imperium staged run (Mac, Round 5 R5-4 — vision readings staged, dispatch endpoint simulated):\nflag -> review -> investigation -> auto-dispatch WITH picture\nreceipt sim-6623d237a90b3d9d (SIMULATED endpoint)" },
      { id: 4, name: "welcome.txt", folder: "Home", trashed: false, content: "Welcome to Meta OS.\nFiles here persist in this browser. Delete moves a file to Trash; restore brings it back." }
    ];
    localStorage.setItem("metaos-face-fs", JSON.stringify(fs));
  }
  return fs;
}
function saveFS(fs) { localStorage.setItem("metaos-face-fs", JSON.stringify(fs)); }
function buildFiles(body, trashOnly) {
  var fs = loadFS();
  body.innerHTML = '<div class="win-sub">' + (trashOnly
    ? "Deleted files land here. Restore returns them to Files; Empty removes them for good (in this browser)."
    : "A small working file store in this browser — seeded with the OS's own records. Create, open, delete.") + '</div>' +
    '<div class="files-list"></div><div class="files-view"></div>' +
    (trashOnly ? '<div style="margin-top:10px"><button class="mini-btn files-empty">Empty trash</button></div>'
               : '<div class="board-post"><input placeholder="New file name"><button class="files-new">Create</button></div>');
  var list = body.querySelector(".files-list"), view = body.querySelector(".files-view");
  function render() {
    fs = loadFS();
    var items = filesIn(fs, trashOnly);
    list.innerHTML = items.length ? "" : '<div style="opacity:.6">' + (trashOnly ? "Trash is empty." : "No files.") + "</div>";
    items.forEach(function (f) {
      var row = document.createElement("div"); row.className = "file-row";
      row.innerHTML = '<span class="file-name"></span><span class="file-folder"></span>';
      row.querySelector(".file-name").textContent = "📄 " + f.name;
      row.querySelector(".file-folder").textContent = f.folder;
      row.addEventListener("click", function () { showFile(f); });
      list.appendChild(row);
    });
  }
  function showFile(f) {
    view.innerHTML = '<div class="win-sub" style="margin-top:10px">' + resolvePath(f.folder, f.name) + '</div><pre></pre>' +
      '<div style="margin-top:8px">' + (trashOnly
        ? '<button class="mini-btn f-restore">Restore</button>'
        : '<button class="mini-btn f-del">Delete (to Trash)</button>') + "</div>";
    view.querySelector("pre").textContent = f.content;
    var rb = view.querySelector(".f-restore"), db = view.querySelector(".f-del");
    if (rb) rb.addEventListener("click", function () { saveFS(restoreFromTrash(loadFS(), f.id)); view.innerHTML = ""; render(); });
    if (db) db.addEventListener("click", function () { saveFS(moveToTrash(loadFS(), f.id)); view.innerHTML = ""; render(); });
  }
  var nb = body.querySelector(".files-new");
  if (nb) nb.addEventListener("click", function () {
    var input = body.querySelector(".board-post input"), name = input.value.trim();
    if (!name) return;
    fs.push({ id: Date.now(), name: name, folder: "Home", trashed: false, content: "(new file — created in Files)" });
    saveFS(fs); input.value = ""; render();
  });
  var eb = body.querySelector(".files-empty");
  if (eb) eb.addEventListener("click", function () {
    fs = emptyTrash(loadFS()); saveFS(fs); view.innerHTML = ""; render();
  });
  render();
}

/* ---------- apps ---------- */
var APPS = {
  terminal: {
    title: "Terminal",
    build: function (body) {
      body.innerHTML = '<div class="win-sub">Shell answers use the recorded session shapes from the real kernel log (os-build/logs/K7-boot.txt). This window is the reference UI, not the kernel.</div>' +
        '<pre class="term-out"></pre>' +
        '<div class="term-line"><span>&gt;</span><input class="term-in" placeholder="help, status, mem, ps, uptime, clear"></div>';
      var out = body.querySelector(".term-out"), input = body.querySelector(".term-in");
      function print(t) { out.textContent += t + "\n"; body.scrollTop = body.scrollHeight; }
      print("META OS 0.1 (K6)");
      print("META OS KERNEL - alive (K1)");
      // The answers live in logic.mjs so the command table is testable; the
      // window only prints what the table returns.
      function answer(cmd) {
        print("> " + cmd);
        var res = terminalAnswer(cmd);
        if (res.clear) out.textContent = "";
        res.lines.forEach(print);
      }
      input.addEventListener("keydown", function (e) { if (e.key === "Enter") { answer(input.value); input.value = ""; } });
      setTimeout(function () { input.focus(); }, 50);
    }
  },
  dashboard: {
    title: "Dashboard",
    build: function (body) {
      body.innerHTML = '<div class="cards">' +
        '<div class="card"><h4>Session uptime (live)</h4><div class="big" id="dash-up">0s</div><div>this face, this tab</div></div>' +
        '<div class="card"><h4>Windows open (live)</h4><div class="big" id="dash-count">0</div><div>on this desktop</div></div>' +
        '<div class="card"><h4>Kernel record</h4><div class="big">META OS 0.1 (K6)</div><div>banner from os-build/logs/K7-boot.txt</div></div>' +
        '<div class="card"><h4>Machine record</h4><div class="big">512K heap &middot; 7 tasks</div><div>gated boot, clean clone, GATE GREEN 7/7</div></div>' +
        '</div><div class="win-sub" style="margin-top:10px">Live cards measure this page. Record cards quote the committed boot log — the two are never mixed.</div>';
      setInterval(function () {
        var el = body.querySelector("#dash-up"); if (!el) return;
        el.textContent = Math.floor((Date.now() - sessionStart) / 1000) + "s";
      }, 1000);
      markRunning();
    }
  },
  board: {
    title: "Board",
    build: function (body) {
      // W7: the Board window is the real board service's viewer, not a
      // browser-only copy. The viewer is served by board/board.mjs
      // (default port 8790); an iframe keeps the viewer on its own
      // origin, so no cross-origin fetch is needed. If the service is
      // not running, the frame stays blank — that blank is the honest
      // signal, not a substitute board.
      body.innerHTML = '<div class="win-sub">Live board from the in-OS board service (board/board.mjs, port 8790). Start it with: node board/board.mjs — a blank window means the service is not running.</div>' +
        '<iframe title="Board" src="http://localhost:8790/" style="width:100%;height:480px;border:1px solid #444;border-radius:8px;background:#fff"></iframe>';
    }
  },
  imperium: {
    title: "Imperium",
    build: function (body) {
      body.innerHTML = '<div style="margin-bottom:8px"><span class="sim-tag">SIMULATED ENDPOINT</span></div>' +
        '<b>Record of the staged run on the Mac (Round 5, R5-4).</b><br>' +
        'A staged camera feed flagged a person down. The review agreed. The investigation ran. ' +
        'Imperium itself sent the dispatch package <b>with the picture</b> to the simulated receiving desk — no human in the loop.<br><br>' +
        'Receipt: <b>sim-6623d237a90b3d9d</b> &middot; simulated = true<br>' +
        'Artifacts: os-build/logs/R5-imperium/ (incident, package sent, receipt).<br>' +
        '<span style="opacity:.7">The vision readings in that run were staged. A real camera run is still owed, and this window does not pretend otherwise.</span>';
    }
  },
  musica: {
    title: "Musica",
    build: function (body) {
      body.innerHTML = '<div style="background:#17101f;border:1px solid #3b2a52;border-radius:10px;padding:12px;color:#e9e2f5">' +
        '<div style="font-weight:700;letter-spacing:.06em;color:#c9a7ff">MUSICA — STUDIO</div>' +
        '<div style="opacity:.75;font-size:12px;margin:2px 0 10px">System candidate three. Sessions run overnight; the studio keeps what passes.</div>' +
        '<b>Session hn029-chipsynth</b> (record)<br>' +
        'Takes: 12 &middot; Keepers: <b>11</b> &middot; Rights: checked per take<br>' +
        'Catalogue written by the studio itself: os/worlds/musica/sessions/<br><br>' +
        '<span style="opacity:.7">Its face is the 3D notation — two voices on a staff, rendered from the real session takes (design/meta-musica-notes.html).</span></div>';
    }
  },
  science: {
    title: "Science Lab",
    build: function (body) {
      body.innerHTML = '<div style="background:#eef4ee;border:1px solid #b9d2b9;border-radius:10px;padding:12px;color:#1d2b1d">' +
        '<div style="font-weight:700;letter-spacing:.06em;color:#2e7d43">SCIENCE LAB</div>' +
        '<div style="opacity:.75;font-size:12px;margin:2px 0 10px">System two. General science; heatsinks were only the practice test.</div>' +
        '<b>Molecule viewer</b> (record): caffeine, C8H10N4O2 — 24 atoms, 25 bonds, ball-and-stick from the real PubChem/RDKit record on file (design/molecules/caffeine.sdf).<br><br>' +
        '<b>Hortus</b> sits inside Science as its breeding engine — not a standalone system.<br>' +
        '<span style="opacity:.7">Viewer: design/meta-scientia-molecules.html. Served over HTTP it renders live; the records are real data files, not drawings.</span></div>';
    }
  },
  calculator: {
    title: "Calculator",
    build: function (body) {
      body.innerHTML = '<div class="calc"><div class="calc-disp">0</div><div class="calc-grid"></div></div>' +
        '<div class="win-sub" style="margin-top:8px">Real arithmetic, buttons and keyboard. State lives in this window only.</div>';
      var disp = body.querySelector(".calc-disp"), state = initialCalc();
      function show() { disp.textContent = state.cur; }
      function press(k) { state = calcKey(state, k); show(); }
      var keys = ["C", "(", ")", "/", "7", "8", "9", "*", "4", "5", "6", "-", "1", "2", "3", "+", "0", ".", "=", "⌫"];
      var grid = body.querySelector(".calc-grid");
      keys.forEach(function (k) {
        var b = document.createElement("button"); b.textContent = k; b.className = "calc-btn";
        b.addEventListener("click", function () { press(k === "⌫" ? "Backspace" : k); });
        grid.appendChild(b);
      });
      body.tabIndex = 0;
      body.addEventListener("keydown", function (e) { if (/[0-9.+\-*/=]|Enter|Escape|Backspace/.test(e.key)) { press(e.key); e.preventDefault(); } });
      show();
    }
  },
  notes: {
    title: "Notes",
    build: function (body) {
      var notes = JSON.parse(localStorage.getItem("metaos-face-notes") || "null") ||
        [{ id: 1, title: "Welcome", text: "Meta OS notes live here.\nThey persist in this browser across reloads.\nThe kernel-face Notes is a Lobster app fed by the Goose settings service — this is its reference UI." }];
      var active = notes.length ? notes[0].id : null;
      body.innerHTML = '<div class="notes"><div class="notes-list"></div><div class="notes-main">' +
        '<input class="notes-title" placeholder="Title"><textarea class="notes-text" placeholder="Write..."></textarea>' +
        '<div style="margin-top:8px"><button class="mini-btn notes-new">New note</button> <button class="mini-btn notes-del">Delete</button></div></div></div>';
      var list = body.querySelector(".notes-list"), title = body.querySelector(".notes-title"), text = body.querySelector(".notes-text");
      function save() { localStorage.setItem("metaos-face-notes", JSON.stringify(notes)); }
      function render() {
        list.innerHTML = "";
        notes.forEach(function (n) {
          var d = document.createElement("div"); d.className = "notes-item" + (n.id === active ? " on" : "");
          d.textContent = n.title || "Untitled";
          d.addEventListener("click", function () { active = n.id; sync(); render(); });
          list.appendChild(d);
        });
        var cur = findNote(notes, active);
        title.value = cur ? cur.title : ""; text.value = cur ? cur.text : "";
        title.disabled = text.disabled = !cur;
      }
      function sync() {
        if (findNote(notes, active)) notes = updateNote(notes, active, { title: title.value, text: text.value });
      }
      title.addEventListener("input", function () { sync(); save(); render(); });
      text.addEventListener("input", function () { sync(); save(); });
      body.querySelector(".notes-new").addEventListener("click", function () {
        notes = newNote(notes, Date.now()); active = notes[0].id; save(); render();
      });
      body.querySelector(".notes-del").addEventListener("click", function () {
        notes = deleteNote(notes, active); active = notes.length ? notes[0].id : null; save(); render();
      });
      render();
    }
  },
  calendar: {
    title: "Calendar",
    build: function (body) {
      var events = JSON.parse(localStorage.getItem("metaos-face-events") || "{}");
      var view = { year: new Date().getFullYear(), month: new Date().getMonth() };
      body.innerHTML = '<div class="cal-head"><button class="mini-btn cal-prev">&lt;</button><b class="cal-name"></b><button class="mini-btn cal-next">&gt;</button></div>' +
        '<div class="cal-grid"></div><div class="cal-detail"></div>';
      var grid = body.querySelector(".cal-grid"), name = body.querySelector(".cal-name"), detail = body.querySelector(".cal-detail");
      var today = new Date();
      function render() {
        name.textContent = new Date(view.year, view.month, 1).toLocaleDateString(undefined, { month: "long", year: "numeric" });
        grid.innerHTML = "";
        DOW.forEach(function (d) { var h = document.createElement("div"); h.className = "cal-dow"; h.textContent = d; grid.appendChild(h); });
        var cells = monthCells(view.year, view.month);
        for (var i = 0; i < cells.leading; i++) grid.appendChild(document.createElement("div"));
        cells.days.forEach(function (dn) {
          var cell = document.createElement("button"); cell.className = "cal-day";
          var dt = new Date(view.year, view.month, dn);
          if (dt.toDateString() === today.toDateString()) cell.classList.add("today");
          cell.textContent = dn + (events[dayKey(dt)] ? " •" : "");
          cell.addEventListener("click", function () { showDay(dt); });
          grid.appendChild(cell);
        });
      }
      function showDay(dt) {
        var k = dayKey(dt), list = events[k] || [];
        detail.innerHTML = '<div class="win-sub" style="margin-top:10px">' + dt.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" }) + '</div>' +
          (list.length ? list.map(function (e) { return "<div>• " + e + "</div>"; }).join("") : '<div style="opacity:.6">No events.</div>') +
          '<div class="board-post"><input placeholder="Add an event"><button>Add</button></div>';
        var input = detail.querySelector("input");
        function add() { if (!input.value.trim()) return; (events[k] = events[k] || []).push(input.value.trim()); localStorage.setItem("metaos-face-events", JSON.stringify(events)); render(); showDay(dt); }
        detail.querySelector("button").addEventListener("click", add);
        input.addEventListener("keydown", function (e) { if (e.key === "Enter") add(); });
      }
      body.querySelector(".cal-prev").addEventListener("click", function () { view = shiftMonth(view, -1); render(); });
      body.querySelector(".cal-next").addEventListener("click", function () { view = shiftMonth(view, 1); render(); });
      render();
    }
  },
  files: {
    title: "Files",
    build: function (body) { buildFiles(body, false); }
  },
  trash: {
    title: "Trash",
    build: function (body) { buildFiles(body, true); }
  },
  settings: {
    title: "Settings",
    build: function (body) {
      body.innerHTML =
        '<div class="set-row"><span>Mode</span><span class="seg" id="set-mode"><button data-v="dark">Dark</button><button data-v="light">Light</button></span></div>' +
        '<div class="set-row"><span>Top bar colour</span><span class="seg" id="set-bar"><button data-v="auto">Auto</button><button data-v="black">Black</button><button data-v="white">White</button><button data-v="blue">Blue</button></span></div>' +
        '<div class="set-row"><span>Wallpaper speed</span><span class="seg" id="set-speed"><button data-v="10">Calm</button><button data-v="25">Normal</button><button data-v="50">Fast</button></span></div>' +
        '<div class="set-row"><span>Wallpaper motion</span><span class="seg" id="set-paused"><button data-v="0">Running</button><button data-v="1">Paused</button></span></div>' +
        '<div class="set-row"><span>Wallpaper</span><span class="seg" id="set-variant"><button data-v="blue">Blue</button><button data-v="deep">Deep</button><button data-v="ice">Ice</button><button data-v="midnight">Midnight</button><button data-v="solid">Solid</button></span></div>' +
        '<div class="set-row"><span>Background colour</span><span class="seg" id="set-bg"><button data-v="default">Default</button><button data-v="navy">Navy</button><button data-v="black">Black</button><button data-v="slate">Slate</button><button data-v="sky">Sky</button></span></div>' +
        '<div class="win-sub" style="margin-top:10px">Every control applies now and survives a reload. Variants restyle the one blue ribbon (filters on the same renderer) — the ribbon itself stays the boss\'s blue infinity loop.</div>';
      function wire(id, key, fn) {
        var seg = body.querySelector(id);
        seg.querySelectorAll("button").forEach(function (b) {
          b.classList.toggle("on", String(settings[key]) === b.dataset.v || (key === "paused" && String(settings.paused ? 1 : 0) === b.dataset.v));
          b.addEventListener("click", function () { fn(b.dataset.v); applySettings(); wireAll(); });
        });
      }
      function wireAll() {
        wire("#set-mode", "mode", function (v) { settings = setSetting(settings, "mode", v); });
        wire("#set-bar", "bar", function (v) { settings = setSetting(settings, "bar", v); });
        wire("#set-speed", "speed", function (v) { settings = setSetting(settings, "speed", +v); });
        wire("#set-paused", "paused", function (v) { settings = setSetting(settings, "paused", v === "1"); });
        wire("#set-variant", "variant", function (v) { settings = setSetting(settings, "variant", v); });
        wire("#set-bg", "bg", function (v) { settings = setSetting(settings, "bg", v); });
      }
      wireAll();
    }
  },
  about: {
    title: "About Meta OS",
    build: function (body) {
      body.innerHTML = '<b>Meta OS 0.1 (K6)</b><br><br>' +
        'Meta OS boots on x86_64 in QEMU, drops to ring 3, runs three userspace programs, isolates a fault to one task, and gives you a shell that reports the machine\'s real state — reproduced from a clean checkout by one command, every claim backed by a committed boot log.<br><br>' +
        '<span style="opacity:.7">This face page is the reference desktop: what the kiosk loads if the web shell wins the spike, and the fidelity target either way (PAX_OS_BUILDOUT A14). Systems: Imperium, Science Lab, Musica, Officina. Custos is retired as a system; its watch idea lives in the OS agents. Layers: Rust kernel, Goose services, Lobster apps.</span>';
    }
  }
};

/* ---------- dock ---------- */
var DOCK = [
  ["terminal", "&#9002;", "Terminal"], ["dashboard", "&#9638;", "Dashboard"],
  ["files", "&#128193;", "Files"], ["notes", "&#128221;", "Notes"],
  ["calendar", "&#128197;", "Calendar"], ["calculator", "&#128425;", "Calculator"],
  ["board", "&#9998;", "Board"], null,
  ["imperium", "&#9960;", "Imperium"], ["musica", "&#9835;", "Musica"], ["science", "&#9879;", "Science"], null,
  ["settings", "&#9881;", "Settings"], ["trash", "&#128465;", "Trash"], ["about", "&#9432;", "About"]
];
DOCK.forEach(function (item) {
  if (item === null) { var s = document.createElement("div"); s.className = "dock-sep"; dockEl.appendChild(s); return; }
  var b = document.createElement("button");
  b.className = "dock-item"; b.dataset.app = item[0];
  b.innerHTML = '<div class="dock-glyph">' + item[1] + '</div><div class="dock-label">' + item[2] + '</div><div class="dock-dot">&#9679;</div>';
  b.addEventListener("click", function () { openApp(item[0]); });
  dockEl.appendChild(b);
});
applySettings();
