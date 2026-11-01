# Queue fix, final (NC-020) — what Pax applies to main, in order

Two patch files in oc-proofs/. Neither is applied to server/ (protected).
Both proven on throwaway copies of current origin/main, deleted after.

## 1. queue-mac-optional-import.diff (trio_store.py) — apply first

What: try/except ImportError around the dynamic_credentials import;
missing module degrades to a shared `_MISSING` marker; env-based host
resolution untouched; store calls needing the surrogate raise the
module's own TrioStoreConfigError; mock.patch-based tests keep working
(names stay defined).

Proof (throwaway of origin/main 9e50001, deleted after):
- plain Mac (module absent): pytest 110 passed, 0 failed.
- plain `unittest` runner: 110 tests OK.
- stub dynamic_credentials importable (module-present path):
  pytest 110 passed, 0 failed.
- v2 of this patch failed exactly this third leg (NameError on a
  sentinel that only existed in the except branch); v3 defines the
  marker in both branches. The stub run is what caught it — keep it.

## 2. queue-sparkgen-optional-path.diff (spark_gen.py) — apply second

What: the DEV-helper subprocess PYTHONPATH insertion becomes conditional
(`os.path.isdir` check, prepend instead of clobber). No behavior change
where the skill exists; no dead dir entry and no wiped PYTHONPATH where
it does not. (The helper binary itself was already existence-checked
with a clear error — that needed no patch.)

Proof (same throwaway, both patches applied): pytest 110/110 with and
without the stub module (before: 110/110). Counts unchanged, as expected
— no test invokes the opt-in helper transport.

## Sandbox-path grep (NC-018/019)

| hit | verdict |
|---|---|
| server/queue/trio_store.py:40 hard import | BREAKS on plain Mac — fixed by diff 1 |
| server/queue/spark_gen.py:220 subprocess env | runtime-only, DEV opt-in — softened by diff 2 |
| os/intel + os/tests /opt/relay strings | HARMLESS — guest-image paths with ${VAR:-default} fallbacks; tests pin the defaults; drills rewrite to a local ROOT. Never touched on Mac |
| ~/workspace/... (SPARK_CALL etc.) | HARMLESS — expanduser-relative, portable; guarded by exists() checks |
| js/: no absolute sandbox paths found | clean |

## Environment used for every Section B run (NC-022)

node v24.21.0, python3 system 3.9.6, pytest 8.4.2.
