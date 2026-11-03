# OC3B-226..230/232 — recorded defaults (canonical + this lane)

Source of truth for on-image defaults: Hana's
`os-build/metaos1-base/defaults/mimeapps.list` (canonical — NOT
edited here, NOT duplicated here). It maps: text/plain→mousepad,
image/png+jpeg→ristretto, application/pdf→evince (deliberate;
browser explicitly left to Bond's lane).

- 226 browser/handler: `x-scheme-handler/http(s)` advertised by this
  lane's `meta-browser-app.desktop` (MimeType line committed).
  Set-as-default belongs to the ISO lane's mimeapps drop-in, not to
  a .desktop file — recorded, not claimed.
- 227 file manager: Thunar opens folders; no MIME type involved
  (inode/directory handled by the file manager itself).
- 228 terminal: no file association (correct — terminals don't open
  files from the shell mimetype set).
- 229 text editor: mousepad=text/plain per canonical. Mine matches.
- 230 image/music/video: image→Ristretto (canonical). Music/video
  had NO claimant anywhere, which is why this lane's parole entry
  now carries `MimeType=video/mp4;video/mpeg;video/ogg;video/webm;
  audio/mpeg;audio/ogg;audio/flac;audio/x-wav` — advertising
  capability in my own file (standard freedesktop, reversible),
  NOT editing Hana's canonical list. Default-selection among
  registered handlers stays the ISO lane's call.
- 232 NOT set, with reasons: browser default (Bond's lane, named);
  mailto: (no mail client ships — see handlers note); print-to-file
  (a print-dialog feature of the viewers, not a MIME default).
- 243 start-page links vs defaults: start-page links are about:blank
  placeholders by design (offline); they open nothing, so no
  association can mismatch them. The tour's film/loop links are
  relative file paths → xdg-open → parole per the advertisement
  above, chain verified on paper, ends on OC1's click.
- 244 no default points at missing software: every .desktop named
  in this section carries TryExec; an absent binary hides its entry
  instead of breaking the association.
