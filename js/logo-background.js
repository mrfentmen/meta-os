// Background ASCII Meta loop for the Trio app.
//
// Adapted from the uploaded Meta ASCII Studio (logo-studio.html):
// the same ribbon path and lighting, rendered dim and slow behind
// the panels. The panels themselves stay opaque, so text never sits
// on top of moving characters. The canvas is aria-hidden in the
// page, ignores pointer input, renders one still frame when the
// user prefers reduced motion, and pauses while the tab is hidden.

(function () {
  "use strict";

  var canvas = document.getElementById("logo-background");
  if (!canvas) return;
  var ctx = canvas.getContext("2d", { alpha: true });
  if (!ctx) return;

  // A slightly smaller field than the studio's 124 x 52 keeps the
  // background cheap enough to run beside the camera and sampler.
  var WIDTH = 110;
  var HEIGHT = 46;
  var RING_POINTS = 240;
  var CAMERA_DISTANCE = 80;
  var LOOP_X = 24.5;
  var LOOP_Y = 26.5;
  var LOOP_Z = 8.2;
  var RIBBON_WIDTH = 3.65;
  var RIBBON_THICKNESS = 0.72;
  var X_PROJECTION = 0.99;
  var Y_PROJECTION = 1.76;
  // Slightly oversized: the panels cover the middle of the page,
  // and the panels are see-through, so the loop ghosts through
  // them at a size that still reads as one loop, not a crop.
  var SCALE = 1.05;
  var GLYPHS = " .,:;irsXA253hMHGS#9B&@";
  // One ramp per product, each built around that product's accent:
  // Vigiles blue #4f7ec2, Ignis red #d92b2b, Medicus green #5da864.
  var PALETTES = {
    vigiles: [
      "#062258", "#07357f", "#0750bc", "#4f7ec2",
      "#6a96d8", "#8ab4e8", "#a8c8f0", "#c8ddf8", "#eaf2ff",
    ],
    ignis: [
      "#3d0a08", "#5c1410", "#7f1d18", "#a32424",
      "#d92b2b", "#e85545", "#f07a68", "#ffa08e", "#ffd9d0",
    ],
    medicus: [
      "#0a2e12", "#123f1c", "#1e5429", "#2f6b3a",
      "#5da864", "#7cc47f", "#9ad69c", "#bfe8c2", "#e6f9e8",
    ],
  };
  var GLOWS = {
    vigiles: "rgba(91, 220, 255, 0.9)",
    ignis: "rgba(255, 120, 90, 0.9)",
    medicus: "rgba(120, 220, 140, 0.9)",
  };
  var SPECULARS = {
    vigiles: "#eafcff",
    ignis: "#ffe8e0",
    medicus: "#e8fbe9",
  };
  var currentProduct = "vigiles";
  var currentPalette = PALETTES.vigiles;
  var currentGlow = GLOWS.vigiles;
  var currentSpecular = SPECULARS.vigiles;

  // LOGO-1 (Del direction, Oct 30): a user-picked logo color
  // overrides the product tint. The studio's own palette build
  // (design/meta-ascii-logo-studio.html) anchors a 9-step ramp
  // on the chosen color: shadows mixed toward near-black,
  // highlights toward white, so the hue survives at every
  // brightness. The override lives only in this browser's local
  // storage (key below); nothing is sent anywhere, and Reset in
  // js/logo-color.js clears it back to the product tint.
  var customColor = null;
  var LOGO_COLOR_KEY = "meta-trio-logo-color";
  function hexToRgb(hex) {
    var clean = String(hex).replace("#", "");
    return {
      r: parseInt(clean.slice(0, 2), 16),
      g: parseInt(clean.slice(2, 4), 16),
      b: parseInt(clean.slice(4, 6), 16),
    };
  }
  function rgbToHex(rgb) {
    return (
      "#" +
      [rgb.r, rgb.g, rgb.b]
        .map(function (value) {
          return Math.round(value).toString(16).padStart(2, "0");
        })
        .join("")
    );
  }
  function mixHex(firstHex, secondHex, amountSecond) {
    var a = hexToRgb(firstHex);
    var b = hexToRgb(secondHex);
    return rgbToHex({
      r: a.r + (b.r - a.r) * amountSecond,
      g: a.g + (b.g - a.g) * amountSecond,
      b: a.b + (b.b - a.b) * amountSecond,
    });
  }
  function buildPalette(baseHex) {
    return [
      mixHex(baseHex, "#020817", 0.88),
      mixHex(baseHex, "#020817", 0.72),
      mixHex(baseHex, "#020817", 0.53),
      mixHex(baseHex, "#020817", 0.31),
      baseHex,
      mixHex(baseHex, "#ffffff", 0.18),
      mixHex(baseHex, "#ffffff", 0.38),
      mixHex(baseHex, "#ffffff", 0.62),
      mixHex(baseHex, "#ffffff", 0.9),
    ];
  }
  function applyCustomColor(hex) {
    var normalized = String(hex).toLowerCase();
    var rgb = hexToRgb(normalized);
    customColor = normalized;
    currentPalette = buildPalette(normalized);
    currentGlow = "rgba(" + rgb.r + ", " + rgb.g + ", " + rgb.b + ", 0.9)";
    currentSpecular = mixHex(normalized, "#ffffff", 0.9);
  }
  function readStoredColor() {
    try {
      var stored =
        window.localStorage && window.localStorage.getItem(LOGO_COLOR_KEY);
      if (typeof stored === "string" && /^#[0-9a-f]{6}$/i.test(stored)) {
        return stored.toLowerCase();
      }
    } catch (e) {
      // An unavailable store leaves the product tint in place.
    }
    return null;
  }

  // The app sets document.body.dataset.product on every product
  // switch (js/app.js), so watch it and re-tint the loop live.
  // A user-picked color wins over a product switch: the switch
  // still records the product, but the palette stays custom
  // until Reset clears it.
  function applyProduct(product) {
    if (!PALETTES[product]) product = "vigiles";
    currentProduct = product;
    if (customColor) return;
    currentPalette = PALETTES[product];
    currentGlow = GLOWS[product];
    currentSpecular = SPECULARS[product];
  }
  function clearCustomColor() {
    customColor = null;
    applyProduct(currentProduct);
  }
  var CELL_COUNT = WIDTH * HEIGHT;
  var glyphBuffer = new Uint8Array(CELL_COUNT);
  var colorBuffer = new Uint8Array(CELL_COUNT);
  var specBuffer = new Float32Array(CELL_COUNT);
  var zBuffer = new Float32Array(CELL_COUNT);

  var angleX = -0.045;
  var angleY = 0.045;
  var viewWidth = 0;
  var viewHeight = 0;
  var running = true;
  var reducedMotion =
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function normalize(v) {
    var length = Math.hypot(v.x, v.y, v.z) || 1;
    return { x: v.x / length, y: v.y / length, z: v.z / length };
  }

  var lightDirection = normalize({ x: -0.38, y: 0.62, z: 0.91 });
  var viewDirection = { x: 0, y: 0, z: 1 };
  var halfVector = normalize({
    x: lightDirection.x + viewDirection.x,
    y: lightDirection.y + viewDirection.y,
    z: lightDirection.z + viewDirection.z,
  });

  function loopPoint(u) {
    var s = Math.sin(u);
    var c = Math.cos(u);
    return {
      x: LOOP_X * s * (1 + 0.018 * s),
      y: LOOP_Y * s * c * (1 + 0.025 * s),
      z: LOOP_Z * c + 0.65 * Math.sin(2 * u),
    };
  }

  function buildSurface() {
    var samples = [];
    var frameStep = 0.0025;
    var WIDTH_STEPS = 18;
    var EDGE_STEPS = 9;
    var j;
    var k;
    var e;
    for (j = 0; j < RING_POINTS; j++) {
      var u = (j / RING_POINTS) * Math.PI * 2;
      var center = loopPoint(u);
      var before = loopPoint(u - frameStep);
      var after = loopPoint(u + frameStep);
      var tangent = normalize({
        x: after.x - before.x,
        y: after.y - before.y,
        z: after.z - before.z,
      });
      var nx = -tangent.y;
      var ny = tangent.x;
      var nz = 0;
      var nLength = Math.hypot(nx, ny, nz) || 1;
      nx /= nLength;
      ny /= nLength;
      var binormal = normalize({
        x: tangent.y * nz - tangent.z * ny,
        y: tangent.z * nx - tangent.x * nz,
        z: tangent.x * ny - tangent.y * nx,
      });
      var localWidth =
        RIBBON_WIDTH * (0.9 + 0.1 * Math.pow(Math.abs(Math.sin(u)), 1.15));
      for (k = 0; k <= WIDTH_STEPS; k++) {
        var across = -1 + (2 * k) / WIDTH_STEPS;
        var crown = 1 - 0.045 * across * across;
        for (var side = -1; side <= 1; side += 2) {
          var faceNormal = normalize({
            x: side * binormal.x - 0.09 * across * nx,
            y: side * binormal.y - 0.09 * across * ny,
            z: side * binormal.z - 0.09 * across * nz,
          });
          samples.push({
            x: center.x + localWidth * across * nx + side * RIBBON_THICKNESS * crown * binormal.x,
            y: center.y + localWidth * across * ny + side * RIBBON_THICKNESS * crown * binormal.y,
            z: center.z + localWidth * across * nz + side * RIBBON_THICKNESS * crown * binormal.z,
            nx: faceNormal.x,
            ny: faceNormal.y,
            nz: faceNormal.z,
            u: u,
            colorWave: 0.5 + 0.5 * Math.sin(u + 0.65),
          });
        }
      }
      for (var edgeSide = -1; edgeSide <= 1; edgeSide += 2) {
        for (e = 0; e < EDGE_STEPS; e++) {
          var theta = -Math.PI / 2 + (Math.PI * e) / (EDGE_STEPS - 1);
          var st = Math.sin(theta);
          var ct = Math.cos(theta);
          var edgeNormal = normalize({
            x: edgeSide * ct * nx + st * binormal.x,
            y: edgeSide * ct * ny + st * binormal.y,
            z: edgeSide * ct * nz + st * binormal.z,
          });
          samples.push({
            x: center.x + localWidth * edgeSide * nx + RIBBON_THICKNESS * st * binormal.x,
            y: center.y + localWidth * edgeSide * ny + RIBBON_THICKNESS * st * binormal.y,
            z: center.z + localWidth * edgeSide * nz + RIBBON_THICKNESS * st * binormal.z,
            nx: edgeNormal.x,
            ny: edgeNormal.y,
            nz: edgeNormal.z,
            u: u,
            colorWave: 0.5 + 0.5 * Math.sin(u + 0.65),
          });
        }
      }
    }
    return samples;
  }

  var surfaceSamples = buildSurface();

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function resizeCanvas() {
    var rect = canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    var ratio = Math.min(window.devicePixelRatio || 1, 1.5);
    var pixelWidth = Math.round(rect.width * ratio);
    var pixelHeight = Math.round(rect.height * ratio);
    if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
      canvas.width = pixelWidth;
      canvas.height = pixelHeight;
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    }
    viewWidth = rect.width;
    viewHeight = rect.height;
  }

  if ("ResizeObserver" in window) {
    new ResizeObserver(resizeCanvas).observe(canvas);
  }
  window.addEventListener("resize", resizeCanvas, { passive: true });

  // Pause while the tab is hidden so the background costs nothing
  // when nobody can see it.
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      running = false;
    } else if (!reducedMotion) {
      running = true;
      requestAnimationFrame(renderFrame);
    }
  });

  function renderFrame() {
    if (!viewWidth || !viewHeight) resizeCanvas();
    if (!viewWidth || !viewHeight) {
      requestAnimationFrame(renderFrame);
      return;
    }

    // Slow drift: a background should move, not demand attention.
    if (!reducedMotion) angleY += 0.0022;

    glyphBuffer.fill(0);
    colorBuffer.fill(0);
    specBuffer.fill(0);
    zBuffer.fill(-Infinity);

    var cosY = Math.cos(angleY);
    var sinY = Math.sin(angleY);
    var cosX = Math.cos(angleX);
    var sinX = Math.sin(angleX);

    for (var i = 0; i < surfaceSamples.length; i++) {
      var p = surfaceSamples[i];
      var x1 = p.x * cosY + p.z * sinY;
      var z1 = -p.x * sinY + p.z * cosY;
      var nx1 = p.nx * cosY + p.nz * sinY;
      var nz1 = -p.nx * sinY + p.nz * cosY;
      var y2 = p.y * cosX - z1 * sinX;
      var z2 = p.y * sinX + z1 * cosX;
      var ny2 = p.ny * cosX - nz1 * sinX;
      var nz2 = p.ny * sinX + nz1 * cosX;
      var depth = CAMERA_DISTANCE - z2;
      if (depth <= 1) continue;
      var invDepth = 1 / depth;
      var xp = Math.round(WIDTH / 2 + x1 * SCALE * invDepth * WIDTH * X_PROJECTION);
      var yp = Math.round(HEIGHT / 2 - y2 * SCALE * invDepth * HEIGHT * Y_PROJECTION);
      if (xp < 0 || xp >= WIDTH || yp < 0 || yp >= HEIGHT) continue;
      var index = xp + yp * WIDTH;
      if (invDepth <= zBuffer[index]) continue;
      var diffuse = Math.max(
        0,
        nx1 * lightDirection.x + ny2 * lightDirection.y + nz2 * lightDirection.z,
      );
      var halfDot = Math.max(
        0,
        nx1 * halfVector.x + ny2 * halfVector.y + nz2 * halfVector.z,
      );
      var specular = Math.pow(halfDot, 28);
      var rimBase = 1 - Math.min(1, Math.abs(nz2));
      var rim = rimBase * rimBase;
      var glyphBrightness = clamp(
        0.13 + diffuse * 0.43 + specular * 0.92 + rim * 0.18,
        0,
        1,
      );
      var glyphIndex = clamp(
        Math.round(glyphBrightness * (GLYPHS.length - 1)),
        1,
        GLYPHS.length - 1,
      );
      var colorBrightness = clamp(
        0.12 + diffuse * 0.48 + specular * 0.73 + rim * 0.13 + p.colorWave * 0.1,
        0,
        1,
      );
      var colorIndex = clamp(
        Math.round(colorBrightness * (currentPalette.length - 1)),
        0,
        currentPalette.length - 1,
      );
      zBuffer[index] = invDepth;
      glyphBuffer[index] = glyphIndex;
      colorBuffer[index] = colorIndex;
      specBuffer[index] = specular;
    }

    ctx.clearRect(0, 0, viewWidth, viewHeight);
    var cellWidth = viewWidth / WIDTH;
    var cellHeight = viewHeight / HEIGHT;
    var fontSize = Math.min(cellHeight * 1.01, cellWidth / 0.59);
    ctx.font =
      '700 ' + fontSize + 'px "SFMono-Regular", Consolas, "Liberation Mono", monospace';
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    for (var c = 0; c < CELL_COUNT; c++) {
      var glyphIndex = glyphBuffer[c];
      if (!glyphIndex) continue;
      var character = GLYPHS[glyphIndex];
      if (character === " ") continue;
      var x = ((c % WIDTH) + 0.5) * cellWidth;
      var y = (Math.floor(c / WIDTH) + 0.5) * cellHeight;
      ctx.fillStyle = currentPalette[colorBuffer[c]];
      ctx.fillText(character, x, y);
    }

    ctx.shadowColor = currentGlow;
    ctx.shadowBlur = cellHeight * 0.85;
    ctx.fillStyle = currentSpecular;
    for (var s = 0; s < CELL_COUNT; s++) {
      if (specBuffer[s] < 0.66 || !glyphBuffer[s]) continue;
      var ch = GLYPHS[glyphBuffer[s]];
      if (ch === " ") continue;
      var sx = ((s % WIDTH) + 0.5) * cellWidth;
      var sy = (Math.floor(s / WIDTH) + 0.5) * cellHeight;
      ctx.fillText(ch, sx, sy);
    }
    ctx.shadowBlur = 0;

    if (running && !reducedMotion) requestAnimationFrame(renderFrame);
  }

  // A saved logo color (LOGO-1) is applied by js/logo-color.js
  // through this event; the background itself only applies it,
  // never writes storage on an event. An unknown or missing
  // color means Reset: back to the product tint.
  window.addEventListener("meta-trio-logo-color", function (event) {
    var color = event && event.detail && event.detail.color;
    if (typeof color === "string" && /^#[0-9a-f]{6}$/i.test(color)) {
      applyCustomColor(color);
    } else {
      clearCustomColor();
    }
  });

  // Tint from the product the page opened on, then follow switches.
  applyProduct(document.body.dataset.product);
  // A color saved on an earlier visit re-tints before the first
  // frame, so a reload never flashes the product tint first.
  var storedColor = readStoredColor();
  if (storedColor) applyCustomColor(storedColor);
  if ("MutationObserver" in window) {
    new MutationObserver(function (mutations) {
      for (var m = 0; m < mutations.length; m++) {
        if (mutations[m].attributeName === "data-product") {
          applyProduct(document.body.dataset.product);
        }
      }
    }).observe(document.body, { attributes: true, attributeFilter: ["data-product"] });
  }

  resizeCanvas();
  renderFrame();
})();
