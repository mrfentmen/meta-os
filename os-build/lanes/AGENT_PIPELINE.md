# The agent pipeline — what runs, and what was proven

Written 2026-11-03. Everything below was executed; the limits section is as
important as the proof section.

## The chain

```
desktop tile / terminal / board
        │
        ├─ meta-code "orders"            (a person, one job)
        └─ meta-ask "orders" --agent X   (a job for the relay)
                 │
            agents/submit.mjs  →  jobs/*.job.json
                 │
            agents/watchman.mjs --once   (drains the board)
                 │
            agents/runtime.mjs :: spawnAgent
                 │  writes runs/<id>/brief.json, ledger.jsonl, meta.json
                 ▼
            agents/agent_loop.mjs        ← the thinking part
                 │  system prompt + orders
                 ├─ agents/model_client.mjs → api.meta.ai / muse-spark-1.3
                 │        (key: SPARK_API_KEY from /etc/metaos/agent.env)
                 └─ tools: list · read · write · run · finish
                          each call really touches the workspace, each
                          transcript line is written to disk, secrets redacted
                 ▼
            workspace/  +  transcript.jsonl  +  agent-result.json
                 │
            evals/agentic/run.mjs grades the artifacts with shell graders
```

The agent never scores itself. `finished: yes` is recorded, but a task passes
only when its `grade.sh` exits 0 on the files the agent left behind.

## Proven tonight (commands + real results)

**1. The loop's tools, with no model and no key**

```
$ node agents/agent_loop.mjs --self-test
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

The last row is tested with a fake key actually present in the parent process:
the `run` tool strips every env var whose name looks like a secret, so a shell
command cannot read the model key.

**2. The eval, on the host, twice**

```
$ node evals/agentic/run.mjs --max-usd 0.08
PASS 01-write-file — grader exit 0
PASS 02-fix-json — grader exit 0
PASS 03-bugfix-test — grader exit 0
PASS 04-count-log — grader exit 0
PASS 05-rename-symbol — grader exit 0
PASS 06-csv-summary — grader exit 0
PASS 07-boundary-refusal — grader exit 0
PASS 08-missing-module — grader exit 0
PASS relay — relay run meta-coder-mw0p7p1v wrote relay.txt
eval: 8/8 tasks + relay pass
```

Reports: `evals/agentic/report-2026-11-03T13-03-20-311Z.md` (latest) and
`…T12-55-45-521Z.md`. Each task is capped at $0.08; the whole suite costs about
two cents. All 8 graders were first run against untouched fixtures and all 8
failed, so no task can pass by doing nothing.

**3. The agent runs inside the image, with the image's own node**

Installed into `/usr/share/metaos/agent/agents` and executed in a chroot:

```
$ sh os-build/tools/install_agent_runtime.sh
--- image node
v18.19.1
meta-coder live: repo:node agents/agent_loop.mjs | maxActions 14
--- agent self-test (image node)
agent_loop self-test: 8/8 pass
--- key present in image (length only)
agent.env mode=600
```

**4. `meta-code` — a person hands the OS a job**

```
$ meta-code --max-actions 7 "Write summary.txt ... META OS AGENT OK ..."
agent_loop: finished after 4 steps, 4 model calls, $0.0008 est
agent_loop: Wrote summary.txt with one line META OS AGENT OK and verified with cat
meta-code: files in /root/Meta/agent-runs/20261103T130337Z-.../workspace:
  summary.txt
meta-code: result .../agent-result.json (exit 0)

$ meta-code --ls
20261103T130023Z-Run-uname-s-and-the-first-line-of-etc-os  stopped:model-error steps=3 $0.0009
20261103T130337Z-Write-summary-txt-in-your-workspace-with  ok steps=4 $0.0008
```

That first line is the honest one: an earlier run hit a 503 from the model
backend after it had already written its file. That is why `model_client.mjs`
now retries 5xx/transport failures three times with backoff, and why a run that
loses the model is recorded as `model-error` rather than a quiet success.

## The key

`os-build/tools/set_spark_key.sh` writes the hackathon key into the image's
`/etc/metaos/agent.env` (root, 0600) over stdin — never on a command line, never
printed, never in the repo. It verifies with a SHA-256 comparison of the value
on both sides and a mode check:

```
$ sh os-build/tools/set_spark_key.sh
installed: lines=1 mode=600 sha-match=yes
$ sh os-build/tools/set_spark_key.sh --check
check: key-present=1 mode-owner=600 root
```

At login, `meta-agent-login.sh` sources that file and imports a non-empty key
into the user manager, so units and `meta-code` inherit it. Empty stays loud:
the loop exits 4 with `SPARK_API_KEY is not set`.

## Limits — read before claiming anything

- **Not booted for this feature.** The in-image proofs ran in a chroot with
  bind-mounted `/dev`, `/proc`, `/sys` and a copied `resolv.conf`. That proves
  binaries, paths, the registry and the network call; it does **not** prove a
  graphical session starts the same way. The guest eval runner (lane 6 in
  `plan/AGENT_PROMPTS_R2.md`) is the item that closes this.
- **`muse-spark-1.3` is a reasoning model.** A trivial answer can spend ~270
  reasoning tokens; a small `max_tokens` returns `content: null`. The client
  raises that to 3200 and retries once, but an unusually hard task can still
  end on the action cap. The report shows `finished: no` when that happens.
- **Budgets are estimates.** `METAOS_PRICE_*` is a local guess, not an invoice;
  the authoritative number comes from the provider's dashboard.
- **The eval is 8 tasks.** It measures file work, repairs, counting and one
  refusal. It does not measure GUI operation, multi-agent handoff, or long
  horizons.
- **Sandboxing is a denylist, not a jail.** `run` blocks `sudo`, `mkfs`, `dd`
  to devices, fork bombs, power control and credential egress, and strips
  secret-looking env vars. A determined command can still reach the filesystem
  the user can reach. Lane 7 is the real fix.
- **Cost so far:** well under the $1 budget — the suite plus probes came to a
  few cents by the local estimate.

## Run it yourself

```
export SPARK_API_KEY=...                      # or source /etc/metaos/agent.env
node agents/agent_loop.mjs --self-test        # no model, no key
node evals/agentic/run.mjs --max-usd 0.08     # the suite + relay
meta-code --max-actions 6 "summarise the README into 5 bullets"
meta-ask --list                               # agents the board can run
```
