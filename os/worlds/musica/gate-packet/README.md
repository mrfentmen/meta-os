# Meta Musica gate packet (HN-055)

Everything needed to gate-1 the Musica lane (HN-026..HN-055)
in one folder. Branch: hana/musica. No merge without the
boss's word.

## How to gate

1. Read PACK.md (status PARTIAL) and ADOPTIONS.md.
2. Re-run the lane tests: `node --test tests/musica-*.test.mjs`
   (their output is filed here as test-results.txt).
3. Replay any take from its log entry:
   `python3 os/worlds/musica/runtime/compose.py --replay \
   os/worlds/musica/sessions/<session>/take_log.jsonl <take-id> out.wav`
   and compare sha256 with the log entry.
4. Open board/board.html (studio board), board/museum.html
   (failure museum), and the session boards under sessions/.
5. Check the flagship bundle: os/worlds/musica/exports/musica-hn029-chipsynth-bundle.zip.

## Lane totals (from records.json)

- Sessions: 5
- Takes logged: 124
- Keepers: 108
- Rejects: 16

## Full suite note

Full suite on branch hana/musica: 2038 tests run / 1982 pass / 56 fail; the 56 failures are the known pre-existing WKWebView/native set, identical to baseline; all 39 musica tests pass. Musica-only run: 39/39.

## Known limits (honest, not hidden)

- Spark-assisted composition is builders only: no key in
  this sandbox, no live calls sent, no model reply recorded.
- Board audio playback is not verified in a real browser
  (no browser in this sandbox; the pages are static HTML).
- The Mac gate needs ffmpeg and pretty_midi installed
  (pip install pretty_midi, MIT).
- Catalogue audio for sessions after hn029 is reproducible
  from the log, not committed (repo-lean policy).
- Duet mode is scoping only (docs/DUET_SCOPE.md), no code.
- Openverse API is unverified from this sandbox (bot check).
