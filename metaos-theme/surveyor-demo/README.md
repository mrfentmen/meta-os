# Meta Surveyor demo art

Concept mockups for the Meta OS demo, made per del's 2026-11-03
applications directive (pics for the demo). These are GENERATED
concept images, not screenshots of a running app — Surveyor is
specced, not built.

- `open-atlas-dashboard.png` — the open atlas: verified readings
  (heat, air, flood water, noise, broken infrastructure) on a
  neighbourhood map. Two-agent confirmation before a reading
  publishes, per the spec.
- `field-capture.png` — an agent's field capture screen: a heat
  reading awaiting second-agent confirmation before publishing.

Spec: `docs/META_SURVEYOR_SPEC.md` on branch `rowan/surveyor-spec`
(@ 0dadabd, off main af457eb). Chip question answered there first:
not all computers sense, so only sensor devices take readings;
sensor-less machines use a dongle (promotion role).
