# B3 bridge drill — three agents, three outcomes

Root: `/var/folders/r0/mc2kkvz94f32cfbmq91kj7p40000gn/T/bridge-drill-Pvdz5k`

## Boot

- started `worker` run `worker-mvz2xk0g`
- started `runner` run `runner-mvz2xk0k`
- started `stoppable` run `stoppable-mvz2xk0l`

## Outcomes

- `worker`: state **stopped**, exit code 0, stopped `—`
- `runner`: state **stopped**, exit code null, stopped `budget-wall-clock`
- `stoppable`: state **stopped**, exit code null, stopped `bridge:drill`
- worker artifact: `done.txt` = "finished"

## bridge.jsonl (the three runs)

```jsonl
{"ts":"2026-11-02T09:51:43.503Z","run":"bridge","event":"start-request","agent":"worker"}
{"ts":"2026-11-02T09:51:43.507Z","run":"worker-mvz2xk0g","event":"started","agent":"worker"}
{"ts":"2026-11-02T09:51:43.508Z","run":"bridge","event":"start-request","agent":"runner"}
{"ts":"2026-11-02T09:51:43.509Z","run":"runner-mvz2xk0k","event":"started","agent":"runner"}
{"ts":"2026-11-02T09:51:43.509Z","run":"bridge","event":"start-request","agent":"stoppable"}
{"ts":"2026-11-02T09:51:43.510Z","run":"stoppable-mvz2xk0l","event":"started","agent":"stoppable"}
{"ts":"2026-11-02T09:51:43.541Z","run":"worker-mvz2xk0g","event":"exited","agent":"worker","code":0,"signal":null,"state":"stopped","stopped":null}
{"ts":"2026-11-02T09:51:43.631Z","run":"bridge","event":"stop-request","agent":"stoppable","reason":"drill"}
{"ts":"2026-11-02T09:51:43.634Z","run":"stoppable-mvz2xk0l","event":"exited","agent":"stoppable","code":null,"signal":"SIGTERM","state":"stopped","stopped":"bridge:drill"}
{"ts":"2026-11-02T09:51:43.812Z","run":"runner-mvz2xk0k","event":"exited","agent":"runner","code":null,"signal":"SIGTERM","state":"stopped","stopped":"budget-wall-clock"}
```

## Per-run ledgers

- `worker` run `worker-mvz2xk0g`: spawn, exit
- `runner` run `runner-mvz2xk0k`: spawn, stop-request, exit
- `stoppable` run `stoppable-mvz2xk0l`: spawn, stop-request, exit

Verdict: one run completed on its own (exit 0), one was stopped by its wall-clock budget,
one was stopped by a filed STOP — each recorded by the runtime and mapped to a supervisor
state by the bridge, with no state the supervisor does not have.
