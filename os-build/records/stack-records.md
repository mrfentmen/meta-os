# `crates/stack` — worked record shapes (B198)

The crate writes no files. These are the in-memory records it returns,
one real example each, annotated field by field. Values are what
`plan(&StackConfig::from_entries(&[]))` produces.

## 1. `Transport::ProductionDirect`

```rust
Transport::ProductionDirect
```

| Field | Value | Meaning |
|---|---|---|
| variant | `ProductionDirect` | `SPARK_API_KEY` was present and non-empty (`src/lib.rs:117-121`) |
| `dev_helper_warning()` | `false` | no warning line is due (`src/lib.rs:59-63`) |

## 2. `Transport::DevHelper`

```rust
Transport::DevHelper
```

| Field | Value | Meaning |
|---|---|---|
| variant | `DevHelper` | key missing or empty in the code; the script's third state is not represented (G1) |
| `dev_helper_warning()` | `true` | the caller should print the DEV warning |

## 3. `Readiness::HttpHealth` (relay)

```rust
Readiness::HttpHealth {
    url: "http://127.0.0.1:8787/health".to_string(),
    max_attempts: 50,
    interval_ms: 200,
    timeout_secs: 2,
}
```

| Field | Value | Source |
|---|---|---|
| `url` | relay base + `/health` | `src/lib.rs:191`; script `run-stack.sh:75` |
| `max_attempts` | `50` | `src/lib.rs:39`; `seq 1 50` at `run-stack.sh:62` |
| `interval_ms` | `200` | `src/lib.rs:41`; `sleep 0.2` at `run-stack.sh:68` |
| `timeout_secs` | `2` | `src/lib.rs:43`; `curl -m 2` at `run-stack.sh:63` |

## 4. `Readiness::ProcessAlive` (resident agent)

```rust
Readiness::ProcessAlive
```

| Field | Value | Meaning |
|---|---|---|
| variant | `ProcessAlive` | no HTTP endpoint; settle and check the PID (`src/lib.rs:73-78`) |
| settle | `AGENT_SETTLE_SECS = 1` | `src/lib.rs:45`; `sleep 1` at `run-stack.sh:86` |

## 5. `Service` (queue service, job namespace exported)

```rust
Service {
    name: "queue service",
    argv: vec!["python3".into(), "queue_service.py".into(), "--port".into(), "8935".into()],
    cwd: "server/queue",
    env: vec![("TRIO_JOB_NS".into(), "scratch-7".into())],
    readiness: Readiness::HttpHealth { /* queue base + /health */ },
}
```

| Field | Value | Source |
|---|---|---|
| `name` | `queue service` | `src/lib.rs:194`; script `run-stack.sh:78` |
| `argv` | `python3 queue_service.py --port 8935` | `src/lib.rs:195-200`; script `run-stack.sh:79` |
| `cwd` | `server/queue` | `src/lib.rs:201` |
| `env` | only `TRIO_JOB_NS`, when exported | `src/lib.rs:202`, `176-184` |
| `readiness` | HTTP GET `http://127.0.0.1:8935/health` | `src/lib.rs:203` |

## 6. `StackConfig` (custom ports, pending job namespace)

```rust
StackConfig {
    relay_port: "9000".into(),
    queue_port: "9001".into(),
    app_port: "9002".into(),
    transport: Transport::DevHelper,
    job_ns: Some("scratch-7".into()),
}
```

| Field | Value | Source |
|---|---|---|
| `relay_port` | `9000` (non-empty env wins) | `src/lib.rs:131` |
| `queue_port` | `9001` | `src/lib.rs:133` |
| `app_port` | `9002` | `src/lib.rs:135` |
| `transport` | `DevHelper` when no key | `src/lib.rs:136` |
| `job_ns` | `Some("scratch-7")`; `Some("")` is kept as an exported empty value | `src/lib.rs:137` |

## 7. Summary lines record

```text
  Meta Nuntius viewer   http://127.0.0.1:8787/
  Queue service         http://127.0.0.1:8935/health
  Resident agent        running (NOTIFY -> http://127.0.0.1:8787/rooms/main)
  Web console + API     http://127.0.0.1:8080/  (POST http://127.0.0.1:8080/api/assess)
```

| Line | Substituted value | Source |
|---|---|---|
| 1 | relay base | `src/lib.rs:237`; script `run-stack.sh:98` |
| 2 | queue base | `src/lib.rs:238`; script `run-stack.sh:99` |
| 3 | relay base in the NOTIFY arrow | `src/lib.rs:239-242`; script `run-stack.sh:100` |
| 4 | app base twice | `src/lib.rs:243-246`; script `run-stack.sh:101` |
