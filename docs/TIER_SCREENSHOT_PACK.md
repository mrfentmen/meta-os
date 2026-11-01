# Tier colours screenshot pack (HN-060) — BLOCKED, no captures exist

Status: BLOCKED — no browser in this sandbox, so no screenshots exist
and none are claimed. The code audit (tests/surfaces-tiers.test.mjs)
proves the mapping; these shots prove it visually at Mac gate.

Capture script (reused from the UI wave):
`scripts/capture-ui-screenshots.sh <label> [outdir]` — starts the
server, then takes full-page captures with Chrome headless.

## Shot list

1. Loop feed, yellow-tier incident row (ignis "visible smoke") — row
   renders #ffe27a with the YELLOW text segment.
2. Loop feed, red-tier incident row (ignis "brown smoke") — row renders
   #ffb3ab with the RED text segment.
3. Loop feed, untiered incident row (category outside the table) — row
   renders in the default text color, NOT red.
4. Ribbon, yellow tier + ribbon, red tier — both carry their tier color.
5. Same yellow/red pair for one vigiles category and one medicus
   category (table coverage across all three divisions).

## Pass rule

Every shot shows the row color matching its display-table tier, and
the untiered row shows no tier color. Any mismatch reopens HN-060.
