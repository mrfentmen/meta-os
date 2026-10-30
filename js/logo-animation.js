// Logo animation controls for the Trio console (LOGO-2, Del
// direction Oct 30): the studio's rotation speed slider and
// pause button, in the Logo panel on the main page. Moving the
// slider re-speeds the spinning ASCII loop behind the panels
// live (js/logo-background.js listens for the events below)
// and saves the choice in this browser's local storage, so it
// survives a reload; pausing holds the loop on its last frame
// and is saved the same way. 25% is the console's usual slow
// drift, 0% is still, 100% is four times the usual drift.
// Nothing here sends anything anywhere; an unavailable store
// leaves the panel working in memory for this visit only, the
// same pattern the session log and js/logo-color.js use. No
// keyboard shortcut: a global Space handler would hijack typing
// in the console's own inputs, so pause is the button only.

(function () {
  "use strict";

  var SPEED_KEY = "meta-trio-logo-speed";
  var PAUSED_KEY = "meta-trio-logo-paused";
  var DEFAULT_SPEED = 25;
  var slider = document.getElementById("logo-speed");
  var valueLine = document.getElementById("logo-speed-value");
  var pauseButton = document.getElementById("logo-pause");
  var pauseLabel = document.getElementById("logo-pause-label");
  if (!slider || !valueLine || !pauseButton || !pauseLabel) return;

  var memorySpeed = null;
  var memorySpeedSet = false;
  var memoryPaused = false;
  var memoryPausedSet = false;

  function clampSpeed(value) {
    var parsed = Number(value);
    if (!Number.isFinite(parsed)) return DEFAULT_SPEED;
    return Math.max(0, Math.min(100, Math.round(parsed)));
  }

  function readStoredSpeed() {
    try {
      var stored =
        window.localStorage && window.localStorage.getItem(SPEED_KEY);
      if (stored !== null) return clampSpeed(stored);
    } catch (e) {
      // Fall through to the in-memory value.
    }
    return memorySpeedSet ? memorySpeed : null;
  }

  function saveStoredSpeed(speed) {
    memorySpeed = speed;
    memorySpeedSet = true;
    try {
      if (window.localStorage) window.localStorage.setItem(SPEED_KEY, String(speed));
    } catch (e) {
      // Store unavailable: the in-memory value still drives this visit.
    }
  }

  function readStoredPaused() {
    try {
      var stored =
        window.localStorage && window.localStorage.getItem(PAUSED_KEY);
      if (stored !== null) return stored === "1";
    } catch (e) {
      // Fall through to the in-memory value.
    }
    return memoryPausedSet ? memoryPaused : false;
  }

  function saveStoredPaused(paused) {
    memoryPaused = paused;
    memoryPausedSet = true;
    try {
      if (window.localStorage) window.localStorage.setItem(PAUSED_KEY, paused ? "1" : "0");
    } catch (e) {
      // Store unavailable: the in-memory value still drives this visit.
    }
  }

  function applyUI(speed, paused) {
    slider.value = String(speed);
    valueLine.textContent = "Rotation speed: " + speed + "%";
    pauseButton.setAttribute("aria-pressed", String(paused));
    pauseLabel.textContent = paused ? "Resume logo" : "Pause logo";
  }

  function dispatchSpeed(speed) {
    window.dispatchEvent(
      new CustomEvent("meta-trio-logo-speed", { detail: { speed: speed } }),
    );
  }

  function dispatchPaused(paused) {
    window.dispatchEvent(
      new CustomEvent("meta-trio-logo-paused", { detail: { paused: paused } }),
    );
  }

  slider.addEventListener("input", function (event) {
    var speed = clampSpeed(event.target.value);
    saveStoredSpeed(speed);
    applyUI(speed, readStoredPaused());
    dispatchSpeed(speed);
  });
  pauseButton.addEventListener("click", function () {
    var paused = !readStoredPaused();
    saveStoredPaused(paused);
    applyUI(readStoredSpeed() === null ? DEFAULT_SPEED : readStoredSpeed(), paused);
    dispatchPaused(paused);
  });

  // The background already re-applied a saved speed and pause
  // from storage on load, so startup only has to show the saved
  // state in the controls — no event is dispatched here.
  var startupSpeed = readStoredSpeed();
  applyUI(startupSpeed === null ? DEFAULT_SPEED : startupSpeed, readStoredPaused());
})();
