# Gap records — R13-015 echo

## R13-015-G1 — no metrics line

- **Claim:** `echo` emits a metrics line.
- **Reality:** `services/echo/echo.goose` has one function, `main`, and its entire output is
  `"> "` plus `"echo: <line>\n"`. There is no counter or stats structure anywhere in the file.
- **Evidence:** `nl -ba services/echo/echo.goose` (22 lines, reproduced in `CONTRACT_R13.md`).
- **Impact:** observability for this program is the line stream only. Any metrics claim about
  `echo` is false until a counter and a sink exist.
- **Owner:** echo program; Layer 4 metrics contract.

## R13-015-G2 — not a service, so there is no metrics attachment point

- **Claim:** `echo` is a service whose metrics can be scraped.
- **Reality:** the file is a standalone `main`; it has no `svc_entry`, no `SVC_*` id, is not in
  `services/MANIFEST.md` and is not in the call matrix. The README states this and calls it
  `NOT IMPORTABLE`.
- **Evidence:** `services/echo/echo.goose:8`; `services/echo/README.md` first paragraph.
- **Impact:** there is no permission check, no supervisor handle and no service registry entry
  through which a metrics consumer could find it.
- **Owner:** echo program classification; manifest/call-matrix inclusion decision.
