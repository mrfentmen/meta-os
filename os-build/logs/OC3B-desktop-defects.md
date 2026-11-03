# OC3B-221 — launcher defects (empty is a result; these are not)

1. Office suite: no source package named in ANY lane (package lists,
   base manifest, payload trees searched). No launcher authored —
   authoring one would be a mock. Owner: whoever names the suite.
2. `metaos-imperium.*` merge-excluded (27fdb760): provision.sh still
   installs both files. Owner: OC1 (restore files or drop the install
   lines). OC3 cannot fix — no shared-file edits.
3. Canonical-home collisions for Pax: agent-status ×2, welcome ×2,
   livebg ×2, files-vs-Thunar (see OC3B-desktop-inventory.md §C).
