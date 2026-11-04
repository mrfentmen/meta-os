# MetaOS 1.0 fonts (no binaries ship in this tree)

Two faces, both open-licensed, both installed as distro packages, both
referenced by name from GTK + terminal + greeter so no surface falls back
to a third-party default.

| face | package in image | licence | referenced from |
|---|---|---|---|
| Inter (display/UI) | `fonts-inter` 4.0+ds-1 (OTF, `fc-list \| grep -i inter`) | SIL Open Font License 1.1 (full text inside the package: `/usr/share/doc/fonts-inter/copyright`, `License: OFL-1.1` stanza) | greeter `font-name=Inter 11`, `gtk.css` `font-family: 'Inter', …` |
| Ubuntu Mono (monospace) | `fonts-ubuntu` (ships in the base image) | Ubuntu Font Licence 1.0 (grant recorded in `/usr/share/doc/fonts-ubuntu/copyright`, upstream `https://design.ubuntu.com/font/`) | terminal `FontName=Ubuntu Mono 11`, `gtk.css` fallback stack |

Licence files live in the installed packages, not here — that is why this
dir carries no `.ttf`/`.otf`: nothing to re-licence, nothing unlicensed.
`apply.sh` refuses to install the theme when `fc-list` cannot find either
face (D7 gate); `theme_proof.sh` re-asserts it on the target root.

Milo audit note (kept): both open-licensed, no Apple fonts anywhere.
