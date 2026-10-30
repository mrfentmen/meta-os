# Agentic architecture of this codebase

How the Meta Trio / OS-queue stack actually implements the standard
agentic-AI architecture pillars — and which ones it deliberately
does not. Every claim below names the file that backs it. If a
mechanism is not in the code, this document says so instead of
stretching.

The system in one paragraph: the Trio apps call `POST /api/assess`
(`server/server.mjs`, `server/assess.mjs`). With the queue enabled,
a request becomes a deterministic job on the OS jobs store, a
resident agent claims it, generates a real Muse Spark assessment,
validates it against the v2 contract, writes the result, and posts
a NOTIFY line to Meta Nuntius, this repo's own relay. `run-stack.sh`
starts the four processes: relay, queue service, resident agent,
app server.

## 1. Planning core — deconstruction and self-reflection

**Deconstruction: present, as a fixed pipeline.** A request is
broken into the same named steps every time: request validation
(`server/assess.mjs`), job construction with a deterministic id
(`buildQueueJob` in `server/queue.mjs`), filing (`server/queue/
queue_service.py`), then claim → verify → generate → validate →
write result → notify (`server/queue/trio_agent.py`). The plan is
the pipeline, fixed in code. Honest limit: the model does not
decompose tasks dynamically; no planner invents new steps at
runtime.

**Self-reflection / self-correction: present, bounded to one
retry.** When Spark's output fails `validateAssessment`,
`trio_agent.py` makes exactly one correction retry: a second
generation call whose prompt carries the validation errors
(`server/queue/spark_gen.py` `build_prompt(..., correction)`),
through the same guardrail — a second counted call, never a free
one. If the retry validates, its output is the result, unannotated
(the contract object stays purely the model's corrected output;
the retry shows only in the agent log and in `latency_ms`, which
sums both calls). If it also fails, the job is written as a failed
result, exactly as a first failure is. On the DEV helper transport
the retry also happens, but the helper's fixed CLI accepts no
correction text, so that retry re-sends the standard prompt; the
correction text reaches the model on the direct transport. Error
reflection also exists one level up: when the queue path fails,
`server/assess.mjs` logs the fallback and takes the direct Spark
path — visible in server logs, never silent. Not present:
open-ended self-rewriting of instructions or retry loops.

## 2. Tool integration — the hands

The agent's tools are few and named: Muse Spark for generation
(direct HTTPS transport in `server/model.mjs` for the app server
and `server/queue/spark_gen.py` for the resident agent), the jobs
store over Upstash Redis REST (`server/queue/trio_store.py`), and
the Meta Nuntius relay for notifications (`relay/relay.mjs`). In
the sandbox, the direct key never enters the environment: the DEV
transport delegates to the `custom.meta-model-api` connector helper
(`spark_call.py`, reached through the credential surrogate), and
that path is labelled DEV everywhere it appears. There is no
general tool-calling surface beyond these; each process can touch
exactly what its job needs.

## 3. Memory — two honest layers, no vector store

**Operational state** lives in the jobs store
(`server/queue/trio_store.py`): the job envelope, a status hash
(open / claimed / done / failed, claim holder, lease), and the
result at `trio:{jid}:result`. That store is the system's working
memory — what is pending, what is claimed, what is finished.

**Durable log** lives in two append-only records: Meta Nuntius
lines (in-memory by default; JSONL file persistence when
`RELAY_STORE_FILE` is set — `relay/relay.mjs`) and the guardrail
cost log (`server/queue/spark_guardrail.py`, one entry per call
with usage, latency, and estimated cost).

**Not present — deliberately:** no vector database, no knowledge
graph, no semantic recall. The state here is small, structured,
and exact (job ids, statuses, results); key-value state answers
every question the system asks, and fuzzy recall would only add
ways to be wrong.

## 4. Orchestration loop — Perceive → Reason → Act → Evaluate

`trio_agent.py` runs the loop as a bounded poll cycle.
Perceive: poll the namespace index for open jobs. Reason: the
fixed pipeline decides the next step (claim, verify, generate).
Act: claim under a lease (a heartbeat thread renews it while
generating), decode and hash-verify the frame, call Spark.
Evaluate: run the repo's own `validateAssessment`
(`js/schema.js`); on failure, the one bounded correction retry;
on success, write the result envelope and post the NOTIFY line.
The loop is not open-ended autonomy: fixed steps, fixed bounds,
and every exit writes a durable result — ok or failed, never
nothing. `server/assess.mjs` runs the same shape per request:
queue first, evaluate the returned assessment, and an invalid
assessment is an HTTP 502 — never a silent fallback or a rewrite.

## 5. Multi-agent specialization

One resident agent process serves three specialized products. The
specialization is data, loaded per job from `js/products.js`:
Vigiles, Ignis, and Medicus each carry their own display name,
department framing, observation categories, and limitations text,
and the generation prompt is built from the job's product profile
(`spark_gen.py`). The processes are also specialized — app server,
queue service, resident agent, relay — each doing one job
(`run-stack.sh`). Not present: runtime agent-to-agent debate or
critique; processes communicate only through the job queue and
NOTIFY lines.

## 6. State checkpointing and recovery

Job state is persisted in the store at every step, so a restarted
agent resumes from the store, not from process memory. Job ids
are deterministic — sha256 over product, timestamp, and frame
bytes (`server/queue.mjs`) — so resubmitting the same frame files
the same job instead of a duplicate. Idempotency is checked
before claiming and again under the claim: if a result already
exists, generation is skipped and the frame is never re-billed
(proven by `tests/queue-python`). Claims are a SET NX mutex plus
a lease, renewed by heartbeat during generation
(`server/queue/trio_store.py`).

**Partial, stated plainly:** if an agent dies mid-generation
after claiming, the claim mutex expires with its lease, but
nothing flips the job's status hash back to open, so automatic
requeue of a claimed-but-unfinished job is not implemented.
Unclaimed jobs and finished results are fully durable; the
claimed-crash case needs a manual reset or a future sweeper.

## 7. Human-in-the-loop gates

Every assessment contract carries `requires_human_review`, a
required boolean enforced by `validateAssessment` (`js/schema.js`)
on both paths — nothing reaches a user without the flag. The
generation prompts instruct the model to set it true when unsure
(`spark_gen.py`); the sandbox helper's prompt sets it true
unconditionally. The Ignis duty-officer review queue
(`js/ignis-review-queue.js`) buckets recorded assessments by that
flag and is a pure reading: it never flags anything itself, never
notifies anyone, never dispatches — reaching out stays a human
action. Nothing in this system auto-dispatches; the product
limitations in `js/products.js` say so in the products' own text.
Live model spend itself is behind a human gate: `server/model.mjs`
refuses calls as "held" until the test phase is green-lit.

## 8. Deterministic guardrails and budgets

- **Budget hard stop:** `server/queue/spark_guardrail.py` counts
  every direct-transport call, logs its estimated cost (usage
  tokens at the published rate card), and refuses to send any
  call that would start at or beyond the $75 test budget. The
  DEV helper transport enforces its own identical guardrail in
  its own state file; calls are never counted in both.
- **Input integrity:** the queue service verifies the envelope's
  byte length and SHA-256 before filing (`queue_service.py`), and
  the agent re-verifies the frame hash against the envelope
  before generating (`trio_agent.py`). A tampered frame is a
  failed result, never an assessment.
- **Output gate:** `validateAssessment` runs before any result
  is written (agent) and before any `/api/assess` response is
  sent (server). An invalid assessment is never written, never
  served, and never silently replaced: agent-side it becomes a
  failed result with the validation errors recorded; server-side
  it is an HTTP 502.
- **Bounded waiting:** the server's queue poll is capped
  (`pollQueueResult` attempts in `server/queue.mjs`), after
  which the logged fallback applies.
- **Secret handling:** `SPARK_API_KEY` is read from the process
  environment only — never from a file, request, or job envelope,
  never printed or logged (`spark_gen.py`, `server/model.mjs`);
  redirects on the API call are refused.

## 9. Sandboxing and governance — partial

What exists in code: single-purpose processes, a namespaced
store (`TRIO_JOB_NS`) shared by exactly the service and the
agent, results writable only at `trio:{jid}:result`, and a
generation step reachable only through the two named transports.
What does not exist: this repo defines no container or VM
sandbox — `run-stack.sh` runs four local processes as the user.
For the demo that is the honest scope; production isolation is
an operations decision, not a claim this codebase makes.

## 10. Observability

Every finished job posts one NOTIFY line to Meta Nuntius (topic
`trio-result`; info with the category on success, warning with
the error on failure — `trio_agent.py`), readable in the relay
viewer (`relay/viewer.html`). Health endpoints name the store
backend honestly — `upstash-redis` vs `local-sqlite-FALLBACK`
(`server/queue/queue_service.py`, `relay/relay.mjs`). The
guardrail state file is a per-call audit log of model, usage,
latency, and estimated cost. Fallbacks and failures are logged
with reasons on stderr by the agent and the server
(`server/assess.mjs`). Not present: third-party tracing tools —
for a four-process stack the NOTIFY feed plus the cost log cover
the audit questions, and no external service sees the data.

## 11. Evaluation discipline — regression suites, not vibe checks

- `npm test`: 1,815 tests (enumerated in `package.json`),
  covering the UI, the server transports with stubbed fetch (no
  live calls), the queue wiring, and the relay.
- `python3 -m unittest discover -s tests/queue-python`: offline
  unittest suite driving the REAL `buildQueueJob` and the REAL
  `validateAssessment` with stubbed generation — envelope
  tamper refusals, guardrail stop-at-budget, exact result shape,
  idempotent no-rebill, the HTTP service end-to-end on the
  fallback store, and the self-correction cases (invalid→valid
  is 2 calls and ok; invalid→invalid is 2 calls and failed;
  valid is exactly 1 call).
- `eval/`: scenario sets whose ground-truth labels were authored
  before any run. `eval/ignis/scenarios.json` (IGN-001..020)
  includes the look-alike negatives this product lives or dies
  on — steam, fog, flame-like lighting, vehicle lights in rain.
  `eval/medicus/scenarios.json` (MED-001..020) includes its
  look-alikes — bench sleeper, sunbather, yoga, curb rest, CPR
  training manikin. Shared scoring: `eval/shared/metrics.mjs`.
- Live proofs are re-run from the repo tree, not the prototype,
  and the spend delta of each proof is counted (the helper's
  `status` before and after: the happy path is exactly +1 call).

## 12. Deliberately absent

- **Tree-search reasoning (Tree of Thoughts / MCTS):** not
  present. The system uses a bounded loop with validation gates
  instead of simulated outcome trees — one frame, one contract,
  one verdict; search would add cost without a decision to spend
  it on.
- **Agent frameworks (LangGraph, CrewAI, AutoGen):** not used.
  The stack is Node and Python standard libraries only —
  `package.json` declares no dependencies — because the loop is
  small enough to read end to end.
- **Transactional / economic agency:** not present. The system
  holds no wallet, signs nothing, buys nothing. The only money
  in the design is the metered API budget, and it is hard-capped
  (section 8).
- **Dynamic tool provisioning:** not present. Each process has a
  fixed, small tool set by construction (section 2).
