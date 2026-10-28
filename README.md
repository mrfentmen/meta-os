# Meta Sentinel

Visual event detection prototype — Meta Global AI Developer Hackathon 2026, Indie track (Push the Frontier). Deadline: November 4, 2026, 9:00 PM ET.

Meta Sentinel turns sampled camera frames into structured, evidence-supported event assessments with explicit uncertainty, and measures how often it is right and wrong against staged ground-truth scenarios. It reports observable evidence only — never criminal intent — and every consequential call stays with a human reviewer.

- Full project brief: [BRIEF.md](BRIEF.md)
- Frontend UI (Agent 1 lane): `index.html` + `js/` — camera capture, frame sampling, assessment client, event timeline, session log export. Run/contract docs: [UI_README.md](UI_README.md)

Lanes (per project lead): Agent 1 frontend/camera — Hana. Agent 2 model integration — Rowan. Agent 3 pipeline/evaluation — Milo. Agent 4 integration/reliability/demo — Pax.

Status: UI first cut landed (tests 30/30). No model backend yet — the UI honestly reports "backend not connected" until the Agent 2 integration lands. Nothing is faked.
