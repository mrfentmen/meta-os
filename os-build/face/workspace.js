"use strict";
/* face workspace.js — two workspaces with toggle for shell.html.
 *
 * Model: every .window gets dataset.ws = "1" | "2" (default: current ws).
 * show(n) hides windows of the other workspace, shows windows of ws n
 * except ones flagged dataset.min="1" (explicitly minimized).
 * Minimize state is tracked by wrapping the shell's minimizeWindow/toggleApp
 * when present, plus observing inline style.display changes for the dock path.
 *
 * UI: #ws-bar (hook in shell.html; created here if missing) with WS1/WS2 buttons.
 * Keys: Alt+1 -> ws 1, Alt+2 -> ws 2, Ctrl+Alt+W -> toggle 1<->2.
 *       (Ctrl+Alt+digits stay reserved for tile.js quarters.)
 */
(function () {
  var current = 1;
  var barId = "ws-bar";

  function desktopEl() { return document.getElementById("desktop"); }

  function allWindows() {
    return Array.prototype.slice.call(document.querySelectorAll(".window"));
  }

  function ensureBar() {
    var bar = document.getElementById(barId);
    if (bar) return bar;
    var topbar = document.getElementById("topbar");
    bar = document.createElement("div");
    bar.id = barId;
    bar.setAttribute("role", "tablist");
    bar.setAttribute("aria-label", "Workspaces");
    if (topbar) topbar.appendChild(bar);
    else document.body.appendChild(bar);
    return bar;
  }

  function ensureStyle() {
    if (document.getElementById("ws-bar-style")) return;
    var st = document.createElement("style");
    st.id = "ws-bar-style";
    st.textContent = "#ws-bar{display:flex;gap:4px;margin-left:8px}" +
      "#ws-bar button{border:1px solid #555;background:transparent;color:inherit;" +
      "border-radius:6px;font-size:11px;padding:1px 8px;cursor:pointer}" +
      "#ws-bar button[aria-selected=\"true\"]{background:#4f7ec2;color:#fff;border-color:#4f7ec2}";
    document.head.appendChild(st);
  }

  function paint() {
    var bar = ensureBar();
    var btns = bar.querySelectorAll("button[data-ws]");
    if (!btns.length) {
      bar.innerHTML = "";
      [1, 2].forEach(function (n) {
        var b = document.createElement("button");
        b.dataset.ws = String(n);
        b.setAttribute("role", "tab");
        b.textContent = "WS" + n;
        b.title = n === 1 ? "Workspace 1 (Alt+1)" : "Workspace 2 (Alt+2)";
        b.addEventListener("click", function () { show(n); });
        bar.appendChild(b);
      });
      btns = bar.querySelectorAll("button[data-ws]");
    }
    Array.prototype.forEach.call(btns, function (b) {
      b.setAttribute("aria-selected", b.dataset.ws === String(current) ? "true" : "false");
    });
  }

  function tagWindow(w) {
    if (!w.dataset.ws) w.dataset.ws = String(current);
    if (w.dataset.min === undefined) w.dataset.min = "";
  }

  function show(n) {
    current = (n === 2) ? 2 : 1;
    allWindows().forEach(function (w) {
      tagWindow(w);
      if (w.dataset.ws === String(current)) {
        if (w.dataset.min === "1") { w.style.display = "none"; }
        else { w.style.display = ""; }
      } else {
        w.style.display = "none";
      }
    });
    try {
      if (typeof window.refreshRunning === "function") {
        // refreshRunning is per-app; easiest is to leave dots as-is.
      }
    } catch (e) { /* ignore */ }
    paint();
  }

  function toggle() { show(current === 1 ? 2 : 1); }

  function observeNew() {
    var d = desktopEl();
    if (!d || typeof MutationObserver === "undefined") {
      allWindows().forEach(tagWindow);
      return;
    }
    allWindows().forEach(tagWindow);
    var mo = new MutationObserver(function (muts) {
      muts.forEach(function (m) {
        Array.prototype.forEach.call(m.addedNodes || [], function (node) {
          if (node.nodeType === 1 && node.classList && node.classList.contains("window")) {
            node.dataset.ws = String(current);
            node.dataset.min = "";
          }
        });
      });
      paint();
    });
    mo.observe(d, { childList: true });
  }

  // Track explicit minimize so workspace switches don't un-minimize.
  function patchMinimize() {
    try {
      if (typeof window.minimizeWindow === "function" && !window.minimizeWindow.__faceWsPatched) {
        var origMin = window.minimizeWindow;
        var wrappedMin = function (w) { try { w.dataset.min = "1"; } catch (e) {} origMin(w); };
        wrappedMin.__faceWsPatched = true;
        window.minimizeWindow = wrappedMin;
      }
      if (typeof window.toggleApp === "function" && !window.toggleApp.__faceWsPatched) {
        var origTog = window.toggleApp;
        var wrappedTog = function (app) {
          var res = origTog(app);
          try {
            var wins = document.querySelectorAll(".window[data-app=\"" + app.id + "\"]");
            Array.prototype.forEach.call(wins, function (w) {
              if (w.isConnected) {
                w.dataset.min = (w.style.display === "none" && w.dataset.ws === String(current)) ? "1" : (w.style.display === "none" ? w.dataset.min : "");
                if (w.style.display !== "none" && w.dataset.ws !== String(current)) w.dataset.ws = String(current);
                if (w.style.display !== "none") w.dataset.min = "";
              }
            });
          } catch (e) { /* ignore */ }
          return res;
        };
        wrappedTog.__faceWsPatched = true;
        window.toggleApp = wrappedTog;
      }
    } catch (e) { /* shell globals may be lexical-only; dataset.min still works via observer */ }

    // Close (x) buttons: clear tracking by removing node (automatic). Min button
    // in shell.html calls minimizeWindow directly, covered above; as a fallback,
    // watch clicks on .titlebar .min to flag dataset.min.
    document.addEventListener("click", function (e) {
      var t = e.target;
      if (t && t.closest && t.closest(".titlebar .min")) {
        var w = t.closest(".window");
        if (w) { try { w.dataset.min = "1"; } catch (err) {} }
      }
      if (t && t.closest && t.closest(".titlebar .close")) {
        /* closing: node removed, nothing to track */
      }
    }, true);
    // Restoring via dock re-show clears min: watch display going from none->"".
    // Lightweight: on pointerdown of a visible window, clear min flag.
    document.addEventListener("pointerdown", function (e) {
      var w = e.target && e.target.closest ? e.target.closest(".window") : null;
      if (w && w.style.display !== "none") { try { if (w.dataset.ws !== String(current)) w.dataset.ws = String(current); } catch (err) {} }
    }, true);
  }

  document.addEventListener("keydown", function (e) {
    var tag = (e.target && e.target.tagName) ? e.target.tagName.toUpperCase() : "";
    var typing = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (e.target && e.target.isContentEditable);
    if (e.altKey && !e.ctrlKey && !e.metaKey && (e.key === "1" || e.key === "2")) {
      if (typing) return;
      e.preventDefault();
      show(e.key === "2" ? 2 : 1);
      return;
    }
    if (e.ctrlKey && e.altKey && (e.key === "w" || e.key === "W")) {
      e.preventDefault();
      toggle();
    }
  });

  ensureStyle();
  ensureBar();
  observeNew();
  patchMinimize();
  paint();

  try {
    window.FaceWorkspace = {
      show: show, toggle: toggle,
      current: function () { return current; },
    };
  } catch (e) { /* ignore */ }
})();
