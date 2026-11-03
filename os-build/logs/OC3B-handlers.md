# OC3B-237/238/247/248 — xdg-open and URL handlers, static record

xdg-open routes per the canonical mimeapps plus desktop-file
MimeType advertisements recorded in OC3B-defaults.md. Mechanism is
freedesktop-standard; per-type confirmation clicks are OC1's boot
check, named here rather than claimed.

http and https: advertised by this lane's meta-browser-app.desktop.
Set-as-default belongs to the ISO lane's mimeapps drop-in, per the
bond lanes split which leaves browser association to Bond's lane.
Not taken here, named here.

mailto: honestly absent everywhere. No mail client ships in any
package list, payload tree, or lane. A mailto: link has no
registered target; Xfce prompts rather than executing, which
satisfies the unknown-schemes rule below. Boot confirmation of the
prompt UI is OC1's; the absence itself is verified statically.

Unknown schemes generally: no custom scheme handlers ship in this
lane or, per tree search, any lane. Absence is the safe default and
it is recorded as such, not as a tested behavior.

236/249 handoff: the parole MimeType advertisement joins the
copy-only procedure in OC3B-desktop-handoff.md. Hana's canonical
mimeapps file is referenced, never edited.
