// Console clock for the top bar: local time, one-second tick.
// Presentation only — no state, no network, no contract surface.
(function () {
  var el = document.getElementById("console-clock");
  if (!el) return;
  function pad(n) {
    return (n < 10 ? "0" : "") + n;
  }
  function tick() {
    var d = new Date();
    // HN-024: name the real zone (EST/EDT/…) instead of the
    // literal " LOCAL" — recomputed each tick so a DST change
    // mid-session renames the clock rather than lying about it.
    var zone = "";
    try {
      var parts = new Intl.DateTimeFormat([], { timeZoneName: "short" }).formatToParts(d);
      for (var i = 0; i < parts.length; i++) {
        if (parts[i].type === "timeZoneName") zone = parts[i].value;
      }
    } catch (e) {}
    el.textContent =
      pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" + pad(d.getSeconds()) +
      (zone ? " " + zone : "");
  }
  tick();
  setInterval(tick, 1000);
})();
