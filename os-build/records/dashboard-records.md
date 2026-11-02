# `dashboard` — record shapes, worked examples (B150)

The crate writes nothing to disk. These are the in-memory records it
defines, one real example each, annotated field by field. Values come
from the crate's own fixtures and tests; nothing is invented.

## 1. `BriefPayload` (contract.rs:39-47)

```
BriefPayload {
    id:           "brief:main:1793101200",
    room:         "main",
    kind:         "morning",
    generated_at: 1793101200,
    age_seconds:  900,
    template:     false,
}
```

| Field | Meaning | Rule |
|---|---|---|
| `id` | record identity | must equal `brief:<room>:<generated_at>` |
| `room` | room the brief is for | non-empty |
| `kind` | brief kind | one of `morning`, `onjoin`, `ondemand` |
| `generated_at` | when Spark wrote it | `>= 0` |
| `age_seconds` | age at render | `>= 0`; stale at `>= 7200` |
| `template` | template, not Spark text | `true` renders `TEMPLATE` |

Refusal example: `id = "brief:other:100"` returns
`Err("bad brief id: brief:other:100")`.

## 2. `AlertCard` and the feed (contract.rs:162-173)

Input:

```
[ AlertCard { id: "b", created_at: 1, resolved: false },
  AlertCard { id: "a", created_at: 2, resolved: false },
  AlertCard { id: "r", created_at: 3, resolved: true } ]
```

`alerts_feed` output order: `r` (3), `a` (2), `b` (1).
`addressable_cards` on that feed returns `a` and `b`; `r` is collapsed
to the resolved count.

## 3. `DeepLink` (contract.rs:181-211)

```
parse_deep_link("#intel/brief/1793101200")
  -> Some(DeepLink::Brief("1793101200"))

parse_deep_link("#intel/alert/alert%3A1")
  -> Some(DeepLink::Alert("alert%3A1"))

parse_deep_link("#intel/alert/")
  -> None
```

`resolve_brief_link("1793101200", &[1793101100, 1793101200])`
returns `Some(1793101200)`; an id outside the window returns `None`.

## 4. `TodayCounts` (contract.rs:224-327)

```
TodayCounts {
    jobs_done:       1,
    briefs:          1,
    alerts_fired:    2,
    alerts_resolved: 3,
}
```

Rendered line:

```
today · jobs done 1 · briefs 1 · alerts fired 2 / resolved 3
```

Counting rules for the same record set (fixture `now = 1793102100`):
jobs need `status == "done"` and a same-day `done_at`; briefs are
distinct same-day timestamps across history plus the current brief;
alerts count `created_at` and `resolved_at` independently.

## 5. Error rows (contract.rs:332-349)

```
error_row("brief", TokenRejected)
  -> "No token, or this token can't read brief. Paste a token above to load brief."

error_row("alerts", Unreachable)
  -> "Can't reach the bus store — alerts is paused. The log above is unaffected."
```

## 6. `CrewAlert` and `Ribbon` (contract.rs:438-496)

Input alert:

```
CrewAlert {
    id:         Some("alert:1"),
    kind:       "stall",
    severity:   "critical",
    status:     None,
    resolved_at: None,
    subjects:   ["milo", "42"],
}
```

`alert_ribbon("42", &[alert])` returns:

```
Ribbon {
    text: "critical alert: stall",
    href: Some("bus.html#intel/alert/alert%3A1"),
}
```

A warning, a resolved alert, or a non-matching subject returns
`None`. An alert with `id: None` returns the text with `href: None`.

## 7. `AttemptsBadge` (contract.rs:499-527)

```
attempts_badge(Some("2"), Some("3"))
  -> Some(AttemptsBadge { text: "attempts 2/3", class: "pill attempts warn" })

attempts_badge(Some("3"), Some("3"))
  -> Some(AttemptsBadge { text: "attempts 3/3", class: "pill attempts danger" })

attempts_badge(Some(""), Some("3"))
  -> None
```

## 8. `Artifact` and `ArtifactLink` (contract.rs:567-604)

Input:

```
Artifact {
    path:      Some("jobs/42/report.md"),
    reference: "artifact:42/report.md@v2",
    version:   2,
    sha256:    "…",
}
```

Output:

```
ArtifactLink {
    href:  "jobs/42/report.md",
    label: "report.md v2",
    title: "artifact:42/report.md@v2",
}
```

Dropped inputs: `None`, `/abs.txt`, `../escape.txt`, `jobs//x.txt`,
`""`.

## 9. `LifecycleAlert` and `LifecycleResult` (contract.rs:654-772)

Start record:

```
LifecycleAlert {
    id: "alert:1",
    severity: "critical",
    status: None,
    acknowledged_at: None,
    acknowledged_by: None,
    resolved_at: None,
}
```

`acknowledge_alert(&mut alerts, "alert:1", 1700003700, "rowan")`:

```
LifecycleResult::Acknowledged(LifecycleAlert {
    id: "alert:1",
    severity: "critical",
    status: Some("acknowledged"),
    acknowledged_at: Some(1700003700),
    acknowledged_by: Some("rowan"),
    resolved_at: None,
})
```

Then `resolve_alert(&mut alerts, "alert:1", 1700003800)`:

```
LifecycleResult::Resolved(LifecycleAlert {
    id: "alert:1",
    severity: "critical",
    status: Some("resolved"),
    acknowledged_at: Some(1700003700),
    acknowledged_by: Some("rowan"),
    resolved_at: Some(1700003800),
})
```

The ack stamp survives the resolve, so the record shows the full walk.

## 10. Keyless signing entries (contract.rs:784-852)

`RenameLogEntry { actor: "Mrfentmen", nick: "alice", display: "Alice Cooper" }`:

```
{"v":1,"cmd":"rename","args":{"nick":"alice","display":"Alice Cooper"},"actor":"Mrfentmen"}
```

`NamesHashEntry { display: "Alice Cooper", set_by: "Mrfentmen", set_at: 1758390000 }`:

```
{"display":"Alice Cooper","set_by":"Mrfentmen","set_at":1758390000}
```

`NamesHistoryEntry { nick: "alice", display: "Alice Cooper", set_by: "Mrfentmen", set_at: 1758390000 }`:

```
{"nick":"alice","display":"Alice Cooper","set_by":"Mrfentmen","set_at":1758390000}
```

No `sig` key appears in any of the three; renames are keyless.
