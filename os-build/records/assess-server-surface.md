# crates/assess-server — public surface inventory (B142)

`crates/assess-server/Cargo.toml:6-8` declares a `[[bin]]` and there is no
`src/lib.rs`. **Every `pub` item below is therefore crate-private in practice:
no other crate can link this package.** "Used" means referenced inside this
crate (including its tests); "external" is the honest column, and it is none
for all of them. This is the largest structural finding in the crate: the
public surface is a documentation promise the package cannot keep.

| Item | Line | One-line purpose | Used in crate | External caller |
|---|---|---|---|---|
| `MAX_IMAGE_BYTES` | 23 | 8 MiB decoded-frame cap | yes (119) | none |
| `MAX_BODY_BYTES` | 24 | 12 MiB request-envelope cap | yes (735) | none |
| `QUEUE_JOB_VERSION` | 25 | job envelope version `1` | yes (207, 350) | none |
| `QUEUE_JOB_KIND` | 26 | job kind `trio-assessment` | yes (207, 351) | none |
| `QUEUE_RESULT_VERSION` | 27 | result envelope version `1` | yes (277) | none |
| `QUEUE_RESULT_KIND` | 28 | result kind `trio-assessment-result` | yes (279) | none |
| `QUEUE_POLL_INTERVAL_MS` | 29 | default poll sleep, 1000 ms | yes (562) | none |
| `QUEUE_POLL_MAX_ATTEMPTS` | 30 | default poll bound, 30 | yes (563) | none |
| `SPARK_ENDPOINT` (re-export) | 32 | default model URL | **no** — the body uses `guardrail::SPARK_ENDPOINT` (475) | none |
| `SPARK_MODEL` (re-export) | 32 | default model id | **no** — the body uses `guardrail::SPARK_MODEL` (447) | none |
| `is_product_id` | 34 | three-product check | yes (140, 195) | none |
| `is_valid_iso8601` | 51 | strict timestamp parser | yes (145) | none |
| `parse_image_data_url` | 110 | JPEG data-URL decode + magic/cap checks | yes (148) | none |
| `ValidInput` | 129 | validated request value | yes (136, 429, 576) | none |
| `validate_assess_request` | 136 | collect every request error | yes (577) | none |
| `QueueError` | 168 | typed queue refusal (`code`, `message`) | yes (194-399, 600-611) | none |
| `QueueConfig` | 179 | enabled + URL pair | yes (340, 359, 584) | none |
| `queue_config_enabled` | 184 | construct a `QueueConfig` | **no** — dead; `handle_assess` builds the struct directly (584) | none |
| `build_queue_job_id` | 190 | alias to `queue_core::deterministic_job_id` | yes (204) | none |
| `build_queue_job` | 194 | build the v1 job envelope | yes (586) | none |
| `http_queue_post` | 223 | POST `/jobs`, return the filed id | yes (556) | none |
| `http_queue_get` | 238 | GET `/jobs/{id}/result`, 404→pending | yes (557) | none |
| `QueueResult` | 254 | pending / done / failed enum | yes (265-399, 588-610) | none |
| `parse_queue_result_envelope` | 265 | normalise both accepted shapes | yes (369) | none |
| `submit_queue_job` | 340 | refuse layers, then post | yes (589) | none |
| `fetch_queue_result` | 359 | refuse layers, then fetch+parse | yes (377) | none |
| `poll_queue_result` | 373 | bounded poll loop | yes (590) | none |
| `ModelError` | 401 | typed model refusal | yes (420-505, 549, 613) | none |
| `ModelConfig` | 411 | key-present + live-enabled pair | **no** — dead; `model_status` takes two bools (416) | none |
| `model_status` | 416 | `{configured, live_enabled}` | yes (773, 801) | none |
| `build_spark_prompt` | 420 | product profile → prompt | yes (441) | none |
| `assess_with_model` | 429 | the only model call path, with refusal layers | yes (550) | none |
| `Env` | 507 | process configuration snapshot | yes (532, 576, 696) | none |
| `Deps` | 532 | injectable transports/timing/log | yes (553, 576) | none |
| `default_deps` | 553 | production wiring | yes (804) | none |
| `handle_assess` | 576 | the `/api/assess` decision table | yes (770) | none |
| `ServerDeps` | 696 | env + deps + doc root | yes (800, 702) | none |

## Unused names, explicitly

- `queue_config_enabled` (184) — zero call sites.
- `ModelConfig` (411) — zero constructions; `model_status` bypasses it.
- The `SPARK_ENDPOINT`/`SPARK_MODEL` re-export (32) — both call sites name the
  guardrail path directly, so the re-export is not what supplies them.

## Consequence

Because the package has no library target:

- `cargo test -p assess-server` can only run the `#[cfg(test)]` module inside
  `main.rs` (813+). Integration tests under `tests/` cannot `use assess_server`.
- `cargo doc -p assess-server` documents the binary, not a linkable API.
- Any future consumer (a router, a stack binary) must either add a `src/lib.rs`
  and move the code, or spawn the binary as a process. Neither exists today.

`assess-server-callers.md` records that no in-repo Rust caller exists, which is
consistent with this inventory rather than a separate defect.
