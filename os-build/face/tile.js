"use strict";
/* face tile.js — keyboard quarter tiling for shell.html windows.
 *
 * Active window: last .window that got pointerdown (fallback: topmost zIndex).
 * Shortcuts (when not typing in input/textarea/select or contentEditable):
 *   Ctrl+Alt+1 -> top-left quarter        Ctrl+Alt+3 -> bottom-left quarter
 *   Ctrl+Alt+2 -> top-right quarter       Ctrl+Alt+4 -> bottom-right quarter
 *   Ctrl+Alt+Left  -> left half           Ctrl+Alt+Right -> right half
 *   Ctrl+Alt+Up / Ctrl+Alt+5 -> maximize  Ctrl+Alt+Down / Ctrl+Alt+0 -> restore
 *   Meta+Arrow / Meta+1..4 mirror the above where the browser/OS delivers them.
 * Geometry is relative to #desktop (the windows' offsetParent).
 */
(function () {
  var prevRect = new WeakMap();
  var active = null;

  function desktopEl() {
    return document.getElementById("desktop");
  }

  function allWindows() {
    return Array.prototype.slice.call(document.querySelectorAll(".window"));
  }

  function isTypingTarget(el) {
    if (!el) return false;
    var tag = (el.tagName || "").toUpperCase();
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
    if (el.isContentEditable) return true;
    // Terminal output handles its own keys; let tiling win only with Ctrl+Alt/Meta.
    return false;
  }

  function getActiveWindow() {
    if (active && active.isConnected && active.style.display !== "none") return active;
    var wins = allWindows().filter(function (w) { return w.style.display !== "none"; });
    if (!wins.length) return null;
    wins.sort(function (a, b) {
      return (parseInt(a.style.zIndex || "0", 10) - parseInt(b.style.zIndex || "0", 10));
    });
    return wins[wins.length - 1];
  }

  function trackPointer(e) {
    var w = e.target && e.target.closest ? e.target.closest(".window") : null;
    if (w) active = w;
  }
  document.addEventListener("pointerdown", trackPointer, true);

  function saveRect(w) {
    if (!prevRect.has(w)) {
      prevRect.set(w, {
        left: w.style.left, top: w.style.top,
        width: w.style.width, height: w.style.height,
      });
    }
  }

  function place(w, frac) {
    var d = desktopEl();
    if (!d) return;
    var W = d.clientWidth || window.innerWidth;
    var H = d.clientHeight || (window.innerHeight - 92);
    saveRect(w);
    w.classList.remove("snapped-left", "snapped-right");
    w.style.left = Math.round(frac.x * W) + "px";
    w.style.top = Math.round(frac.y * H) + "px";
    w.style.width = Math.round(frac.w * W) + "px";
    w.style.height = Math.round(frac.h * H) + "px";
    if (w.style.zIndex !== undefined) {
      try {
        var z = window.__faceZTop;
        if (typeof z === "number") { w.style.zIndex = String(z + 1); }
      } catch (e) { /* keep z-index as-is */ }
    }
  }

  function maximize(w) {
    place(w, { x: 0, y: 0, w: 1, h: 1 });
  }

  function restore(w) {
    var p = prevRect.get(w);
    if (!p) { // nothing saved: center a default-size window
      var d = desktopEl();
      var W = (d && d.clientWidth) || window.innerWidth;
      var H = (d && d.clientHeight) || 600;
      w.classList.remove("snapped-left", "snapped-right");
      w.style.width = "560px";
      w.style.height = "";
      w.style.left = Math.max(0, Math.round((W - 560) / 2)) + "px";
      w.style.top = "20px";
      void H;
      return;
    }
    w.classList.remove("snapped-left", "snapped-right");
    w.style.left = p.left; w.style.top = p.top;
    w.style.width = p.width; w.style.height = p.height;
    prevRect.delete(w);
  }

  var QUARTERS = {
    "1": { x: 0, y: 0, w: 0.5, h: 0.5 },
    "2": { x: 0.5, y: 0, w: 0.5, h: 0.5 },
    "3": { x: 0, y: 0.5, w: 0.5, h: 0.5 },
    "4": { x: 0.5, y: 0.5, w: 0.5, h: 0.5 },
  };

  function handle(mode) {
    var w = getActiveWindow();
    if (!w) return false;
    if (QUARTERS[mode]) { place(w, QUARTERS[mode]); return true; }
    if (mode === "left") { place(w, { x: 0, y: 0, w: 0.5, h: 1 }); return true; }
    if (mode === "right") { place(w, { x: 0.5, y: 0, w: 0.5, h: 1 }); return true; }
    if (mode === "max") { maximize(w); return true; }
    if (mode === "restore") { restore(w); return true; }
    return false;
  }

  document.addEventListener("keydown", function (e) {
    var withMod = (e.ctrlKey && e.altKey) || e.metaKey;
    if (!withMod) return;
    if (!e.ctrlKey && !e.metaKey) return;
    // Alt+1/Alt+2 belong to workspaces; ignore bare Alt+digit here.
    if (e.altKey && !e.ctrlKey && !e.metaKey) return;
    var k = e.key;
    var mode = null;
    if (k === "ArrowLeft") mode = "left";
    else if (k === "ArrowRight") mode = "right";
    else if (k === "ArrowUp") mode = "max";
    else if (k === "ArrowDown") mode = "restore";
    else if (k === "1") mode = "1";
    else if (k === "2") mode = "2";
    else if (k === "3") mode = "3";
    else if (k === "4") mode = "4";
    else if (k === "5" || k === "m" || k === "M") mode = "max";
    else if (k === "0" || k === "c" || k === "C") mode = "restore";
    if (!mode) return;
    // Avoid hijacking terminal/editor typing unless Ctrl+Alt/Meta combo is explicit (it is).
    if (isTypingTarget(e.target) && !e.ctrlKey && !e.metaKey) return;
    if (handle(mode)) e.preventDefault();
  });

  try {
    window.FaceTile = {
      tile: handle, active: getActiveWindow, restore: function () {
        var w = getActiveWindow(); if (w) restore(w);
      },
    };
  } catch (e) { /* non-browser check harness */ }
})();
