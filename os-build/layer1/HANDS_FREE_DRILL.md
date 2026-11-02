# C drill — inbox to brief, with the boss's word in the ledger

Root: `/var/folders/r0/mc2kkvz94f32cfbmq91kj7p40000gn/T/handsfree-drill-lKOS8k`

## 1. The inbox

```
# tonight
worker: sweep the board
runner: check the gate
stopper: wait for the boss
this line is not an order
```
- orders taken: 3 (`worker-20261102095339-0`, `runner-20261102095339-1`, `stopper-20261102095339-2`)
- lines refused and left in the inbox: 1 → `this line is not an order`

## 2. The runs

- `runner-20261102095339-1` → run `runner-mvz301k2`
- `stopper-20261102095339-2` → run `stopper-mvz301k6`
- `worker-20261102095339-0` → run `worker-mvz301k7`
- STOP filed for `stopper`; `runner` has a 300 ms wall-clock budget

## 3. The brief (speakable, verbatim)

```
3 orders ran.
1 finished, 2 stopped, 0 failed.
runner was stopped.
stopper was stopped.
worker finished.
```

## 4. The approval

- request: "send the sweep report"
- answer: `yes` by `boss` at `2026-11-02T09:53:39.867Z`
- ledger line: `{"ts":"2026-11-02T09:53:39.868Z","run":"worker-mvz301k7","event":"approval","decision":"yes","by":"boss","at":"2026-11-02T09:53:39.867Z","what":"send the sweep report"}`

Verdict: the inbox is text, the jobs are the watchman's own files, the brief is one block with
numbers first, and the yes is in the run's append-only ledger rather than beside it.
