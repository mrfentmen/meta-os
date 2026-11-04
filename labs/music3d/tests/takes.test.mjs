// labs/music3d/tests/takes.test.mjs — node:test, no dependencies.
// Guards the take manifest and the SMF parser against the real session
// files, plus the transport reducer. Run:
//   node --test labs/music3d/tests/
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  TAKES, SESSION_MIDI_DIR, parseSMF, takeVoices,
  midiName, midiFreq, transport, initialTransport, audioState,
} from "../takes-data.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "..", "..", "..");
const sessDir = path.join(repo, "os/worlds/musica/sessions/hn029-chipsynth");
const midiJson = JSON.parse(fs.readFileSync(path.join(sessDir, "midi.json"), "utf8"));
const takeLog = fs.readFileSync(path.join(sessDir, "take_log.jsonl"), "utf8")
  .trim().split("\n").map((l) => JSON.parse(l));
const logById = Object.fromEntries(takeLog.map((e) => [e.take_id, e]));
const catById = Object.fromEntries(midiJson.takes.map((t) => [t.take_id, t]));

test("manifest lists exactly the 11 keeper takes, take-004 excluded", () => {
  assert.equal(TAKES.length, 11);
  const ids = TAKES.map((t) => t.id);
  assert.ok(!ids.includes("take-004"), "rejected take-004 has no MIDI file");
  assert.deepEqual([...ids].sort(), Object.keys(catById).sort());
});

test("manifest matches midi.json + take_log.jsonl exactly", () => {
  for (const t of TAKES) {
    const cat = catById[t.id], log = logById[t.id];
    assert.ok(cat, t.id + " in midi.json");
    assert.ok(log, t.id + " in take_log.jsonl");
    assert.equal(t.file, cat.file);
    assert.equal(t.melody, cat.melody_notes);
    assert.equal(t.bass, cat.bass_notes);
    assert.equal(t.dur, log.measurement.duration_s ?? log.duration_s);
    assert.equal(t.tempo, log.params.tempo);
    assert.equal(t.verdict, log.verdict);
    assert.equal(log.verdict, "keeper");
    const mid = path.join(sessDir, cat.file);
    assert.ok(fs.existsSync(mid), mid + " exists on disk");
  }
});

test("parseSMF recovers the catalogue note counts from every real .mid", () => {
  for (const t of TAKES) {
    const bytes = fs.readFileSync(path.join(sessDir, t.file));
    const p = parseSMF(bytes);
    assert.equal(p.division, 220);
    assert.ok(p.tempoUsec > 0);
    assert.ok(p.tracks.length >= 3, t.id + " has meta+melody+bass tracks");
    const { melody, bass, span } = takeVoices(p);
    assert.equal(melody.length, t.melody, t.id + " melody note-ons");
    assert.equal(bass.length, t.bass, t.id + " bass note-ons");
    for (let k = 1; k < melody.length; k++) {
      assert.ok(melody[k].t >= melody[k - 1].t, t.id + " melody times sorted");
    }
    assert.ok(span > 0 && Math.abs(span - t.dur) < 0.05,
      `${t.id} file span ${span.toFixed(3)}s ~= session log ${t.dur}s`);
  }
});

test("parseSMF rejects non-MIDI bytes", () => {
  assert.throws(() => parseSMF(new Uint8Array([1, 2, 3, 4])), /not an SMF/);
});

test("note names and frequencies are sane", () => {
  assert.equal(midiName(69), "A4");
  assert.equal(midiName(60), "C4");
  assert.ok(Math.abs(midiFreq(69) - 440) < 1e-9);
  assert.ok(Math.abs(midiFreq(72) / midiFreq(60) - 2) < 1e-9);
});

test("transport reducer covers play/pause/replay/stop/ended/mute", () => {
  let s = initialTransport(true);
  assert.equal(audioState(s), "stopped");
  s = transport(s, "play");
  assert.equal(audioState(s), "playing");
  s = transport(s, "pause");
  assert.equal(s.mode, "paused");
  assert.equal(audioState(s), "stopped");
  s = transport(s, "play");
  s = transport(s, "ended");
  assert.equal(s.mode, "ended");
  s = transport(s, "replay");
  assert.equal(audioState(s), "playing");
  s = transport(s, "mute");
  assert.equal(audioState(s), "muted");
  s = transport(s, "unmute");
  assert.equal(audioState(s), "playing");
  s = transport(s, "stop");
  assert.equal(audioState(s), "stopped");
  const dead = transport(initialTransport(false), "play");
  assert.equal(audioState(transport(dead, "nosupport")), "unsupported");
});
