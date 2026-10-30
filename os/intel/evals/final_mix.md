# DEM-014 — narration final mix (provisional)

Date: 2026-10-28. Check script: `intel/final_mix_check.py` — 11/11 PASS.
Output: `demo-assets/audio/dem014-final-mix.mp3`, 68.49 s.

## What the mix is

Opening framing take 1 (WDG-031, Helio, 19.92 s) + 0.5 s silence +
watchdog segment take 1 (WDG-030, Helio, 48.07 s), one MP3 track.
Take 1 of each is the provisional pick: Helio is the default production
voice and the voice of the WDG-033 fallback track and the DEM-015 caption,
so the mix cuts against those assets without a voice change. No take is
marked final by Dale yet — the rehearsal pick is still open, and if Dale
picks take 2 the mix is rebuilt from take 2 (same script, same check).

## Level check (measured, not claimed)

- Both inputs MP3, decode clean; durations match the take log.
- Mix length 68.49 s = opening + gap + watchdog, exact to the probe.
- Mix peak -6.7 dB: no clipping, and within 0.6 dB of the louder input
  (-6.1 dB), so no level jump at the join.
- Reference: WDG-033 fallback track peaks at -5.5 dB (same voice,
  different edit) — reported for comparison, not forced as a target.

## What is NOT proven here

- Dale's rehearsal pick: not made. This mix is provisional, not final.
- Sync into the DEM-003 fallback video: that edit is not landed (Pax's
  task), so the mix is not yet placed in any video timeline.
- Level check against screen-capture audio: no screen capture exists
  yet. The check runs against the narration assets themselves plus the
  fallback-track reference. When the fallback video lands, the mix is
  re-checked against its capture audio before it is called final.
- Listening check on demo hardware: DEM-018, still open; this mix was
  verified by measurement only, not played on demo speakers/headphones.
- No human voice is involved: synthesized takes in Milo's voice lane,
  to be replaced or approved at rehearsal.
