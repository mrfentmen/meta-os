// Meta OS face — reference web desktop (PAX_OS_BUILDOUT A-section).
// Honesty scope: this page is the DESIGN REFERENCE + website demo.
// The terminal answers with the recorded K7 kernel session shapes;
// the dashboard mixes LIVE page values with the RECORD from the
// committed boot log. Nothing here claims to be the kernel itself.
"use strict";

var $ = function (s) { return document.querySelector(s); };
var windowsEl = $("#windows"), dockEl = $("#dock");
var openWins = {};   // appId -> element
var zTop = 20, cascade = 0;
var sessionStart = Date.now();

/* ---------- settings (persisted) ---------- */
var settings = {
  mode: localStorage.getItem("metaos-face-mode") || "dark",
  bar: localStorage.getItem("metaos-face-bar") || "auto",
  speed: +(localStorage.getItem("metaos-face-speed") || 25),
  paused: localStorage.getItem("metaos-face-paused") === "1"
};
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
  window.dispatchEvent(new CustomEvent("meta-trio-logo-speed", { detail: { speed: settings.speed } }));
  window.dispatchEvent(new CustomEvent("meta-trio-logo-paused", { detail: { paused: settings.paused } }));
  localStorage.setItem("metaos-face-mode", settings.mode);
  localStorage.setItem("metaos-face-bar", settings.bar);
  localStorage.setItem("metaos-face-speed", String(settings.speed));
  localStorage.setItem("metaos-face-paused", settings.paused ? "1" : "0");
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
  node.querySelector(".win-close").addEventListener("click", function () { node.remove(); delete openWins[id]; markRunning(); });
  node.querySelector(".win-min").addEventListener("click", function () { node.hidden = true; });
  dragify(node);
  node.addEventListener("mousedown", function () { focusWin(node); });
  openWins[id] = node; focusWin(node); markRunning();
}
function focusWin(w) { w.style.zIndex = ++zTop; document.querySelectorAll(".window").forEach(function (x) { x.classList.toggle("focused", x === w); }); }
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
      function answer(cmd) {
        print("> " + cmd);
        switch (cmd.trim().toLowerCase()) {
          case "help": print("commands: status help uptime mem ps"); break;
          case "status": print("STATUS tasks 7 heap_total 512K milestone K6"); break;
          case "mem": print("mem frames_free 118784 heap_total 512K"); break;
          case "ps":
            print("ps id 1 state running (kernel)");
            print("ps id 4 state sleeping (sleeper)");
            print("ps id 7 state running (console)");
            print("ps id 8 state held (readkey - spawn held until its boot proof)"); break;
          case "uptime": print("uptime 141s ticks 14100"); break;
          case "clear": out.textContent = ""; break;
          case "": break;
          default: print("unknown command"); print("commands: status help uptime mem ps");
        }
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
      var posts = JSON.parse(localStorage.getItem("metaos-face-board") || "[]");
      body.innerHTML = '<div class="win-sub">Web reference board (this browser only). The real board is the in-repo board server; wiring it into the shell is a listed task.</div><div class="board-list"></div>' +
        '<div class="board-post"><input placeholder="Write a post"><button>Post</button></div>';
      var list = body.querySelector(".board-list"), input = body.querySelector("input");
      function render() {
        list.innerHTML = posts.length ? "" : '<div style="opacity:.6">No posts yet.</div>';
        posts.forEach(function (p) { var d = document.createElement("div"); d.textContent = "Mrfentmen: " + p; list.appendChild(d); });
      }
      function post() {
        if (!input.value.trim()) return;
        posts.push(input.value.trim()); input.value = "";
        localStorage.setItem("metaos-face-board", JSON.stringify(posts)); render();
      }
      body.querySelector("button").addEventListener("click", post);
      input.addEventListener("keydown", function (e) { if (e.key === "Enter") post(); });
      render();
    }
  },
  imperium: {
    title: "Imperium",
    build: function (body) {
      body.innerHTML = '<div style="margin-bottom:8px"><span class="sim-tag">SIMULATED ENDPOINT</span></div>' +
        '<b>Record of the live run on the Mac (Round 5, R5-4).</b><br>' +
        'A staged camera feed flagged a person down. The review agreed. The investigation ran. ' +
        'Imperium itself sent the dispatch package <b>with the picture</b> to the simulated receiving desk — no human in the loop.<br><br>' +
        'Receipt: <b>sim-6623d237a90b3d9d</b> &middot; simulated = true<br>' +
        'Artifacts: os-build/logs/R5-imperium/ (incident, package sent, receipt).<br>' +
        '<span style="opacity:.7">The vision readings in that run were staged. A real camera run is still owed, and this window does not pretend otherwise.</span>';
    }
  },
  settings: {
    title: "Settings",
    build: function (body) {
      body.innerHTML =
        '<div class="set-row"><span>Mode</span><span class="seg" id="set-mode"><button data-v="dark">Dark</button><button data-v="light">Light</button></span></div>' +
        '<div class="set-row"><span>Top bar colour</span><span class="seg" id="set-bar"><button data-v="auto">Auto</button><button data-v="black">Black</button><button data-v="white">White</button><button data-v="blue">Blue</button></span></div>' +
        '<div class="set-row"><span>Wallpaper speed</span><span class="seg" id="set-speed"><button data-v="10">Calm</button><button data-v="25">Normal</button><button data-v="50">Fast</button></span></div>' +
        '<div class="set-row"><span>Wallpaper motion</span><span class="seg" id="set-paused"><button data-v="0">Running</button><button data-v="1">Paused</button></span></div>' +
        '<div class="win-sub" style="margin-top:10px">Every control applies now and survives a reload. Wallpaper variants + background colour picker are face tasks A4/A5 — next slice.</div>';
      function wire(id, key, fn) {
        var seg = body.querySelector(id);
        seg.querySelectorAll("button").forEach(function (b) {
          b.classList.toggle("on", String(settings[key]) === b.dataset.v || (key === "paused" && String(settings.paused ? 1 : 0) === b.dataset.v));
          b.addEventListener("click", function () { fn(b.dataset.v); applySettings(); wireAll(); });
        });
      }
      function wireAll() {
        wire("#set-mode", "mode", function (v) { settings.mode = v; });
        wire("#set-bar", "bar", function (v) { settings.bar = v; });
        wire("#set-speed", "speed", function (v) { settings.speed = +v; });
        wire("#set-paused", "paused", function (v) { settings.paused = v === "1"; });
      }
      wireAll();
    }
  },
  about: {
    title: "About Meta OS",
    build: function (body) {
      body.innerHTML = '<b>Meta OS 0.1 (K6)</b><br><br>' +
        'Meta OS boots on x86_64 in QEMU, drops to ring 3, runs three userspace programs, isolates a fault to one task, and gives you a shell that reports the machine\'s real state — reproduced from a clean checkout by one command, every claim backed by a committed boot log.<br><br>' +
        '<span style="opacity:.7">This face page is the reference desktop: what the kiosk loads if the web shell wins the spike, and the fidelity target either way (PAX_OS_BUILDOUT A14). Systems: Imperium, Science Lab, Musica, Custos, Officina. Layers: Rust kernel, Goose services, Lobster apps.</span>';
    }
  }
};

/* ---------- dock ---------- */
var DOCK = [
  ["terminal", "&#9002;", "Terminal"], ["dashboard", "&#9638;", "Dashboard"],
  ["board", "&#9998;", "Board"], null,
  ["imperium", "&#9960;", "Imperium"], null,
  ["settings", "&#9881;", "Settings"], ["about", "&#9432;", "About"]
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
