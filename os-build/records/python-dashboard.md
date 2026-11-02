# Python dashboard — behaviour record (B221)

Source: `os/intel/devpack.py` (141 lines), the dashboard lane's payload
shaper (DSH-037). The dashboard *page* is static HTML/JS served by
`relay-dashboard.service`; the Python side that this record covers is the
module that turns real producer output into the four panel payloads the
viewer reads. Unit: `os/os/services/relay-dashboard.service` (a stdlib
`http.server` over `/opt/relay`, port 8080).

## What it is

Pure shaping functions plus a loader for the checked-in pack under
`os/intel/devpack/` (`devpack.py:1-27`, `:29-34`). No network, no Redis,
no bus post, no Spark call. `load_pack()` reads the four files named in
`PACK_FILES`; nothing in this module writes (`:127-139`).

## Inputs and outputs

| Function | Input | Output | Where |
|---|---|---|---|
| `brief_entry(record, as_of)` | brief record dict with int `generated_at`; int `as_of` | deep copy + `as_of` + `age_seconds = as_of - generated_at` | `:50-68` |
| `plan_preview(plan, order)` | validated plan dict (`summary`, `jobs[]`), topological `order` | `summary`, `jobs[]` (key, title, files, deps, max_attempts, accept, req), `posting_order`, `budgets{jobs, max_attempts_total}` | `:71-103` |
| `alerts_feed(records)` | iterable of alert records | deep-copied list, newest first by `(created_at, id)` | `:106-115` |
| `crew_board(presence, caps, jobs)` | presence nicks, capability records, `jobs list --json` rows | `{presence, caps, jobs}` deep-copied | `:118-124` |
| `load_pack(directory=None)` | directory or default `intel/devpack` | `{brief, plan_preview, alerts, crew_board}` parsed JSON | `:127-139` |

Record fields are copied verbatim: `brief_entry` adds fields but rewrites
none (`:64-67`), and `plan_preview` copies each job's arrays rather than
aliasing them (`:86-98`).

## Refusals

| Input | Refusal | Where |
|---|---|---|
| `brief_entry`: record not a dict | `ValueError("brief record must be a dict")` | `:50-56` |
| `brief_entry`: `generated_at` not an int, or a bool | `ValueError("brief record needs an int generated_at")` | `:57-62` |
| `brief_entry`: `as_of` not an int, or a bool | `ValueError("as_of must be an int epoch timestamp")` | `:63-65` |
| `plan_preview`: plan not a dict, or `jobs` not a list | `ValueError("plan must be a validated plan dict")` | `:71-75` |
| `plan_preview`: `order` does not cover exactly the job keys | `ValueError("posting order must cover exactly the plan jobs")` | `:76-80` |
| `alerts_feed`: a record is not a dict | `AttributeError` from `.get` — no clean refusal | `:106-115` |
| `alerts_feed`: input is a non-empty dict/str | `AttributeError`/`TypeError` while sorting — no clean refusal | `:106-115` |
| `crew_board`: malformed inputs | no validation; `list()`/deep copy may raise | `:118-124` |
| `load_pack`: a pack file is missing or not JSON | `FileNotFoundError` / `json.JSONDecodeError` — not wrapped | `:127-139` |

## The service side

`relay-dashboard.service` runs `python3 -m http.server 8080 --bind
0.0.0.0 --directory /opt/relay`, `Type=simple`, `Restart=on-failure`
(unit file, `[Service]` block). It serves static files; it has no auth, no
TLS, and no application routes of its own.

## Findings (reported, not fixed)

1. **`plan_preview` can raise `KeyError`, not `ValueError`, for malformed
   jobs.** `job["key"]`, `job["title"]`, `job["files"]`, `job["deps"]`,
   `job["max_attempts"]`, and `job["accept"]` are indexed directly
   (`:85-100`), so a plan that passed the shallow check but lacks a field
   fails with an uncaught `KeyError`.
2. **`alerts_feed` silently invents order for missing fields.** Missing
   `created_at` sorts as 0 and missing `id` as `""` (`:109-113`); a record
   with neither is still returned, so the feed order can be wrong without
   an error. It does not invent field values in the output, only the sort
   key.
3. **`alerts_feed` has no input-type guard.** A non-list iterable of
   non-dicts fails inside `sorted`, unlike `brief_entry` and
   `plan_preview`, which refuse explicitly (`:106-115`).
4. **`crew_board` trusts its three sources.** It copies whatever it is
   given (`:118-124`); the DSH-003 contract ("exactly as the viewer reads
   them") is enforced by the producers and the pack test, not here.
5. **The default pack path is tied to the module's location**
   (`:130-132`), so `load_pack()` from a copied tree reads that tree's
   files, not the installed one. Intended for the repo, worth knowing for
   a packaged install.
