# Meta Surveyor — spec

Status: SPEC ONLY, branch only, no merge, no code, no hardware built.
Written for del's 2026-11-03 ~21:2x EST order on the bus: spec out the
Meta Surveyor idea more — how it would work, and how it is better and
differs from the other apps. Answers del's sensor question first, because
it decides the whole design.

## 1. Del's sensor question, answered straight

Del is right: not all computers have the chips to read these fields. A
desktop with no temperature, air, barometer, or mic sensor cannot take a
field reading, and pretending otherwise would make the whole atlas fake.

So Surveyor does NOT require every device to sense. It splits the fleet
into roles, and only one role senses:

| Role | Device | Job | Needs sensors? |
| ---- | ------ | --- | -------------- |
| S — Sensor | Phone, tablet, sensor node, or any computer with a USB/Bluetooth sensor dongle | Takes the reading | YES |
| V — Verifier | Any Meta OS computer, including a sensor-less desktop | Runs the second-agent check, atlas, and cluster analysis | NO |
| H — Human confirm | A person on site with any device | Confirms a disputed or high-stakes reading in person | NO |

A sensor-less computer is not left out: it is where the verification,
the atlas, and the dispatch decision live. Sensing is the minority job;
checking and publishing is the majority job, and any machine can do it.
A cheap sensor dongle (temperature / humidity / air / water-level) can
also promote an ordinary computer to role S later — no new computer
needed, just the chip.

## 2. What it measures

One reading = one environmental fact at one place and time. Nothing
about any person.

| Field | Sensor source (role S) | Sensor-less fallback |
| ----- | ---------------------- | -------------------- |
| Heat | Phone / node temperature sensor | Weather-station feed, marked as second-hand, never as a field reading |
| Air quality | Particulate / gas sensor, or dongle | None — no reading is published without a sensor |
| Flood water | Water-level / pressure sensor, or a marked gauge photo | Human-confirmed gauge photo (role H) |
| Noise | Microphone, decibel level ONLY | None — no audio is stored (see §5) |
| Broken infrastructure | Camera photo of the damage (pothole, broken light, fallen sign) | Human-confirmed photo (role H) |
| Tree canopy | Camera photo, canopy-cover estimate | Satellite / public imagery, marked second-hand |

Rule: a field reading is only published if a real sensor or a real
photo produced it. Second-hand data is labelled second-hand and never
counts toward the two-agent confirmation in §3.

## 3. How it works, step by step

1. Agent A (role S) captures a reading: value, sensor type, device
   class, GPS place, time. The reading is unpublished.
2. Agent B (role V, on a DIFFERENT device, ideally a different device
   class) checks it independently: is there a second nearby reading in
   the same time window that agrees? Is the sensor sane (not stuck, not
   wildly out of range)? For photos, does the photo show what the claim
   says?
3. Only on agreement does the reading publish to the open atlas. On
   disagreement it stays unpublished and is flagged for a human check.
4. Published readings cluster: several confirmed heat readings in one
   neighbourhood make a heat island; several confirmed flood readings
   make a flood pocket. Clusters, not single readings, trigger action.
5. Humans are dispatched ONLY on confirmed clusters — a cooling centre
   for a heat cluster, a crew for a flood cluster, a repair ticket for
   a broken-infrastructure cluster. No dispatch on one unverified blip.

Nothing is forced: devices opt in, owners choose which sensors to share,
and a device can be role V only forever and still be a full citizen of
the app.

## 4. How it differs from the other apps

| App | What it is | Surveyor is not that because… |
| --- | ---------- | ------------------------------ |
| Meta Haven | Lookup of existing shelter beds | Haven looks up beds that already exist; Surveyor creates NEW primary data no lookup can return |
| Crime cameras | Agents watch cameras to catch crime | Cameras watch PEOPLE; Surveyor measures the ENVIRONMENT — no faces, no identity, no surveillance of anyone |
| Science Lab | Controlled lab experiments for agents | The Lab runs experiments in a lab; Surveyor senses the uncontrolled real world, street by street |
| Meta Mother Tongue | Elders' language, recorded with permission, taught back to kids | Mother Tongue preserves CULTURE; Surveyor maps the PHYSICAL world — different data, different users |
| Meta Forge | Agents design a part, a human confirms, a workshop makes it | Forge MAKES things; Surveyor MEASURES things. Forge fixes one broken object; Surveyor finds where the broken objects are |

## 5. Why it is better — the honest version

- Data no search engine has. A search engine can list shelters (Haven's
  problem) and show old satellite photos. It cannot tell you the heat on
  your block right now, the air on your street this morning, or which
  drains are flooding tonight, because nobody has published verified
  readings at that resolution. Surveyor's dataset is the product.
- Verified, not just crowdsourced. One phone saying "it's hot" is noise.
  Two independent agents agreeing, from different devices, is a fact
  worth acting on. The two-agent rule is the whole trust model.
- Helps people and civilization directly. Heat islands kill; floods
  strand people; bad air harms kids; broken infrastructure injures.
  A living, verified map of these is useful to residents, councils,
  researchers, and emergency planners alike — not just to agents.
- Privacy by construction. Readings are environmental aggregates: a
  temperature, a decibel number, a water level, a photo of a pothole.
  No names, no faces, no speech, no audio recordings, no tracking of
  any person. Noise is a number, never a recording.
- Cheap because it reuses what exists. Phones already carry most of
  these sensors; computers already run the verification. The only new
  hardware is an optional dongle, not a new fleet.

## 6. What agents use it for

- Route and dispatch: send help to confirmed clusters first.
- Planning: where to plant trees (heat + canopy together), where drains
  fail (flood clusters over time), where air is worst (school routes).
- Research: a dated, verified, open record of a neighbourhood's
  environment that scientists can cite, instead of anecdotes.
- Cross-checking other apps: Forge gets real reports of what is broken;
  Science Lab gets real field conditions to compare against lab results.

## 7. Demo tonight (still / video shot list, not yet made)

1. The atlas: a neighbourhood map with confirmed clusters glowing —
   one heat island, one flood pocket, one broken-light cluster.
2. The confirm flow: reading arrives → second agent checks → published
   stamp appears. One disputed reading shown held back, not published.
3. The dispatch line: "3 confirmed readings → crew ticket" — humans
   only on clusters, never on single blips.

## 8. Out of scope, explicitly not claimed

- No sensor network exists yet; no live readings have been taken.
- No hardware has been built or bought; the dongle is a proposal.
- No atlas is live; this spec is the design, and the demo visuals are
  mock-ups, labelled as such.
- Nothing here merges to main and nothing is forced on any device.
  Branch only, per the branches-only rule in force.
