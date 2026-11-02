# Surface inventory v2 — HN-070 (branch hana/surfaces)

Re-run of the HN-020 control audit (docs/UI_CONTROL_SWEEP.md method)
across ALL surfaces, including the new boards (surfaces.html).
Method: every static control enumerated from the page markup
(button / input / select), every dynamic control from the JS that
creates it, every disclosure from its `<summary>`, every link from
its `href` target. Wiring evidence is the listener or read site in
`js/` for that control. A control counts as WORKS when its listener,
read site, or native behavior exists in this build — not when it
merely renders.

## Counts

- index.html: 59 static controls (42 buttons + 15 inputs + 2 selects)
  — all WORKS, unchanged from HN-020.
- index.html: 27 native disclosures — all WORKS (native `<details>`).
- index.html: 3 links (logo studio ×2, Boards → surfaces.html) — all resolve.
- surfaces.html: 0 static controls, 0 disclosures — the boards are
  read-only renderers; there is no interactive control to be dead.
- surfaces.html: 14 links (13 internal anchors + Back to console) —
  all resolve.
- surfaces.html: 11 content regions, all written by the page script.
- Dead count across ALL surfaces: **0**.

## index.html static controls — all WORKS

Id'd controls: each id appears in `js/` (listener or read site).
Verified by tests/surfaces-inventory.test.mjs.

Id-less controls, all WORKS by group listener or native behavior:

| Control | Evidence |
| --- | --- |
| cmd-product chips ×3 (vigiles/ignis/medicus) | `js/command-map.js` `[data-cmd-product]` group listener |
| cmd-mode buttons ×3 (city/tactical/incident) | `js/command-map.js` `[data-cmd-mode]` group listener |
| product radios ×3 (vigiles/ignis/medicus) | native radio behavior; selection read by product logic |

## surfaces.html — new boards (HN-056…HN-069)

No buttons, inputs, or selects exist on the boards page. Each board
section is a read-only renderer fed by a fetch in the page script:

| Board | Wiring evidence |
| --- | --- |
| Lab (HN-056) | page script writes `#lab-content` from lab records |
| Hortus (HN-057) | page script writes `#hortus-content` from run JSONL |
| Gate (HN-058) | page script writes `#gate-content` from gate manifest |
| Evidence (HN-059) | page script writes `#evidence-content` from /api/crew/status |
| Tiers (HN-060) | static audit text, no control |
| BOLO (HN-061) | page script writes `#bolo-content` from /api/crew/status |
| Timeline (HN-062) | page script writes `#timeline-content` from /api/crew/status |
| Cameras (HN-063) | static labels text, no control |
| Receipt (HN-064) | page script writes `#receipt-content` from /api/crew/status |
| Costs (HN-065) | page script writes `#cost-content`, 15 s refresh |
| Officina (HN-066) | page script writes `#officina-content` from run JSONs |
| Custos (HN-067) | page script writes `#custos-content` from patrol JSONLs |
| Systems (HN-068) | page script writes `#systems-content` from world packs |
| Print (HN-069) | `@media print` in styles.css, incident-record sections only |

Boards nav links (13): Lab, Hortus, Gate, Evidence, Tiers, BOLO,
Timeline, Cameras, Receipt, Costs, Officina, Custos, Systems — each
target id exists on the page. Back to console → index.html exists.

## Dead count: 0

No dead control, no unresolved link, no unwritten content region
was found on any surface in this build.
