# NB-011 — queue suite Mac diagnosis: exact error text

Command: `python3 -m pytest tests/queue-python/ -q` from a plain Mac checkout.

```
ERROR tests/queue-python/test_supervisor.py
ERROR tests/queue-python/test_queue.py
ERROR tests/queue-python/test_evidence.py
ERROR tests/queue-python/test_crew.py
!!!!!!!!!!!!!!!!!!! Interrupted: 4 errors during collection !!!!!!!!!!!!!!!!!!!!
4 errors in 0.20s
```

Each error is the same root traceback (shown here for test_queue.py,
the other three are identical apart from the file name):

```
File "tests/queue-python/test_queue.py", line 14, in <module>
    import trio_store
File "server/queue/trio_store.py", line 41, in <module>
    from dynamic_credentials import (  # noqa: E402
ModuleNotFoundError: No module named 'dynamic_credentials'
```

unittest fallback collects 29 tests (25 pass) because it only imports
the modules it can; pytest aborts the whole directory on the 4 bad ones.
Either way the 4 modules importing `trio_store` never run on this Mac.

## NB-012 root cause (one paragraph)

`server/queue/trio_store.py` line 41 does an unconditional
`from dynamic_credentials import ...` after inserting the absolute path
`/opt/muse/skills/custom-connector-setup/bin` into `sys.path`. That path
exists in the sandbox layout and on no plain Mac checkout, so importing
`trio_store` raises `ModuleNotFoundError` before any code runs — taking
down `queue_service.py`, `trio_agent.py`, and the 4 test modules that
import it at top level. The module's own design already expects a missing
host (env-first `TRIO_UPSTASH_HOST` resolution with a config error); only
the import is unconditional.

## NB-013 fix (patch file, not applied to server/)

`oc-proofs/queue-mac-optional-import.diff` (v2): wraps the import in
try/except ImportError. When the module is missing, the three names stay
defined as stubs that raise the module's own `TrioStoreConfigError`, so
imports, collection, and mock.patch-based tests keep working; env-first
host resolution is untouched (identity check skips the stub when a test
patches it). The store call path raises the config error with an
actionable message instead of NameError. No behavior change where the
module exists.
Apply on a throwaway copy only: `patch -p1 < oc-proofs/queue-mac-optional-import.diff`
Proved: applied on a throwaway worktree of origin/main — 110 passed, 0 failed
(v1 of the patch got 108+2 because the names vanished entirely and two
tests mock them; v2 keeps the names as stubs).

## NB-015 same-risk grep

Only other reference: `server/queue/spark_gen.py` sets that
`/opt/muse/...` path into a subprocess `PYTHONPATH` for the DEV helper
transport (runtime only, never imported) — no collection risk. No other
suite imports the module. Nothing else at risk.
