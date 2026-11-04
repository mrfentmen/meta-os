// labs/music3d/takes-data.mjs — single source of truth for the Musica take
// list, the minimal SMF parser, and the transport reducer. Imported by
// index.html AND by tests/takes.test.mjs, so the test guards the exact data
// and code the page plays.
//
// Take facts below are copied from the session record, not invented:
//   os/worlds/musica/sessions/hn029-chipsynth/midi.json      (file, counts)
//   os/worlds/musica/sessions/hn029-chipsynth/take_log.jsonl (dur, tempo,
//     key, mode, waveform, verdict). take-004 was rejected by the keeper
//   pass (repetition 1.0) and has no MIDI file, so it is excluded.
export const SESSION_MIDI_DIR =
  "os/worlds/musica/sessions/hn029-chipsynth/midi";

export const TAKES = [
  { id: "take-001", file: "midi/take-001.mid", melody: 11, bass: 16, dur: 7.273, tempo: 132, key: "C", mode: "minor", verdict: "keeper" },
  { id: "take-002", file: "midi/take-002.mid", melody: 11, bass: 16, dur: 7.273, tempo: 132, key: "C", mode: "minor", verdict: "keeper" },
  { id: "take-003", file: "midi/take-003.mid", melody: 14, bass: 16, dur: 7.273, tempo: 132, key: "C", mode: "minor", verdict: "keeper" },
  { id: "take-005", file: "midi/take-005.mid", melody: 12, bass: 16, dur: 7.273, tempo: 132, key: "C", mode: "minor", verdict: "keeper" },
  { id: "take-006", file: "midi/take-006.mid", melody: 13, bass: 16, dur: 7.273, tempo: 132, key: "C", mode: "minor", verdict: "keeper" },
  { id: "take-007", file: "midi/take-007.mid", melody: 13, bass: 16, dur: 7.273, tempo: 132, key: "C", mode: "minor", verdict: "keeper" },
  { id: "take-008", file: "midi/take-008.mid", melody: 12, bass: 16, dur: 7.273, tempo: 132, key: "C", mode: "minor", verdict: "keeper" },
  { id: "take-009", file: "midi/take-009.mid", melody: 14, bass: 16, dur: 7.273, tempo: 132, key: "C", mode: "minor", verdict: "keeper" },
  { id: "take-010", file: "midi/take-010.mid", melody: 12, bass: 16, dur: 7.273, tempo: 132, key: "C", mode: "minor", verdict: "keeper" },
  { id: "take-011", file: "midi/take-011.mid", melody: 15, bass: 16, dur: 7.273, tempo: 132, key: "C", mode: "minor", verdict: "keeper" },
  { id: "take-012", file: "midi/take-012.mid", melody: 15, bass: 16, dur: 7.273, tempo: 132, key: "C", mode: "minor", verdict: "keeper" },
];

// Minimal Standard MIDI File reader: format 0/1, note-on/off, tempo map.
// Returns { division, tempoUsec, tracks } where each track is a list of
// { tick, kind: "on", pitch, vel } in file order. Throws on bad header.
export function parseSMF(bytes) {
  const d = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  const u32 = (o) =>
    (d[o] * 16777216 + d[o + 1] * 65536 + d[o + 2] * 256 + d[o + 3]) >>> 0;
  if (d[0] !== 0x4d || d[1] !== 0x54 || d[2] !== 0x68 || d[3] !== 0x64) {
    throw new Error("not an SMF (missing MThd)");
  }
  const ntracks = (d[10] << 8) | d[11];
  const division = (d[12] << 8) | d[13];
  if (division & 0x8000) throw new Error("SMPTE division not supported");
  let pos = 14;
  let tempoUsec = 500000;
  const tracks = [];
  for (let t = 0; t < ntracks; t++) {
    if (
      d[pos] !== 0x4d || d[pos + 1] !== 0x54 ||
      d[pos + 2] !== 0x72 || d[pos + 3] !== 0x6b
    ) {
      throw new Error("missing MTrk at track " + t);
    }
    const len = u32(pos + 4);
    const tr = d.subarray(pos + 8, pos + 8 + len);
    pos += 8 + len;
    const ev = [];
    let i = 0, tick = 0, status = 0;
    while (i < tr.length) {
      let v = 0;
      for (;;) {
        const b = tr[i++];
        v = (v << 7) | (b & 0x7f);
        if (!(b & 0x80)) break;
      }
      tick += v;
      const b = tr[i];
      if (b === 0xff) {
        const type = tr[i + 1], ln = tr[i + 2];
        if (type === 0x51 && ln === 3) {
          tempoUsec = (tr[i + 3] << 16) | (tr[i + 4] << 8) | tr[i + 5];
        }
        i += 3 + ln;
        continue;
      }
      if (b === 0xf0 || b === 0xf7) {
        i += 1;
        let v2 = 0;
        for (;;) {
          const bb = tr[i++];
          v2 = (v2 << 7) | (bb & 0x7f);
          if (!(bb & 0x80)) break;
        }
        i += v2;
        continue;
      }
      const explicit = !!(b & 0x80);
      if (explicit) { status = b; i += 1; }
      const cmd = status >> 4;
      if (cmd === 0x0c || cmd === 0x0d) { i += 1; continue; } // 1 data byte
      let d1, d2;
      if (explicit) { d1 = tr[i]; d2 = tr[i + 1]; i += 2; }
      else { d1 = b; d2 = tr[i + 1]; i += 2; } // running status: b IS d1
      if (cmd === 0x09 && d2 > 0) ev.push({ tick, kind: "on", pitch: d1, vel: d2 });
      else if (cmd === 0x08 || cmd === 0x09) ev.push({ tick, kind: "off", pitch: d1 });
    }
    tracks.push(ev);
  }
  return { division, tempoUsec, tracks };
}

// Voice split for the hn029 files: track 0 is meta, track 1 is the melody,
// track 2 is the bass. Times are converted to seconds at the file tempo.
export function takeVoices(parsed) {
  const secPerTick = parsed.tempoUsec / 1e6 / parsed.division;
  const toNotes = (ev) =>
    ev.map((e) => ({ t: e.tick * secPerTick, pitch: e.pitch, vel: e.vel }));
  const melody = toNotes((parsed.tracks[1] || []).filter((e) => e.kind === "on"));
  const bass = toNotes((parsed.tracks[2] || []).filter((e) => e.kind === "on"));
  const allTicks = parsed.tracks.flat().map((e) => e.tick);
  const last = Math.max(0, ...allTicks) * secPerTick;
  return { melody, bass, span: last };
}

const NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
export function midiName(pitch) {
  return NAMES[pitch % 12] + (Math.floor(pitch / 12) - 1);
}
export function midiFreq(pitch) {
  return 440 * Math.pow(2, (pitch - 69) / 12);
}
// Monotonic staff height: one semitone = 0.15 units, MIDI 48 (C3) = staff
// base. Melody (~60-75) sits on/above the staff, bass (~36) below it like a
// bass region. Labels carry the exact note name so height is indicative.
export function yOfPitch(pitch) {
  return 2.2 + (pitch - 48) * 0.15;
}

// Pure transport reducer (browser and node share it; node tests cover it).
// mode: stopped | playing | paused | ended. muted is independent.
export function transport(state, action) {
  switch (action) {
    case "play":
      if (!state.supported) return { ...state, mode: "stopped" };
      return { ...state, mode: "playing" };
    case "pause":
      if (state.mode !== "playing") return state;
      return { ...state, mode: "paused" };
    case "replay":
      if (!state.supported) return { ...state, mode: "stopped" };
      return { ...state, mode: "playing" };
    case "stop":
      return { ...state, mode: "stopped" };
    case "ended":
      return { ...state, mode: state.mode === "playing" ? "ended" : state.mode };
    case "mute":
      return { ...state, muted: true };
    case "unmute":
      return { ...state, muted: false };
    case "nosupport":
      return { ...state, supported: false, mode: "stopped" };
    default:
      return state;
  }
}
export function initialTransport(supported) {
  return { mode: "stopped", muted: false, supported: !!supported };
}
// The four visible audio states the page may show.
export function audioState(state) {
  if (!state.supported) return "unsupported";
  if (state.muted) return "muted";
  if (state.mode === "playing") return "playing";
  return "stopped";
}
