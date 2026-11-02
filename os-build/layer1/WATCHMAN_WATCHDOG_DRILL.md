# A3 watchdog drill — the heartbeat of a real relay, stopped

Temp root: `/var/folders/r0/mc2kkvz94f32cfbmq91kj7p40000gn/T/watchdog-drill-kRI67w`

## While the relay runs

- heartbeat file: `{"agent":"watchman","pid":66529,"ts":1793613001041,"iso":"2026-11-02T09:50:01.041Z"}`
- `check` with a 400 ms limit → exit 0, output ""

## After SIGKILL on the relay process (pid 66529)

- `check` → exit 2
- output:

```
ALARM watchman heartbeat lost: last beat 1.0s ago (limit 0.4s, last 2026-11-02T09:50:01.041Z)
```

- `check` again → exit 2, output "" (the same death is not re-announced)

