# Input + accessibility checks (NC-185..NC-192)

Home page only, findings for Hana's lane (nothing here was fixed).

- NC-185 keyboard-only: full Tab tour hits 25+ stops in a sane order
  (topbar → map controls → products → modes → search → camera list),
  no traps. Enter activates: AI Focus via keyboard shows its status
  line; camera buttons open the inspector. Every control reachable
  AND activatable by keyboard alone.
- NC-186 mouse-only: everything is a button/link/input — all clickable.
  Only keyboard-dependent case: none found. Reverse finding: the map
  CANVAS itself is mouse-only (drag pan, no keyboard pan alternative).
- NC-187 tab order: Logo studio, Map, Console, map canvas, zoom
  in/out, reset-north, attribution, CARTO links, Vigiles/Ignis/Medicus,
  City/Tactical/Incident, AI Focus, Fires, Radar, search input+button,
  shortcuts, then camera buttons in list order. No jumps over visible
  controls.
- NC-188 focus visibility: 3 shots (nc-188-focus-*.png) — bright ring
  on Map, AI Focus, Console buttons. Visible in each (verified viewed).
- NC-189 contrast (WCAG math on rendered colors, alpha-blended):
  wordmark 10.0, source 9.7, honesty 5.8 (AA), dark-on-accent 10.0 x2,
  body 15.2, input 12+, chip 10.0, accent-on-dark 10.0. All pairs pass
  AA or better. Brand hexes from js/products.js (read-only).
- NC-190 reduced motion: respected — styles.css has a
  prefers-reduced-motion block; logo-background.js and motion.js gate
  animation on matchMedia. OS setting honored (code-verified; visual
  animation sampling not attempted headless).
- NC-191 200% zoom at 390 px: topbar view-switch overflows — CONSOLE
  button text clipped at the right edge, backend pill truncated
  (nc-191-zoom200.png). Finding for Hana, not fixed.
- NC-192 landmarks: status, group, region, button, radiogroup roles
  present (plus native header/main/nav). List from the live DOM.
