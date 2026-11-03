# OC3B-018/019/020 — handoff to the ISO lane

Handing over (copy-only, this branch): OC3B-startpage.html,
oc3b-desktop/meta-browser-app.desktop, and the OC3B-*.md records in
os-build/logs/. Receiver installs the page to
/usr/share/metaos/start/index.html and the entry to
/usr/share/applications/, records per-file sha256, bakes the homepage
seed (OC3B-homepage.md), and posts acceptance.

OC3B-019 acceptance note: PENDING — no response yet from the ISO lane.
OC3B-020 self-install instructions (usable if unreachable): copy the
eight files above to the listed paths on any Xfce host with Chromium,
set the homepage seed per OC3B-homepage.md, validate with the same
offline checks recorded in OC3B-startpage-offline.txt.
