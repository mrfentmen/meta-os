# Trio — what the split lost, and why the three apps look like one app

Written 2026-11-04, before any change. This is the "find out first" pass: an
inventory, not a build.

Sources compared:

- **original**: `imperium/index.html` (546 lines) — the single console the Trio
  was split out of, at `3eb9e033` and earlier.
- **new**: `trio/vigiles.html` (439), `trio/ignis.html` (396),
  `trio/medicus.html` (564), from `c78a88a9`.

---

## 1. Features the original had, and the new pages do not

Every row was checked with a grep over the three new pages; the counts were
zero in all three unless a column says otherwise.

| Original feature | Evidence | vigiles | ignis | medicus |
|---|---|---|---|---|
| Camera wall (watched cameras + LA Caltrans feeds) | `imperium/index.html:121` `#cmd-wall` | no | no | no |
| Local camera: start/stop, facing, analysis sampler | `:185` `#btn-camera-start` | no | no | no |
| Still image → assess | `:244` `#image-input` | no | no | no |
| Recorded video → assess one frame | `:259` `#video-input` | no | no | no |
| Assessment config (endpoint, interval, scenario) | `:273` `#endpoint` | no | no | no |
| Latest assessment panel | `:289` `#latest-assessment` | partial (inspector result) | partial (hot frame) | no |
| Event history with "show assessment" | `:297` `#history-list` | no | no | no |
| Evaluation session log + stats + export/clear | `:302` `#log-stats` | no | no | no |
| Ctrl/Cmd+K search overlay + shortcut sheet | `:143` `#cmd-search-overlay` | no | no | no |
| Map modes: City / Tactical / Incident / AI Focus | `:46-48` | no | no | no |
| Map layers: Fires, Radar | `:52` | no | no | no |
| Watch sampling start/stop, Mark reviewed | `:94-95` | no | no | no |
| Assessment pipeline stepper | `:99` `#cmd-stepper` | no | no | no |
| Ignis analytics (21 panels: scoreboard, confidence, review queue/triage/audit, evidence, uncertainty, observation classes, model attribution, footage source, scenario breakdown…) | `:392+` | no | no | no |
| Backend/system panel (endpoint, model, latency, watched/flagged bars) | `.cmd-system` | no | no | no |

What did carry over: map, camera list, watch/unwatch, assess-now, flagged
queue (vigiles), crew status line, clock, and one shared store in `core.js`.

The three new pages are not thin by accident — each is a deliberate single
idea (Vigiles = map, Ignis = wall, Medicus = triage board). The gap list above
is the price of that decision, and the question is which rows to buy back and
where they belong.

## 2. The "chat box"

There is **no chat UI in the original console** — no composer, no transcript,
no message list. A repo-wide search for `chat` over `.html/.js/.py` returns
only model-server code.

Two chat-shaped things exist today:

1. **Medicus duty-agent panel** — `trio/medicus.html:41` `<form id="agent-form">`
   with `#agent-log` above it ("Ask the duty agent about this board"). This is
   the only in-app agent chat, and only Medicus has it.
2. **Messages** — `bus.html:230` `<input id="compose">` + Send, docked as a tile
   (`os-build/face/meta-desktop.sh:372`, served from 18934). This is a real
   message bus, not an AI chat.

So "the chat box we're missing" is almost certainly (1) the agent panel, which
Vigiles and Ignis do not have — or (2) Messages never rendering because the bus
backend is not answering. Both are plausible; they are different fixes.

## 3. Why the three read as one app

The layouts differ, the tokens differ, and it still reads as one product line:

- all three link the same `trio.css` (`vigiles.html:7`, `ignis.html:7`,
  `medicus.html:7`), which carries the type stack (`trio.css:20-21`), the
  13 px body size (`:35`), every button/chip/focus/scrollbar rule;
- the same chrome anatomy in all three: wordmark left, clock right, 30-46 px
  top bar, one-line status strip at the bottom;
- the same component vocabulary: uppercase 10 px mono micro-labels, `.btn`
  pairs, pill chips, hairline panels;
- emoji glyphs used as identity marks (`❖` Ignis, `✚` Medicus, `✕` closes).

`anti-ai-slop-ui`'s lint over `trio/` scores 1.0/10 risk but flags four emoji
icons — the mechanical tells are low, the sameness is structural, not
mechanical.

### Three directions that cannot be confused

Chosen with the skill's direction library, one per division, and deliberately
different in *density, palette temperature, radius and type voice* — not three
hues of the same dark console.

| | Vigiles | Ignis | Medicus |
|---|---|---|---|
| direction | Security Operations Console | Incident wall / broadcast gallery | Clinical triage paper |
| base | near-black slate `#070b16` | charcoal `#14100d` + ember `#d9602b` | **light** paper `#f4f1e8`, ink `#20241f` |
| accent | one cold blue `#4f7ec2` | ember, used only on live/flag | trauma red `#b23a2f`, used only on immediate |
| radius | 0 everywhere | 2 px frames, 0 chips | 10-14 px cards, pill chips |
| type | 12 px grotesk, mono only for IDs | serif wordmark + 15 px labels, big numerals | 13 px humanist, serif headings, mono only timestamps |
| primary object | the map | the camera wall | the three lanes |
| map | full-bleed, panels slide over | inset, closed by default | separate tab, not on the board |
| motion | none but state | frame cross-fade on new assessment | card entry only |

And the code split that makes it stick: each page owns its own CSS file
(`trio/vigiles.css`, `trio/ignis.css`, `trio/medicus.css`) with no shared
stylesheet. `core.js` stays shared — backend wiring is not a look.

## 4. Proposed order (needs a yes)

1. Drop `trio.css`; three private stylesheets; remove the emoji marks.
2. Buy back the rows that belong to each division only:
   - Vigiles: camera wall collapsed to a bottom drawer, local camera + still
     image inputs, event history, Ctrl+K, map modes.
   - Ignis: the 21 analytics panels as a collapsible "session" drawer, video
     frame input, radar/fires layers.
   - Medicus: agent panel promoted (transcript + canned questions), history.
3. One shared shell contract only: `core.js` exports and the backend ports.
4. Re-shoot the three pages at 1440×900 and 1180×780 before any image sync.

Not in scope until asked: renaming, new backends, booting QEMU.
