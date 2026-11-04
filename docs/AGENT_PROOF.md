# Agent proof: what is wired, why the OS is agentic, and what the tools did

Evidence log, not a plan. Every number below came from a command that is named
under it, run on this machine on 2026-11-04 against commit `39a9381a` (plus the
commit that adds this file). Where something is not proven, §8 says so in plain
words instead of leaving it implied.

**The claim, scoped.** Meta OS ships an agent layer that (a) answers on every
application page through one endpoint, (b) keeps a roster of named agents with
their own instructions and model, (c) remembers a room across restarts, and
(d) runs a real think → act → verify loop whose tools touch a real directory and
a real shell. It does **not** yet let the on-page chat run tools, and its
permissioned gateway is not yet the loop's path. Both are named in §8.

---

## 1. What is wired

| Surface | Route / entry | Backend | Proof |
|---|---|---|---|
| All 14 app personas, one chat box | `POST /api/agent/ask` | `server/agent-chat.mjs` | §3 |
| Bot roster (12 bots, titles, voices, model) | `GET /api/agent/roster` | `server/bot-roster.mjs` | §4 |
| Room transcript, restored on reopen | `GET /api/agent/thread?id=` + append on ask | `server/agent-thread.mjs` | §4 |
| Who answers, and why | `picked_by` on every reply | `chooseResponder` in `server/agent-chat.mjs` | §4 |
| Chat box on each page | `js/agent-chat.js` (`data-app=…`) | same origin / 18934 | §3 |
| Division consoles | `trio/agent.js` → same route with `division` | `server/agent-chat.mjs` | §3 |
| Think → act → verify loop | `node agents/agent_loop.mjs` | `agents/agent_loop.mjs` + `agents/model_client.mjs` | §6 |
| Permissioned tool gateway with receipts | `createToolGateway()` | `agents/tools.mjs` | §6 |
| Shared spend ledger | `server/budget.mjs` | JSON ledger, $75 test budget | §7 |

Two spend bounds protect every path: the server checks the shared ledger before
each call (`checkBudget`), and the loop carries `--max-usd` (default $0.25).

---

## 2. How to reproduce everything in this document

```sh
# §3 and §4 — every app, the roster, thread memory, mention routing (~$0.09)
METAOS_KEY_FILE="$HOME/Desktop/Hackathon Key.txt" tools/proof_agent_chat.sh

# §6 — tools, the gateway, a live tool-calling run (~$0.002)
METAOS_KEY_FILE="$HOME/Desktop/Hackathon Key.txt" tools/proof_agent_tools.sh

# §5 — the suites
npm run test:agents                                    # 254 tests
node --test tests/agent-chat.test.mjs tests/agent-roster.test.mjs
sh os-build/tools/verify_tree.sh                       # the image gate
```

Both proof scripts refuse to run without a key, print the spend they caused,
and exit non-zero on any failed check.

---

## 3. Proof the agents answer: every app, one endpoint

`tools/proof_agent_chat.sh`, run live (real model, contributor tier):

```
== every app answers through /api/agent/ask
  [200] vigiles   Board shows 2 of 6 watched. 34th St is clear with normal activity. 8th Ave is flagged as crowd gathered so a human should look at that feed. The flag is not a dispatch and not an identification.
  [200] ignis     Take-003 is listed as flagged for smoke described as a low grey column above the roofline … A flag is a reason to look, not a report of a fire. The context shows smoke only with no visible flame described, so visible flame is missing to answer whether fire is visible.
  [200] medicus   You have three frames queued: take-001 not assessed, take-002 flagged with the note person seated on the kerb, and take-003 not assessed. The flag only marks take-002 for review … It is not a diagnosis and does not sort patients.
  [200] science   You have caffeine loaded with 24 atoms and formula C8H10N4O2.
  [200] musica    The session record for hn029-chipsynth take-006 shows wav served (4128 KB). This machine has no audio device so playback cannot start, which is why the track is silent.
  [200] officina  No, the figures on this sheet are not live telemetry. They are records from the merged tree as stated in the footer. The actual callout values … were not included in the context provided so I cannot quote them here.
  [200] custos    The header you quoted says STATE: PARKED so it is not showing as live … The two agent records and $0.004 figure you quoted is an estimated spend, which is an estimate and not a bill.
  [200] boards    DSNY is the empty section showing no pack file. A red pin means a camera a division flagged for human review.
  [200] aegis     This page shows a read-only dashboard over recorded findings with four findings newest first including one high severity secret in a test fixture. It scans nothing and fixes nothing …
  [200] nervus    No port on 127.0.0.1 answered in the information provided … What is missing is the Nervus service view showing ports trays and which backend answered with health.
  [200] messages  The Board currently shows rooms main, custos, officina, science and musica. NOTIFY lines are posted by the resident agent crew.
  [200] monitor   These cards come from http://127.0.0.1:18932/facts with the last reading showing load 1.42, memory 61 percent and uptime 2h14m …
  [200] notes     The context does not name which Meta OS app is open so I cannot name the app from what is given …
  [200] general   No app context was provided because the page did not identify itself … I am read-only and cannot open apps or check anything myself.

== every page serves its box
  [ok]   surfaces.html                          boards
  [ok]   design/meta-custos-watch.html          custos
  [ok]   design/meta-officina-blueprint.html    officina
  [ok]   labs/molecules/index.html              science
  [ok]   aegis-page/index.html                  aegis
  [ok]   nervus/index.html                      nervus
  [ok]   trio/vigiles.html                      vigiles
  [ok]   trio/ignis.html                        ignis
  [ok]   trio/medicus.html                      medicus
  [ok]   musica.html (face, 18900)              musica
  [ok]   dashboard.html (face, 18900)           monitor

this run, estimated: $0.082830 (cap $0.40)
RESULT: PASS — every app answered and every page carries its box
```

What this proves: one endpoint, fourteen personas, every page carrying the box,
and a refusal path that names the port instead of spinning (the two face pages
hit a 18934 that was running and answered). What it does **not** prove: that the
answers are *deep* — each is bounded to the page context handed to it, by design.

---

## 4. Proof the desk is a room, not a form

Same script, room section, live:

```
== the room: roster, thread memory, and who answered
  [ok]   roster lists 12 bots
  [ok]   lead answers the first turn        {"status":200,"bot":"ember","picked_by":"lead","history_turns":0,…}
  [ok]   the fire desk's bot is Ember       {"status":200,"bot":"ember",…}
  [ok]   nothing to remember yet            {"status":200,…,"history_turns":0,…}
  [ok]   the second turn sees the first     {"status":200,…,"history_turns":2,…}
  [ok]   a mention reaches Beaker           {"status":200,"bot":"beaker","picked_by":"mention","history_turns":4,…}
  [ok]   a mention is reported as one       {"status":200,…,"picked_by":"mention",…}
  [ok]   the thread kept all 6 lines
```

Browser check (Chrome, headless, real panel, real API): twelve chips rendered
with the page's own bot lit, `@Watch …` answered by **Watch** with
`picked_by: "mention"`, and a second full page load **restored the earlier turn
from the server** before the new exchange:

```
"chips": ["Beaker*","Watch","Ember","Halo","Sentry","Wire","Ledger","Forge","Reed","Desk","Gauge","Meta"]
"res":   {"ok": true, "bot": "Watch", "picked_by": "mention"}
run 2 log: ["user|@Watch what does the camera board show?", "agent|Watch …", "user|@Watch …", "agent|Watch …"]
```

Routing rule, in one line: a typed `@name` beats the lit chip; `@everyone` is
answered once by the room's lead and says so; a message that clearly belongs to
another desk (two matching terms) is routed there and marked `routing`; anything
else goes to the page's own bot as `lead`. The reply always carries which one
happened, so a guess never looks like a person's choice.

---

## 5. Why the OS is agentic (the definition being used)

Agentic here means the loop closes: **perceive → decide → act → verify → record**,
with the decision made by the model and the action performed on the real machine.

- **Perceive**: the page hands the model what it shows (`contextFor()` in
  `js/agent-chat.js`); the loop reads the workspace and the task.
- **Decide**: the model chooses the next tool as one JSON object
  (`SYSTEM` in `agents/agent_loop.mjs`), not a canned script.
- **Act**: real filesystem writes and real `spawn()`ed commands inside a
  workspace (`execTool`), with path escapes, destructive commands and the API key
  all refused or stripped.
- **Verify**: the loop feeds each tool result back and the run only ends `ok`
  when the model calls `finish`; this document then re-runs the artefact itself.
- **Record**: every step is appended to `transcript.jsonl`, and the gateway
  writes `receipts.jsonl` with a hash per action.

The chat layer is deliberately **read-only** and says so in its own system
prompt ("you cannot open apps, move the pointer, change the board, or send
anything"). So "agentic" is true of the agent runtime; the chat box is the
conversation surface in front of it. §6 is the proof the runtime's hands work.

---

## 6. Proof tools and tool calls work

`tools/proof_agent_tools.sh`, three parts, run live:

### A. The tools themselves — no model, no key, no spend

```
PASS write creates parents
PASS read returns content
PASS list sees the file
PASS run executes and captures stdout
PASS run reports a nonzero exit
PASS path escape is refused
PASS dangerous command is refused
PASS tool subprocess never sees the key
agent_loop self-test: 8/8 pass
```

### B. The permissioned gateway: grant → action → receipt, and a refusal that is recorded

```
write  receipt tool-1-fbdd9e ok=true bytes=12 sha256=48cd412e3a12…
read   bytes=12 evidence=tool:tool-2-45e601 sha256:48cd412e3a12641df429228f39c829defa0a00125d9da15cddbd0a2e0824334d
exec   stdout="42" exit=0 stdoutSha256=73475cb40a56…
refuse code=path-outside-grant receipt=tool-4-2de1a2 ok=false
receipts 4 [write:true,read:true,exec:true,write:false] seq=1,2,3,4
escape file created=false
gateway ok
```

Each allowed action carries a content hash; the refused one carries its grant
code and still leaves a receipt; the refused write did not touch the disk.

### C. A model choosing the tools, and the OS performing them

Live, `muse-spark-1.3-contributor`, `--max-actions 6 --max-usd 0.20`:

```
agent_loop: finished after 4 steps, 4 model calls, $0.0012 est
agent_loop: Created build/hello.mjs with a for-loop summing 1..10 and printing sum. Ran `node build/hello.mjs` — output was exactly `55` (stdout: "55\n", exit code 0).

{"ok":true,"stopped":"finished","model":"muse-spark-1.3-contributor",
 "tools":["list","write","run","finish"],"writes":1,"runs":1,"calls":4,"usd":0.001157}

  [ok]   the loop finished on its own                   exit 0
  [ok]   the model called write and run                 tools: list → write → run → finish
  [ok]   the artefact runs and prints 55                node build/hello.mjs -> 55
  [ok]   the transcript records the run                 4 lines, no key
```

The model chose `list`, wrote a 77-byte file, ran `node build/hello.mjs` (a real
6-second subprocess), read the result and finished with that output as its
evidence. The script then ran the artefact **itself** and got `55`, so the proof
does not rest on the agent's own summary.

```
RESULT: PASS — the tools run, the gateway refuses and records, the model called them, the artefact verifies
```

---

## 7. Testing and spend

| Check | Result |
|---|---|
| `npm run test:agents` (agent layer, chaos pack) | **254/254 pass** |
| `tests/agent-roster.test.mjs` (roster, routing, threads) | **29/29 pass** |
| `tests/agent-chat.test.mjs` (14 personas, refusals, ledger) | **20/20 pass** |
| `tools/proof_agent_chat.sh` (live, 14 apps + room) | **PASS**, $0.0828 |
| `tools/proof_agent_tools.sh` (tools + gateway + live run) | **PASS**, $0.0012 |
| `os-build/tools/verify_tree.sh` (image gate) | **14/14 PASS** |

Spend for this document and the work in it, measured rather than estimated:

- live chat proof run: **$0.08283**
- browser probes and direct endpoint checks (server ledger delta): **$0.0322**
- three live tool-calling runs: **$0.00347**
- **total ≈ $0.119**, against the **$1.00** limit for this task; the shared
  ledger stands at **107 calls / $0.3776 of the $75 test budget**.

One honest accounting gap: `agent_loop.mjs` reports its own usage
(`usage.usd` in `agent-result.json`) and enforces `--max-usd`, but it does not
write the server's shared ledger. The two numbers above are kept separately for
that reason.

---

## 8. What this does not prove

- **The chat box cannot run tools.** It answers from page context; the runtime
  that acts is `agents/agent_loop.mjs`, reached through the job queue, not
  through `/api/agent/ask`.
- **The permissioned gateway is not yet the loop's path.** `agents/tools.mjs`
  checks grants and writes receipts (§6B) and is covered by
  `tests/agents-tools.test.mjs`, but `execTool` in the loop performs the action
  directly. Wiring the loop through the gateway is the next piece of work, and
  until it lands, "every action leaves a receipt" is true of the gateway and not
  yet of the loop.
- **No approval cards.** There is no Allow/Deny surface for a risky action; the
  loop's protection is its refusals (path escape, destructive command) and its
  caps, not a person in the loop.
- **No delegation between agents.** A roster entry answers questions; it cannot
  hand work to another bot.
- **No new ISO boot since these changes.** §1–§7 prove the running system and
  the image gate, not a fresh install; the boot proof is a separate artefact.
- **The loop is capped at 12 actions by default.** A task needing more is
  stopped and says so (`stopped: "actions"`), rather than running on.

Next, in the order that makes the claims above stronger: route `execTool`
through `createToolGateway`, surface its refusals as Allow/Deny cards in the
chat, then re-run §6 with the gateway in the path and update this document from
the new outputs.
