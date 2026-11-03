# Section D — Goose services, third ring and cross-service pairs (R13-076..100)

Run: `python3 os-build/layer1/pair_audit.py` — output committed verbatim at
`os-build/round13/pair_audit.txt`. 25 / 25 addressed, **0 pair contracts exist as
named, 0 pairs runnable**.

## Method

For every pair the list names, three facts are checked independently:

| fact | how | why it is separate |
|---|---|---|
| BOOTABLE | `services/<name>/entry.goose` exists and exports `svc_entry` | a pair test needs two programs that can start |
| IMPORTS | some file in `services/<caller>/` has `import <callee>.` | the matrix is a permission, not evidence of a call |
| MATRIX | `services/callmatrix/callmatrix.goose` sets the callee bit on the caller's row | an import that the matrix denies is a boot failure, not an edge |

`EDGE` = IMPORTS and MATRIX. `DORMANT` = MATRIX only. `NOT_A_SERVICE` = at least one side
does not ship an entry point. Everything else is `DENIED`.

## The finding that decides the section

Only **four** service directories ship an entry point at all:

```
services/bootlog/entry.goose    services/console/entry.goose
services/logd/entry.goose       services/time/entry.goose
```

(plus `services/example`, the template). The other 21 directories the task list treats as
callers and callees are modules: they export functions and are exercised by the driver
programs in `services/tests/`, but they are not bootable programs. A pair of modules is not
a pair of services, and a pair run needs both sides to start. That is why the section is
25 gap records and not 25 passing drills.

This is the same finding Section C recorded from the restart side: nine of ten services
had no process to kill. Two independent sections reaching it from different directions is
the strongest signal in Round 13 — the service layer is a library corpus with four
executables, and every document that calls the 25 directories "services" is describing the
intent, not the artifact.

## Verbatim audit output

```
task      caller       callee       verdict        import   matrix   bootable
R13-076   agenthost    display      NOT_A_SERVICE  no       DENY     n/n
R13-077   audit        dns          NOT_A_SERVICE  no       DENY     n/n
R13-078   board        dock         NOT_A_SERVICE  no       DENY     n/n
R13-079   bootlog      echo         NOT_A_SERVICE  no       DENY     y/n
R13-080   build        fs           NOT_A_SERVICE  no       DENY     n/n
R13-081   callmatrix   heartbeat    NOT_A_SERVICE  no       DENY     n/n
R13-082   console      input        NOT_A_SERVICE  no       DENY     y/n
R13-083   dashboard    logd         NOT_A_SERVICE  no       DENY     n/y
R13-084   devices      logfmt       NOT_A_SERVICE  no       DENY     n/n
R13-085   devmgr       mcp-host     NOT_A_SERVICE  no       DENY     n/n
R13-086   dhcp         net          NOT_A_SERVICE  no       ALLOW    n/n
R13-087   display      netcfg       NOT_A_SERVICE  no       DENY     n/n
R13-088   dns          notify       NOT_A_SERVICE  no       DENY     n/n
R13-089   dock         registry     NOT_A_SERVICE  no       DENY     n/n
R13-090   echo         session      NOT_A_SERVICE  no       DENY     n/n
R13-091   fs           settings     NOT_A_SERVICE  no       DENY     n/n
R13-092   heartbeat    shell        NOT_A_SERVICE  no       DENY     n/n
R13-093   input        socket       NOT_A_SERVICE  no       DENY     n/n
R13-094   logd         sockets      NOT_A_SERVICE  no       DENY     y/n
R13-095   logfmt       storage      NOT_A_SERVICE  no       DENY     n/n
R13-096   mcp-host     supervisor   NOT_A_SERVICE  no       DENY     n/n
R13-097   net          time         NOT_A_SERVICE  no       DENY     n/y
R13-098   netcfg       timesync     NOT_A_SERVICE  no       DENY     n/n
R13-099   notify       updater      NOT_A_SERVICE  no       DENY     n/n
R13-100   registry     wallpaper    NOT_A_SERVICE  no       DENY     n/n

total=25 NOT_A_SERVICE=25
```

## Per-task records

Each record states the contract **as it is**, which for all 25 is: no edge. The evidence
for every row is the audit line above plus the directory check it is derived from. No exit
code is claimed for a side that has no program to exit — `n` in the bootable column is the
absence of that exit code, stated rather than filled in.

| task | pair | contract as found | evidence |
|---|---|---|---|
| R13-076 | agenthost → display | no edge. Neither side boots. agenthost's row (supervisor, audit, session, log, time, storage) has no display bit. | audit line 076; `ls services/agenthost/entry.goose` empty |
| R13-077 | audit → dns | no edge. audit's row is storage, time, log. | audit line 077 |
| R13-078 | board → dock | no edge. board's row is net, storage, log, time, notify. | audit line 078 |
| R13-079 | bootlog → echo | caller boots; callee is a demo program, not a service, and has no id in the matrix. | audit line 079; `echo` absent from `SVC_*` |
| R13-080 | build → fs | no edge. `build` is a codegen tool, not a bootable service. | audit line 080 |
| R13-081 | callmatrix → heartbeat | no edge. `callmatrix` is deliberately outside its own table; `heartbeat` is a demo program. | audit line 081; `NOT_SERVICES` in callmatrix_audit.py |
| R13-082 | console → input | no edge. console's row is bootlog and log only. | audit line 082 |
| R13-083 | dashboard → logd | **permission denied**, and no import: the only pair on the list whose callee boots. dashboard reads log through the log service's *name* (`log`), which the matrix does not map for this caller. | audit line 083 |
| R13-084 | devices → logfmt | no edge. devices' row is log and bootlog. | audit line 084 |
| R13-085 | devmgr → mcp-host | no edge. Neither is in the matrix. | audit line 085 |
| R13-086 | dhcp → net | **matrix allows it; no code makes it.** The one DORMANT pair on the list, and the only row here that is a live permission. dhcp imports `netcfg` (the address model), not `net`. | audit line 086; `grep -n "^import" services/dhcp/*.goose` |
| R13-087 | display → netcfg | no edge. display's row is session and log. | audit line 087 |
| R13-088 | dns → notify | no edge. The notify bit was added to board and updater_client, not to dns. | audit line 088 |
| R13-089 | dock → registry | no edge. `registry` has no id in the matrix at all. | audit line 089 |
| R13-090 | echo → session | no edge. Neither is a bootable service. | audit line 090 |
| R13-091 | fs → settings | no edge. fs's row is storage and log, deliberately short. | audit line 091; matrix comment on `SVC_FS` |
| R13-092 | heartbeat → shell | no edge. heartbeat is a demo program; shell's row does not include it either. | audit line 092 |
| R13-093 | input → socket | no edge. input's row is session, display, log. | audit line 093 |
| R13-094 | logd → sockets | no edge. `sockets` has no id; log's row is console, storage, logfmt, time. | audit line 094 |
| R13-095 | logfmt → storage | no edge. logfmt's row is time. | audit line 095 |
| R13-096 | mcp-host → supervisor | no edge. mcp-host is a demo program, excluded from the table by name. | audit line 096 |
| R13-097 | net → time | no edge on net's row (netcfg, log, devices), though the callee boots. | audit line 097 |
| R13-098 | netcfg → timesync | no edge. netcfg's row is net, storage, log, fs. | audit line 098 |
| R13-099 | notify → updater | no edge. notify's row is log and time by design (a bar that could call back is a bar that can be made to lie). | audit line 099 |
| R13-100 | registry → wallpaper | no edge. Neither side is in the matrix. | audit line 100 |

## The one real pair this section can prove

R13-086 is the only live permission on the list. It is a permission, not a pair: dhcp may
call net, and no dhcp source does. The honest record is a DORMANT finding, filed as such,
not a pair run with invented exit codes.

## What this section cannot claim

- That any pair was exercised end to end, because 21 of 25 named callers or callees have no
  entry point and two of the remaining four are on the wrong side of the matrix.
- That the matrix has no drift. The auditor for that is `os-build/layer1/callmatrix_audit.py`
  and it reports MISSING/DORMANT separately; this section only asks the 25 named questions.
- That the list was wrong to ask. Pairs are the right thing to test once the services boot;
  today the answer is that the thing to test does not exist yet, which is worth knowing
  before anyone writes 25 pair tests against it.
