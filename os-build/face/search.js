"use strict";
/* face search.js — topbar search across Files, Notes, and dock Apps.
 *
 * UI: #shell-search (input hook in shell.html topbar; created if missing)
 *     #search-results (dropdown hook; created if missing).
 * Sources:
 *   Apps  — the shell's APPS list (name/id match, client-side, always works).
 *   Notes — localStorage "metaos-notes" lines matching the query.
 *   Files — files.py :18936 /list of the face dir (+1 subdir level) filtered
 *           by name; for queries >= 3 chars also /read small text matches
 *           (bounded: first 8 candidate files, 512KB server cap applies).
 * Keys: Ctrl+K or "/" (outside inputs) focuses search; Esc clears/closes;
 *       Enter opens the top result; Up/Down moves selection.
 * Click: Apps -> toggle/open window; Files -> open Files/Editor window;
 *        Notes -> open Notes window.
 */
(function () {
  var FILES_API = "http://127.0.0.1:18936";
  var NOTES_KEY = "metaos-notes";
  var DEBOUNCE_MS = 200;
  var MAX_RESULTS = 8;

  function $(id) { return document.getElementById(id); }

  function ensureStyle() {
    if ($("shell-search-style")) return;
    var st = document.createElement("style");
    st.id = "shell-search-style";
    st.textContent =
      "#shell-search{margin-left:8px;min-width:180px;max-width:280px;flex:0 1 240px;" +
      "padding:2px 8px;font-size:12px;background:#222;color:#eee;border:1px solid #555;border-radius:6px}" +
      "#search-results{position:fixed;top:30px;left:50%;transform:translateX(-50%);width:min(480px,90vw);" +
      "max-height:50vh;overflow:auto;z-index:200;background:var(--bar,#111);color:var(--fg,#eee);" +
      "border:1px solid #555;border-radius:10px;padding:6px}" +
      "#search-results .grp{font-size:11px;opacity:.7;padding:6px 8px 2px}" +
      "#search-results button{display:block;width:100%;text-align:left;background:transparent;color:inherit;" +
      "border:none;padding:6px 8px;font-size:13px;cursor:pointer;border-radius:6px}" +
      "#search-results button.sel,#search-results button:hover{background:rgba(127,127,127,.25)}" +
      "#search-results .empty{padding:8px;font-size:12px;opacity:.7}";
    document.head.appendChild(st);
  }

  function ensureUI() {
    ensureStyle();
    var topbar = $("topbar");
    var input = $("shell-search");
    if (!input) {
      input = document.createElement("input");
      input.id = "shell-search";
      input.type = "search";
      input.placeholder = "Search Files Notes apps (Ctrl+K)";
      input.setAttribute("aria-label", "Search");
      input.autocomplete = "off";
      if (topbar) {
        var appName = $("app-name");
        if (appName && appName.nextSibling) topbar.insertBefore(input, appName.nextSibling);
        else topbar.appendChild(input);
      } else document.body.appendChild(input);
    }
    var box = $("search-results");
    if (!box) {
      box = document.createElement("div");
      box.id = "search-results";
      box.hidden = true;
      box.setAttribute("role", "listbox");
      document.body.appendChild(box);
    }
    return { input: input, box: box };
  }

  function getApps() {
    try {
      if (typeof APPS !== "undefined" && Array.isArray(APPS)) return APPS.filter(function (a) { return !a.sep; });
    } catch (e) { /* lexical APPS not visible; fall through */ }
    try {
      if (Array.isArray(window.APPS)) return window.APPS.filter(function (a) { return !a.sep; });
    } catch (e) { /* ignore */ }
    return [
      { id: "files", name: "Files", kind: "url", target: "files.html" },
      { id: "notes", name: "Notes", kind: "url", target: "notes.html" },
    ];
  }

  function openAppTarget(app) {
    try {
      if (typeof window.toggleApp === "function") { window.toggleApp(app); return true; }
    } catch (e) { /* fall through */ }
    try {
      if (typeof toggleApp === "function") { toggleApp(app); return true; }
    } catch (e) { /* fall through */ }
    try {
      if (typeof window.openWindow === "function") { window.openWindow(app); return true; }
    } catch (e) { /* fall through */ }
    try {
      if (typeof openWindow === "function") { openWindow(app); return true; }
    } catch (e) { /* fall through */ }
    // Fallback: open the page directly in a shell window-ish way.
    try {
      window.open(app.target || (app.id + ".html"), "_blank");
      return true;
    } catch (e) { return false; }
  }

  function searchApps(q) {
    q = q.toLowerCase();
    return getApps()
      .filter(function (a) {
        return (a.name && a.name.toLowerCase().indexOf(q) !== -1) ||
          (a.id && a.id.toLowerCase().indexOf(q) !== -1);
      })
      .slice(0, MAX_RESULTS)
      .map(function (a) {
        return { group: "Apps", label: a.name + " (app)", detail: a.id, run: function () { openAppTarget(a); } };
      });
  }

  function searchNotes(q) {
    var text = "";
    try { text = window.localStorage.getItem(NOTES_KEY) || ""; } catch (e) { text = ""; }
    if (!text) return [];
    var ql = q.toLowerCase();
    var out = [];
    var lines = text.split("\n");
    for (var i = 0; i < lines.length && out.length < MAX_RESULTS; i++) {
      if (lines[i].toLowerCase().indexOf(ql) !== -1) {
        (function (ln, txt) {
          out.push({
            group: "Notes", label: "Line " + (ln + 1) + ": " + txt.slice(0, 80),
            detail: "notes", run: function () {
              var app = { id: "notes", name: "Notes", kind: "url", target: "notes.html" };
              var found = getApps().filter(function (a) { return a.id === "notes"; })[0];
              openAppTarget(found || app);
            },
          });
        })(i, lines[i].trim());
      }
    }
    return out;
  }

  function fetchJSON(url) {
    return fetch(url).then(function (r) {
      return r.json().then(function (d) { return { ok: r.ok, d: d }; });
    });
  }

  function searchFiles(q) {
    var ql = q.toLowerCase();
    return fetchJSON(FILES_API + "/list").then(function (x) {
      if (!x.ok || !x.d.ok) return [];
      var entries = x.d.entries || [];
      var hits = entries.filter(function (e) {
        return e.name && e.name.toLowerCase().indexOf(ql) !== -1;
      }).slice(0, MAX_RESULTS);
      // One subdir level for name matches (bounded, best-effort).
      var dirs = entries.filter(function (e) { return e.is_dir; }).slice(0, 4);
      var sub = Promise.all(dirs.map(function (d) {
        return fetchJSON(FILES_API + "/list?path=" + encodeURIComponent(d.path))
          .then(function (sx) {
            if (!sx.ok || !sx.d.ok) return [];
            return (sx.d.entries || []).filter(function (e) {
              return e.name && e.name.toLowerCase().indexOf(ql) !== -1;
            }).slice(0, 2);
          }).catch(function () { return []; });
      }));
      return sub.then(function (lists) {
        lists.forEach(function (l) { hits = hits.concat(l); });
        hits = hits.slice(0, MAX_RESULTS);
        return hits.map(function (e) {
          return {
            group: "Files", label: (e.is_dir ? "Dir " : "File ") + e.name, detail: e.path,
            run: function () {
              var target = e.is_dir ? "files.html" : "editor.html?path=" + encodeURIComponent(e.path);
              var name = e.is_dir ? "Files" : "Code Editor";
              var id = e.is_dir ? "files" : "editor";
              var known = getApps().filter(function (a) { return a.id === id; })[0];
              openAppTarget(known || { id: id, name: name, kind: "url", target: target });
            },
          };
        });
      });
    }).catch(function () { return []; });
  }

  function init() {
    var ui = ensureUI();
    var input = ui.input, box = ui.box;
    var timer = null, selIdx = -1, current = [];

    function render(results) {
      current = results;
      selIdx = results.length ? 0 : -1;
      box.innerHTML = "";
      if (!results.length) {
        var em = document.createElement("div");
        em.className = "empty";
        em.textContent = "No matches in Apps, Files, or Notes.";
        box.appendChild(em);
      } else {
        var lastGroup = null;
        results.forEach(function (r, i) {
          if (r.group !== lastGroup) {
            var g = document.createElement("div");
            g.className = "grp";
            g.textContent = r.group;
            box.appendChild(g);
            lastGroup = r.group;
          }
          var b = document.createElement("button");
          b.setAttribute("role", "option");
          b.textContent = r.label + (r.detail ? " — " + r.detail : "");
          if (i === selIdx) b.classList.add("sel");
          (function (res) { b.addEventListener("click", function () { close(); res.run(); }); })(r);
          b.addEventListener("mousemove", function () {
            selIdx = i;
            Array.prototype.forEach.call(box.querySelectorAll("button"), function (x) { x.classList.remove("sel"); });
            b.classList.add("sel");
          });
          box.appendChild(b);
        });
      }
      box.hidden = false;
    }

    function close() { box.hidden = true; selIdx = -1; current = []; }

    function runSearch(q) {
      if (!q) { close(); return; }
      var appHits = searchApps(q);
      var noteHits = searchNotes(q);
      var base = appHits.concat(noteHits).slice(0, MAX_RESULTS);
      if (base.length >= MAX_RESULTS) { render(base); return; }
      searchFiles(q).then(function (fileHits) {
        render(base.concat(fileHits).slice(0, MAX_RESULTS));
      });
    }

    input.addEventListener("input", function () {
      if (timer) clearTimeout(timer);
      timer = setTimeout(function () { runSearch(input.value.trim()); }, DEBOUNCE_MS);
    });
    input.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { input.value = ""; close(); input.blur(); }
      else if (e.key === "Enter") {
        if (selIdx >= 0 && current[selIdx]) { var r = current[selIdx]; close(); r.run(); }
      } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        if (!current.length) return;
        e.preventDefault();
        selIdx = e.key === "ArrowDown"
          ? (selIdx + 1) % current.length
          : (selIdx - 1 + current.length) % current.length;
        var btns = box.querySelectorAll("button");
        Array.prototype.forEach.call(btns, function (x) { x.classList.remove("sel"); });
        if (btns[selIdx]) { btns[selIdx].classList.add("sel"); btns[selIdx].scrollIntoView({ block: "nearest" }); }
      }
    });
    document.addEventListener("pointerdown", function (e) {
      if (e.target !== input && !box.contains(e.target)) close();
    });
    document.addEventListener("keydown", function (e) {
      var tag = (e.target && e.target.tagName) ? e.target.tagName.toUpperCase() : "";
      var typing = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (e.target && e.target.isContentEditable);
      if ((e.ctrlKey && (e.key === "k" || e.key === "K")) || (!typing && e.key === "/")) {
        e.preventDefault();
        input.focus();
        input.select();
      }
    });

    try {
      window.FaceSearch = {
        search: function (q) { input.value = q; runSearch(q); },
        searchApps: searchApps, searchNotes: searchNotes, searchFiles: searchFiles,
      };
    } catch (e) { /* ignore */ }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
