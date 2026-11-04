# MetaOS R2-T1 vendored fonts — role mapping + rationale

STATE 2026-11-04: skeleton — binaries not vendored (this host is offline for
font fetching per lane orders; no downloads performed). MANIFEST.txt lists the
exact files + upstream URLs; LICENSES/README.txt records where each OFL text
lands at vendoring. `install.sh --check` fails until the six rows exist.

## The six families (brief: UI, document, mono, display, label + one spare)

| # | role     | family          | file (vendored name)        | license | why this one |
|---|----------|-----------------|-----------------------------|---------|--------------|
| 1 | UI       | Inter           | Inter-Regular.woff2         | OFL-1.1 | Neo-grotesque drawn for UI text: tall x-height, tabular figures, hand-hinted. Already the desktop's referenced UI face (`gtk.css`, `settings.ini`, greeter `font-name`), so vendoring it keeps continuity while dropping the `fonts-inter` apt package. Source: https://github.com/rsms/inter |
| 2 | document | Source Sans 3   | SourceSans3-Regular.woff2   | OFL-1.1 | Adobe's open-source text face for long-form/document reading (evince, mousepad): humanist-grotesque blend, wide weights, large language coverage. Source: https://github.com/adobe-fonts/source-sans |
| 3 | mono     | JetBrains Mono  | JetBrainsMono-Regular.woff2 | OFL-1.1 | Terminal + code: raised x-height, unambiguous `0/O`, `1/l/I`, programming ligatures optional. Replaces Ubuntu Mono as the mono face (see test-no-ubuntu.sh). Source: https://github.com/JetBrains/JetBrainsMono |
| 4 | display  | Space Grotesk   | SpaceGrotesk-Regular.woff2  | OFL-1.1 | Geometric-grotesk display for titles, heroes, splash/hero type: distinctive without ornament, pairs with Inter. Source: https://github.com/floriankarsten/space-grotesk |
| 5 | label    | Archivo         | Archivo-Regular.woff2       | OFL-1.1 | Grotesque workhorse for dense small labels, badges, panel/pager text: narrow apertures stay legible at 10–12 px, family ships expanded widths for tight spots. Source: https://github.com/Omnibus-Type/Archivo |
| 6 | spare    | IBM Plex Sans   | IBMPlexSans-Regular.woff2   | OFL-1.1 | Neutral grotesque spare covering UI + document fallback in one family (Plex ships Sans/Text at matched metrics); corporate-neutral tone for installer/legal surfaces. Source: https://github.com/IBM/plex |

Why these constraints hold:

- Neo-grotesque/geometric sans + mono only: every row above is a grotesk or
  geometric sans (or a mono). No serifs, no scripts, no decorative faces —
  the set cannot drift into a theme-incompatible face.
- OFL-1.1 only: all six are SIL Open Font License 1.1, recorded per file in
  MANIFEST.txt with upstream URL; full texts land in LICENSES/ at vendoring.
- One Regular woff2 per family: six files keep the payload far under the
  3 MB budget (woff2 Regular latin ≈ 100–200 KB each; exact bytes recorded by
  `du` after vendoring). Bold/italic synthetic or later weights are a later
  lane's call, not this one's.

## Generic resolution (fontconfig: 69-meta.conf)

- `sans-serif` → Inter, Source Sans 3, Archivo, IBM Plex Sans, Space Grotesk
- `serif` → Source Sans 3, IBM Plex Sans, Inter (deliberate: no serif is
  vendored, so `serif` resolves to Meta sans instead of falling through to a
  non-Meta serif)
- `monospace` → JetBrains Mono, then DejaVu Sans Mono (last-resort fallback;
  already in the base image via `fonts-dejavu-core`, and carries no forbidden
  family name, keeps text readable if the vendored mono is ever absent)

## What the old stack was (base-manifest inventory, read-only sources)

- `iso/base/metaos.packages:12` → `fonts-inter` (theme lane)
- `iso/base/metaos.packages:23` → `fonts-dejavu-core` (desktop-shell lane)
- `os-build/metaos1-base/packages.txt:40` → `fonts-inter` (theme lane append)
- `/tmp/fs.manifest` (Xubuntu 24.04.5 base image content, spot-check 2026-11-04):
  fonts-dejavu-core, fonts-dejavu-mono, fonts-droid-fallback,
  fonts-liberation, fonts-liberation-sans-narrow, fonts-liberation2,
  fonts-mathjax, fonts-noto-cjk, fonts-noto-color-emoji, fonts-noto-core,
  fonts-noto-hinted, fonts-noto-mono, fonts-noto-ui-core, fonts-opensymbol,
  fonts-symbola, fonts-ubuntu, fonts-urw-base35 (+ fontconfig stack,
  gnome-font-viewer, xfonts-*) — full grep pasted in the lane report.
