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
    el.textContent =
      pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" + pad(d.getSeconds()) + " LOCAL";
  }
  tick();
  setInterval(tick, 1000);
})();
