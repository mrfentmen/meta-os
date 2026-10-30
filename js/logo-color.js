// Logo color controls for the Trio console (LOGO-1, Del direction
// Oct 30): the studio's presets plus a custom picker, in the Logo
// panel on the main page. Picking a color re-tints the spinning
// ASCII loop behind the panels live (js/logo-background.js listens
// for the event below) and saves the choice in this browser's
// local storage, so it survives a reload. Reset clears the saved
// choice and returns the loop to the selected product's color.
// Nothing here sends anything anywhere; an unavailable store
// leaves the panel working in memory for this visit only, the
// same pattern the session log uses.

(function () {
  "use strict";

  var STORAGE_KEY = "meta-trio-logo-color";
  var swatches = document.querySelectorAll(".logo-swatch[data-logo-color]");
  var picker = document.getElementById("logo-color-picker");
  var valueLine = document.getElementById("logo-color-value");
  var resetButton = document.getElementById("logo-color-reset");
  if (!picker || !valueLine || !resetButton) return;

  var memoryColor = null;
  var memorySet = false;

  function isValidHex(value) {
    return typeof value === "string" && /^#[0-9a-f]{6}$/i.test(value);
  }

  function readStored() {
    try {
      var stored =
        window.localStorage && window.localStorage.getItem(STORAGE_KEY);
      if (isValidHex(stored)) return stored.toLowerCase();
    } catch (e) {
      // Fall through to the in-memory value.
    }
    return memorySet ? memoryColor : null;
  }

  function saveStored(color) {
    memoryColor = color;
    memorySet = true;
    try {
      if (window.localStorage) window.localStorage.setItem(STORAGE_KEY, color);
    } catch (e) {
      // Store unavailable: the in-memory value still drives this visit.
    }
  }

  function clearStored() {
    memoryColor = null;
    memorySet = false;
    try {
      if (window.localStorage) window.localStorage.removeItem(STORAGE_KEY);
    } catch (e) {
      // Nothing to undo in memory beyond the clear above.
    }
  }

  function applyUI(color) {
    var normalized = color ? color.toLowerCase() : null;
    swatches.forEach(function (swatch) {
      var selected =
        normalized !== null &&
        swatch.dataset.logoColor.toLowerCase() === normalized;
      swatch.classList.toggle("is-selected", selected);
      swatch.setAttribute("aria-pressed", String(selected));
    });
    if (normalized) picker.value = normalized;
    valueLine.textContent = normalized
      ? "Logo color: " + normalized.toUpperCase()
      : "Logo color: product color";
  }

  function dispatch(color) {
    window.dispatchEvent(
      new CustomEvent("meta-trio-logo-color", { detail: { color: color } }),
    );
  }

  function pick(color) {
    if (!isValidHex(color)) return;
    var normalized = color.toLowerCase();
    saveStored(normalized);
    applyUI(normalized);
    dispatch(normalized);
  }

  swatches.forEach(function (swatch) {
    swatch.addEventListener("click", function () {
      pick(swatch.dataset.logoColor);
    });
  });
  picker.addEventListener("input", function (event) {
    pick(event.target.value);
  });
  resetButton.addEventListener("click", function () {
    clearStored();
    applyUI(null);
    dispatch(null);
  });

  // The background already re-tinted itself from storage on load,
  // so startup only has to show the saved state in the controls.
  applyUI(readStored());
})();
