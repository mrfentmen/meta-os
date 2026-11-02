# Public surface — crates/os-identity (B058)

Every exported name, one line each, with today's usage. "Tests" means the
in-crate `#[cfg(test)]` module (`lib.rs:574-938`); no Rust code outside the
crate references any of these (see `os-identity-callers.md`), so
"production" is "unused" for all of them.

## Constants

| Name | Line | What it is | Used in repo today |
|---|---|---|---|
| `DEFAULT_CAPNS` | 56 | `"muse-bus:cap"` namespace | crate `Default` only |
| `DEFAULT_STALE_AFTER` | 60 | `900` seconds | crate `Default` only |

## Types

| Name | Line | What it is | Used in repo today |
|---|---|---|---|
| `Config` | 64 | namespace + staleness window | tests |
| `Config::capns` | 65 | public field, key prefix | tests |
| `Config::stale_after` | 66 | public field, seconds | tests |
| `Config::from_env` | 82 | reads the two env vars | **unused** (no caller, no test) |
| `Config::key_for` | 98 | `<ns>:<nick>` | tests |
| `Config::index` | 103 | `<ns>:index` | tests |
| `AgentRecord` | 114 | typed hash record | tests |
| `AgentRecord::caps` | 115 | comma-joined caps | tests |
| `AgentRecord::roles` | 116 | optional roles | tests |
| `AgentRecord::max_jobs` | 117 | capacity string | tests |
| `AgentRecord::host` | 118 | writer host | tests |
| `AgentRecord::updated` | 119 | heartbeat seconds | tests |
| `AgentRecord::dm` | 120 | optional DM secret | tests |
| `AgentRecord::info` | 121 | optional note | tests |
| `AgentRecord::from_fields` | 126 | hash fields → record, defaults | tests |
| `AgentRecord::to_fields` | 140 | record → non-empty fields | tests |
| `AgentRecord::cap_set` | 164 | caps string → vec | tests |
| `StoreError` | 178 | `pub String` transport error | tests |
| `StoreError::0` | 178 | public inner string | tests |
| `JobClaim` | 192 | one job's `status`/`claim` | tests |
| `JobClaim::status` | 193 | public field | tests |
| `JobClaim::claim` | 194 | public field | tests |
| `CapStore` | 200 | storage trait | implemented by `MemoryStore` + test doubles |
| `RegisterError` | 221 | validation error enum | tests |
| `RegisterError::NickRequired` | 222 | blank nick | tests |
| `RegisterError::AtLeastOneCapabilityRequired` | 223 | no usable caps | tests |
| `RegistryError` | 242 | validation-or-store error | tests |
| `RegistryError::Validation` | 243 | wraps `RegisterError` | tests |
| `RegistryError::Store` | 244 | wraps `StoreError` | tests |
| `CapabilityRegistry<S>` | 284 | the registry | tests |
| `MemoryStore` | 484 | in-memory `CapStore` | tests |

## Trait methods (`CapStore`)

| Method | Line | Used in repo today |
|---|---|---|
| `hgetall` | 203 | called by `get`; implemented by `MemoryStore` + doubles |
| `hset` | 205 | called by `register`/`touch`; implemented |
| `del` | 207 | called by `unregister`; implemented |
| `zadd` | 209 | called by `register`/`touch`; implemented |
| `zrem` | 211 | called by `unregister`; implemented |
| `zrange` | 214 | called by `agents`; implemented |
| `job_claims` | 216 | called by `active_claims`; implemented |

## Functions

| Name | Line | What it is | Used in repo today |
|---|---|---|---|
| `is_fresh` | 268 | freshness rule | `find_for`, `prune_stale`, tests |

## `CapabilityRegistry` methods

| Method | Line | Used in repo today |
|---|---|---|
| `new` | 293 | tests |
| `store` | 297 | tests |
| `store_mut` | 301 | tests |
| `config` | 305 | **unused** (no caller, no test) |
| `register` | 312 | tests |
| `touch` | 362 | tests |
| `unregister` | 375 | tests |
| `get` | 385 | tests |
| `agents` | 398 | tests |
| `active_claims` | 414 | tests |
| `find_for` | 428 | tests |
| `prune_stale` | 462 | tests |

## `MemoryStore` methods and impl

| Name | Line | Used in repo today |
|---|---|---|
| `new` | 491 | tests |
| `set_jobs` | 496 | tests |
| `put_hash` | 501 | tests |
| `put_index_member` | 509 | tests |
| `CapStore` impl | 517-570 | via the registry in tests |

## Trait impls that matter to callers

| Impl | Line | Note |
|---|---|---|
| `Default for Config` | 69-76 | defaults 56/60 |
| `Display for StoreError` | 180-185 | `store error: <inner>` |
| `Error for StoreError` | 186 | usable in `Box<dyn Error>` |
| `Display for RegisterError` | 226-236 | Python's exact messages |
| `Error for RegisterError` | 237 | |
| `Display for RegistryError` | 247-255 | forwards inner |
| `Error for RegistryError` | 256 | |
| `From<StoreError> for RegistryError` | 258-261 | the only conversion |

## Summary

- Exported names: 2 constants, 8 structs/enums, 1 trait (7 methods),
  1 function, 20 registry/memory methods, 8 trait impls.
- No name is used by production code outside the crate today.
- `Config::from_env` and `CapabilityRegistry::config` have no test and no
  caller; they are the two genuinely unexercised public items.
